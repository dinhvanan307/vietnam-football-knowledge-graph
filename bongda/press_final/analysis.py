"""Report observed connectivity; count distinct neighbors separately from reported events."""
from collections import Counter,defaultdict
import argparse,json
from pathlib import Path
from bongda.core.ban_giao import table,idx
def run(s):
 n=idx(table(s/"entities.csv"),"entity_id");f=table(s/"facts.csv");adj=defaultdict(set);degree=Counter()
 for r in f:
  a,b=r["src_id"],r["dst_id"];adj[a].add(b);adj[b].add(a);degree.update((a,b))
 yet=set(n);sizes=[]
 while yet:
  q=[yet.pop()];count=0
  while q:
   k=q.pop();count+=1;sub=adj[k]&yet;yet.difference_update(sub);q.extend(sub)
  sizes.append(count)
 return dict(weak_components=len(sizes),largest_component=max(sizes),vertices=len(n),directed_event_edges=len(f),mean_distinct_neighbors=sum(map(len,adj.values()))/len(n),largest_component_fraction=max(sizes)/len(n),top_clubs=[dict(id=k,name=n[k]["canonical_name"],neighbors=len(adj[k]),incident_events=degree[k]) for k in sorted([i for i,v in n.items() if v["type"]=="Club"],key=lambda i:(-len(adj[i]),i))[:8]])
if __name__=="__main__":
 p=argparse.ArgumentParser(description=__doc__);p.add_argument("root",type=Path);r=p.parse_args().root;(r/"network_analysis.json").write_text(json.dumps(run(r/"snapshot"),indent=2,ensure_ascii=False)+"\n")
