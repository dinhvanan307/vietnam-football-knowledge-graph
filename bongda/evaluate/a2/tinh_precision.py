"""Tổng hợp nhãn đã đọc từ nguồn; khoảng một phía dùng phân phối siêu bội hữu hạn."""
from bongda.evaluate.labels import review_sheet
import json, math
from collections import Counter,defaultdict
from bongda.evaluate.a2.chuan_bi_doi_chieu import ROOT, OUT, tsv, lines, digest, select, put_tsv, CONTROL_SEED

def hyper_tail(N,D,n,k):
    return sum(math.comb(D,i)*math.comb(N-D,n-i)
               for i in range(max(0,n-(N-D)),min(k,n,D)+1))
def srs_lower_bound(N,n,k):
    denom=math.comb(N,n)
    if k==n:return 0.
    lo,hi=0,N
    while hi-lo>1:
        d=(lo+hi)//2
        if 20*hyper_tail(N,d,n,k)<=denom:hi=d
        else:lo=d
    return (N-lo)/N

def main():
    sample,facts,control=select();N=len(facts)
    expected=json.loads((ROOT/"checksums.json").read_bytes())
    for n in ["mau_ra_soat.tsv","facts.csv","entities.csv","evidence.jsonl","articles.jsonl"]:
        if digest((ROOT/n).read_bytes())!=expected[n]:raise ValueError(n)
    packet=lines(OUT/"hoso_doi_chieu.jsonl")
    labels={r["ma"]:r for r in tsv(review_sheet(OUT))}
    assert len(labels)==len(packet)==len(sample)+len(control)
    assert [r["fact_id"] for r in packet]==[r["fact_id"] for r in sample]+control
    assert all(e["raw_check"] for r in packet for e in r["support"])
    methods=Counter(r["method"] for r in facts)
    types=Counter(r["relation_type"] for r in facts)
    groups=defaultdict(list)
    exports={"S":[],"C":[]};unique={};eids=set()
    for row in packet:
        label=labels[row["no"]];fid=row["fact_id"];ev=row["support"]
        assert fid==label["fact_id"] and label["nhan_kiem_tra"] in {"DUNG","SAI","CHUA_RO"} and label["ly_do"]
        assert unique.setdefault(fid,label["nhan_kiem_tra"])==label["nhan_kiem_tra"]
        depth=row["no"][0];groups[depth,row["relation_type"]].append(label["nhan_kiem_tra"])
        primary=ev[0]
        if depth=="S":
            record=dict(sample[int(row["no"][1:])-1])
            assert record["ngu_canh"]==primary["context"] and record["bang_chung"]==primary["quote"] and record["url"]==primary["url"]
        else:
            record=dict(fact_id=fid,quan_he=row["relation_type"],nguon=row["src"],dich=row["dst"],thoi_gian=row["period"],
                        url=primary["url"],ngu_canh=primary["context"],bang_chung=primary["quote"],nhan_A="",nhan_B="")
        record.update(ma=label["ma"],phuong_phap=row["method"],nhan_kiem_tra=label["nhan_kiem_tra"],loai_loi=label["loai_loi"],ly_do=label["ly_do"],
                      so_bang_chung=len(ev),nguon_bo_sung=label["nguon_bo_sung"])
        exports[depth].append(record)
        eids.update((fid,e["article_id"],e["start"],e["end"]) for e in ev)
    put_tsv(OUT/"mau_82_da_cham.tsv",exports["S"])
    put_tsv(OUT/"kiem_chung_100_da_cham.tsv",exports["C"])
    put_tsv(OUT/"cac_canh_can_sua.tsv",[r for d in "SC" for r in exports[d] if r["nhan_kiem_tra"]!="DUNG"])
    results=[];weighted_terms=[]
    for rel,N_h in sorted(types.items()):
        s,c=groups["S",rel],groups["C",rel];n=len(s);ok=s.count("DUNG")
        assert n==min(8,N_h)
        weighted_terms.append(N_h*ok/n)
        results.append(dict(quan_he=rel,N_h=N_h,n_phan_tang=n,dung_phan_tang=ok,sai_phan_tang=s.count("SAI"),chua_ro_phan_tang=s.count("CHUA_RO"),
                            precision_phan_tang=ok/n,n_kiem_chung=len(c),dung_kiem_chung=c.count("DUNG"),sai_kiem_chung=c.count("SAI"),chua_ro_kiem_chung=c.count("CHUA_RO")))
    wp=math.fsum(weighted_terms)/N
    put_tsv(OUT/"theo_loai_quan_he.tsv",results)
    counts={d:Counter(r["nhan_kiem_tra"] for r in xs) for d,xs in exports.items()}
    n=len(control);k=n-counts["C"]["DUNG"];null_errors=(N+9)//10
    data=dict(population=N,snapshot_sha256=expected["facts.csv"],sample_sha256=expected["mau_ra_soat.tsv"],
              fixed_sample=dict(n=len(sample),counts=counts["S"],weighted_precision=wp),
              control=dict(n=n,seed=CONTROL_SEED,counts=counts["C"],precision=(n-k)/n,
                           exact_one_sided_95_lower=srs_lower_bound(N,n,k),null_min_errors=null_errors,
                           one_sided_p_at_90=hyper_tail(N,null_errors,n,k)/math.comb(N,n)),
              overlap=len(packet)-len(unique),unique_facts_read=len(unique),distinct_support_spans=len(eids),
              methods_population=methods,methods_in_fixed_sample=Counter(r["phuong_phap"] for r in exports["S"]),
              human_labels_A_B=sum(bool(r["nhan_A"] or r["nhan_B"]) for r in sample),
              review_method="Đối chiếu nguồn", human_double_review=False,
              unresolved_rule="CHUA_RO được tính vào mẫu số và không được tính đúng.")
    (OUT/"ket_qua.json").write_text(json.dumps(data,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps(data,ensure_ascii=False))
if __name__=="__main__":main()
