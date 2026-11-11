"""Check counts, provenance, direction, uniqueness, source payloads and every text span."""
import argparse,json,re
from collections import Counter,defaultdict
from pathlib import Path
from urllib.parse import urlsplit
from bongda.core.ban_giao import table,idx,sha,jlines,require
from bongda.core.ontology import ENDS
from bongda.press.build import NEWS_DOMAINS
from bongda.collect.danh_sach_tre_bao import TRUSTED,domain

EXTRA=dict(GOP_MAT_TRONG_TRAN=("Club","Match"),THUOC_GIAI_DAU=("Match","Competition"),DA_CHINH_TRONG_TRAN=("Person","Match"),DANG_KY_DU_BI_TRONG_TRAN=("Person","Match"),VAO_SAN_THAY_NGUOI_TRONG_TRAN=("Person","Match"))
EXTRA.update({r:("Person","Club") for r in ["CO_TEN_TRONG_DOI_HINH_MUA","CHUYEN_DI_TU","CHUYEN_DEN_CLB","CO_TEN_TRONG_DANH_SACH_CLB","DUOC_BAO_GHI_NHAN_THUOC_CLB"]})
def verify_snapshot(root):
    m=json.loads((root/"manifest.json").read_text());require(m["schema_version"]=="A9-1" and m["record_kind"]=="real","Manifest")
    for fn,digest in m["files_sha256"].items():require(sha((root/fn).read_bytes())==digest,fn)
    nodes=idx(table(root/"entities.csv"),"entity_id");facts=idx(table(root/"facts.csv"),"fact_id")
    docs=idx(jlines(root/"articles.jsonl"),"article_id");ev=idx(jlines(root/"evidence.jsonl"),"evidence_id")
    meta=idx(jlines(root/"event_attributes.jsonl"),"fact_id");raw=set(); connected=set();keys=set();games=defaultdict(set);leagues=Counter()
    allowed=TRUSTED|NEWS_DOMAINS|{"baolamdong.vn"};domains=Counter()
    for a in docs.values():
        u=a["canonical_url"];host=domain(u);fmt=a.get("source_format","editorial")
        require(host in allowed and urlsplit(u).scheme in {"http","https"} and not a.get("revid") and a["source_kind"]=="press",u)
        require(a["record_kind"]=="real" and a["clean_text"].strip() and sha(a["clean_text"].encode())==a["clean_sha256"],a["article_id"])
        require(a["retrieved_at"] and (a["published_at"] or fmt=="news_table"),"missing date: "+u)
        if a.get("data_url"):require(urlsplit(a["data_url"]).hostname=="gw.vnexpress.net" and a.get("public_page_sha") and host=="vnexpress.net",u)
        raw.update(x for x in (a["raw_sha256"],a.get("public_page_sha")) if x);domains[host]+=1
    for sig in raw:require(re.fullmatch("[0-9a-f]{64}",sig) and sha((root/"raw"/sig).read_bytes())==sig,sig)
    for e in ev.values():
        a=docs[e["article_id"]];start,end=e["start"],e["end"]
        require(e["fact_id"] in facts and e["role"]=="supports" and 0<=start<end<=len(a["clean_text"]) and a["clean_text"][start:end]==e["quote"],"quote: "+e["evidence_id"])
    for fid,f in facts.items():
        s,r,o,k=(f[i] for i in ("src_id","relation_type","dst_id","event_key"));e=ev[f["evidence_id"]]
        require(s!=o and k and (s,r,o,k) not in keys and f["status"]=="accepted",fid);keys.add((s,r,o,k));connected.update([s,o])
        a,b=(nodes[x]["type"] for x in (s,o))
        require((a,b)==EXTRA.get(r) if r in EXTRA else a in ENDS[r][0] and b in ENDS[r][1],fid)
        require((e["fact_id"],e["article_id"],docs[e["article_id"]]["canonical_url"],e["quote"])==(fid,f["article_id"],f["article_url"],f["quote"]),fid)
        if r=="GOP_MAT_TRONG_TRAN":games[o].add(s)
        if r=="THUOC_GIAI_DAU":leagues[s]+=1
    mids={n for n,v in nodes.items() if v["type"]=="Match"}
    require(set(nodes)==connected and len(docs)==m["article_count"] and all(len(games[i])==2 and leagues[i]==1 for i in mids),"entity/match integrity")
    for fid,attributes in meta.items():
        f=facts[fid]
        if f["dst_id"] in mids and "club_id" in attributes:require(attributes["club_id"] in games[f["dst_id"]],fid)
    st=json.loads((root/"stats.json").read_text());require(st["edges"]==len(facts) and st["nodes"]==len(nodes) and st["types"]==Counter(f["relation_type"] for f in facts.values()),"stats")
    return dict(nodes=len(nodes),edges=len(facts),relation_types=len(st["types"]),source_urls=st["source_urls"],evidence_spans=len(ev),raw_objects=len(raw),matches=len(mids),non_match_nodes=len(nodes)-len(mids),wiki_source_documents=0)
if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("snapshot",type=Path);print(json.dumps(verify_snapshot(p.parse_args().snapshot),ensure_ascii=False,indent=2))
