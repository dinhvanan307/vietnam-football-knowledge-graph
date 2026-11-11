"""Draw a reproducible simple random sample of accepted news facts."""
import argparse
from pathlib import Path
import random
from bongda.core.ban_giao import idx,jlines,table,sha
from bongda.press.build import write_csv
def sample(root,size=100,seed=20261111):
    nodes=idx(table(root/"entities.csv"),"entity_id")
    arts=idx(jlines(root/"articles.jsonl"),"article_id")
    facts=sorted(table(root/"facts.csv"),key=lambda r:r["fact_id"])
    ev=idx(jlines(root/"evidence.jsonl"),"evidence_id")
    fields="index fact_id source relation target period title url quote context method".split()
    rows=[]
    for i,f in enumerate(random.Random(seed).sample(facts,size),1):
        a=arts[f["article_id"]]; e=ev[f["evidence_id"]]; text=a["clean_text"]
        start=e.get("context_start",max(0,e["start"]-300));end=e.get("context_end",min(len(text),e["end"]+300))
        rows.append(dict(index=i,fact_id=f["fact_id"],source=nodes[f["src_id"]]["canonical_name"],target=nodes[f["dst_id"]]["canonical_name"],
                         period=f["period"],title=a["title"],url=a["canonical_url"],quote=f["quote"],relation=f["relation_type"],context=text[start:end],method=f["method"]))
    return rows,fields
if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("snapshot",type=Path);p.add_argument("output",type=Path)
    a=p.parse_args()
    rows,fields=sample(a.snapshot)
    write_csv(a.output,rows,fields,"\t")
    print("Frame SHA-256:",sha((a.snapshot/"facts.csv").read_bytes()))
