"""Operate the verified release. Projection edges are not included in graph acceptance counts."""
import argparse,csv,json
from collections import defaultdict,Counter
from itertools import combinations
from pathlib import Path
from bongda.core.ban_giao import table,idx,jlines
from bongda.press.build import write_csv
from bongda.press.import_graph import run
from bongda.press.visual import render
from bongda.press_final.verify import verify_snapshot
LABELS=dict(GOP_MAT_TRONG_TRAN="góp mặt trong trận",THUOC_GIAI_DAU="thuộc giải đấu",DA_CHINH_TRONG_TRAN="đá chính trong trận",DANG_KY_DU_BI_TRONG_TRAN="đăng ký dự bị trong trận",VAO_SAN_THAY_NGUOI_TRONG_TRAN="vào sân thay người",CHUYEN_DI_TU="chuyển đi từ",CHUYEN_DEN_CLB="chuyển đến CLB",CO_TEN_TRONG_DANH_SACH_CLB="có tên trong danh sách CLB",DUOC_BAO_GHI_NHAN_THUOC_CLB="được báo ghi nhận thuộc CLB")
def project(root):
    snap=root/"snapshot";n=idx(table(snap/"entities.csv"),"entity_id");meta=idx(jlines(snap/"event_attributes.jsonl"),"fact_id")
    groups=defaultdict(set);counts=defaultdict(list)
    for f in table(snap/"facts.csv"):
        c=meta.get(f["fact_id"],{}).get("club_id")
        if f["relation_type"]=="DA_CHINH_TRONG_TRAN" and c:groups[f["dst_id"],c].add(f["src_id"])
    for (m,c),players in groups.items():
        if len(players)>11:continue # different names/sources within a line-up need a further identity check
        for pair in combinations(sorted(players),2):counts[pair].append((m,c))
    fields="player1 player2 name1 name2 matches example_match club_id".split();rows=[]
    for (a,b),v in sorted(counts.items(),key=lambda x:(-len(x[1]),x[0])):
        rows.append(dict(zip(fields,[a,b,n[a]["canonical_name"],n[b]["canonical_name"],len({m for m,c in v}),v[0][0],v[0][1]])))
    write_csv(root/"dong_doi.csv",rows,fields)
    return dict(pairs=len(rows),people=len({x for p in counts for x in p}),top=rows[:10],excluded_groups_over_eleven=sum(len(v)>11 for v in groups.values()))
def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("command",choices=["check","neo4j","explore","projection"]);p.add_argument("root",type=Path)
    a=p.parse_args();s=a.root/"snapshot"
    version=json.loads((s/"stats.json").read_text())["version"];port=7700 if version=="A9.1" else 7699
    if a.command=="neo4j":return run(a.root,verify=verify_snapshot,uri=f"bolt://127.0.0.1:{port}")
    if a.command=="explore":return render(s,a.root/"Ban_do_bao_chi.html",verify=verify_snapshot,version=version,extra=LABELS)
    value=project(a.root) if a.command=="projection" else verify_snapshot(s)
    fn="projection.json" if a.command=="projection" else "integrity.json"
    (a.root/fn).write_text(json.dumps(value,indent=2,ensure_ascii=False)+"\n")
    print(json.dumps(value,ensure_ascii=False))
if __name__=="__main__":main()
