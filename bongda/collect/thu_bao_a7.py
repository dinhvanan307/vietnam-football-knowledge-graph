"""Download only listed news articles, retain dated article text and original response."""
import csv,hashlib,json,re,unicodedata
from datetime import datetime,timezone
from pathlib import Path
from urllib.parse import urljoin,urlsplit
import scrapy
from trafilatura import extract
from lxml import etree
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from bongda.collect.thu_bao_mau import article_body
class FinalPress(scrapy.Spider):
    name='football_a7_holdout'
    allowed_domains = ['baodanang.vn', 'baohatinh.vn', 'baokhanhhoa.vn', 'baoxaydung.vn', 'bongdaplus.vn', 'cand.vn', 'phunuvietnam.vn', 'plo.vn', 'thanhnien.vn', 'thethaovanhoa.vn', 'tienphong.vn', 'tuoitre.vn', 'vov.vn', 'vtcnews.vn', 'vtv.vn', 'znews.vn']
    custom_settings={'ROBOTSTXT_OBEY':True,'DOWNLOAD_DELAY':1.5,'CONCURRENT_REQUESTS_PER_DOMAIN':1,'DOWNLOAD_TIMEOUT':30,'RETRY_TIMES':1,'COOKIES_ENABLED':False,'USER_AGENT':'FootballGraphCoursework/0.1'}
    def __init__(self,lot_dir,**kw):
        super().__init__(**kw);self.b=Path(lot_dir).resolve();self.d=self.b/'nguon';self.d.mkdir(exist_ok=False)
        (self.d/'html').mkdir();(self.d/'txt').mkdir()
        self.cols='source source_kind canonical_url title published_at retrieved_at story_group pageid revid revision_at raw_file text_file'.split()
        self.write('intake.tsv',self.cols);self.write('errors.tsv',['url','reason'])
    def write(self,n,r):
        with (self.d/n).open('a',newline='') as f:csv.writer(f,delimiter='\t').writerow(r)
    async def start(self):
        for row in csv.DictReader((self.b/'seeds.tsv').open(),delimiter='\t'):
            yield scrapy.Request(row['url'],callback=self.parse,errback=self.error,cb_kwargs={'row':row})
    def error(self,f):self.write('errors.tsv',[f.request.url,f.getErrorMessage()])
    def parse(self,response,row):
        host=urlsplit(response.url).hostname or ''
        if not any(host==d or host.endswith('.'+d) for d in self.allowed_domains):self.write('errors.tsv',[row['url'],'publisher redirect']);return
        url=urljoin(response.url,response.css('link[rel="canonical"]::attr(href)').get() or response.url).split('?')[0]
        if urlsplit(url).hostname!=host:url=response.url.split('?')[0]
        title=(response.css('meta[property="og:title"]::attr(content)').get() or ' '.join(response.css('h1 ::text,h1::text').getall())).strip()
        if host.endswith(('thanhnien.vn','tuoitre.vn')):body=article_body(response,url)
        else:
            tree=extract(response.body,url=url,output_format='xml',include_formatting=False,include_tables=False,include_comments=False)
            paras=etree.fromstring(tree.encode()).xpath('//main//p|//main//item') if tree else []
            body='\n\n'.join(dict.fromkeys(' '.join(''.join(p.itertext()).split()) for p in paras if ''.join(p.itertext()).strip()))
        date=response.css('meta[property="article:published_time"]::attr(content),meta[name="pubdate"]::attr(content),meta[itemprop="datePublished"]::attr(content),time[datetime]::attr(datetime)').get() or ''
        if not date:
            m=re.search(r'"datePublished"\s*:\s*"([^"]+)',response.text);date=m[1] if m else ''
        if not date:
            m=re.search(r'(?<!\d)([0-3]?\d)[/\.-]([01]?\d)[/\.-](20(?:1\d|2[0-5]))\b', ' '.join(response.xpath('//body//text()[not(parent::script or parent::style)]').getall())[:12000])
            if m:date=f'{m[3]}-{int(m[2]):02}-{int(m[1]):02}'
        if not re.match('20(1[2-9]|2[0-5])-',date) or not title or len(body)<100:self.write('errors.tsv',[row['url'],str(('bad metadata',date,len(body)))]);return
        digest=hashlib.sha256(response.body).hexdigest();raw=f'html/{digest}.html';txt=f'txt/{digest}.txt'
        (self.d/raw).write_bytes(response.body);(self.d/txt).write_text(unicodedata.normalize('NFC',body.strip()))
        self.write('intake.tsv',[row['source'],'press',url,title,date,datetime.now(timezone.utc).isoformat(),'news-'+digest[:16],'','','',raw,txt])
        self.write('redirects.tsv',[row['url'],url])
