"""Hai lượt nhập A3 trên DB riêng. Đối chiếu toàn bộ thuộc tính sau từng lần commit."""
import argparse
import json
import shutil
from collections import defaultdict
from pathlib import Path

from neo4j import GraphDatabase
from bongda.core.ban_giao import idx, jlines, table, verify
from bongda.storage.kiem_tra_neo4j_a3 import fingerprint
from bongda.storage.nhap_neo4j import queries


def payload(root, facts):
    evidence = idx(jlines(root / "evidence.jsonl"), "evidence_id")
    articles = idx(jlines(root / "articles.jsonl"), "article_id")
    attrs = idx(jlines(root / "event_attributes.jsonl"), "fact_id")
    all_ids = defaultdict(list)
    for e in evidence.values():
        all_ids[e["fact_id"]].append(e["evidence_id"])
    rows = []
    for fid, f in facts.items():
        primary = evidence[f["evidence_id"]]
        meta = dict(attrs.get(fid, {}))
        meta.pop("fact_id", None)
        meta.update(evidence_start=primary["start"], evidence_end=primary["end"], evidence_ids=sorted(all_ids[fid]))
        if "context_start" in primary:
            text = articles[primary["article_id"]]["clean_text"]
            meta["evidence_context"] = text[primary["context_start"]:primary["context_end"]]
        rows.append(dict(src=f["src_id"], dst=f["dst_id"], id=fid, meta=meta))
    return rows


def compare(session, nodes, facts, batches):
    seen = set()
    for r in session.run("MATCH (n) RETURN n.entity_id AS id, labels(n) AS labels, properties(n) AS p"):
        n = nodes[r["id"]]
        props = dict(entity_id=r["id"], name=n["canonical_name"], kind=n["type"], role=n["role"])
        if r["id"] in seen or set(r["labels"]) != {"Entity", n["type"]} or r["p"] != props:
            raise ValueError("Sai node: " + r["id"])
        seen.add(r["id"])
    if seen != nodes.keys():
        raise ValueError("Thiếu node.")
    meta_by_id = {p["id"]: p["meta"] for p in batches}
    seen = set()
    for r in session.run("""MATCH (s)-[r]->(d) RETURN s.entity_id AS s, d.entity_id AS d,
                         type(r) AS t, r.fact_id AS id, properties(r) AS p"""):
        fid = r["id"]
        f = facts[fid]
        props = {k:v for k, v in f.items() if k not in {"src_id", "dst_id", "relation_type"}}
        props.update(meta_by_id[fid])
        if fid in seen or r["p"] != props or (r["s"], r["t"], r["d"]) != (f["src_id"], f["relation_type"], f["dst_id"]):
            raise ValueError("Sai cạnh: " + fid)
        seen.add(fid)
    if seen != facts.keys():
        raise ValueError("Thiếu cạnh.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path)
    root = parser.parse_args().snapshot
    if not (root / "audit_a3.json").is_file() or root.resolve() == Path("work/a2_final").resolve():
        raise ValueError("Chỉ nhập snapshot A3.")
    verify(root, False, True)
    nodes = idx(table(root / "entities.csv"), "entity_id")
    facts = idx(table(root / "facts.csv"), "fact_id")
    batch = payload(root, facts)
    pw = dict(s.split("=", 1) for s in Path(".env").read_text().splitlines() if "=" in s)["NEO4J_PASSWORD"]
    uri = "bolt://127.0.0.1:7689"
    path = Path("work/a3_import")
    path.mkdir(exist_ok=True)
    commands = queries(Path("cypher/02_import_real.cypher"))
    with GraphDatabase.driver(uri, auth=("neo4j", pw)) as driver, driver.session(database="neo4j") as db:
        driver.verify_connectivity()
        before = fingerprint(db)
        if before["nodes"] or before["edges"]:
            # Chỉ chấp nhận chạy lại trên đúng snapshot đang có.
            compare(db, nodes, facts, batch)
        for name in ("facts.csv", "entities.csv"):
            temp = path / (name + ".part")
            shutil.copyfile(root / name, temp)
            temp.replace(path / name)
        db.run(commands[0]).consume()
        results = []
        for run in (1, 2):
            created = [0, 0]
            with db.begin_transaction() as tx:
                for query in commands[1:]:
                    counters = tx.run(query).consume().counters
                    created[0] += counters.nodes_created
                    created[1] += counters.relationships_created
                for i in range(0, len(batch), 800):
                    rows = batch[i:i + 800]
                    n = tx.run("""UNWIND $rows AS x MATCH (s:Entity {entity_id:x.src})-[r]->(d:Entity {entity_id:x.dst})
                                  WHERE r.fact_id=x.id SET r += x.meta RETURN count(r) AS n""", rows=rows).single(strict=True)["n"]
                    if n != len(rows):
                        raise ValueError("Số cạnh ghi metadata không khớp.")
                tx.commit()
            compare(db, nodes, facts, batch)
            result = fingerprint(db)
            result.update(run=run, created_nodes=created[0], created_edges=created[1])
            results.append(result)
        if results[0]["graph_sha256"] != results[1]["graph_sha256"] or any((results[1]["created_nodes"], results[1]["created_edges"])):
            raise ValueError("Lần nhập thứ hai thay đổi graph.")
        version = db.run("CALL dbms.components() YIELD name,versions WHERE name='Neo4j Kernel' RETURN versions[0] AS v").single()["v"]
        result = dict(uri=uri, database="neo4j", project="vietnam_football_a3", neo4j=version, before=before, import_runs=results,
                      full_property_comparison=True)
        output = root / "neo4j_check.json"
        # Bảo toàn biên bản lượt nhập đầu tiên từ DB rỗng khi người dùng chạy lại.
        if output.exists():
            output = root / "neo4j_recheck.json"
        output.write_text(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2) + "\n")
        print(json.dumps(results, ensure_ascii=False))


if __name__ == "__main__":
    main()
