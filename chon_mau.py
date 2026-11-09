"""Lấy mẫu từ facts.csv của bản tự động đã khóa; ghi file TSV mới."""
import csv, random, sys
from pathlib import Path
if len(sys.argv)!=3: sys.exit("Dùng: python3 chon_mau.py facts.csv phan_cong.tsv")
source,dest=map(Path,sys.argv[1:])
with source.open(encoding="utf-8-sig",newline="") as f:
    ids=[row["fact_id"] for row in csv.DictReader(f) if row["status"]=="accepted" and row["method"].startswith("nlp_") and not row["method"].endswith("_reviewed")]
if not ids:sys.exit("Không có fact NLP đủ điều kiện. Kiểm tra scope/method của snapshot.")
if len(set(ids))!=len(ids) or "" in ids:sys.exit("fact_id trùng hoặc rỗng; sửa tổng thể trước khi lấy mẫu.")
rng=random.Random(22);sample=rng.sample(sorted(ids),min(300,len(ids)))
a,b=sample[::2],sample[1::2]
double=set(rng.sample(a,min(30,round(len(a)*.2)))+rng.sample(b,min(30,round(len(b)*.2))))
with dest.open("x",encoding="utf-8",newline="") as f:
    w=csv.writer(f,delimiter="\t");w.writerow(["fact_id","primary","second"])
    for i,item in enumerate(sample):
        owner="A" if i%2==0 else "B";other="B" if owner=="A" else "A"
        w.writerow([item,owner,other if item in double else ""])
print(f"Eligible={len(ids)}; unique_sample={len(sample)}; double_coded={len(double)}; seed=22")
