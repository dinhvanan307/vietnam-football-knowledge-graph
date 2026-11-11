"""Extract dated results and transfer rows from newspaper-published sports tables."""
import gzip,json,re,sqlite3
from collections import defaultdict
from datetime import datetime
from lxml import html
from bongda.core.ban_giao import enc
from bongda.press_final.clubs import identify,key,LEAGUES
from bongda.press_final.network import tidy,iso_day

def result_tables(graph,root):
    db=sqlite3.connect(f"file:{root/'archive.sqlite'}?mode=ro",uri=True)
    for url,sig,stamp in db.execute("SELECT url,sha,retrieved FROM pages ORDER BY url"):
        path=root/"raw"/(sig+".gz");doc=html.fromstring(gzip.decompress(path.read_bytes()),parser=html.HTMLParser(encoding="utf-8"))
        title=tidy(doc.xpath("//h1")[0].text_content())
        rows=[]
        for tr in doc.xpath('//table[.//th[normalize-space()="Sân"] and .//th[normalize-space()="Trận đấu"]]//tr[td]'):
            v=[tidy(td.text_content()) for td in tr.xpath("./td")]
            if len(v)!=5:continue
            ds,comp,pair,score,stadium=v;league=LEAGUES.get(key(comp))
            if not league or not re.fullmatch(r"\d{2}/\d{2}/\d{4}",ds):continue
            day=datetime.strptime(ds,"%d/%m/%Y").date().isoformat()
            if day>"2026-11-11":continue
            candidates=set()
            for m in re.finditer(r"\s+–\s+",pair):
                a=identify(pair[:m.start()],day);b=identify(pair[m.end():],day)
                if a and b and a!=b:candidates.add((a,b))
            sc=re.fullmatch(r"(\d{1,2})\s*[–-]\s*(\d{1,2})",score)
            if len(candidates)==1 and sc:
                a,b=next(iter(candidates))
                rows.append((a,b,day,league,tuple(map(int,sc.groups()))," | ".join(v)))
        if not rows:continue
        aid=graph.document(url,title,[title,"Ngày | Giải | Trận đấu | Tỷ số | Sân",*(r[-1] for r in rows)],path,stamp,"","news_table","Báo Lâm Đồng")
        for a,b,date,league,sc,q in rows:graph.match(a,b,date,league,sc,aid,q,"bang_ket_qua_bao")
    db.close()
def feed(root,meta):
    f=json.loads(meta.read_text())
    return f,json.loads((root/"data"/f["json_sha"]).read_bytes())["data"]
def vne_document(g,root,m,title,lines):
    return g.document(m["page"],title,lines,root/"data"/m["json_sha"],m["retrieved_at"],"","news_table","VnExpress",
                      m["endpoint"],m["page_sha"],root/"data"/m["page_sha"])
def transfer_rows(root):
    for file in sorted(root.glob("transfer_*.json")):
        team_id=file.stem.split("_")[1];m,raw=feed(root,file)
        records=raw.get(team_id,{}).get("data",[])
        candidates=[]
        for row in records:
            pid=row.get("player_id");name=row.get("player_name") or "";date=row.get("transfer_date","")
            if not isinstance(pid,int) or not name or not iso_day(date) or date>"2026-11-11":continue
            a=row.get("team_out") or {};b=row.get("team_in") or {}
            if str(a.get("team_id"))!=team_id and str(b.get("team_id"))!=team_id:continue
            one=identify(a.get("team_name") or "",date,a.get("team_id"));two=identify(b.get("team_name") or "",date,b.get("team_id"))
            if not (one or two) or one==two:continue
            candidates.append((pid,name,one,two,date,enc(row),a.get("team_id"),b.get("team_id")))
        if candidates:yield m,candidates
def squads(root):
    for file in sorted(root.glob("squad_*.json")):
        num=file.stem.split("_")[1];event=root/f"events_{num}.json"
        if not event.exists():continue
        em,events=feed(root,event);m,s=feed(root,file);fx=events.get(num,{}).get("fixture_detail",{})
        if fx.get("league_id")!=340 or fx.get("status_short") not in {"FT","AET","PEN"}:continue
        ds=fx["event_date"][:10]
        clubs={};order=[]
        for field in ("home_team","away_team"):
            t=fx[field];club=identify(t["team_name"],ds,t["team_id"]);clubs[t["team_id"]]=club;order.append(club)
        if not all(order) or len(set(order))!=2 or ds>"2026-11-11":continue
        rows=[]
        for line in s.get("lineups",[]) or []:
            group=line.get("start_xi",[]) or []
            if len(group)!=11:continue
            for r in group:
                cid=clubs.get(r.get("team_id"));pid=r.get("player_id");name=r.get("player") or ""
                if cid and isinstance(pid,int) and name:rows.append((pid,name,cid,enc(r)))
        yield m,em,fx,order,ds,rows
def transfers_and_squads(g,root):
    moves=list(transfer_rows(root)); games=list(squads(root))
    for m,rows in moves:
        for pid,name,*_ in rows:g.register_person_names(pid,name)
    for *_,rows in games:
        for pid,name,*_ in rows:g.register_person_names(pid,name)
    g.preindex_people()
    dates=defaultdict(set)
    for m,moveset in moves:
        for pid,name,c1,c2,day,q,one,two in moveset:dates[pid,one,two,day[:4]].add(day)
    for m,rows in moves:
        title="Bảng chuyển nhượng CLB trên VnExpress";aid=vne_document(g,root,m,title,[title,*[r[5] for r in rows]])
        for pid,name,c1,c2,ds,q,one,two in rows:
            if g.version!="A9" and (len(dates[pid,one,two,ds[:4]])>1 or (ds>="2025-07-14" and "c-hcm" in (c1,c2) and any(key(t.get("team_name","") or "") in {"tp hcm","ho chi minh","ho chi minh city","tphcm"} for t in [json.loads(q).get("team_in") or {},json.loads(q).get("team_out") or {}]))):
                g.logs["ambiguous_transfer_rows_held"]+=1;continue
            ident=g.person(pid)
            if not ident:continue
            event=f"{ds}|{one}|{two}"
            for c,rel in [(c1,"CHUYEN_DI_TU"),(c2,"CHUYEN_DEN_CLB")]:
                if c:
                    g.club(c);g.link(ident,rel,c,event,ds,aid,q,"bang_chuyen_nhuong_bao")
                    g.teams[ident].add(c);g.byteam[(c,key(name))].add(ident)
    for m,em,fx,pair,ds,rows in games:
        title="V.League 1 · "+fx["home_team"]["team_name"].strip()+" – "+fx["away_team"]["team_name"].strip()+" · "+ds
        fq=enc(fx);eid=vne_document(g,root,em,title,[title,fq])
        mid=g.match(*pair,ds,("g-vl1","V.League 1"),(fx["goals_home_team"],fx["goals_away_team"]),eid,fq,"bang_ket_qua_bao")
        if not mid or not rows:continue
        aid=vne_document(g,root,m,title,[title,*[r[3] for r in rows]])
        for pid,name,cid,q in rows:
            who=g.person(pid)
            if not who:continue
            g.link(who,"DA_CHINH_TRONG_TRAN",mid,mid,ds,aid,q,"bang_doi_hinh_xuat_phat",dict(club_id=cid))
            g.teams[who].add(cid); g.byteam[(cid,key(name))].add(who)
