"""Discover domestic match IDs from the newspaper's club result pages. Archive each public score sheet."""
import argparse,gzip,hashlib,json,re,sqlite3,time
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser
from concurrent.futures import ThreadPoolExecutor
import requests
from lxml import html
from bongda.collect.vne_bongda import slug

L="https://baolamdong.vn";V="https://vnexpress.net";GW="https://gw.vnexpress.net";AGENT="FootballGraphCoursework/0.3"
class Reader:
    def __init__(self):
        self.s=requests.Session();self.s.headers["User-Agent"]=AGENT;self.rules={};self.last={}
    def get(self,url):
        host=urlsplit(url).hostname
        if host not in {"baolamdong.vn","vnexpress.net","gw.vnexpress.net"}:raise ValueError("external URL")
        if host not in self.rules:
            r=self.s.get("https://"+host+"/robots.txt",timeout=15)
            if r.status_code not in (200,404):r.raise_for_status()
            p=RobotFileParser();p.parse(r.text.splitlines() if r.status_code==200 else []);self.rules[host]=p
        if not self.rules[host].can_fetch(AGENT,url):raise ValueError("robots disallows "+url)
        time.sleep(max(0,.70-time.monotonic()+self.last.get(host,0)));self.last[host]=time.monotonic()
        r=self.s.get(url,timeout=(6,16));r.raise_for_status();return r
def run(profiles,root,mode):
    root.mkdir(parents=True,exist_ok=True);(root/"raw").mkdir(exist_ok=True)
    db=sqlite3.connect(root/"index.sqlite",timeout=45);db.execute("PRAGMA journal_mode=WAL")
    db.executescript("""CREATE TABLE IF NOT EXISTS resultpages(url TEXT PRIMARY KEY,sha TEXT);
    CREATE TABLE IF NOT EXISTS matches(id INTEGER PRIMARY KEY,url TEXT);CREATE TABLE IF NOT EXISTS docs(id INTEGER PRIMARY KEY,page TEXT,events TEXT,squad TEXT,html TEXT,htmlsha TEXT,evtsha TEXT,sqdsha TEXT,retrieved TEXT);
    CREATE TABLE IF NOT EXISTS skips(id INTEGER PRIMARY KEY,reason TEXT);""")
    reader=Reader()
    def archive(b):
        h=hashlib.sha256(b).hexdigest();dest=root/"raw"/(h+".gz")
        if not dest.exists():
            with gzip.open(dest,"wb") as f:f.write(b)
        return h
    if mode=="index":
        pdb=sqlite3.connect(profiles/"pages.sqlite");roots=[r[0].rsplit("/",1)[0] for r in pdb.execute("SELECT url FROM docs WHERE role='cau-thu'")]
        urls=[u+"/ket-qua/"+comp for comp in ("v-league","hang-nhat-viet-nam","cup-quoc-gia-viet-nam","cup-quoc-gia") for u in roots]
        for url in urls:
            if db.execute("SELECT 1 FROM resultpages WHERE url=?",(url,)).fetchone():continue
            try:
                r=reader.get(url);doc=html.fromstring(r.content,parser=html.HTMLParser(encoding="utf-8"))
                links=set()
                for x in doc.xpath('//a[contains(@href,"/bong-da/tran-dau-")]/@href'):
                    m=re.fullmatch(r"https://baolamdong.vn/bong-da/tran-dau-[\w-]+-(\d+)\.html",x)
                    if m:links.add((int(m[1]),x))
                if links:
                    db.execute("INSERT INTO resultpages VALUES(?,?)",(url,archive(r.content)));db.executemany("INSERT OR IGNORE INTO matches VALUES(?,?)",sorted(links));db.commit()
            except (requests.RequestException,ValueError):continue
    else:
        idle=0
        while idle<40:
            ids=db.execute("SELECT id,url FROM matches WHERE id NOT IN(SELECT id FROM docs) AND id NOT IN(SELECT id FROM skips) ORDER BY id LIMIT 30").fetchall()
            if not ids:idle+=1;time.sleep(3);continue
            idle=0
            for i,url in ids:
                try:
                    event=GW+f"/football/fixture/event?fixture_id={i}";squad=GW+f"/football/fixture/stats?fixture_id={i}"
                    r=reader.get(event);fx=r.json().get("data",{}).get(str(i),{}).get("fixture_detail",{})
                    if fx.get("status_short") not in {"FT","PEN","AET"} or fx.get("league",{}).get("country")!="Vietnam":
                        raise ValueError("No archived final Vietnam fixture")
                    sj=reader.get(squad)
                    if not sj.json().get("data",{}).get("lineups"):raise ValueError("No public lineups")
                    page=V+f"/the-thao/du-lieu-bong-da/tran-dau/{i}/{slug(fx['home_team']['team_name'])}-{slug(fx['away_team']['team_name'])}"
                    v=reader.get(page)
                    if str(i) not in v.text or not html.fromstring(v.content).xpath('//*[@data-fixtureid]'):raise ValueError("public viewer unavailable")
                    db.execute("INSERT OR IGNORE INTO docs VALUES(?,?,?,?,?,?,?,?,?)",(i,page,event,squad,url,archive(v.content),archive(r.content),archive(sj.content),datetime.now(timezone.utc).isoformat()))
                except (requests.RequestException,ValueError,AttributeError) as e:db.execute("INSERT OR REPLACE INTO skips VALUES(?,?)",(i,str(e)[:150]))
                db.commit()
    print(mode,db.execute("SELECT count(*) FROM matches").fetchone(),db.execute("SELECT count(*) FROM docs").fetchone(),flush=True)
if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("profiles",type=Path);p.add_argument("root",type=Path);p.add_argument("mode",choices=["index","fetch"]);a=p.parse_args();run(a.profiles,a.root,a.mode)
