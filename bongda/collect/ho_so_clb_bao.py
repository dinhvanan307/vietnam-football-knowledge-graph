"""Archive the club squad, coach and competition profiles published by Báo Lâm Đồng."""
import argparse,gzip,hashlib,json,re,sqlite3,time
from datetime import datetime,timezone
from pathlib import Path
from urllib.robotparser import RobotFileParser
import requests
from lxml import html
from bongda.collect.vne_bongda import slug
from bongda.press_final.clubs import identify
H="https://baolamdong.vn"
def run(vne,root):
    root.mkdir(parents=True,exist_ok=True);(root/"raw").mkdir(exist_ok=True)
    db=sqlite3.connect(root/"pages.sqlite");db.execute("CREATE TABLE IF NOT EXISTS docs(url TEXT PRIMARY KEY,team INTEGER,role TEXT,sha TEXT,retrieved TEXT)")
    session=requests.Session();agent="FootballGraphCoursework/0.3";session.headers["User-Agent"]=agent
    robots=session.get(H+"/robots.txt",timeout=20);robots.raise_for_status();policy=RobotFileParser();policy.parse(robots.text.splitlines())
    teams={}
    for p in vne.glob("transfer_*.json"):
        code=int(p.stem.split("_")[1]);m=json.loads(p.read_text());url=m["page"]
        teams[code]=url.split("/doi-bong/")[1].split("/")[0]
    # Each ID is linked from a domestic club transfer record. Skip other sports/school teams.
    extra={3670:"ha-noi",3673:"hoang-anh-gia-lai",3678:"song-lam-nghe-an",3675:"quang-nam",9161:"binh-phuoc",9167:"phu-dong",3672:"ho-chi-minh",3668:"binh-duong",3681:"viettel",9166:"pho-hien"}
    def read(url,code,role):
        row=db.execute("SELECT sha FROM docs WHERE url=?",(url,)).fetchone()
        if row:return html.fromstring(gzip.decompress((root/"raw"/(row[0]+".gz")).read_bytes()),parser=html.HTMLParser(encoding="utf-8"))
        if not policy.can_fetch(agent,url):return
        try:
            time.sleep(.7);r=session.get(url,timeout=(6,17))
            if r.status_code!=200:return
            doc=html.fromstring(r.content,parser=html.HTMLParser(encoding="utf-8"))
            if not doc.xpath('//h1') or "404" in doc.xpath('//h1')[0].text_content():return
            sig=hashlib.sha256(r.content).hexdigest()
            with gzip.open(root/"raw"/(sig+".gz"),"wb") as f:f.write(r.content)
            db.execute("INSERT INTO docs VALUES(?,?,?,?,?)",(url,code,role,sig,datetime.now(timezone.utc).isoformat()));db.commit()
            return doc
        except requests.RequestException:return None
    for code,path in sorted(teams.items()):
        front=H+"/bong-da/doi-bong/"+(extra.get(code,path.rsplit("-",1)[0]))+"-"+str(code)
        for role in ("cau-thu","huan-luyen-vien"):
            read(front+"/"+role,code,role)
    # Archive athlete profiles for positive identification and season-specific statistics.
    players={}
    for url,code,sig in list(db.execute("SELECT url,team,sha FROM docs WHERE role='cau-thu'")):
        doc=html.fromstring(gzip.decompress((root/"raw"/(sig+".gz")).read_bytes()),parser=html.HTMLParser(encoding="utf-8"))
        for a in doc.xpath('//a[contains(@class,"fb-plcard") and @href]'):
            if re.fullmatch(r"https://baolamdong.vn/bong-da/cau-thu-[\w-]+-\d+\.html",a.get("href")):players[a.get("href")]=code
    for url,code in sorted(players.items()):read(url,code,"player")
    print("Source pages",db.execute("SELECT role,count(*) FROM docs GROUP BY role").fetchall(),flush=True)
if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("vne",type=Path);p.add_argument("root",type=Path);a=p.parse_args();run(a.vne,a.root)
