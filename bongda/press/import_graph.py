"""Import a press-only snapshot twice into the dedicated local Neo4j instance."""
import argparse
import json
from pathlib import Path

from neo4j import GraphDatabase
from bongda.core.ban_giao import idx, table
from bongda.press.build import verify_news
from bongda.storage.nhap_neo4j_a3 import compare, payload
from bongda.storage.kiem_tra_neo4j_a3 import fingerprint

def run(root,*,verify=verify_news,uri="bolt://127.0.0.1:7697"):
    snap=root/"snapshot";verify(snap)
    nodes=idx(table(snap/"entities.csv"),"entity_id")
    facts=idx(table(snap/"facts.csv"),"fact_id")
    attrs=payload(snap,facts)
    extra={r["id"]:r["meta"] for r in attrs}
    rows=[]
    for k,f in facts.items():
        props={name:value for name,value in f.items() if name not in {"src_id","dst_id","relation_type"}}
        rows.append(dict(src=f["src_id"],dst=f["dst_id"],rel=f["relation_type"],id=k,props={**props,**extra[k]}))
    ns=[dict(id=n["entity_id"],name=n["canonical_name"],kind=n["type"],role=n["role"]) for n in nodes.values()]
    password=dict(x.split("=",1) for x in (root/".env").read_text().splitlines() if "=" in x)["NEO4J_PASSWORD"]
    with GraphDatabase.driver(uri,auth=("neo4j",password)) as driver, driver.session(database="neo4j") as db:
        before=fingerprint(db)
        if before["nodes"] or before["edges"]:compare(db,nodes,facts,attrs)
        db.run("CREATE CONSTRAINT news_entity_id IF NOT EXISTS FOR (n:Entity) REQUIRE n.entity_id IS UNIQUE").consume()
        results=[]
        for _ in range(2):
            with db.begin_transaction() as tx:
                a=tx.run("""UNWIND $rows AS x MERGE (n:Entity {entity_id:x.id})
                    SET n:$(x.kind), n.name=x.name,n.kind=x.kind,n.role=x.role""",rows=ns).consume().counters.nodes_created
                b=tx.run("""UNWIND $rows AS x MATCH (s:Entity {entity_id:x.src}),(o:Entity {entity_id:x.dst})
                    MERGE (s)-[r:$(x.rel) {fact_id:x.id}]->(o) SET r+=x.props""",rows=rows).consume().counters.relationships_created
                tx.commit()
            compare(db,nodes,facts,attrs)
            results.append(dict(**fingerprint(db),created_nodes=a,created_edges=b))
        if results[-1]["created_nodes"] or results[-1]["created_edges"] or results[0]["graph_sha256"]!=results[1]["graph_sha256"]:
            raise ValueError("Second import changed the graph")
    fn="neo4j_check.json" if not (root/"neo4j_check.json").exists() else "neo4j_recheck.json"
    (root/fn).write_text(json.dumps(dict(before=before,runs=results,full_property_comparison=True),indent=2)+"\n")
    print(results[-1]["nodes"],results[-1]["edges"],results[-1]["types"])
if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("root",type=Path)
    run(p.parse_args().root)
