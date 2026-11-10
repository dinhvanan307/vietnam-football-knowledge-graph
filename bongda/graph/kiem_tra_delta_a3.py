"""Đối chiếu A2→A3 theo mọi bằng chứng, khóa trận, mùa và bốn ca gốc."""
import argparse
from collections import defaultdict
from pathlib import Path

from bongda.core.ban_giao import idx, jlines, require, table
from bongda.graph.tao_a3 import A2, json_out, span

CASES = {
    "C070": ("f_a46256f795b0f5a5d7b3", "p-0e78e7f3420f2a9f6f4b", "c-tc", "2017-04-02"),
    "C077": ("f_0d8b7e01359bd9121b2b", "p-a1645f9a34d078780285", "club-khatoco-khanh-hoa-cu", "2012-02-25"),
    "C088": ("f_71febab7aaba6f197c95", "club-w445434", "club-w883584", "2012-02-04"),
    "C092": ("f_fc330152a7a602c1800c", None, None, None),
}


def check(root):
    f2 = idx(table(A2 / "facts.csv"), "fact_id")
    f3 = idx(table(root / "facts.csv"), "fact_id")
    e2 = idx(jlines(A2 / "evidence.jsonl"), "evidence_id")
    e3 = idx(jlines(root / "evidence.jsonl"), "evidence_id")
    changes = idx(jlines(root / "doi_chieu_bang_chung.jsonl"), "a2_evidence_id")
    delta = idx(jlines(root / "doi_chieu_canh.jsonl"), "a2_fact_id")
    articles = idx(jlines(root / "articles.jsonl"), "article_id")
    extra = idx(jlines(root / "event_attributes.jsonl"), "fact_id")
    observed = set()
    expected_targets = defaultdict(set)
    for eid, old in e2.items():
        new_id = changes[eid]["a3_evidence_id"] if eid in changes else eid
        if not new_id:
            require(bool(changes[eid]["reasons"]), eid)
            continue
        now = e3[new_id]
        require(all(old[k] == now[k] for k in old if k not in {"evidence_id", "fact_id"}), eid)
        expected_targets[old["fact_id"]].add(now["fact_id"])
        observed.add(new_id)
    require(observed == e3.keys(), "Bằng chứng A3 không nối về A2")
    for old in f2:
        targets = set(delta[old]["a3_fact_ids"]) if old in delta else {old}
        require(targets == expected_targets[old], old)
        if old not in delta:
            require(f2[old] == f3[old], old)
    require(set().union(*expected_targets.values()) == f3.keys(), "Có fact A3 thiếu nguồn")
    baseline = {k for k, f in f2.items() if f["method"] == "nlp_rules_reviewed"}
    require(all(f2[k] == f3[k] and k not in delta for k in baseline), "NLP pilot đã thay đổi")

    by_span = {}
    for e in e3.values():
        f = f3[e["fact_id"]]
        if f["method"] == "wiki_match_result":
            expected = ":".join((f["period"], f["src_id"], f["dst_id"]))
            require(expected == f["event_key"] == extra[f["fact_id"]]["match"], f["fact_id"])
            by_span[span(e)] = f
    venue_games = defaultdict(set)
    checked = set()
    for e in e3.values():
        f = f3[e["fact_id"]]
        method = f["method"]
        art = articles[e["article_id"]]
        if method in ("wiki_match_result", "wiki_match_event", "wiki_match_venue"):
            fixture = by_span[span(e)]
            sides = {fixture["src_id"], fixture["dst_id"]}
            require("club-w591109" not in sides, fixture["event_key"])
            if art["story_group"] == "season:VL1:2012" and "Khatoco Khánh Hòa" in e["quote"].split("báo cáo")[0]:
                if "club-khatoco-khanh-hoa-cu" in sides:
                    checked.add("khatoco_cu")
                require("club-w2452083" not in sides, fixture["event_key"])
            if art["story_group"] in {"season:VL2:2012", "season:VL2:2018"}:
                require("c-hn" not in sides, fixture["event_key"])
            if method == "wiki_match_event":
                require(f["dst_id"] in sides and f["event_key"] == fixture["event_key"] == extra[f["fact_id"]]["match"], f["fact_id"])
            if method == "wiki_match_venue":
                require(f["src_id"] in sides, f["fact_id"])
                venue_games[f["fact_id"]].add(fixture["event_key"])
        if method == "wiki_roster_row":
            context = art["clean_text"][e["context_start"]:e["context_end"]]
            require(art["revid"] not in {"56438500", "57233042", "9285244", "26056561", "22387636",
                                         "45120892", "57201576", "43073609", "57320476"}, e["evidence_id"])
            if "===Đội hình 2===" in context and "TDC Bình Dương" in context:
                require(f["dst_id"] == "club-w502739", f["fact_id"])
                checked.add("tdc_binh_duong")
            if art["revid"] == "25288199":
                require(f["period"] == "2016" and "Hạng nhất 2016" in context, f["fact_id"])
                checked.add("nam_dinh_mua_hien_thi_2016")
    require(checked == {"khatoco_cu", "tdc_binh_duong", "nam_dinh_mua_hien_thi_2016"}, str(checked))
    for fid, matches in venue_games.items():
        dates = sorted(k.split(":")[0] for k in matches)
        require(extra[fid] == dict(fact_id=fid, first_observed=dates[0], last_observed=dates[-1], distinct_matches=len(matches)), fid)

    cases = {}
    for name, (old, src, dst, period) in CASES.items():
        require(old not in f3, old)
        targets = delta[old]["a3_fact_ids"]
        if dst is None:
            require(not targets, old)
        else:
            require(len(targets) == 1, old)
            r = f3[targets[0]]
            require((r["src_id"], r["dst_id"], r["period"], r["relation_type"]) ==
                    (src, dst, period, f2[old]["relation_type"]), old)
        cases[name] = delta[old]
    report = dict(a2_facts_accounted_for=len(f2), a3_facts_traced=len(f3), a2_evidence_accounted_for=len(e2),
                  a3_evidence_traced=len(e3), venue_summaries_checked=len(venue_games),
                  fixtures_checked=len(by_span), unchanged_pilot_facts=len(baseline), four_cases=cases)
    json_out(root / "qa_delta.json", report)
    print(f"PASS {len(cases)} ca gốc; {len(f3)} fact và {len(e3)} bằng chứng A3 truy về A2.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot", type=Path)
    check(parser.parse_args().snapshot)
