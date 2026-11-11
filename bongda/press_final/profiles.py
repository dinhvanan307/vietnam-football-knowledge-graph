"""Read registered professionals from published squad cards. No invented season."""
import gzip,json,re,sqlite3
from lxml import html
from bongda.press_final.clubs import identify,key
from bongda.press_final.network import tidy

def club_cards(root):
    db=sqlite3.connect(f"file:{root/'pages.sqlite'}?mode=ro",uri=True)
    for url,team,sig,stamp in db.execute("SELECT url,team,sha,retrieved FROM docs WHERE role='cau-thu' ORDER BY url"):
        path=root/"raw"/(sig+".gz");d=html.fromstring(gzip.decompress(path.read_bytes()),parser=html.HTMLParser(encoding="utf-8"))
        title=tidy(d.xpath('//h1')[0].text_content());label=re.sub(r"^Danh sách cầu thủ\s+","",title)
        club=identify(label,"",team)
        if not club:continue
        feats=[]
        for el in d.xpath('//*[contains(concat(" ",@class," ")," fb-plcard ")]'):
            node=el.xpath('.//*[contains(@class,"fb-plcard__nm")]');pos=el.xpath('.//*[contains(@class,"fb-plcard__mt")]')
            if len(node)!=1 or len(pos)!=1:continue
            name=tidy(node[0].text_content());role=tidy(pos[0].text_content()).split(" · ")[0]
            images=el.xpath('.//img/@src');href=el.get("href") or ""
            pid=re.search(r"/players/(\d+)\.",images[0]) if images else None
            if not pid:pid=re.search(r"-(\d+)\.html$",href)
            if not pid or role not in {"Thủ môn","Hậu vệ","Tiền vệ","Tiền đạo"}:continue
            if re.search(r"[\ufffdÂÃ]|áº|á»",name):continue
            feats.append((int(pid[1]),name,f"{title} | {name} | {role}"))
        if feats:yield url,title,path,stamp,club,feats
    db.close()

def add_club_cards(g,data):
    for url,title,path,stamp,club,rows in data:
        aid=g.document(url,title,[title,*[r[2] for r in rows]],path,stamp,"","news_table","Báo Lâm Đồng")
        g.club(club)
        for pid,name,q in rows:
            who=g.person(pid)
            if not who:continue
            g.link(who,"CO_TEN_TRONG_DANH_SACH_CLB",club,"danh-sach-dang-tai","Bản danh sách truy cập "+stamp[:10],aid,q,"bang_danh_sach_clb_bao")
            g.teams[who].add(club);g.byteam[(club,key(name))].add(who)
