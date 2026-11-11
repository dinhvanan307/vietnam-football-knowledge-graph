"""Collect editorial match reports from the public archive of Tạp chí Bóng đá."""
import argparse
import gzip
import hashlib
import json
import re
import sqlite3
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin,urlsplit
from urllib.robotparser import RobotFileParser

import requests
from lxml import html

HOST = "https://bongdaplus.vn"
AGENT = "FootballGraphCoursework/0.3"
CATEGORIES = ["v-league","hang-nhat-quoc-gia","cup-quoc-gia","bong-da-nu-viet-nam","u21-viet-nam","u19-viet-nam","u17-viet-nam"]
ARTICLE = re.compile(r"^/("+("|".join(CATEGORIES))+r")/[^/?]+-\d{8,12}\.html$")
SCORE = re.compile(r"(?:^|-)(?:[0-9]|1[0-4])-(?:[0-9]|1[0-4])(?:-|$)")
REPORT = re.compile(r"(?:^|-)(?:ket-qua|tuong-thuat|truc-tiep|doi-hinh-thi-dau|danh-sach-cau-thu|gioi-thieu-clb|danh-sach-dang-ky)(?:-|$)")
EXCLUDE = re.compile(r"(?:nhan-dinh|soi-keo|lich-thi-dau|xem-truc-tiep-o-dau|link-xem|ket-qua-boc-tham|du-doan|tin-nhanh|nhan-dinh-truoc-tran)")
def open_db(root):
    root.mkdir(parents=True,exist_ok=True)
    db=sqlite3.connect(root/"archive.sqlite",timeout=40)
    db.execute("PRAGMA journal_mode=WAL")
    db.executescript("""
    CREATE TABLE IF NOT EXISTS listings (category TEXT,page INTEGER,url TEXT,links INTEGER,PRIMARY KEY(category,page));
    CREATE TABLE IF NOT EXISTS urls (url TEXT PRIMARY KEY, category TEXT,rank INTEGER,published_hint TEXT);
    CREATE TABLE IF NOT EXISTS articles (url TEXT PRIMARY KEY, sha TEXT, downloaded TEXT, raw_bytes INTEGER);
    CREATE TABLE IF NOT EXISTS errors (url TEXT PRIMARY KEY,message TEXT,attempts INTEGER);
    """)
    return db

class Reader:
    def __init__(self):
        self.session=requests.Session()
        self.session.headers["User-Agent"]=AGENT
        self.policy=RobotFileParser()
        response=self.session.get(HOST+"/robots.txt",timeout=20)
        response.raise_for_status();self.policy.parse(response.text.splitlines())
        self.last=0
    def get(self,url):
        if urlsplit(url).netloc!="bongdaplus.vn" or not self.policy.can_fetch(AGENT,url):
            raise ValueError("Disallowed URL "+url)
        time.sleep(max(0,0.85-(time.monotonic()-self.last)))
        self.last=time.monotonic()
        r=self.session.get(url,timeout=(5,18));r.raise_for_status()
        if urlsplit(r.url).netloc!="bongdaplus.vn":raise ValueError("unexpected redirect")
        return r

def add_page(db,category,page,url,raw):
    d=html.fromstring(raw)
    links=set()
    for a in d.xpath('//a[@href]'):
        full=urljoin(HOST,a.get("href"));u=urlsplit(full)
        match=ARTICLE.fullmatch(u.path)
        if u.netloc!="bongdaplus.vn" or not match or match[1]!=category:continue
        links.add(HOST+u.path)
    for link in sorted(links):
        slug=link.rsplit("/",1)[1]
        rank=(0 if SCORE.search(slug) and not EXCLUDE.search(slug) else 1 if REPORT.search(slug) and not EXCLUDE.search(slug) else 5)
        db.execute("INSERT OR IGNORE INTO urls VALUES(?,?,?,?)",(link,category,rank,slug[-9:-5]))
    db.execute("INSERT OR REPLACE INTO listings VALUES(?,?,?,?)",(category,page,url,len(links)));db.commit()
    return len(links)
def record_error(db,url,e):
    db.execute("INSERT INTO errors VALUES(?,?,1) ON CONFLICT(url) DO UPDATE SET message=excluded.message, attempts=attempts+1",(url,str(e)[:350]));db.commit()
def indexing(db,reader,limit):
    ids={}
    for cat in CATEGORIES:
        url=HOST+"/"+cat
        try:
            r=reader.get(url)
            doc=html.fromstring(r.content)
            def val(k):return doc.xpath(f'//input[@id="viewmore_{k}"]/@value')[0]
            ids[cat]=(val("type"),val("id"))
            add_page(db,cat,1,url,r.content)
        except Exception as e:record_error(db,url,e)
    print("sections",ids,flush=True)
    # Visit different years early, then fill the gaps in each archive.
    pages=list(dict.fromkeys([2,5,10,20,40,75,100,150,200,300,400,600,800,1000,1200,1500,1800,2200,2600,3000]+list(range(2,limit+1))))
    upper={c:limit+1 for c in ids}
    for page in (n for n in pages if n<=min(limit,10)):
        for cat,(kind,channel) in ids.items():
            if page>=upper[cat]:continue
            old=db.execute("SELECT links FROM listings WHERE category=? AND page=?",(cat,page)).fetchone()
            if old:
                if not old[0]:upper[cat]=min(page,upper[cat])
                continue
            url=f"{HOST}/loadviewmore/{kind}/{channel}/{page}"
            try:
                r=reader.get(url)
                count=add_page(db,cat,page,url,r.content) if r.content.strip() else add_page(db,cat,page,url,b"<div/>")
                if not count:upper[cat]=min(page,upper[cat])
            except Exception as e:record_error(db,url,e)
        if page%20==0 or page==2:print("index",page,db.execute("SELECT rank,count(*) FROM urls GROUP BY rank").fetchall(),flush=True)
def related(db,doc):
    for href in set(doc.xpath("//a[@href]/@href")):
        u=urlsplit(urljoin(HOST,href));m=ARTICLE.fullmatch(u.path)
        if not m or u.hostname!="bongdaplus.vn":continue
        slug=u.path.rsplit("/",1)[1]
        rank=0 if SCORE.search(slug) and not EXCLUDE.search(slug) else 1 if REPORT.search(slug) and not EXCLUDE.search(slug) else 5
        db.execute("INSERT OR IGNORE INTO urls VALUES(?,?,?,?)",(HOST+u.path,m[1],rank,slug[-9:-5]))

def download(db,root,reader,limit):
    cache=root/"html_gz";cache.mkdir(exist_ok=True)
    for (sig,) in db.execute("SELECT sha FROM articles").fetchall():
        related(db,html.fromstring(gzip.decompress((cache/(sig+".html.gz")).read_bytes())))
    db.commit()
    n=0;idle=0
    while n<limit and idle<80:
        rows=db.execute("""SELECT u.url FROM urls u LEFT JOIN articles a USING(url) LEFT JOIN errors e USING(url)
            WHERE category!="bong-da-phong-trao" AND rank<5 AND a.url IS NULL AND COALESCE(e.attempts,0)<2
            ORDER BY rank, substr(u.url,-9,4),u.url LIMIT 30""").fetchall()
        if not rows:
            idle+=1;time.sleep(4);continue
        idle=0
        for (url,) in rows[:limit-n]:
            try:
                r=reader.get(url)
                d=html.fromstring(r.content)
                if not d.xpath('//*[@id="newsDetails"]') or not ARTICLE.fullmatch(urlsplit(r.url).path):
                    raise ValueError("not a newsroom article")
                related(db,d)
                sig=hashlib.sha256(r.content).hexdigest(); dest=cache/(sig+".html.gz")
                if not dest.exists():
                    with gzip.open(dest,"wb") as f:f.write(r.content)
                db.execute("INSERT OR IGNORE INTO articles VALUES(?,?,?,?)",(url,sig,datetime.now(timezone.utc).isoformat(),len(r.content)));db.commit();n+=1
                if n%50==0:print("archived",n,flush=True)
            except Exception as e:record_error(db,url,e)
if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("root",type=Path);p.add_argument("mode",choices=["index","fetch"]);p.add_argument("--limit",type=int,required=True)
    a=p.parse_args();db=open_db(a.root);reader=Reader()
    if a.mode=="index":indexing(db,reader,a.limit)
    else:download(db,a.root,reader,a.limit)
