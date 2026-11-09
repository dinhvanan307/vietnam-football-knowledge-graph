"""Tạo snapshot A2 từ bản pilot và bằng chứng mùa giải. Không sửa pilot."""
import argparse,csv,json,os,re,shutil,unicodedata
from itertools import chain
from collections import Counter,defaultdict
from pathlib import Path
from ban_giao import enc,sha,table,jlines,verify
from gom_su_kien import group_articles
from doi_chieu_wiki import key
from trich_quan_he import write_csv
from doc_bien_ban import read_pages
PILOT=Path("work/pilot_01")
def compact(v):return " ".join(unicodedata.normalize("NFC",v).split())
def norm(v):return key(compact(v)).replace("–","-").replace("—","-")
def ident(v):return sha(v.encode())[:20]
def put_raw(src,dest):
    if not dest.exists():
        try:os.link(src,dest)
        except OSError:shutil.copyfile(src,dest)

class Resolver:
    def __init__(self, lookup_path=Path("work/a2_identity/person_club_map.json")):
        self.lookup=json.loads(lookup_path.read_bytes())
        self.tpl=json.loads(Path("work/a2_identity/template_map.json").read_bytes())
        bp=Path("work/a2_identity/football_pages.json")
        self.bios=json.loads(bp.read_bytes()) if bp.exists() else {}
        cp=Path("work/a2_identity/company_pages.json")
        self.companies=json.loads(cp.read_bytes()) if cp.exists() else {}
        self.alts=defaultdict(set);self.person_alts=defaultdict(set)
        self.entities={e["entity_id"]:e for e in table(PILOT/"entities.csv")}
        self.pilot_clubs={};self.registry={};self.reject=Counter()
        self.pilot_people={norm(e["canonical_name"]):i for i,e in self.entities.items() if e["type"]=="Person"}
        aliases={"c-cahn":["CAHN"],"c-hn":["HNFC"],"c-bd":["BFC"],"c-th":["ĐATH"],"c-hp":["HPFC"],"c-hagl":["HAGL"],"c-ht":["HLHT"],"c-nd":["TXNĐ"],"c-qn":["QNFC"],"c-dn":["SHBĐN"],"c-slna":["SLNA"],"c-binhdinh":["QNBĐ"],"c-tc":["TCVT"],"c-hcm":["HCMC"],"c-ph":["PHFC"]}
        for i,ts in aliases.items():
            for t in ts:
                name=self.tpl.get("Bản mẫu:"+t,"")
                record=self.lookup.get(name,{})
                if record.get("id"):self.pilot_clubs[record["id"]]=i
        for t in self.tpl.values():
            if t:
                a=re.sub(r"^Câu lạc bộ (bóng đá )?","",t)
                self.alts[norm(a)].add(t)
    def club(self,v):
        if re.search(r"(?i)\b(?:trẻ|U[.-]?\d{2})\b",v["name"]) and not re.search(r"(?i)\b(?:trẻ|U[.-]?\d{2})\b",v["key"]):return None
        title=self.tpl.get("Bản mẫu:"+v["key"]) if v["kind"]=="template" else v["key"]
        if v["kind"]=="text":
            possible=self.alts[norm(title)]
            title=next(iter(possible)) if len(possible)==1 else None
        record=self.lookup.get(title,{})
        if not record.get("id") or record.get("dab"):return None
        i=self.pilot_clubs.get(record["id"],"club-w"+str(record["id"]))
        self.entities.setdefault(i,dict(entity_id=i,type="Club",canonical_name=record["title"],role="Club"))
        self.registry[i]=dict(entity_id=i,wiki_id=record["id"],wiki_title=record["title"],basis="club_article")
        return i
    def observe(self,v):
        page=self.lookup.get(v["key"],{})
        if page.get("id") and not page.get("dab") and self.bios.get(str(page["id"]),{}).get("football"):
            for a in (v["name"],v["key"],re.sub(r"\s*\([^()]+\)$","",v["key"])):
                self.person_alts[norm(a)].add((page["id"],page["title"]))
    def venue(self,v):
        if not v or v["kind"]!="link":return None
        rec=self.lookup.get(v["key"],{})
        if not rec.get("id") or rec.get("dab") or not rec["title"].lower().startswith(("sân vận động","sân bóng")):return None
        eid="s-hd" if rec["title"].casefold()=="sân vận động hàng đẫy" else "stadium-w"+str(rec["id"])
        self.entities.setdefault(eid,dict(entity_id=eid,type="Stadium",canonical_name=rec["title"],role="Stadium"))
        self.registry[eid]=dict(entity_id=eid,wiki_id=rec["id"],wiki_title=rec["title"],basis="stadium_article")
        return eid
    def sponsor(self,v):
        rec=self.lookup.get(v["key"],{});pid=rec.get("id")
        if not pid or rec.get("dab") or not self.companies.get(str(pid),{}).get("company"):return None
        eid="firm-w"+str(pid)
        nm=norm(rec["title"])
        if "hanaka" in nm:eid="o-hanaka"
        if "sâm ngọc linh" in nm and "kon tum" in nm:eid="o-snl"
        self.entities.setdefault(eid,dict(entity_id=eid,type="Organization",canonical_name=rec["title"],role="Company"))
        self.registry[eid]=dict(entity_id=eid,wiki_id=pid,wiki_title=rec["title"],basis="company_article")
        return eid
    def person(self,v):
        n=compact(v["key"]);display=compact(v["name"])
        if v["kind"]=="template" or not n or len(n)>90 or not any(c.isalpha() for c in n):return None
        if n.count("(")!=n.count(")") or re.search(r"(?i)^clb\b|huấn luyện viên|trọng tài|câu lạc bộ|thể loại:|^đội |^[*\d]|file:|tập tin:|^tệp:|nhân viên|trợ l[íý]|bác s[ĩỹ]|quan chức|<|\?|=",n):return None
        page=self.lookup.get(n,{})
        if page.get("dab") and v["kind"]=="link":return None
        linked=(page["id"],page["title"]) if page.get("id") and not page.get("dab") and self.bios.get(str(page["id"]),{}).get("football") else None
        alts=self.person_alts[norm(display)]|self.person_alts[norm(n)]
        if not linked and len(alts)==1:linked=next(iter(alts))
        if not linked and len(alts)>1:return None
        checked=self.bios.get(str(page.get("id")))
        if v["kind"]=="link" and not linked and checked is not None and not checked["football"]:return None
        if linked:
            pid,canonical=linked
            if re.search(r"(?i)^câu lạc bộ|^tỉnh |^đội tuyển|^giải bóng|^danh sách|^mùa giải",canonical):return None
            anchor="wiki:"+str(pid);basis="linked_person_page"
        else:
            canonical=n if v["kind"]=="link" and not page.get("id") else display
            canonical=re.sub(r"(?i)\s*\((?:c|đội trưởng|thủ môn|cầu thủ(?: bóng đá)?)\)\s*$","",canonical).strip()
            # Không tạo người mới từ tên gọi tắt, một từ, chữ cái đầu hoặc nhãn không đủ nhận dạng.
            name_core=re.sub(r"\s*\(.*?\)$","",canonical).strip()
            if len(name_core.split())<3 or any(len(x.strip("."))<2 for x in name_core.split()):return None
            if not re.fullmatch(r"[\wÀ-ỹ .'’()-]+",canonical) or any(c.isdigit() for c in name_core):return None
            anchor="name:"+norm(canonical);basis="full_name_in_roster_or_match";pid=None
        pk=self.pilot_people.get(norm(canonical)) or self.pilot_people.get(norm(display))
        if pk and len(self.person_alts[norm(display)])>1:pk=None
        # Hai cầu thủ Quang Hải khác tuổi có thể dùng chung tên hiển thị.
        if "quang hải" in norm(display+" "+canonical) and "1997" in canonical:pk="p-qh"
        if pk=="p-qh" and "1985" in canonical:pk=None
        i=pk or "p-"+ident(anchor)
        self.entities.setdefault(i,dict(entity_id=i,type="Person",canonical_name=canonical,role="Player"))
        self.registry[i]=dict(entity_id=i,wiki_id=pid,wiki_title=canonical,basis=basis)
        return i

def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument("dest",type=Path);a=ap.parse_args()
    out=a.dest
    if out.exists():raise ValueError("Chọn tên snapshot mới")
    out.mkdir(parents=True);rawdir=out/"raw";rawdir.mkdir()
    arts=jlines(PILOT/"articles.jsonl");groups=group_articles(arts,Path("templates/article_events_02.tsv"),out)
    for p in (PILOT/"raw").iterdir():put_raw(p,rawdir/p.name)
    facts={r["fact_id"]:r for r in table(PILOT/"facts.csv")};ev={r["evidence_id"]:r for r in jlines(PILOT/"evidence.jsonl")}
    res=Resolver();pages={};data=[]
    for p,rev,txt,f in chain(read_pages(Path("work/a2_wiki")),read_pages(Path("work/a2_clubwiki"))):
        cache=Path("work/a2_records")/f"{p['pageid']}-{rev['revid']}.json"
        if not cache.exists():continue
        rows=json.loads(cache.read_bytes())["rows"]
        if not rows:continue
        title=p["title"];season=re.search(r"20\d\d(?:[–-]\d{2,4})?",title)
        if not season and not rows[0].get("season"):continue
        season=rows[0].get("season") or season[0].replace("-","–")
        league="VL2" if "hạng nhất" in title.lower() else ("CUP" if "cúp" in title.lower() else "VL1")
        league=rows[0].get("league",league)
        raw=f.read_bytes();h=sha(raw);put_raw(f,rawdir/h)
        url="https://vi.wikipedia.org/w/index.php?oldid="+str(rev["revid"])
        ch=sha(txt.encode());aid="a_"+sha(enc([url,str(rev["revid"]),h,ch]).encode())[:24]
        article=dict(article_id=aid,record_kind="real",source_kind="wiki",source="Wikipedia tiếng Việt",
                     canonical_url=url,title=title,published_at="",retrieved_at=json.loads(f.with_suffix(".meta").read_bytes())["retrieved_at"],
                     pageid=str(p["pageid"]),revid=str(rev["revid"]),revision_at=rev["timestamp"],story_group=f"season:{league}:{season}",
                     clean_text=txt,clean_sha256=ch,raw_sha256=h)
        arts.append(article);pages[aid]=article
        for r in rows:
            if r["kind"] in {"roster","staff"}:
                if r.get("role")!="Sponsor":res.observe(r["player"])
            else:
                for e in r["events"]:res.observe(e["player"])
            data.append((aid,r.get("league",league),r.get("season",season),r))
    dropped=Counter();details={}
    def add(s,rel,d,event,period,aid,r,method,extra=None):
        if not s or not d or s==d:return
        art=pages[aid];start,end=r["start"],r["end"];quote=art["clean_text"][start:end]
        fid="f_"+sha(enc([s,rel,d,event]).encode())[:20]
        eid="e_"+sha(enc([fid,aid,start,end]).encode())[:20]
        e=dict(evidence_id=eid,article_id=aid,fact_id=fid,start=start,end=end,quote=quote,role="supports")
        if r.get("context"):e["context_start"],e["context_end"]=r["context"]
        ev[eid]=e
        facts.setdefault(fid,dict(fact_id=fid,src_id=s,dst_id=d,relation_type=rel,event_key=event,period=period,status="accepted",method=method,evidence_id=eid,article_id=aid,article_url=art["canonical_url"],quote=quote))
        if extra:details[fid]=extra
    scores=defaultdict(set)
    def match_info(r,season):
        h=res.club(r["team1"]);v=res.club(r["team2"])
        if not h or not v or h==v:return None
        year=int(r["date"][:4]);lo=int(season[:4]);hi=lo+(1 if "–" in season else 0)
        if not lo<=year<=hi:return None
        return (h,v, f"{r['date']}:{h}:{v}")
    for _,_,seas,r in data:
        if r["kind"]=="match":
            info=match_info(r,seas)
            if info:scores[info[2]].add(re.sub(r"\s|['’]","",r["score"]).replace("–","-").replace("—","-"))
    observed=defaultdict(set)
    venues=defaultdict(dict)
    baseline_coaches={(f["src_id"],f["dst_id"]) for f in facts.values() if f["relation_type"]=="DAN_DAT"}
    for aid,league,season,r in data:
        if r["kind"]=="staff":
            c=res.club(r["club"])
            person=res.sponsor(r["player"]) if r["role"]=="Sponsor" else res.person(r["player"])
            if not c or not person:dropped["unresolved_staff"]+=1;continue
            typ={"Coach":"DAN_DAT","Captain":"DOI_TRUONG_CUA","Sponsor":"TAI_TRO"}[r["role"]]
            if typ=="TAI_TRO" and any(f["relation_type"]==typ and f["src_id"]==person and f["dst_id"]==c for f in table(PILOT/"facts.csv")):continue
            if typ=="DAN_DAT" and (person,c) in baseline_coaches:continue
            event="documented-team-role"
            fid="f_"+sha(enc([person,typ,c,event]).encode())[:20]
            observed[fid].add(season)
            add(person,typ,c,event,season,aid,r,"wiki_staff_table")
            facts[fid]["period"]=", ".join(sorted(observed[fid]))
            continue
        if r["kind"]=="roster":
            club=res.club(r["club"]);player=res.person(r["player"])
            if not club or not player:dropped["unresolved_roster"]+=1;continue
            add(player,"DANG_KY_THI_DAU_CHO",club,"season:"+season,season,aid,r,"wiki_roster_row",{"shirt":r["shirt"],"position":r["pos"]})
            continue
        info=match_info(r,season)
        if not info:dropped["unresolved_match"]+=1;continue
        h,v,datekey=info
        if len(scores[datekey])!=1:dropped["score_conflict"]+=1;continue
        attrs={"score":next(iter(scores[datekey])),"competition":league,"match":datekey}
        add(h,"DOI_DAU",v,datekey,r["date"],aid,r,"wiki_match_result",attrs)
        stadium=res.venue(r.get("venue"))
        if stadium:
            for club in (h,v):
                event="observed-ground"
                fid="f_"+sha(enc([club,"THI_DAU_TAI_SAN",stadium,event]).encode())[:20]
                venues[fid][datekey]=r["date"]
                add(club,"THI_DAU_TAI_SAN",stadium,event,r["date"],aid,r,"wiki_match_venue")
                dates=venues[fid].values()
                facts[fid]["period"]=f"ghi nhận {min(dates)} đến {max(dates)}"
                details[fid]=dict(distinct_matches=len(dates),first_observed=min(dates),last_observed=max(dates))
        for e in r["events"]:
            player=res.person(e["player"]);opp=v if e["side"]==1 else h
            if not player:dropped["unresolved_player_event"]+=1;continue
            rel="GHI_BAN_VAO_LUOI" if e["kind"]=="goal" else "NHAN_THE_VANG_KHI_GAP"
            add(player,rel,opp,datekey,r["date"],aid,r,"wiki_match_event",attrs)
    # Các tên khác cách đặt dấu, đảo trật tự hoặc thêm danh xưng được rà theo nhóm.
    # Không suy đoán hai người cùng tên là một. Giữ ID đã xác minh; tách các
    # trường hợp chưa phân biệt được khỏi số đếm, giữ toàn bộ fact ở hàng chờ.
    referred=Counter(eid for f in facts.values() for eid in (f["src_id"],f["dst_id"]))
    baseline={e["entity_id"] for e in table(PILOT/"entities.csv")}
    collisions=defaultdict(list)
    for eid in referred:
        e=res.entities[eid]
        if e["type"]!="Person":continue
        spelling=e["canonical_name"].split("(")[0].casefold().replace("đ","d")
        letters="".join(c for c in unicodedata.normalize("NFD",spelling) if not unicodedata.combining(c))
        collisions[" ".join(sorted(set(re.findall(r"\w+",letters))))].append(eid)
    quarantine=set(); decisions=[]
    for signature,ids in sorted(collisions.items()):
        if len(ids)<2:continue
        anchors={i for i in ids if i in baseline or res.registry.get(i,{}).get("basis")=="linked_person_page"}
        if not anchors:anchors={min(ids,key=lambda i:(-referred[i],i))}
        for i in sorted(set(ids)-anchors):
            quarantine.add(i)
            decisions.append(dict(held_id=i,name=res.entities[i]["canonical_name"],possible_ids=sorted(anchors),signature=signature))
    specific={norm(r["name"]):r for r in table(Path("templates/identity_defer.tsv"),"\t")}
    for i in sorted(referred):
        row=specific.get(norm(res.entities[i]["canonical_name"]))
        if row and i not in baseline and i not in quarantine:
            quarantine.add(i)
            decisions.append(dict(held_id=i,name=row["name"],possible_name=row["possible_name"],reason=row["reason"]))
    held_facts={k:v for k,v in facts.items() if v["src_id"] in quarantine or v["dst_id"] in quarantine}
    facts={k:v for k,v in facts.items() if k not in held_facts}
    ev={k:v for k,v in ev.items() if v["fact_id"] in facts}
    (out/"identity_review.jsonl").write_text("".join(enc(x)+"\n" for x in decisions))
    (out/"facts_identity_review.jsonl").write_text("".join(enc(f)+"\n" for f in held_facts.values()))
    dropped["identity_review_nodes"]=len(quarantine);dropped["identity_review_facts"]=len(held_facts)
    roles=defaultdict(set)
    for f in facts.values():
        if res.entities[f["src_id"]]["type"]!="Person":continue
        if f["relation_type"]=="DAN_DAT":roles[f["src_id"]].add("Coach")
        elif f["relation_type"]=="CHU_TICH_CUA":roles[f["src_id"]].add("Executive")
        else:roles[f["src_id"]].add("Player")
    for eid,rs in roles.items():res.entities[eid]["role"]="|".join(sorted(rs))
    active={id for f in facts.values() for id in (f["src_id"],f["dst_id"])}
    arts.sort(key=lambda r:r["article_id"]);articlefile=out/"articles.jsonl"
    articlefile.write_text("".join(enc(r)+"\n" for r in arts),encoding="utf-8")
    (out/"manifest.json").write_text(enc(dict(schema_version="1",record_kind="real",article_count=len(arts),articles_sha256=sha(articlefile.read_bytes())))+"\n")
    write_csv(out/"entities.csv",["entity_id","type","canonical_name","role"],[res.entities[i] for i in sorted(active)])
    write_csv(out/"facts.csv",list(next(iter(facts.values()))),[facts[k] for k in sorted(facts)])
    (out/"evidence.jsonl").write_text("".join(enc(ev[k])+"\n" for k in sorted(ev)))
    (out/"entity_resolution.jsonl").write_text("".join(enc(res.registry[k])+"\n" for k in sorted(active & set(res.registry))))
    (out/"event_attributes.jsonl").write_text("".join(enc({"fact_id":k,**details[k]})+"\n" for k in sorted(set(details)&set(facts))))
    verify(out,False,True)
    stats=dict(press_decisions=188,former_pending=186,press_groups=len(groups),wiki_source_pages=len(pages),
               articles=len(arts),connected_nodes=len(active),edges=len(facts),node_types=dict(Counter(res.entities[i]["type"] for i in active)),
               relations=dict(Counter(f["relation_type"] for f in facts.values())),methods=dict(Counter(f["method"] for f in facts.values())),
               identity_basis=dict(Counter(res.registry[i]["basis"] for i in active if i in res.registry)),skipped=dropped)
    (out/"stats.json").write_text(json.dumps(stats,ensure_ascii=False,indent=2,sort_keys=True)+"\n");print(json.dumps(stats,ensure_ascii=False))
if __name__=="__main__":main()
