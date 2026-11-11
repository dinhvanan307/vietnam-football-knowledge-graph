"""Find youth and professional squad selections in domestic newsroom archives."""
import argparse,gzip,hashlib,json,re,sqlite3,time
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urlsplit,urljoin
from urllib.robotparser import RobotFileParser
from concurrent.futures import ThreadPoolExecutor
import requests
from lxml import html,etree
TRUSTED=set("thanhnien.vn tuoitre.vn vov.vn vtv.vn vnexpress.net dantri.com.vn thethao.sggp.org.vn nhandan.vn qdnd.vn vietnamplus.vn bongdaplus.vn thethaovanhoa.vn tienphong.vn baonghean.vn baothanhhoa.vn".split())
def domain(url):
    return urlsplit(url).netloc.lower().removeprefix("www.").removeprefix("amp.")
def ranking(url):
    slug=url.rsplit("/",1)[-1]
    if any(w in slug for w in ["sinh-vien","futsal","bong-chuyen","bong-ro","cau-long","pickleball","-nu-","viet-nam-nu"]):return 9
    youth=bool(re.search(r"u-?(?:1[579]|2[0-3])",slug))
    group=bool(re.search("danh-sach|chot-|trieu-tap|goi-|cong-bo|tap-trung|hoi-quan|doi-hinh-tieu-bieu|diem-danh|duy[eê]t-bin[h]|bo-sung|dang-ky|duoi-truong|chan-dung",slug))
    reg=bool(re.search(r"viet-nam|quoc-gia|viettel|ha-noi|hagl|slna|pvf|vinh-long|da-nang|song-lam|nghe-an|long-an|dong-thap|thanh-hoa|ha-tinh|binh-duong|nam-dinh|hai-phong|khanh-hoa",slug))
    if group and youth and reg:return 0
    if youth and reg and re.search(r"quoc-gia|viettel|ha-noi|hagl|slna|pvf|song-lam|dong-thap",slug):return 2
    if group and reg and re.search(r"doi-tuyen|tuyen-viet-nam|v-league|hang-nhat",slug):return 1
    return 9
def open_db(root):
    root.mkdir(exist_ok=True,parents=True);(root/"raw").mkdir(exist_ok=True);db=sqlite3.connect(root/"docs.sqlite",timeout=30);db.execute("PRAGMA journal_mode=WAL");db.executescript("""
    CREATE TABLE IF NOT EXISTS urls(url TEXT PRIMARY KEY,rank INTEGER); CREATE TABLE IF NOT EXISTS docs(url TEXT PRIMARY KEY,sha TEXT,retrieved TEXT);
    CREATE TABLE IF NOT EXISTS skips(url TEXT PRIMARY KEY,reason TEXT); CREATE TABLE IF NOT EXISTS maps(url TEXT PRIMARY KEY);
    """);return db
class Client:
    def __init__(self):
        self.s=requests.Session();self.agent="FootballGraphCoursework/0.3";self.s.headers.update({"User-Agent":self.agent,"Accept-Encoding":"gzip, deflate"})
        self.policy={};self.last={}
    def read(self,u):
        host=urlsplit(u).netloc
        if domain(u) not in TRUSTED:raise ValueError("external")
        if host not in self.policy:
            r=self.s.get("https://"+host+"/robots.txt",timeout=(7,13))
            if r.status_code not in (200,404):raise ValueError("robots "+str(r.status_code))
            p=RobotFileParser();p.parse(r.text.splitlines() if r.status_code==200 else []);self.policy[host]=p
        if not self.policy[host].can_fetch(self.agent,u):raise ValueError("robots excluded")
        time.sleep(max(0,.65-time.monotonic()+self.last.get(host,0)));self.last[host]=time.monotonic()
        r=self.s.get(u,timeout=(6,19));r.raise_for_status()
        if domain(r.url) not in TRUSTED:raise ValueError("external redirect")
        return r
def index(root):
    db=open_db(root);cl=Client()
    from lxml.etree import XMLParser
    for front,pattern in [("https://thethao.sggp.org.vn/sitemap.xml",r"news-\d+-\d+\.xml$"),("https://thanhnien.vn/sitemap.xml",r"sitemaps-\d+-\d+-\d+-\d+\.xml$")]:
        top=etree.fromstring(cl.read(front).content)
        urls=[x for x in top.xpath('//*[local-name()="loc"]/text()') if re.search(pattern,x)]
        # Interleave years so that coverage grows across different generations.
        urls=sorted(urls,key=lambda x:(x.rsplit("/",1)[1].split("-")[-1],x))
        for j,url in enumerate(urls):
            if db.execute("SELECT 1 FROM maps WHERE url=?",(url,)).fetchone():continue
            try:
                data=cl.read(url).content;tree=etree.fromstring(data,parser=XMLParser(recover=True))
                locs=tree.xpath('//*[local-name()="url"]/*[local-name()="loc"]/text()')
                if not locs:continue
                chosen=[(u,ranking(u)) for u in locs if ranking(u)<9]
                db.executemany("INSERT OR IGNORE INTO urls VALUES(?,?)",chosen);db.execute("INSERT INTO maps VALUES(?)",(url,));db.commit()
            except Exception as exc:
                if j%100==0:print(url,str(exc)[:95],flush=True)
def fetch(root,seeds,limit):
    db=open_db(root);cl=Client();n=idle=0
    db.executemany("INSERT OR IGNORE INTO urls VALUES(?,-1)",[(x,) for x in seeds.read_text().splitlines() if domain(x) in TRUSTED]);db.commit()
    while n<limit and idle<60:
        picks=db.execute("SELECT url FROM urls WHERE url NOT IN(SELECT url FROM docs) AND url NOT IN(SELECT url FROM skips) ORDER BY rank,url LIMIT 30").fetchall()
        if not picks:idle+=1;time.sleep(5);continue
        idle=0
        for (url,) in picks[:limit-n]:
            try:
                r=cl.read(url);doc=html.fromstring(r.content,parser=html.HTMLParser(encoding="utf-8"))
                if not doc.xpath("//h1"):raise ValueError("No article title")
                sig=hashlib.sha256(r.content).hexdigest()
                with gzip.open(root/"raw"/(sig+".gz"),"wb") as f:f.write(r.content)
                db.execute("INSERT OR IGNORE INTO docs VALUES (?,?,?)",(url,sig,datetime.now(timezone.utc).isoformat()));n+=1
                seeds2=set()
                for link in doc.xpath("//a[@href]/@href"):
                    u=urljoin(url,link).split("#")[0].split("?")[0]
                    if domain(u)==domain(url) and re.search(r"\.(?:htm[l]?|vov|vnp|tpo)$",u) and ranking(u)<3:seeds2.add(u)
                db.executemany("INSERT OR IGNORE INTO urls VALUES(?,?)",[(u,ranking(u)) for u in sorted(seeds2)])
                if n%150==0:print("Archived",n,flush=True)
            except Exception as exc:db.execute("INSERT OR REPLACE INTO skips VALUES(?,?)",(url,str(exc)[:160]))
            db.commit()
if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("root",type=Path);p.add_argument("mode",choices=["index","fetch"]);p.add_argument("--seeds",type=Path);p.add_argument("--limit",type=int,default=1800);a=p.parse_args()
    if a.mode=="index":index(a.root)
    else:fetch(a.root,a.seeds,a.limit)
