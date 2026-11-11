"""Portable submission tables: event data, source URL and identifiers, without entire newspaper documents."""
import argparse,csv,json,os,shutil
from collections import Counter
from pathlib import Path
from bongda.core.ban_giao import table,idx,jlines,sha
from bongda.press.build import write_csv
def export(s,d):
 from bongda.press_final.verify import verify_snapshot
 verify_snapshot(s);d.mkdir(parents=True,exist_ok=True);shutil.copyfile(s/"entities.csv",d/"entities.csv")
 fields="fact_id src_id relation_type dst_id event_key period method article_url evidence_id club_id".split()
 meta=idx(jlines(s/"event_attributes.jsonl"),"fact_id"); rows=[]
 for f in table(s/"facts.csv"):
  rows.append({k:(meta.get(f["fact_id"],{}).get(k,"") if k=="club_id" else f[k]) for k in fields})
 write_csv(d/"facts.csv",rows,fields);m=dict(version=json.loads((s/"stats.json").read_text())["version"],nodes=len(table(d/"entities.csv")),edges=len(rows),types=dict(Counter(r["relation_type"] for r in rows)),sha256={x:sha((d/x).read_bytes()) for x in ["entities.csv","facts.csv"]})
 (d/"manifest.json").write_text(json.dumps(m,indent=2,ensure_ascii=False)+"\n");return m
def read(d):
 m=json.loads((d/"manifest.json").read_text())
 for k,v in m["sha256"].items():
  if sha((d/k).read_bytes())!=v:raise ValueError("Hash: "+k)
 ns=idx(table(d/"entities.csv"),"entity_id");fs=idx(table(d/"facts.csv"),"fact_id")
 if len(ns)!=m["nodes"] or len(fs)!=m["edges"] or Counter(x["relation_type"] for x in fs.values())!=m["types"]:raise ValueError("Counts")
 for x in fs.values():
  if x["src_id"] not in ns or x["dst_id"] not in ns or not x["article_url"]:raise ValueError(x["fact_id"])
 return m,ns,fs
def restore(d,env,uri):
 from neo4j import GraphDatabase
 m,ns,fs=read(d);pw=dict(s.split("=",1) for s in env.read_text().splitlines() if "=" in s)["NEO4J_PASSWORD"]
 with GraphDatabase.driver(uri,auth=("neo4j",pw)) as driver,driver.session() as db:
  def inspect():
   n={r["id"]:r["k"] for r in db.run("MATCH (n) RETURN n.entity_id AS id,n.kind AS k")}
   f={r["i"]:(r["s"],r["t"],r["o"]) for r in db.run("MATCH (a)-[r]->(b) RETURN r.fact_id AS i,a.entity_id AS s,type(r) AS t,b.entity_id AS o")}
   return n,f
  target=({k:v["type"] for k,v in ns.items()},{k:(v["src_id"],v["relation_type"],v["dst_id"]) for k,v in fs.items()})
  before=inspect()
  if before!=({},{}) and before!=target:raise ValueError("Use a separate empty Neo4j instance; existing graph differs.")
  db.run("CREATE CONSTRAINT compact_entity_id IF NOT EXISTS FOR (n:Entity) REQUIRE n.entity_id IS UNIQUE").consume()
  with db.begin_transaction() as t:
   t.run("UNWIND $rows AS x MERGE (n:Entity {entity_id:x.entity_id}) ON CREATE SET n:$(x.type), n.kind=x.type,n.name=x.canonical_name,n.role=x.role",rows=list(ns.values())).consume()
   for i in range(0,len(fs),650):
    rows=list(fs.values())[i:i+650];t.run("UNWIND $rows AS x MATCH (a:Entity {entity_id:x.src_id}),(b:Entity {entity_id:x.dst_id}) MERGE (a)-[r:$(x.relation_type) {fact_id:x.fact_id}]->(b) ON CREATE SET r.period=x.period,r.event_key=x.event_key,r.method=x.method,r.article_url=x.article_url,r.evidence_id=x.evidence_id,r.club_id=CASE WHEN x.club_id='' THEN null ELSE x.club_id END",rows=rows).consume()
   t.commit()
  if inspect()!=target:raise ValueError("Restored graph differs from portable tables")
 return m
if __name__=="__main__":
 p=argparse.ArgumentParser(description=__doc__);p.add_argument("op",choices=["export","check","restore"]);p.add_argument("directory",type=Path);p.add_argument("--snapshot",type=Path);p.add_argument("--env",type=Path,default=Path(".env"));p.add_argument("--uri",default="bolt://127.0.0.1:7700");a=p.parse_args()
 m=export(a.snapshot,a.directory) if a.op=="export" else restore(a.directory,a.env,a.uri) if a.op=="restore" else read(a.directory)[0];print(m["nodes"],m["edges"],len(m["types"]))
