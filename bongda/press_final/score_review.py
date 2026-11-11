"""Summarize a completed, fixed review sheet; missing or unconfirmed rows are not successes."""
import argparse,json,math
from collections import Counter,defaultdict
from pathlib import Path
from bongda.core.ban_giao import table,idx,sha
def score(root):
 q=root/"qa";locked=idx(table(q/"mau_graph.tsv","\t"),"fact_id");rows=idx(table(q/"mau_graph_da_ra.tsv","\t"),"fact_id");meta=json.loads((q/"mau_graph.json").read_text())
 if set(rows)!=set(locked) or sha((root/"snapshot/facts.csv").read_bytes())!=meta["facts_sha256"]:raise ValueError("Sample changed")
 counts=Counter();types=defaultdict(Counter)
 for fid,r in rows.items():
  outcome=r["verdict"]
  if not r["reason"].strip() or outcome not in {"DUNG","SAI","CHUA_RO"}:raise ValueError(fid)
  counts[outcome]+=1;types[locked[fid]["relation"]][outcome]+=1
 n=len(rows);p=counts["DUNG"]/n;z=1.959963984540054;d=1+z*z/n;c=(p+z*z/2/n)/d;h=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
 summary=dict(**meta,confirmed=counts["DUNG"],unresolved=counts["CHUA_RO"],wrong=counts["SAI"],precision_conservative=p,wilson95_approx=[c-h,c+h],sources_in_sample=len({r["url"] for r in locked.values()}),by_relation=types,method="Single source-grounded reading. Uncertain = non-success. A graph-edge sample is not an NLP recall test.")
 (q/"precision_graph.json").write_text(json.dumps(summary,indent=2,ensure_ascii=False)+"\n");print(counts,p,c-h,c+h)
if __name__=="__main__":
 p=argparse.ArgumentParser(description=__doc__);p.add_argument("root",type=Path);score(p.parse_args().root)
