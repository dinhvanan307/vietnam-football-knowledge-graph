"""Áp dụng bảng phân nhóm đã rà và lưu căn cứ theo từng bài, không đổi article_id."""
import csv, hashlib, json
from collections import Counter
from pathlib import Path
from bongda.core.ban_giao import enc, jlines, table

def group_articles(articles, decisions, out):
    press={a["article_id"]:a for a in articles if a["source_kind"]=="press"}
    rows=table(decisions,"\t")
    if {r["article_id"] for r in rows}!=set(press) or len(rows)!=len(press):
        raise ValueError("Bảng quyết định chưa phủ đúng toàn bộ báo")
    summary={}
    for r in rows:
        a=press[r["article_id"]]
        if a["canonical_url"]!=r["url"] or r["anchor"] not in a["clean_text"] or not r["anchor"]:
            raise ValueError("Căn cứ không khớp "+r["article_id"])
        if not a["story_group"].startswith("pending-") and a["story_group"]!=r["story_group"]:
            raise ValueError("Nhóm đã chốt bị đổi")
        a["story_group"]=r["story_group"]
        group=summary.setdefault(r["story_group"],dict(label=r["event_label"],articles=[]))
        if group["label"]!=r["event_label"]:raise ValueError("Nhóm có hai nhãn")
        group["articles"].append(a["article_id"])
    with (out/"event_groups.jsonl").open("w") as f:
        for key,g in summary.items(): f.write(enc({"story_group":key,**g})+"\n")
    (out/"article_event_map.tsv").write_bytes(decisions.read_bytes())
    return summary
