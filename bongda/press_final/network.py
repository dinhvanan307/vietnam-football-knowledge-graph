"""Graph assembly, evidence lineage and integrity checks for the A9 press release."""
from __future__ import annotations
import csv,gzip,hashlib,json,re,shutil
from collections import Counter,defaultdict
from pathlib import Path
from urllib.parse import urlsplit
from bongda.core.ban_giao import enc,idx,jlines,table,sha
from bongda.press.build import write_csv,write_lines
from bongda.press_final.clubs import NAMES,key
def token(*parts):return hashlib.sha256("\x1f".join(map(str,parts)).encode()).hexdigest()[:22]
def tidy(s):return " ".join(s.split())
def data_object(path):
    b=path.read_bytes()
    return gzip.decompress(b) if path.suffix==".gz" else b
def iso_day(date):return bool(re.fullmatch(r"(?:19|20)\d\d-\d\d-\d\d",date or ""))
class Graph:
    def __init__(self,parent,review,version="A9"):
        self.version=version
        self.nodes=idx(table(parent/"entities.csv"),"entity_id")
        rejected={r["fact_id"] for r in table(review,"\t") if r["verdict"]!="DUNG"}
        self.docs=idx(jlines(parent/"articles.jsonl"),"article_id")
        self.raw={k:parent/"raw"/a["raw_sha256"] for k,a in self.docs.items()}
        self.facts={};self.emap={};self.attrs={};self.logs=Counter()
        self.teams=defaultdict(set);self.people=defaultdict(set);self.byteam=defaultdict(set)
        self.matchdata={};self.pairdates=defaultdict(set);self.conflicts=set()
        for f in table(parent/"facts.csv"):
            title=self.docs[f["article_id"]]["title"]
            if f["fact_id"] in rejected:continue
            if f["relation_type"]=="KY_LUAT" and re.search(r"U\.?\s*(?:15|17|19|21)",title,re.I):
                continue  # age-group sanction alone does not prove affiliation to a professional club
            self.facts[f["fact_id"]]=f
            if self.nodes[f["src_id"]]["type"]=="Person" and self.nodes[f["dst_id"]]["type"]=="Club":
                self.teams[f["src_id"]].add(f["dst_id"])
        for n in self.nodes.values():
            if n["type"]=="Person":
                self.people[key(n["canonical_name"].split(" (")[0])].add(n["entity_id"])
        self.emap={e["evidence_id"]:e for e in jlines(parent/"evidence.jsonl") if e["fact_id"] in self.facts}
        self.attrs={e["fact_id"]:e for e in jlines(parent/"event_attributes.jsonl") if e["fact_id"] in self.facts}
        self.pidx={};self.labels_by_pid=defaultdict(set);self.pidnames=defaultdict(set)
        self.logs["base_accepted"]=len(self.facts)
    def document(self,url,title,lines,raw_path,stamp,published,mode,source,api="",page_sha="",page_path=None):
        text="\n\n".join(lines);raw_sig=raw_path.name.split(".")[0]
        aid="a9_"+token(url,raw_sig,sha(text.encode()));self.docs[aid]=dict(article_id=aid,canonical_url=url,title=title,clean_text=text,clean_sha256=sha(text.encode()),
            raw_sha256=raw_sig,source_kind="press",source=source,published_at=published,retrieved_at=stamp,story_group=aid,record_kind="real",pageid="",revid="",revision_at="",
            source_format=mode,data_url=api,public_page_sha=page_sha)
        self.raw[aid]=raw_path
        if page_path:self.raw[page_sha]=page_path
        return aid
    def node(self,ident,name,kind,role):
        if ident not in self.nodes:self.nodes[ident]=dict(entity_id=ident,canonical_name=name,type=kind,role=role)
        return ident
    def club(self,c):return self.node(c,NAMES[c],"Club","Club")
    def link(self,s,r,d,event,period,aid,quote,method,attrs=None):
        if not s or not d or s==d or not quote:raise ValueError((s,r,d,event))
        text=self.docs[aid]["clean_text"];offset=text.find(quote)
        if offset<0:raise ValueError("evidence not found")
        f="f9_"+token(s,r,d,event); e="e9_"+token(f,aid,offset)
        if f not in self.facts:
            self.facts[f]=dict(fact_id=f,src_id=s,relation_type=r,dst_id=d,event_key=event,period=period,status="accepted",method=method,
                article_id=aid,evidence_id=e,article_url=self.docs[aid]["canonical_url"],quote=quote)
            if attrs:self.attrs[f]=dict(fact_id=f,**attrs)
        self.emap.setdefault(e,dict(evidence_id=e,fact_id=f,article_id=aid,role="supports",quote=quote,start=offset,end=offset+len(quote)))
        return f
    def match(self,one,two,date,league,score,aid,quote,method):
        if not one or not two or one==two or not iso_day(date) or date>"2026-11-11":return None
        c,lname=league
        # The HCMC name was reassigned in July 2025. The top-flight predecessor
        # cannot be the similarly named second-division participant.
        if self.version!="A9" and c=="g9-vl2" and date>="2025-07-14" and "c-hcm" in (one,two):
            self.logs["division_name_conflict_rows_held"]+=1;return None
        a,b=sorted((one,two));canon=score if one==a else score[::-1]
        mid="m9_"+token(c,a,b,date)
        if mid in self.matchdata and self.matchdata[mid]["score"]!=canon:
            self.conflicts.add(mid);return None
        self.club(a);self.club(b);self.node(c,lname,"Competition","League")
        self.node(mid,f"{NAMES[a]} – {NAMES[b]} ({date})","Match","Fixture")
        self.matchdata[mid]=dict(pair=(a,b),date=date,league=c,score=canon)
        self.pairdates[a,b].add(mid)
        for t in [a,b]:self.link(t,"GOP_MAT_TRONG_TRAN",mid,mid,date,aid,quote,method)
        self.link(mid,"THUOC_GIAI_DAU",c,mid,date,aid,quote,method,dict(score=("-".join(map(str,canon))),score_team1=a,score_team2=b))
        return mid
    def register_person_names(self,pid,n):
        if pid and isinstance(n,str) and n.strip() and not re.search(r"[\ufffdÂÃ]|(?:áº|á»)",n):
            self.labels_by_pid[pid].add(tidy(n))
    def preindex_people(self):
        for pid,names in self.labels_by_pid.items():
            for n in names:
                k=key(n)
                if len(k.split())>=2 and not re.search(r"\b[A-Z]\.",n):self.pidnames[k].add(pid)
    def person(self,pid):
        if pid in self.pidx:return self.pidx[pid]
        names=self.labels_by_pid.get(pid)
        if not names:return None
        def quality(n):return (not bool(re.search(r'\b[A-Z]\.',n)),not n.isascii(),len(n.split()),len(n))
        name=max(sorted(names),key=quality);k=key(name)
        if not k or re.search(r'\b[A-Z]\.',name) or k in {"unknown","cau thu","undefined"}:return None
        candidates=set()
        for n in names:
            nk=key(n)
            if len(self.pidnames[nk])>1:return None
            if len(nk.split())>=2:candidates.update(self.people.get(nk,set()))
        if len(candidates)>1:return None
        ident=next(iter(candidates),"p9_vne_"+str(pid))
        self.node(ident,name,"Person","Player");self.pidx[pid]=ident
        for n in names:
            if len(key(n).split())>=2:self.people[key(n)].add(ident)
        return ident
    def dump(self,root):
        excluded={i for i,f in self.facts.items() if f["src_id"] in self.conflicts or f["dst_id"] in self.conflicts}
        facts={i:f for i,f in self.facts.items() if i not in excluded}
        es={i:e for i,e in self.emap.items() if e["fact_id"] in facts}
        used={e["article_id"] for e in es.values()};nodes={n for f in facts.values() for n in (f["src_id"],f["dst_id"])}
        root.mkdir(parents=True,exist_ok=True);(root/"raw").mkdir(exist_ok=True)
        for aid in sorted(used):
            a=self.docs[aid]
            for sig,path in [(a["raw_sha256"],self.raw[aid]),(a.get("public_page_sha",""),self.raw.get(a.get("public_page_sha","")))]:
                if not sig:continue
                file=root/"raw"/sig
                if not file.exists():
                    raw=data_object(path)
                    if sha(raw)!=sig:raise ValueError("raw digest "+sig)
                    file.write_bytes(raw)
        for fn,items,fields in [("entities.csv",[self.nodes[i] for i in sorted(nodes)],["entity_id","type","canonical_name","role"]),
                                ("facts.csv",[facts[i] for i in sorted(facts)],list(next(iter(facts.values()))))]:
            write_csv(root/fn,items,fields)
        write_lines(root/"articles.jsonl",[self.docs[i] for i in sorted(used)])
        write_lines(root/"evidence.jsonl",[es[i] for i in sorted(es)])
        write_lines(root/"event_attributes.jsonl",[self.attrs[f] for f in sorted(set(self.attrs)&set(facts))])
        formats=Counter(self.docs[i].get("source_format","editorial") for i in used)
        fm=defaultdict(set)
        for e in es.values():fm[self.docs[e["article_id"]].get("source_format","editorial")].add(e["fact_id"])
        stats=dict(version=self.version,nodes=len(nodes),edges=len(facts),entities_by_type=dict(Counter(self.nodes[i]["type"] for i in nodes)),types=dict(Counter(f["relation_type"] for f in facts.values())),methods=dict(Counter(f["method"] for f in facts.values())),
            source_urls=len({self.docs[i]["canonical_url"] for i in used}),domains=dict(Counter(urlsplit(self.docs[i]["canonical_url"]).hostname for i in used)),documents_by_format=dict(formats),
            facts_with_editorial_support=len(fm["editorial"]),facts_with_table_support=len(fm["news_table"]),facts_with_both=len(fm["editorial"]&fm["news_table"]),conflicting_matches_held=len(self.conflicts),stages=dict(self.logs))
        (root/"stats.json").write_text(json.dumps(stats,ensure_ascii=False,indent=2))
        (root/"manifest.json").write_text(enc(dict(schema_version="A9-1",article_count=len(used),record_kind="real",files_sha256={f:sha((root/f).read_bytes()) for f in ["entities.csv","facts.csv","evidence.jsonl","articles.jsonl","event_attributes.jsonl","stats.json"]})))
        return stats
