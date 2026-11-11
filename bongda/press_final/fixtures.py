"""Read a published Vietnamese professional match sheet. A reserve is not a substitution."""
import gzip,json,sqlite3
from bongda.core.ban_giao import enc
from bongda.press_final.clubs import identify,key,LEAGUES
from bongda.press_final.network import iso_day

def games(root):
    db=sqlite3.connect(f"file:{root/'index.sqlite'}?mode=ro",uri=True)
    for i,page,events,squad,ps,es,ss,stamp in db.execute("SELECT id,page,events,squad,htmlsha,evtsha,sqdsha,retrieved FROM docs ORDER BY id"):
        path=lambda s:root/"raw"/(s+".gz")
        def read(s):return json.loads(gzip.decompress(path(s).read_bytes()))["data"]
        event=read(es)[str(i)]["fixture_detail"]; comp=event.get("league") or {}
        league=LEAGUES.get(key(comp.get("name",""))) or ({"v league 2":("g9-vl2","Giải hạng Nhất quốc gia"),"cup":("g9-cup","Cúp Quốc gia Việt Nam")}.get(key(comp.get("name",""))))
        date=event["event_date"][:10];pair=[];clubs={}
        if not league or comp.get("country")!="Vietnam" or not iso_day(date) or date>"2026-11-11":continue
        score=(event.get("goals_home_team"),event.get("goals_away_team"))
        if not all(isinstance(v,int) and 0<=v<30 for v in score):continue
        for side in ("home_team","away_team"):
            team=event[side];c=identify(team["team_name"],date,team["team_id"]);clubs[team["team_id"]]=c;pair.append(c)
        if not all(pair) or len(set(pair))!=2:continue
        lines=[]
        for line in read(ss).get("lineups") or []:
            if int(line.get("fixture_id") or 0)!=i or len(line.get("start_xi") or [])!=11:continue
            cname=line.get("team_name","")
            for bucket,relation in [("start_xi","DA_CHINH_TRONG_TRAN"),("substitutes","DANG_KY_DU_BI_TRONG_TRAN")]:
                for row in line.get(bucket) or []:
                    c=clubs.get(row.get("team_id"));pid=row.get("player_id");name=row.get("player")
                    if not c or not isinstance(pid,int) or not isinstance(name,str) or not name.strip() or c!=identify(cname,date,row.get("team_id")):continue
                    lines.append((pid,name,c,relation,bucket+" | "+cname+" | "+enc(row)))
        yield (i,page,events,squad,path(ps),path(es),path(ss),stamp,event,league,pair,date,score,lines)
    db.close()

def apply_games(g,games):
    for i,page,events,squad,p,e,s,stamp,ev,league,pair,date,score,rows in games:
        title=f"{ev['home_team']['team_name']} – {ev['away_team']['team_name']} · {league[1]} · {date}"
        def doc(path,url,lines):return g.document(page,title,[title,*lines],path,stamp,"","news_table","VnExpress",url,p.name.split(".")[0],p)
        eq=enc(ev);ed=doc(e,events,[eq]);mid=g.match(*pair,date,league,score,ed,eq,"bang_ket_qua_bao")
        if mid and rows:
            ad=doc(s,squad,[row[-1] for row in rows])
            for pid,name,club,rel,q in rows:
                who=g.person(pid)
                if who:
                    g.link(who,rel,mid,mid,date,ad,q,"phieu_doi_hinh_bao",dict(club_id=club))
                    g.teams[who].add(club);g.byteam[club,key(name)].add(who)
