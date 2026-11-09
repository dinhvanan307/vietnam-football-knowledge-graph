"""Nhập snapshot vào Neo4j cục bộ, kiểm tra ID/bằng chứng và chạy degree."""
import argparse
import json
import os
import shutil
from collections import defaultdict
from pathlib import Path
from neo4j import GraphDatabase
from ban_giao import jlines, table, verify

def queries(path):
    source="\n".join(line for line in path.read_text().splitlines() if not line.lstrip().startswith("//"))
    return [s.strip() for s in source.split(";") if s.strip()]

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("bundle",type=Path);a=p.parse_args()
    verify(a.bundle,False,True)
    entities=table(a.bundle/"entities.csv");facts=table(a.bundle/"facts.csv")
    expected_nodes={r["entity_id"] for r in entities}
    expected_facts={r["fact_id"]:r for r in facts}
    arts={r["article_id"]:r for r in jlines(a.bundle/"articles.jsonl")}
    evidence={r["evidence_id"]:r for r in jlines(a.bundle/"evidence.jsonl")}
    for f in facts:
        e=evidence[f["evidence_id"]];art=arts[e["article_id"]]
        if (f["quote"],f["article_url"],f["article_id"])!=(e["quote"],art["canonical_url"],art["article_id"]):
            raise ValueError("Thông tin dẫn nguồn sai: "+f["fact_id"])
    all_ev=defaultdict(list)
    for e in evidence.values():all_ev[e["fact_id"]].append(e["evidence_id"])
    metadata_path=a.bundle/"event_attributes.jsonl"
    extras={r["fact_id"]:r for r in jlines(metadata_path)} if metadata_path.exists() else {}
    patches=[]
    for f in facts:
        e=evidence[f["evidence_id"]]
        meta={k:v for k,v in extras.get(f["fact_id"],{}).items() if k!="fact_id"}
        meta.update(evidence_start=e["start"],evidence_end=e["end"],evidence_ids=sorted(all_ev[f["fact_id"]]))
        if "context_start" in e:
            meta["evidence_context"]=arts[e["article_id"]]["clean_text"][e["context_start"]:e["context_end"]]
        patches.append(dict(src=f["src_id"],dst=f["dst_id"],fid=f["fact_id"],meta=meta))
    pw=os.environ.get("NEO4J_PASSWORD") or dict(line.split("=",1) for line in Path(".env").read_text().splitlines() if "=" in line)["NEO4J_PASSWORD"]
    with GraphDatabase.driver("bolt://127.0.0.1:7687",auth=("neo4j",pw)) as driver, driver.session(database="neo4j") as session:
        driver.verify_connectivity()
        old={r["id"] for r in session.run("MATCH (n:Entity) RETURN n.entity_id AS id")}
        old_facts={r["id"] for r in session.run("MATCH (:Entity)-[r]->(:Entity) RETURN r.fact_id AS id")}
        if not old<=expected_nodes or not old_facts<=set(expected_facts):
            raise ValueError("DB có dữ liệu ngoài snapshot; dùng project/volume mới.")
        for name in ("entities.csv","facts.csv"):
            temp=Path("real-import")/(name+".part")
            shutil.copyfile(a.bundle/name,temp);temp.replace(Path("real-import")/name)
        commands=queries(Path("cypher/02_import_real.cypher"))
        session.run(commands[0]).consume()
        counts=[]
        for _ in range(2):
            with session.begin_transaction() as tx:
                for command in commands[1:]:tx.run(command).consume()
                for i in range(0,len(patches),800):
                    n=tx.run("""UNWIND $batch AS x MATCH (s:Entity {entity_id:x.src})-[r]->(d:Entity {entity_id:x.dst})
                      WHERE r.fact_id=x.fid SET r += x.meta RETURN count(r) AS n""",batch=patches[i:i+800]).single()["n"]
                    if n!=len(patches[i:i+800]):raise ValueError("Thiếu cạnh khi bổ sung bằng chứng.")
                tx.commit()
            node_ids={r["id"] for r in session.run("MATCH (n:Entity) RETURN n.entity_id AS id")}
            rows=session.run("""MATCH (s:Entity)-[r]->(d:Entity) RETURN s.entity_id AS src_id,type(r) AS relation_type,
            d.entity_id AS dst_id,r.fact_id AS fact_id,r.article_url AS article_url,r.quote AS quote,r.event_key AS event_key,
            r.evidence_id AS evidence_id,r.period AS period,r.method AS method,r.article_id AS article_id,r.status AS status""").data()
            if node_ids!=expected_nodes or len(rows)!=len(expected_facts) or {r["fact_id"] for r in rows}!=set(expected_facts):
                raise ValueError("Số dòng hoặc định danh Neo4j khác CSV.")
            for row in rows:
                fact=expected_facts[row["fact_id"]]
                if any(fact[k]!=v for k,v in row.items()):raise ValueError("Sai dữ liệu sau import: "+row["fact_id"])
            counts.append({"nodes":len(node_ids),"edges":len(rows),"types":len({r["relation_type"] for r in rows})})
        result={"import_runs":counts}
        result["neo4j"]=session.run("CALL dbms.components() YIELD name, versions WHERE name='Neo4j Kernel' RETURN versions[0] AS version").single(strict=True)["version"]
        result["gds"]=session.run("RETURN gds.version() AS v").single()["v"]
        projection="football_pilot_"+os.urandom(5).hex()
        graph_q,degree_q,check_q=queries(Path("cypher/04_degree.cypher"))
        proj=session.run(graph_q.replace("d22_aff_rc01",projection)).single()
        try:
            degree=session.run(degree_q.replace("d22_aff_rc01",projection)).data()
            cypher=session.run(check_q).data()
            if {r["id"]:r["score"] for r in degree}!={r["id"]:r["degree_check"] for r in cypher}:
                raise ValueError("Kết quả GDS và Cypher không khớp.")
            result.update(projection_nodes=proj["nodes"],projection_relationships=proj["projected_relationships"],club_degree=degree)
        finally:
            session.run("CALL gds.graph.drop($name) YIELD graphName RETURN graphName",name=projection).consume()
    (a.bundle/"neo4j_check.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps(result,ensure_ascii=False))
if __name__=="__main__":main()
