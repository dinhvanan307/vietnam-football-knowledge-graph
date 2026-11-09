"""Dựng A3 từ các fact và bằng chứng đã đóng băng trong A2."""
import argparse
import json
import shutil
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

import mwparserfromhell as mw
from ban_giao import enc, idx, jlines, sha, table, verify
from doc_bien_ban import BOX_NAMES, item, param, position
from quy_tac_a3 import HISTORICAL, SOURCES, club_decision, roster_decision
from trich_quan_he import write_csv

A2 = Path("work/a2_final")
A2_HASH = "06325b399bc0ef82f3553d6bf878289e6207d4942fe115735927616ac2144f62"
MATCH_METHODS = {"wiki_match_result", "wiki_match_event", "wiki_match_venue"}


def json_out(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, sort_keys=True, indent=2) + "\n")


def lines(path, records):
    path.write_text("".join(enc(r) + "\n" for r in records))


def hashed(prefix, values):
    return prefix + sha(enc(values).encode())[:20]


def span(e):
    return e["article_id"], e["start"], e["end"]


def match_index(evidence, facts, attrs, articles):
    matches = {}
    scores = defaultdict(set)
    for e in evidence:
        f = facts[e["fact_id"]]
        if f["method"] != "wiki_match_result":
            continue
        home, away = f["src_id"], f["dst_id"]
        _, league, season = articles[e["article_id"]]["story_group"].split(":")
        box = next(t for t in mw.parse(e["quote"]).filter_templates()
                   if str(t.name).strip().casefold() in BOX_NAMES)
        resolved = {}
        reasons = []
        for old, names in ((home, ("team1", "đội 1")), (away, ("team2", "đội 2"))):
            label = item(param(box, *names))["name"]
            resolved[old], reason = club_decision(old, label, season, league)
            if reason:
                reasons.append(reason)
        key = None
        if all(resolved.values()) and resolved[home] != resolved[away]:
            key = ":".join([f["period"], resolved[home], resolved[away]])
            scores[key].add(attrs[f["fact_id"]]["score"])
        else:
            reasons.append("chua_ro_hai_doi")
        matches[span(e)] = (resolved, key, reasons)
    return matches, {key for key, observed in scores.items() if len(observed) > 1}


def build(out):
    if sha((A2 / "checksums.json").read_bytes()) != A2_HASH:
        raise ValueError("Sai bản nguồn A2.")
    for name, digest in json.loads((A2 / "checksums.json").read_bytes()).items():
        if sha((A2 / name).read_bytes()) != digest:
            raise ValueError("Checksum A2 sai: " + name)
    verify(A2, False, True)
    for name in ("manifest.json", "articles.jsonl", "source_index.jsonl", "article_event_map.tsv",
                 "event_groups.jsonl", "identity_review.jsonl", "facts_identity_review.jsonl"):
        shutil.copyfile(A2 / name, out / name)
    shutil.copytree(A2 / "raw", out / "raw")
    entities = idx(table(A2 / "entities.csv"), "entity_id")
    registry = idx(jlines(A2 / "entity_resolution.jsonl"), "entity_id")
    articles = idx(jlines(A2 / "articles.jsonl"), "article_id")
    facts = idx(table(A2 / "facts.csv"), "fact_id")
    evidence = jlines(A2 / "evidence.jsonl")
    attrs = idx(jlines(A2 / "event_attributes.jsonl"), "fact_id")
    matches, conflicts = match_index(evidence, facts, attrs, articles)
    for entity_id, (name, url) in HISTORICAL.items():
        entities[entity_id] = dict(entity_id=entity_id, type="Club", canonical_name=name, role="Club")
        registry[entity_id] = dict(entity_id=entity_id, basis="historical_club", source_url=url)
    records = {}
    priority = {}
    new_ev = {}
    new_attrs = {}
    venue_matches = defaultdict(set)
    staff_seasons = defaultdict(set)
    decisions = []
    replacements = defaultdict(set)
    reasons_by_id = defaultdict(set)
    parents = defaultdict(set)
    for e in evidence:
        old = e["fact_id"]
        f = facts[old]
        art = articles[e["article_id"]]
        src, dst, event = f["src_id"], f["dst_id"], f["event_key"]
        method = f["method"]
        reasons = []
        match = None
        if method in MATCH_METHODS:
            remap, match, match_reasons = matches[span(e)]
            reasons.extend(match_reasons)
            src, dst = remap.get(src, src), remap.get(dst, dst)
            if not match or match in conflicts:
                dst = None
                if match in conflicts:
                    reasons.append("mau_thuan_ti_so")
            elif method != "wiki_match_venue":
                event = match
        elif method == "wiki_roster_row":
            dst, why = roster_decision(f, art, e)
            if why:
                reasons.append(why)
        elif method == "wiki_staff_table":
            _, league, season = art["story_group"].split(":")
            label = mw.parse(e["quote"].splitlines()[0].lstrip("| ")).strip_code()
            dst, why = club_decision(dst, label, season, league)
            if why:
                reasons.append(why)

        fid = eid = None
        if src and dst:
            key = [src, f["relation_type"], dst, event]
            fid = old if key == [f["src_id"], f["relation_type"], f["dst_id"], f["event_key"]] else hashed("f_", key)
            eid = e["evidence_id"] if fid == old else hashed("e_", [fid, *span(e)])
            new = dict(e, evidence_id=eid, fact_id=fid)
            if eid in new_ev and new_ev[eid] != new:
                raise ValueError("Bằng chứng trùng ID nhưng khác dữ liệu: " + eid)
            new_ev[eid] = new
            replacements[old].add(fid)
            parents[fid].add(old)
            # Ưu tiên giữ đúng nguồn chính A2 nếu nguồn đó vẫn đủ điều kiện.
            rank = (old != fid, e["evidence_id"] != f["evidence_id"], old, eid)
            if fid not in priority or rank < priority[fid]:
                priority[fid] = rank
                records[fid] = dict(f, fact_id=fid, src_id=src, dst_id=dst, event_key=event,
                                    article_id=e["article_id"], article_url=art["canonical_url"],
                                    evidence_id=eid, quote=e["quote"])
                if old in attrs:
                    new_attrs[fid] = dict(attrs[old], fact_id=fid)
                    if "match" in new_attrs[fid]:
                        new_attrs[fid]["match"] = match
                    if method == "wiki_roster_row" and (old != fid or e["evidence_id"] != f["evidence_id"]):
                        row = mw.parse(e["quote"]).filter_templates()[0]
                        new_attrs[fid].update(shirt=param(row, "no"), position=position(param(row, "pos")))
            if method == "wiki_match_venue":
                venue_matches[fid].add(match)
            if method == "wiki_staff_table":
                staff_seasons[fid].add(art["story_group"].split(":")[-1])
        if reasons:
            reasons = sorted(set(reasons))
            reasons_by_id[old].update(reasons)
            decisions.append(dict(a2_fact_id=old, a3_fact_id=fid, a2_evidence_id=e["evidence_id"],
                                  a3_evidence_id=eid, reasons=reasons, article_url=art["canonical_url"],
                                  start=e["start"], end=e["end"], source_checks=[SOURCES[r] for r in reasons if r in SOURCES]))
    for fid, games in venue_matches.items():
        dates = sorted(k.split(":")[0] for k in games)
        new_attrs[fid] = dict(fact_id=fid, distinct_matches=len(games),
                              first_observed=dates[0], last_observed=dates[-1])
        records[fid]["period"] = f"ghi nhận {dates[0]} đến {dates[-1]}"
    for fid, seasons in staff_seasons.items():
        records[fid]["period"] = ", ".join(sorted(seasons))

    active = {n for f in records.values() for n in (f["src_id"], f["dst_id"])}
    roles = defaultdict(set)
    for f in records.values():
        if entities[f["src_id"]]["type"] == "Person":
            roles[f["src_id"]].add({"DAN_DAT": "Coach", "CHU_TICH_CUA": "Executive"}.get(f["relation_type"], "Player"))
    for eid, rs in roles.items():
        entities[eid]["role"] = "|".join(sorted(rs))
    write_csv(out / "entities.csv", list(next(iter(entities.values()))), [entities[k] for k in sorted(active)])
    write_csv(out / "facts.csv", list(next(iter(facts.values()))), [records[k] for k in sorted(records)])
    lines(out / "evidence.jsonl", (new_ev[k] for k in sorted(new_ev)))
    lines(out / "entity_resolution.jsonl", (registry[k] for k in sorted(active & registry.keys())))
    lines(out / "event_attributes.jsonl", (new_attrs[k] for k in sorted(new_attrs)))
    lines(out / "doi_chieu_bang_chung.jsonl", decisions)
    delta = []
    for old in sorted(facts):
        targets = sorted(replacements[old])
        if not targets:
            status = "withdrawn"
        elif old not in targets:
            status = "replaced"
        elif len(targets) > 1:
            status = "split"
        elif (old in reasons_by_id or len(parents[old]) > 1 or records[old] != facts[old]
              or new_attrs.get(old) != attrs.get(old)):
            status = "updated"
        else:
            continue
        related = sorted(set().union(*(parents[k] for k in targets)) - {old})
        reasons = sorted(reasons_by_id[old]) or (["nhan_them_bang_chung"] if related else [])
        delta.append(dict(status=status, a2_fact_id=old, a3_fact_ids=targets, reasons=reasons, related_a2_ids=related,
                          relation=facts[old]["relation_type"], a2_period=facts[old]["period"],
                          a2_src=facts[old]["src_id"], a2_dst=facts[old]["dst_id"], url=facts[old]["article_url"]))
    lines(out / "doi_chieu_canh.jsonl", delta)
    audit = dict(parent_checksum=A2_HASH, a2_nodes=len(table(A2 / "entities.csv")), a2_facts=len(facts),
                 a2_evidence=len(evidence), a3_nodes=len(active), a3_facts=len(records), a3_evidence=len(new_ev),
                 match_spans_checked=len(matches), roster_evidence_checked=sum(facts[e["fact_id"]]["method"] == "wiki_roster_row" for e in evidence),
                 status_counts=Counter(d["status"] for d in delta), processed_evidence=len(evidence),
                 dropped_support=sum(d["a3_fact_id"] is None for d in decisions),
                 removed_ids=len(facts.keys() - records.keys()), new_ids=len(records.keys() - facts.keys()),
                 convergent_facts=sum(len(p) > 1 for p in parents.values()),
                 rules_by_a2_fact={r: sum(r in keys for keys in reasons_by_id.values()) for r in sorted({r for keys in reasons_by_id.values() for r in keys})},
                 match_score_conflicts=sorted(conflicts))
    json_out(out / "audit_a3.json", audit)
    baseline = json.loads((A2 / "stats.json").read_bytes())
    stats = {k: baseline[k] for k in ("articles", "press_decisions", "former_pending", "press_groups", "wiki_source_pages")}
    stats.update(version="A3", connected_nodes=len(active), edges=len(records),
                 relations=Counter(f["relation_type"] for f in records.values()), methods=Counter(f["method"] for f in records.values()),
                 node_types=Counter(entities[k]["type"] for k in active), identity_basis=Counter(registry[k]["basis"] for k in active & registry.keys()))
    json_out(out / "stats.json", stats)
    verify(out, False, True)
    print(json.dumps(audit, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("dest", type=Path)
    dest = parser.parse_args().dest
    if dest.exists():
        raise SystemExit("Đích phải là thư mục mới.")
    dest.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=dest.parent) as tmp:
        staged = Path(tmp) / "snapshot"
        staged.mkdir()
        build(staged)
        if dest.exists():
            raise FileExistsError(dest)
        staged.rename(dest)
