"""Archive public head-to-head tables for Vietnamese professional club pairs."""
import argparse,gzip,hashlib,itertools,sqlite3,time
from datetime import datetime,timezone
from pathlib import Path
from urllib.robotparser import RobotFileParser
from urllib.parse import urlsplit
import requests
from lxml import html

HOST="https://baolamdong.vn"; AGENT="FootballGraphCoursework/0.3"
# Paths use the club slugs displayed by the newspaper. Accept completed fixtures only.
CLUBS="ha-noi hai-phong hoang-anh-gia-lai song-lam-nghe-an thanh-hoa nam-dinh viettel binh-duong da-nang binh-dinh hong-linh-ha-tinh ho-chi-minh cong-an-ha-noi quang-nam khanh-hoa sai-gon than-quang-ninh can-tho long-an dong-thap binh-phuoc dong-nai pho-hien phu-dong hue dak-lak an-giang tay-ninh ba-ria-vung-tau phu-tho hoa-binh binh-thuan hai-nam-vinh-yen-phu-tho".split()
def run(root):
    root.mkdir(exist_ok=True,parents=True);cache=root/"raw";cache.mkdir(exist_ok=True)
    db=sqlite3.connect(root/"archive.sqlite");db.executescript("""CREATE TABLE IF NOT EXISTS pages(url TEXT PRIMARY KEY,sha TEXT,retrieved TEXT); CREATE TABLE IF NOT EXISTS skipped(url TEXT PRIMARY KEY,reason TEXT);""")
    session=requests.Session();session.headers["User-Agent"]=AGENT
    robots=session.get(HOST+"/robots.txt",timeout=16);robots.raise_for_status();policy=RobotFileParser();policy.parse(robots.text.splitlines())
    pairs=sorted(itertools.combinations(CLUBS,2),key=lambda p: max(CLUBS.index(p[0]),CLUBS.index(p[1])))
    for a,b in pairs:
        pair="-vs-".join(sorted((a,b)));u=HOST+"/bong-da/lich-su-doi-dau/"+pair
        if db.execute("SELECT url FROM pages WHERE url=? UNION SELECT url FROM skipped WHERE url=?",(u,u)).fetchone():continue
        if not policy.can_fetch(AGENT,u):raise ValueError("robots.txt disallows "+u)
        try:
            time.sleep(.65);r=session.get(u,timeout=(5,17))
            if r.status_code==429:time.sleep(20);continue
            if r.status_code!=200:
                if r.status_code==404:db.execute("INSERT OR IGNORE INTO skipped VALUES(?,?)",(u,"404"));db.commit()
                continue
            doc=html.fromstring(r.content,parser=html.HTMLParser(encoding="utf-8"))
            if not doc.xpath('//table[.//th[normalize-space()="Trận đấu"] and .//th[normalize-space()="Ngày"] and .//th[normalize-space()="Sân"]]//tr[td]'):
                db.execute("INSERT INTO skipped VALUES(?,?)",(u,"no published results table"));db.commit();continue
            sig=hashlib.sha256(r.content).hexdigest()
            with gzip.open(cache/(sig+".gz"),"wb") as f:f.write(r.content)
            db.execute("INSERT INTO pages VALUES(?,?,?)",(u,sig,datetime.now(timezone.utc).isoformat()));db.commit()
        except (requests.RequestException,ValueError) as e:print(pair,str(e)[:95],flush=True)
    print("verified tables",db.execute("SELECT count(*) FROM pages").fetchone(),flush=True)
if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("root",type=Path);run(p.parse_args().root)
