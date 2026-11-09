"""Spider mẫu chạy local, chỉ đọc danh sách URL của hai báo, không khám phá URL mới."""
import csv, hashlib
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse, urljoin, urldefrag
import scrapy
from trafilatura import extract

class News(scrapy.Spider):
    name="d22_seeds"
    allowed_domains=["tuoitre.vn","thanhnien.vn"]
    custom_settings={"ROBOTSTXT_OBEY":True,"AUTOTHROTTLE_ENABLED":True,"CONCURRENT_REQUESTS_PER_DOMAIN":1,"DOWNLOAD_DELAY":2,"DOWNLOAD_TIMEOUT":25,"RETRY_TIMES":1,"COOKIES_ENABLED":False,"USER_AGENT":"FootballGraphCoursework/0.1"}
    fields="source source_kind canonical_url title published_at retrieved_at story_group pageid revid revision_at raw_file text_file".split()
    def __init__(self,seeds="templates/seeds.tsv",out="work/thu01",**kwargs):
        super().__init__(**kwargs);self.seeds=Path(seeds);self.out=Path(out)
        with self.seeds.open(encoding="utf-8-sig",newline="") as f:self.urls=list(csv.DictReader(f,delimiter="\t"))
        self.out.mkdir(parents=True,exist_ok=False)
        for d in ["html","txt"]:(self.out/d).mkdir()
        self.record("intake.tsv",self.fields)
        self.record("errors.tsv",["url","reason"])
    def record(self,file,fields,row=None):
        with (self.out/file).open("a",encoding="utf-8",newline="") as f:
            w=csv.writer(f,delimiter="\t");w.writerow(fields if row is None else [row.get(k,"") for k in fields])
    def problem(self,url,reason):
        self.record("errors.tsv",["url","reason"],dict(url=url,reason=reason))
    async def start(self):
        seen=set()
        for r in self.urls:
            u=r["url"].strip();host=urlparse(u).hostname
            if urlparse(u).scheme!="https" or host not in ("tuoitre.vn","www.tuoitre.vn","thanhnien.vn","www.thanhnien.vn"):
                self.problem(u,"outside_allowlist");continue
            if u in seen:self.problem(u,"duplicate_seed");continue
            seen.add(u);yield scrapy.Request(u,callback=self.parse,errback=self.error,cb_kwargs={"seed":r})
    def error(self,failure):
        self.problem(failure.request.url,failure.getErrorMessage())
    def parse(self,response,seed):
        host=urlparse(response.url).hostname
        if host not in ("tuoitre.vn","www.tuoitre.vn","thanhnien.vn","www.thanhnien.vn"):self.problem(response.url,"redirect_outside_allowlist");return
        u=urldefrag(urljoin(response.url,response.css('link[rel="canonical"]::attr(href)').get() or response.url))[0]
        if urlparse(u).hostname!=host and (urlparse(u).hostname or "").removeprefix("www.")!=host.removeprefix("www."):
            self.problem(response.url,"canonical_outside_source");return
        key=hashlib.sha256(response.url.encode()).hexdigest()[:20]
        raw="html/"+key+".html"; clean="txt/"+key+".txt"
        (self.out/raw).write_bytes(response.body)
        try:
            title=" ".join(response.css("h1 ::text, h1::text").getall()).strip() or response.css('meta[property="og:title"]::attr(content)').get() or ""
            stamp=(response.css('meta[property="article:published_time"]::attr(content),meta[name="pubdate"]::attr(content)').get() or "").strip()
            if not stamp:stamp=(seed.get("published_at") or "").strip()
            iso=datetime.fromisoformat(stamp.replace("Z","+00:00"));stamp=iso.isoformat() if iso.utcoffset() is not None else iso.date().isoformat()
            if not 2012 <= iso.year <= 2025:
                raise ValueError("publication_outside_2012_2025")
            # Hai báo dùng data-role để phân biệt sapo/nội dung với tin bên lề.
            article=response.css('[data-role="content"]')
            paragraphs=response.css('[data-role="sapo"]') + article.xpath('.//p[not(ancestor::figure or ancestor::table or ancestor::aside or ancestor::*[contains(@class,"VCSortableInPreviewMode")])]')
            parts=[]
            for element in paragraphs:
                line=" ".join(element.xpath("string(.)").get("").split())
                if line and line not in parts:
                    parts.append(line)
            body="\n\n".join(parts)
            if len(body)<80:
                body=extract(response.body,url=u,include_comments=False,include_tables=False) or ""
            if not title or len(body.strip())<80:raise ValueError("empty/short article or missing title")
            (self.out/clean).write_text(body.strip(),encoding="utf-8")
            self.record("intake.tsv",self.fields,dict(source=seed["source"],source_kind="press",canonical_url=u,title=title,published_at=stamp,retrieved_at=datetime.now(timezone.utc).isoformat(),story_group=seed.get("story_group") or "pending-"+key,raw_file=raw,text_file=clean))
        except (ValueError,TypeError) as err:self.problem(response.url,str(err)+"; raw="+raw)
