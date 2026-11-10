"""So sánh ba phương án trên cùng bài, nhãn và không gian ID."""
import argparse
from collections import Counter, defaultdict
import csv
import json
from pathlib import Path
import re
import sys

from trich_xuat import ROOT, TYPES, digest
sys.path.insert(0, str(ROOT))
from trich_quan_he import candidates


def table(path, sep="\t"):
    with path.open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream, delimiter=sep))


def save_table(path, fields, rows):
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fields, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)


def metrics(pred, ref):
    tp, fp, fn = len(pred & ref), len(pred - ref), len(ref - pred)
    return dict(tp=tp, fp=fp, fn=fn, precision=tp/(tp+fp) if tp+fp else None,
                recall=tp/(tp+fn) if tp+fn else None, f1=2*tp/(2*tp+fp+fn) if tp+fp+fn else None)


def vocabularies(entities):
    pilot = table(ROOT/"templates/entities_pilot.tsv")
    wider = {r["entity_id"]: dict(r) for r in pilot}
    for r in table(entities, ","):
        e = wider.setdefault(r["entity_id"],dict(r,aliases=""))
        if e["type"] == "Club":
            n = e["canonical_name"]
            short = re.sub(r"^(?:CLB|Câu lạc bộ(?: bóng đá)?)\s+","",n,flags=re.I)
            if short != n:
                e["aliases"] = "|".join(dict.fromkeys([*filter(None,e["aliases"].split("|")),short]))
    return {"pilot":pilot,"tu_dien_A3":list(wider.values())}


def score(docs, gold_rows, entities, predictions, output, allow_mixed=False):
    corpus = {d["article_id"]:d for d in docs}
    if len(corpus) != len(docs) or not docs:
        raise ValueError("Tập bài trống hoặc trùng ID.")
    reference = {}
    for r in gold_rows:
        key = (r["bai"],r["nguon_id"],r["quan_he"],r["dich_id"])
        spans = {int(n) for n in r["doan"].split(",")}
        if key in reference or key[0] not in corpus or key[2] not in TYPES or not spans:
            raise ValueError(key)
        reference[key] = spans
    gold = set(reference)
    proposals = {}
    for name, lexicon in vocabularies(entities).items():
        proposals[name] = {(c["article_id"],c["src_id"],c["relation_type"],c["dst_id"])
                           for c in candidates(docs,lexicon) if c["relation_type"] in TYPES}
    inferred = {}
    identity = None
    server_versions = Counter()
    by_model = defaultdict(set)
    rows = []
    for aid, d in corpus.items():
        raw = json.loads((predictions/(aid+".json")).read_bytes())
        meta = raw["input"]
        info = {key:meta[key] for key in ("code_sha256","provider","rules_sha256","graph_sha256","facts_sha256","pilot_sha256")}
        for optional in ("aliases_sha256", "callup_code_sha256", "callup_names_sha256"):
            if optional in meta:
                info[optional] = meta[optional]
        version = raw.get("api_model_version") or "unknown"
        server_versions[version] += 1
        by_model[(meta["model"],version)].add(aid)
        if len(by_model) > 1 and not allow_mixed:
            raise ValueError("Có nhiều phiên bản API. Dùng --allow-mixed để chấm kèm thống kê riêng từng bản.")
        if identity and info != identity:
            raise ValueError("Hai bài được chạy bằng cấu hình khác nhau.")
        identity = info
        if meta["article_id"] != aid or meta["canonical_url"] != d["canonical_url"] or meta["text_sha256"] != digest(d["clean_text"].encode()):
            raise ValueError("Dự đoán khác phiên bản bài " + aid)
        for edge in raw["edges"]:
            k = (aid,edge["src_id"],edge["relation_type"],edge["dst_id"])
            if k in inferred or not edge["evidence"]:
                raise ValueError(k)
            for e in edge["evidence"]:
                if d["clean_text"][e["start"]:e["end"]] != e["quote"]:
                    raise ValueError("Sai bằng chứng " + str(k))
            inferred[k] = {e["paragraph"] for e in edge["evidence"]}
            rows.append(dict(bai=aid,nguon_id=k[1],chu_the=edge["src"],quan_he=k[2],dich_id=k[3],doi_tuong=edge["dst"],
                             doan=",".join(map(str,sorted(inferred[k]))),url=d["canonical_url"]))
    proposals["luat_va_gemini"] = set(inferred)
    scores, decisions = {}, []
    for name, pred in proposals.items():
        scores[name] = dict(overall=metrics(pred,gold), per_relation={rel: metrics({k for k in pred if k[2]==rel},
                            {k for k in gold if k[2]==rel}) for rel in TYPES})
        for aid,src,rel,dst in sorted(pred | gold):
            k = (aid,src,rel,dst)
            decisions.append(dict(model=name,bai=aid,nguon_id=src,quan_he=rel,dich_id=dst,
                ket_qua="TP" if k in pred & gold else "FP" if k in pred else "FN",
                url=corpus[aid]["canonical_url"]))
    output.mkdir(exist_ok=True,parents=True)
    fields = ["bai","nguon_id","chu_the","quan_he","dich_id","doi_tuong","doan","url"]
    save_table(output/"ung_vien.tsv",fields,rows)
    save_table(output/"doi_chieu.tsv",["model","bai","nguon_id","quan_he","dich_id","ket_qua","url"],decisions)
    groups = []
    for (requested,served), aids in sorted(by_model.items()):
        groups.append(dict(requested=requested,served=served,articles=sorted(aids),
                           scores={name:metrics({k for k in pred if k[0] in aids},
                                                {k for k in gold if k[0] in aids}) for name,pred in proposals.items()}))
    report = dict(api_groups=groups, articles=len(docs), gold=len(gold), model=identity, server_versions=server_versions, scores=scores,
                  tp_trung_doan=sum(bool(reference[k] & inferred[k]) for k in gold & inferred.keys()))
    (output/"diem.json").write_text(json.dumps(report,ensure_ascii=False,indent=2)+"\n")
    for name, group in scores.items():
        print(name,group["overall"])


if __name__ == "__main__":
    cli = argparse.ArgumentParser(description=__doc__)
    for name in ("articles","gold","entities","predictions","output"):
        cli.add_argument(name,type=Path)
    cli.add_argument("--allow-mixed",action="store_true",help="Báo số liệu gộp và riêng từng model API")
    args = cli.parse_args()
    docs = [json.loads(line) for line in args.articles.read_text().splitlines() if line]
    score(docs,table(args.gold),args.entities,args.predictions,args.output,args.allow_mixed)
