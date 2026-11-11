"""Evaluate the text-to-match step on independently selected newsroom pages with locked reading notes."""
import argparse,collections,csv,gzip,json
from pathlib import Path
from types import SimpleNamespace
from bongda.core.ban_giao import table,idx,jlines,sha
from bongda.press.build import write_csv
from bongda.press_final.editorial import docdata,match_of
def run(s,lot,out,v2=False):
  from bongda.press_final.match_text import read_sggp,resolve
  facts=table(s/"facts.csv");meta=idx(jlines(s/"event_attributes.jsonl"),"fact_id");by=collections.defaultdict(set);games={};docs=jlines(s/"articles.jsonl");used={r["canonical_url"] for r in docs};known={r["raw_sha256"] for r in docs}
  for f in facts:
    if f["relation_type"]!="THUOC_GIAI_DAU":continue
    m=meta[f["fact_id"]];pair=(m["score_team1"],m["score_team2"]);mid=f["src_id"];by[pair].add(mid)
    games[mid]=dict(pair=pair,date=f["period"],score=tuple(int(x) for x in m["score"].split("-")))
  g=SimpleNamespace(pairdates=by,matchdata=games);gold=idx(table(lot/"gold.tsv","\t"),"index");urls=json.loads((lot/"locked.json").read_text())["urls"]
  rows=[];tp=fp=fn=0;neg=multi=0
  for i,u in enumerate(urls,1):
    raw=gzip.decompress((lot/f"{i:02}.html.gz").read_bytes())
    if sha(raw) in known or u in used:raise ValueError("Test leakage: "+u)
    t,stamp,lines=(read_sggp(raw) if v2 else docdata("sggp",raw));mid,quote=(resolve if v2 else match_of)(g,t,lines,stamp[:10])
    a=gold[str(i)];state=a["status"];target={a["club1"],a["club2"]} if state=="match" else set();pred=set(games[mid]["pair"]) if mid else set()
    # Both club-to-event edges require the same, correct match. A wrong match yields no true edge.
    pos=(len(pred) if pred and pred==target else 0);wrong=len(pred)-pos;missing=len(target)-pos
    if state=="multi":multi+=1;pos=wrong=missing=0
    else:tp+=pos;fp+=wrong;fn+=missing;neg+=state=="negative"
    rows.append(dict(index=i,url=u,title=t,publication=stamp[:10],scope=state,expected="|".join(sorted(target)),predicted="|".join(sorted(pred)),predicted_match=mid or "",explanation=a["reason"],matched_text=quote or "",TP=pos,FP=wrong,FN=missing))
  def ratio(a,b):return a/b if b else None
  score=dict(articles=len(rows),scored=len(rows)-multi,multiple_primary_excluded=multi,negatives=neg,positive_articles=len(rows)-multi-neg,TP=tp,FP=fp,FN=fn,precision=ratio(tp,tp+fp),recall=ratio(tp,tp+fn),F1=ratio(2*tp,2*tp+fp+fn),correctly_linked_matches=tp//2,predicted_matches=(tp+fp)//2,gold_sha256=sha((lot/"gold.tsv").read_bytes()),selection_pool=json.loads((lot/"locked.json").read_text())["pool"],known_overlap_by_url_or_raw_hash=0)
  tag="lo_bao_moi_v2" if v2 else "lo_bao_moi"
  write_csv(out/(tag+".tsv"),rows,list(rows[0]),"\t");(out/(tag+".json")).write_text(json.dumps(score,indent=2,ensure_ascii=False)+"\n");print(score)
if __name__=="__main__":
 p=argparse.ArgumentParser(description=__doc__);[p.add_argument(k,type=Path) for k in ("snapshot","lot","out")];p.add_argument("--v2",action="store_true");a=p.parse_args();run(a.snapshot,a.lot,a.out,a.v2)
