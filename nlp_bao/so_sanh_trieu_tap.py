"""Chấm quan hệ triệu tập trước/sau trên cùng phản hồi Gemini và so hai tập lỗi."""
import argparse
from collections import Counter
import json
from pathlib import Path
import re

from danh_gia import table, save_table, metrics
import trich_xuat as tx

REL = "DUOC_TRIEU_TAP_VAO"


def callups(edges, aid, article):
    spans = {}
    for edge in edges:
        if edge["relation_type"] != REL:
            continue
        if edge["dst_id"] != "nt-vn":
            raise ValueError("Sai ID đội tuyển")
        key = (aid, edge["src_id"])
        if key in spans or not edge["evidence"]:
            raise ValueError(f"Trùng cạnh hoặc thiếu bằng chứng: {key}")
        for item in edge["evidence"]:
            if article["clean_text"][item["start"]:item["end"]] != item["quote"]:
                raise ValueError(f"Sai vị trí nguồn: {key}")
        spans[key] = {ev["paragraph"] for ev in edge["evidence"]}
    return spans


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    for param in ("articles", "gold", "entities", "base_predictions", "output"):
        cli.add_argument(param,type=Path)
    args = cli.parse_args()
    reg = tx.Registry(args.entities)
    docs = [json.loads(line) for line in args.articles.read_text().splitlines() if line]
    corpus = {a["article_id"]:a for a in docs}
    if not docs or len(corpus) != len(docs):
        raise ValueError("Thiếu bài hoặc trùng ID")
    reference = {}
    for r in table(args.gold):
        if r["quan_he"] != REL:
            continue
        k = (r["bai"], r["nguon_id"])
        evidence = {int(i) for i in r["doan"].split(",")}
        if (k in reference or r["dich_id"] != "nt-vn" or k[0] not in corpus or not evidence
                or min(evidence)<1 or max(evidence)>len(re.findall(r"[^\n]+",corpus[k[0]]["clean_text"]))):
            raise ValueError(f"Nhãn không hợp lệ: {r}")
        reference[k] = evidence
    truth = set(reference)
    pairs = {"truoc":{}, "sau":{}}
    versions = Counter()
    per_doc = []
    graph_sha = tx.digest(args.entities.read_bytes())
    facts_sha = tx.digest(args.entities.with_name("facts.csv").read_bytes())
    base_code = None
    for aid,a in corpus.items():
        raw = json.loads((args.base_predictions/(aid+".json")).read_bytes())
        meta = raw["input"]
        if (meta["provider"] != "gemini" or meta["article_id"] != aid or meta["canonical_url"] != a["canonical_url"]
                or meta["text_sha256"] != tx.digest(a["clean_text"].encode()) or
                meta["graph_sha256"] != graph_sha or meta["facts_sha256"] != facts_sha):
            raise ValueError("Khác nguồn hoặc snapshot: "+aid)
        if base_code and base_code != meta["code_sha256"]:
            raise ValueError("Bộ xử lý gốc thay đổi giữa các bài")
        base_code = meta["code_sha256"]
        if "api_edges" not in raw:
            raise ValueError("Thiếu phản hồi nguyên bản của Gemini: "+aid)
        versions[(meta["model"],raw.get("api_model_version", ""))] += 1
        improved, _ = tx.normalize_records(raw["api_edges"],a,reg)
        others = lambda edges: {(e["src_id"],e["relation_type"],e["dst_id"]):e for e in edges if e["relation_type"]!=REL}
        if others(improved) != others(raw["edges"]):
            raise ValueError("Thay đổi ngoài quan hệ triệu tập: "+aid)
        actual = {k for k in truth if k[0]==aid}
        row = dict(bai=aid,url=a["canonical_url"],model=meta["model"],served=raw.get("api_model_version"),nhan=len(actual))
        for method, edges in (("truoc",raw["edges"]),("sau",improved)):
            pred = callups(edges,aid,a)
            pairs[method].update(pred)
            stats = metrics(set(pred),actual)
            row.update({method+"_"+m:stats[m] for m in ("tp","fp","fn")})
        per_doc.append(row)
    scores = {name:metrics(set(pred),truth) for name,pred in pairs.items()}
    previous,current = (set(pairs[m]) for m in ("truoc","sau"))
    result = dict(articles=len(docs), gold=len(truth), old_code_sha256=base_code,
                  versions=[dict(model=m,served=v,n=n) for (m,v),n in versions.items()],scores=scores,
                  newly_correct=len((current-previous)&truth),lost_correct=len((previous-current)&truth),
                  new_false=len(current-previous-truth),removed_false=len(previous-current-truth),
                  tp_with_overlapping_gold_paragraph=sum(bool(reference[k]&pairs["sau"][k]) for k in current&truth))
    result["sha256"] = {"articles":tx.digest(args.articles.read_bytes()), "gold":tx.digest(args.gold.read_bytes()),
                        **{n:tx.digest(Path(tx.__file__).with_name(n).read_bytes())
                           for n in ("trich_xuat.py","trieu_tap.py","ten_tuyen_thu.tsv","ten_clb.tsv")}}
    result["delta_percentage_points"]={m:(scores["sau"][m]-scores["truoc"][m])*100
        if None not in (scores["sau"][m],scores["truoc"][m]) else None for m in ("precision","recall","f1")}
    args.output.mkdir(parents=True,exist_ok=True)
    save_table(args.output/"theo_bai.tsv",list(per_doc[0]),per_doc)
    rows=[]
    for k in sorted(truth|current|previous):
        aid,sid=k
        row=dict(bai=aid,nguon_id=sid,ten=reg.names.get(sid,sid),nhan=int(k in truth),url=corpus[aid]["canonical_url"])
        for name,pred in pairs.items():
            row[name]=int(k in pred)
            row["doan_"+name]=",".join(map(str,sorted(pred.get(k,()))))
        row["doan_nhan"]=",".join(map(str,sorted(reference.get(k,()))))
        rows.append(row)
    if rows:
        save_table(args.output/"doi_chieu.tsv",list(rows[0]),rows)
    (args.output/"diem.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps(result,ensure_ascii=False))


if __name__ == "__main__":
    main()
