"""Build a news-only graph in a NEW directory from frozen source documents."""
import argparse
import csv
import hashlib
import json
import re
import shutil
import tempfile
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlsplit

from bongda.core.ban_giao import enc, idx, jlines, sha, table, verify
from bongda.core.ontology import ENDS
from bongda.press.rosters import RELATION, article, digest, key, squad

NEWS_DOMAINS = set("tuoitre.vn thanhnien.vn vtv.vn bongdaplus.vn baodanang.vn baokhanhhoa.vn tienphong.vn vov.vn phunuvietnam.vn baoxaydung.vn".split())
AMBIGUOUS = {"bùi tiến dũng", "nguyễn văn toàn", "nguyễn văn tùng"}
KH = "club-press-khanhhoa-2023"
def write_csv(path, rows, fields, delimiter=","):
    with path.open("w", newline="", encoding="utf-8") as f:
        out=csv.DictWriter(f,fieldnames=fields,delimiter=delimiter)
        out.writeheader()
        out.writerows(rows)
def write_lines(path,rows):
    path.write_text("".join(enc(x)+"\n" for x in rows),encoding="utf-8")
def name_key(name):
    return key(re.split(r"\s*\(",name)[0])
def clean_name(name):
    words=name.split()
    return 3<=len(words)<=6 and all(re.fullmatch(r"[^\W\d_]+(?:[-’'][^\W\d_]+)*",w,re.U)
        and (w[0].isupper() or w in {"de","do","da","van","dos"}) for w in words)
def press_article(a):
    host=(urlsplit(a["canonical_url"]).hostname or "").removeprefix("www.")
    return a["source_kind"]=="press" and host in NEWS_DOMAINS and not a["revid"]
def verify_news(root):
    verify(root,False)
    articles=idx(jlines(root/"articles.jsonl"),"article_id")
    facts=idx(table(root/"facts.csv"),"fact_id")
    nodes=idx(table(root/"entities.csv"),"entity_id")
    ev=idx(jlines(root/"evidence.jsonl"),"evidence_id")
    if not all(press_article(a) for a in articles.values()):raise ValueError("Non-news source")
    for e in ev.values():
        a=articles[e["article_id"]]
        if e["fact_id"] not in facts or e["role"]!="supports" or not e["quote"] or not 0<=e["start"]<e["end"]<=len(a["clean_text"]) or a["clean_text"][e["start"]:e["end"]]!=e["quote"]:
            raise ValueError("Evidence mismatch: "+e["evidence_id"])
    connected=set(); events=set()
    ends={**ENDS,RELATION:({"Person"},{"Club"})}
    for f in facts.values():
        e=ev[f["evidence_id"]];a=articles[e["article_id"]];s,o=f["src_id"],f["dst_id"]
        domain,target=ends[f["relation_type"]]
        k=(s,f["relation_type"],o,f["event_key"])
        if (e["fact_id"],e["article_id"],a["canonical_url"],e["quote"])!=(f["fact_id"],f["article_id"],f["article_url"],f["quote"]) or k in events or f["status"]!="accepted" or not f["event_key"] or nodes[s]["type"] not in domain or nodes[o]["type"] not in target:
            raise ValueError("Invalid fact: "+f["fact_id"])
        events.add(k);connected.update([s,o])
    if connected!=set(nodes):raise ValueError("Unconnected or missing entity")
    return len(nodes),len(facts),len({k[1] for k in events})

def build(parent,archive,stage):
    old=idx(table(parent/"entities.csv"),"entity_id")
    oldfacts=idx(table(parent/"facts.csv"),"fact_id")
    arts=idx((a for a in jlines(parent/"articles.jsonl") if press_article(a)),"article_id")
    by_fact=defaultdict(list)
    for e in jlines(parent/"evidence.jsonl"):
        if e["article_id"] in arts and e["role"]=="supports":by_fact[e["fact_id"]].append(e)
    facts={}; nodes={}; evidence=[]; meta=[]; hold=[]; article_log=[]
    # The two cross-source sponsorship edges have direct editorial confirmation.
    cross_period={"f_5482994e1ed48e66b588":"mùa 2019","f_6dc5c35936951ecb3287":"từ mùa 2017–2018, thời hạn 2 năm"}
    for fid,refs in by_fact.items():
        f=oldfacts[fid].copy()
        e=next((v for v in refs if v["evidence_id"]==f["evidence_id"]),None)
        if e is None:
            if fid not in cross_period:raise ValueError("Review non-press primary before import: "+fid)
            e=refs[0];f.update(period=cross_period[fid],event_key=cross_period[fid],method="press_sponsorship_reviewed")
        a=arts[e["article_id"]]
        f.update(evidence_id=e["evidence_id"],article_id=a["article_id"],article_url=a["canonical_url"],quote=e["quote"])
        for field in ("src_id","dst_id"):
            n=old[f[field]].copy()
            if n["entity_id"]=="club-w2452083":
                if fid not in {"f_5cb36ca1b692bce02808","f_8a884d0d2e5309caaaf0"}:raise ValueError("Ambiguous historical club")
                n.update(entity_id=KH,canonical_name="CLB Khánh Hòa");f[field]=KH
            nodes[n["entity_id"]]=n
        evidence.extend(refs); facts[fid]=f
    used={e["article_id"] for e in evidence};arts={i:a for i,a in arts.items() if i in used}
    rawpaths={i:parent/"raw"/a["raw_sha256"] for i,a in arts.items()}
    base_n,base_f=len(nodes),len(facts)
    aliases=defaultdict(set)
    for n in nodes.values():
        if n["type"]=="Person":aliases[name_key(n["canonical_name"])].add(n["entity_id"])
    candidates=[]; seen_articles=set(); by_name_club=defaultdict(set); per_team=Counter()
    for m in table(archive/"sources.tsv","\t"):
        path=archive/"html"/m["raw_sha256"]
        a=article(m,path.read_bytes())
        native=re.search(r"-(\d+)\.html$",a["canonical_url"])[1]
        if native in seen_articles:continue
        seen_articles.add(native)
        rows,reason=squad(a)
        article_log.append(dict(article_id=a["article_id"],url=a["canonical_url"],reason=reason,mentions=len(rows)))
        if not rows:continue
        arts[a["article_id"]]=a;rawpaths[a["article_id"]]=path
        for row in rows:
            row["article_id"]=a["article_id"];candidates.append(row)
            k=name_key(row["name"]);by_name_club[k].add(row["club"])
            per_team[(a["article_id"],k)]+=1
    linked=set()
    for row in candidates:
        k=name_key(row["name"]);reasons=[]
        if not clean_name(row["name"]):reasons.append("short or incomplete name")
        if len(aliases[k])>1 or k in AMBIGUOUS:reasons.append("ambiguous identity")
        if len(by_name_club[k])>1:reasons.append("multiple clubs, identity needs review")
        if per_team[(row["article_id"],k)]>1:reasons.append("duplicate within roster")
        if reasons:
            hold.append(dict(article_id=row["article_id"],name=row["name"],club=row["club"],season=row["season"],reason="; ".join(reasons)));continue
        sid=next(iter(aliases[k]),"p_news_"+digest(k))
        cid=row["club"];season=row["season"];aid=row["article_id"];a=arts[aid]
        if sid in nodes and "Player" not in nodes[sid]["role"]:
            hold.append(dict(article_id=aid,name=row["name"],club=cid,season=season,reason="role mismatch"));continue
        nodes.setdefault(sid,dict(entity_id=sid,type="Person",canonical_name=row["name"],role="Player"))
        nodes.setdefault(cid,dict(entity_id=cid,type="Club",canonical_name=row["club_name"],role="Club"))
        fid="f_news_"+digest("|".join((sid,RELATION,cid,season)))
        eid="e_news_"+digest(fid+"|"+aid)
        if eid in linked:continue
        linked.add(eid)
        lines=a["clean_text"].split("\n\n");starts=[];offset=0
        for line in lines:starts.append(offset);offset+=len(line)+2
        start=starts[row["line_index"]];end=start+len(row["line"])
        evidence.append(dict(article_id=aid,fact_id=fid,evidence_id=eid,role="supports",start=start,end=end,
                    quote=row["line"],context_start=starts[row["section_index"]],context_end=end))
        if fid not in facts:
            facts[fid]=dict(fact_id=fid,src_id=sid,dst_id=cid,relation_type=RELATION,event_key=season,period=season,
                status="accepted",method="press_squad_position_list",evidence_id=eid,article_id=aid,article_url=a["canonical_url"],quote=row["line"])
            meta.append(dict(fact_id=fid,section_heading=row["heading"],position_as_printed=row["position"],name_as_printed=row["name"]))
    used={e["article_id"] for e in evidence}
    articles=[arts[k] for k in sorted(used)]
    (stage/"raw").mkdir()
    for a in articles:
        target=stage/"raw"/a["raw_sha256"]
        if not target.exists():shutil.copyfile(rawpaths[a["article_id"]],target)
    write_lines(stage/"articles.jsonl",articles)
    for file,rows,field in [("evidence.jsonl",evidence,"evidence_id"),("event_attributes.jsonl",meta,"fact_id")]:
        write_lines(stage/file,sorted(rows,key=lambda x:x[field]))
    for file,rows,fields in [("entities.csv",nodes,("entity_id","type","canonical_name","role")),("facts.csv",facts,next(iter(oldfacts.values())).keys())]:
        write_csv(stage/file,[rows[k] for k in sorted(rows)],fields)
    write_csv(stage/"sources_checked.tsv",article_log,["article_id","url","reason","mentions"],"\t")
    write_csv(stage/"needs_review.tsv",hold,["article_id","name","club","season","reason"],"\t")
    manifest=dict(schema_version="1",record_kind="real",article_count=len(articles),articles_sha256=sha((stage/"articles.jsonl").read_bytes()))
    (stage/"manifest.json").write_text(enc(manifest)+"\n")
    n,e,t=verify_news(stage)
    stats=dict(version="A8-press",nodes=n,edges=e,relation_types=t,press_articles=len(articles),wiki_articles=0,
        press_base_nodes=base_n,press_base_edges=base_f,pilot_articles_examined=len(article_log),
        pilot_articles_contributing=len({f["article_id"] for f in evidence if f["evidence_id"] in linked}),
        pilot_net_nodes=n-base_n,pilot_new_edges=e-base_f,pilot_mentions=len(candidates),held_mentions=len(hold),
        types=dict(Counter(f["relation_type"] for f in facts.values())),sources=dict(Counter(urlsplit(a["canonical_url"]).hostname for a in articles)),
        targets=dict(nodes=2000,edges=5000,relation_types=10))
    (stage/"stats.json").write_text(json.dumps(stats,ensure_ascii=False,indent=2)+"\n")
    return stats

if __name__=="__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ["parent","archive","output"]:parser.add_argument(name,type=Path)
    args=parser.parse_args()
    if args.output.exists():parser.error("Choose a new output directory")
    with tempfile.TemporaryDirectory(dir=args.output.parent) as tmp:
        stage=Path(tmp)/"snapshot";stage.mkdir()
        result=build(args.parent,args.archive,stage)
        stage.rename(args.output)
    print(enc(result))
