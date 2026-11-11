"""Draw a deterministic uniform sample specifically from the direct social layer."""
import argparse,random,json
from pathlib import Path
from bongda.core.ban_giao import table,jlines,idx,sha
from bongda.press_final.layers import tsv
def run(root):
 p=root/"phan_lop/xa_hoi.tsv";rows=sorted(table(p,"\t"),key=lambda x:x["fact_id"]);rng=random.Random(2026111122);chosen=rng.sample(rows,80)
 s=root/"snapshot";fs=idx(table(s/"facts.csv"),"fact_id");docs=idx(jlines(s/"articles.jsonl"),"article_id");ev=idx(jlines(s/"evidence.jsonl"),"evidence_id")
 out=[]
 for i,row in enumerate(chosen,1):
  f=fs[row["fact_id"]];a=docs[f["article_id"]];e=ev[f["evidence_id"]];out.append(dict(index=i,**row,title=a["title"],quote=e["quote"],context=a["clean_text"][max(0,e["start"]-200):e["end"]+200]))
 tsv(root/"kiem_tra/mau_xa_hoi.tsv",out,list(out[0]))
 (root/"kiem_tra/khung_xa_hoi.json").write_text(json.dumps(dict(size=80,frame=len(rows),seed=2026111122,sha256=sha(p.read_bytes()),sampling="SRS without replacement on sorted fact_id")))
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("root",type=Path);run(p.parse_args().root)

