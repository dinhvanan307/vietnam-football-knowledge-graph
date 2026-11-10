"""Baseline NLP theo từ điển + luật. Mỗi đề xuất được giữ riêng để kiểm tra."""
import argparse
import csv
import json
import re
from collections import Counter
from pathlib import Path
from ban_giao import enc, jlines, sha, table, verify
from ontology import ENDS

TRIGGERS={
    "THI_DAU_CHO":r"ra sân|thi đấu cho|ghi bàn|màu áo|vào lưới",
    "DAN_DAT":r"dẫn dắt|bổ nhiệm|làm HLV trưởng",
    "KY_HOP_DONG_VOI":r"ký (?:bản )?hợp đồng",
    "GIA_HAN_VOI":r"gia hạn|ký tiếp|thêm \d+ mùa giải",
    "THANH_LY_VOI":r"thanh lý|chấm dứt hợp đồng",
    "DUOC_CHO_MUON_DEN":r"cho mượn|dạng mượn",
    "DUOC_TRIEU_TAP_VAO":r"triệu tập|được gọi lên",
    "KY_LUAT":r"án phạt|quyết định kỷ luật|treo giò",
    "TAI_TRO":r"tài trợ",
    "CHU_TICH_CUA":r"chủ tịch",
    "THAM_GIA_GIAI":r"có sự tham dự|tham gia giải",
    "TO_CHUC_GIAI":r"đơn vị tổ chức|đứng ra tổ chức",
    "SU_DUNG_SAN_NHA":r"sân nhà",
}
UNCERTAIN=re.compile(r"\b(?:sắp|tin đồn|đang đàm phán|có thể|chưa ký|chưa gia hạn|phủ nhận)\b", re.I)
def mentions(text, entities):
    spans=[]
    for e in entities:
        for alias in [e["canonical_name"], *e["aliases"].split("|")]:
            if alias:
                for m in re.finditer(r"(?<!\w)"+re.escape(alias)+r"(?!\w)",text,re.I):
                    spans.append((m.start(),m.end(),e["entity_id"]))
    # Không nhận 'Hà Nội' nằm bên trong 'Công an Hà Nội' thành một CLB khác.
    return {eid for i,j,eid in spans if not any(a<=i and j<=b and (a<i or j<b) for a,b,_ in spans)}

def candidates(articles, entities):
    by_id={e["entity_id"]:e for e in entities}
    for a in articles:
        for m in re.finditer(r"[^\n]+",a["clean_text"]):
            para=m.group()
            if len(para)>2000:continue
            found=sorted(mentions(para,entities))
            for rel,trigger in TRIGGERS.items():
                if not re.search(trigger,para,re.I):continue
                src_types,dst_types=ENDS[rel]
                for src in found:
                    if by_id[src]["type"] not in src_types:continue
                    for dst in found:
                        if src==dst or by_id[dst]["type"] not in dst_types:continue
                        yield dict(article_id=a["article_id"],url=a["canonical_url"],src_id=src,
                                   dst_id=dst,relation_type=rel,start=m.start(),end=m.end(),quote=para,
                                   status="modality_review" if UNCERTAIN.search(para) else "needs_review")

def write_csv(path,columns,rows):
    with path.open("w",encoding="utf-8",newline="") as f:
        writer=csv.DictWriter(f,fieldnames=columns);writer.writeheader();writer.writerows(rows)
def apply_reviews(folder,rows,entities,reviews):
    approved={}; evidence={}; used=set()
    for r in reviews:
        for dest in r["dst_ids"].split(","):
            for source in r["src_ids"].split(","):
                matches=[c for c in rows if r["url_key"] in c["url"] and c["quote"].startswith(r["paragraph_start"]) and
                         (c["src_id"],c["relation_type"],c["dst_id"])==(source,r["relation_type"],dest)]
                if len(matches)!=1:raise ValueError(f"Quyết định phải khớp đúng 1 ứng viên, có {len(matches)}: {r} {source} {dest}")
                c=matches[0]
                c["status"]="accepted_after_review"
                key=[source,c["relation_type"],dest,r["event_key"]]
                fid="f_"+sha(enc(key).encode())[:20]
                eid="e_"+sha(enc([fid,c["article_id"],c["start"],c["end"]]).encode())[:20]
                approved.setdefault(fid, dict(fact_id=fid,src_id=source,dst_id=dest,relation_type=c["relation_type"],
                                    event_key=r["event_key"],period=r["period"],status="accepted",method="nlp_rules_reviewed",
                                    evidence_id=eid,article_id=c["article_id"],article_url=c["url"],quote=c["quote"]))
                evidence[eid]=dict(evidence_id=eid,fact_id=fid,article_id=c["article_id"],start=c["start"],end=c["end"],quote=c["quote"],role="supports")
                used.update([source,dest])
    write_csv(folder/"entities.csv",["entity_id","type","canonical_name","role"],[
        {k:e[k] for k in ["entity_id","type","canonical_name","role"]} for e in entities if e["entity_id"] in used])
    write_csv(folder/"facts.csv",list(next(iter(approved.values()))),approved.values())
    (folder/"evidence.jsonl").write_text("".join(enc(row)+"\n" for row in evidence.values()))
    verify(folder,False,True)

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument("bundle",type=Path)
    ap.add_argument("--aliases",type=Path,default=Path("templates/entities_pilot.tsv"))
    ap.add_argument("--reviews",type=Path,default=Path("templates/reviews_pilot.tsv"))
    args=ap.parse_args()
    verify(args.bundle, False)
    entities=table(args.aliases,"\t")
    rows=list(candidates(jlines(args.bundle/"articles.jsonl"),entities))
    apply_reviews(args.bundle,rows,entities,table(args.reviews,"\t"))
    # Hai đoạn trong bài 01/07 chỉ mô tả kế hoạch gia hạn của CAHN.
    for row in rows:
        if ("185240701162802574" in row["url"] and row["src_id"]=="p-qh" and
            row["relation_type"]=="GIA_HAN_VOI" and row["dst_id"]=="c-cahn" and
            row["quote"].startswith(("Dự kiến trong mùa giải", "Để sớm chuẩn bị lực lượng"))):
            row["status"]="rejected_planned_event"
    (args.bundle/"candidates.jsonl").write_text("".join(enc(r)+"\n" for r in rows))
    print("candidate_mentions_by_type",dict(Counter(c["relation_type"] for c in rows)))
if __name__=="__main__":main()
