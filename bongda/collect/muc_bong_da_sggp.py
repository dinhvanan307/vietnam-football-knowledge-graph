"""Collect historical football reports from SGGP's public monthly sitemaps."""
import argparse,gzip,hashlib,re,sqlite3,time
from pathlib import Path
from datetime import datetime,timezone
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser
import requests
from lxml import etree,html

H="https://thethao.sggp.org.vn"
TEAM=r"(?:ha-noi|slna|song-lam-nghe-an|hai-phong|da-nang|thanh-hoa|nam-dinh|hagl|gia-lai|ha-tinh|binh-duong|binh-dinh|khanh-hoa|viettel|the-cong|cahn|dong-nai|binh-phuoc|pho-hien|quang-nam|long-an|can-tho|dong-thap|quang-ninh|quy-nhon|kien-giang|dong-tam|ninh-binh|sai-gon|tphcm|tp-hcm|hcm-city|ho-chi-minh|ba-ria|song-be|an-giang|thua-thien-hue|dak-lak)"
score=re.compile(r"(?:^|-)(?:[0-9]|1[0-4])-(?:[0-9]|1[0-4])(?:-|$)")
verb=re.compile(r"(?:thang|danh-bai|vuot-qua|chia-diem|hoa|ha-guc|quat-nga|lan-nguoc|nguoc-dong|thua|dai-thang|doi-hinh|ghi-ban|lap-cu-dup|cap-ben|ky-hop-dong|chieu-mo|chuyen-nhuong)")
def priority(url):
    s=url.split("/")[-1].split("-post")[0];clubs=set(re.findall(TEAM,s))
    if re.search(r"bong-chuyen|bong-ro|futsal|sinh-vien|bong-ban|phong-trao|sao-do|cau-long|pickleball|dien-kinh|giai-quan-vot|danh-bac|tin-du-doan",s):return 9
    if score.search(s) and clubs:return 0
    if len(clubs)>=2 and verb.search(s):return 1
    if clubs and re.search(r"(?:v-league|vleague|hang-nhat|cup-quoc-gia)",s) and verb.search(s):return 2
    return 9
def run(root,mode,limit):
    root.mkdir(exist_ok=True,parents=True);cache=root/"raw";cache.mkdir(exist_ok=True)
    db=sqlite3.connect(root/"urls.sqlite",timeout=30);db.execute("PRAGMA journal_mode=WAL")
    db.executescript("""CREATE TABLE IF NOT EXISTS maps(url TEXT PRIMARY KEY); CREATE TABLE IF NOT EXISTS urls(url TEXT PRIMARY KEY,priority INTEGER);
    CREATE TABLE IF NOT EXISTS files(url TEXT PRIMARY KEY,sha TEXT,retrieved TEXT); CREATE TABLE IF NOT EXISTS errors(url TEXT PRIMARY KEY,message TEXT);""")
    s=requests.Session();agent="FootballGraphCoursework/0.3";s.headers["User-Agent"]=agent
    p=RobotFileParser();raw=s.get(H+"/robots.txt",timeout=20);raw.raise_for_status();p.parse(raw.text.splitlines());last=0
    def get(url):
        nonlocal last
        if urlsplit(url).netloc!=urlsplit(H).netloc or not p.can_fetch(agent,url):raise ValueError(url)
        time.sleep(max(0,.7-(time.monotonic()-last)));last=time.monotonic()
        r=s.get(url,timeout=(8,22));r.raise_for_status();return r
    if mode=="index":
        r=get(H+"/sitemap.xml");urls=etree.fromstring(r.content).xpath('//*[local-name()="loc"]/text()')
        for url in [u for u in urls if re.search(r"news-\d+-\d+\.xml$",u)][:limit]:
            if db.execute("SELECT 1 FROM maps WHERE url=?",(url,)).fetchone():continue
            try:
                links=etree.fromstring(get(url).content).xpath('//*[local-name()="url"]/*[local-name()="loc"]/text()')
                db.executemany("INSERT OR IGNORE INTO urls VALUES(?,?)",[(u,priority(u)) for u in links if priority(u)<9])
                db.execute("INSERT INTO maps VALUES(?)",(url,));db.commit()
            except Exception as e:print(url,str(e)[:70],flush=True)
    else:
        n=idle=0
        while n<limit and idle<60:
            urls=db.execute("SELECT url FROM urls WHERE url NOT IN (SELECT url FROM files) AND url NOT IN (SELECT url FROM errors) ORDER BY priority,url LIMIT 25").fetchall()
            if not urls:idle+=1;time.sleep(4);continue
            idle=0
            for (url,) in urls[:limit-n]:
                try:
                    body=get(url).content;sig=hashlib.sha256(body).hexdigest()
                    with gzip.open(cache/(sig+".gz"),"wb") as f:f.write(body)
                    db.execute("INSERT OR IGNORE INTO files VALUES (?,?,?)",(url,sig,datetime.now(timezone.utc).isoformat()));n+=1
                    if n%100==0:print("archived",n,flush=True)
                except Exception as e:db.execute("INSERT OR REPLACE INTO errors VALUES(?,?)",(url,str(e)[:300]))
                db.commit()
if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("root",type=Path);p.add_argument("mode",choices=["index","fetch"]);p.add_argument("--limit",type=int,required=True);a=p.parse_args();run(a.root,a.mode,a.limit)
