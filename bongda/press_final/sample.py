"""Freeze an SRS of graph edges, and a separate clustered evaluation of text if requested."""
import argparse,csv,hashlib,json,random
from pathlib import Path
from collections import Counter
from bongda.press.audit import sample
from bongda.core.ban_giao import table,idx,sha
from bongda.press.build import write_csv
def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument("root",type=Path);p.add_argument("--size",type=int,default=160);p.add_argument("--seed",type=int,default=26111193);a=p.parse_args();q=a.root/"qa";q.mkdir(exist_ok=True);s=a.root/"snapshot"
 rows,fields=sample(s,a.size,a.seed)
 write_csv(q/"mau_graph.tsv",rows,fields,"\t")
 meta=dict(seed=a.seed,n=a.size,graph_edges=len(table(s/"facts.csv")),facts_sha256=sha((s/"facts.csv").read_bytes()),selection="uniform without replacement, sorted fact_id; one judgement per fact")
 (q/"mau_graph.json").write_text(json.dumps(meta,indent=2))
if __name__=="__main__":main()
