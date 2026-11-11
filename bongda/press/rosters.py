"""Read only explicit season squad lists in Vietnamese editorial articles."""
import hashlib
import re
import unicodedata
from urllib.parse import urlsplit

from lxml import html

RELATION = "CO_TEN_TRONG_DOI_HINH_MUA"
CLUBS = {
    "hagl": ("c-hagl", "Hoàng Anh Gia Lai"),
    "hà nội": ("c-hn", "CLB Hà Nội"), "hà nội fc": ("c-hn", "CLB Hà Nội"),
    "cahn": ("c-cahn", "CLB Công an Hà Nội"), "công an hà nội": ("c-cahn", "CLB Công an Hà Nội"),
    "nam định": ("c-nd", "CLB Nam Định"), "thép xanh nam định": ("c-nd", "CLB Nam Định"),
    "slna": ("c-slna", "Sông Lam Nghệ An"), "sông lam nghệ an": ("c-slna", "Sông Lam Nghệ An"),
    "bình định": ("c-binhdinh", "CLB Bình Định"), "hải phòng": ("c-hp", "CLB Hải Phòng"),
    "hà tĩnh": ("c-ht", "CLB Hồng Lĩnh Hà Tĩnh"), "hồng lĩnh hà tĩnh": ("c-ht", "CLB Hồng Lĩnh Hà Tĩnh"),
    "b.bình dương": ("c-bd", "CLB Bình Dương"), "becamex tp.hcm": ("c-bd", "CLB Bình Dương"),
    "tp.hcm": ("c-hcm", "CLB TP.HCM"), "công an tp.hcm": ("c-hcm", "CLB TP.HCM"),
    "ca tp.hcm": ("c-hcm", "CLB TP.HCM"), "quảng nam": ("c-qn", "CLB Quảng Nam"),
    "thể công viettel": ("c-tc", "Thể Công Viettel"), "viettel": ("c-tc", "Thể Công Viettel"),
    "thanh hóa": ("c-th", "CLB Thanh Hóa"), "shb đà nẵng": ("c-dn", "CLB Đà Nẵng"),
    "ninh bình": ("club-press-ninhbinh-2025", "CLB Ninh Bình (2025/26)"),
    "khánh hòa": ("club-press-khanhhoa-2023", "CLB Khánh Hòa (2023–24)"),
}
POSITION = re.compile(r"^(thủ môn|hậu vệ|tiền vệ|tiền đạo)\s*(?:\((\d+)\))?\s*:\s*(.+)$", re.I)
SEASON = re.compile(r"(20\d\d(?:/\d\d)?)\b")
def norm(s):
    return " ".join(unicodedata.normalize("NFC",s).split())
def key(s):
    return norm(s).lower().replace("hoà","hòa").replace("hoá","hóa")
def club_for(s):
    text=key(s)
    for alias in sorted(CLUBS,key=len,reverse=True):
        if re.search(r'(?<!\w)'+re.escape(alias)+r'(?!\w)',text):
            return CLUBS[alias]
    return None
def digest(s):
    return hashlib.sha256(s.encode()).hexdigest()[:20]
def article(meta,raw):
    """Keep DOM order. A BR ends a roster line on several generations of the website."""
    if hashlib.sha256(raw).hexdigest()!=meta["raw_sha256"]: raise ValueError("HTML checksum mismatch")
    doc=html.fromstring(raw,parser=html.HTMLParser(encoding="utf-8"))
    body=doc.xpath('//*[@id="postContent"]')
    if len(body)!=1: raise ValueError("Article body missing")
    title=norm(doc.xpath("//h1")[0].text_content())
    canonical=doc.xpath('//link[@rel="canonical"]/@href')
    url=canonical[0] if canonical else meta["url"]
    if urlsplit(url).hostname!="bongdaplus.vn": raise ValueError("Publisher mismatch")
    date=doc.xpath('//meta[@property="article:published_time" or @itemprop="datePublished"]/@content')
    if not date: raise ValueError("Date missing")
    for br in body[0].xpath(".//br"):
        br.tail="\n"+(br.tail or "")
    lines=[]
    for el in body[0].xpath(".//p[not(descendant::p)]|.//h2|.//h3|.//h4"):
        if el.xpath('ancestor::figure|ancestor::figcaption'):continue
        for line in el.text_content().splitlines():
            line=norm(line)
            if line:lines.append(line)
    text="\n\n".join([title]+lines)
    date_string=re.sub(r'([+-])(\d):',r'\g<1>0\2:',date[0])
    aid="a_news_"+digest(url)
    return dict(article_id=aid,source="Tạp chí Bóng đá",source_kind="press",canonical_url=url,
                published_at=date_string,retrieved_at=meta["retrieved_at"],title=title,clean_text=text,
                raw_sha256=meta["raw_sha256"],clean_sha256=hashlib.sha256(text.encode()).hexdigest(),
                record_kind="real",pageid="",revid="",revision_at="",story_group=aid)
def squad(a):
    lines=a["clean_text"].split("\n\n")
    title=lines[0].split(":")[0]
    club=club_for(title)
    season_match=SEASON.search(title)
    if not club or not season_match:return [],"unresolved title"
    season=season_match[1]
    for i,line in enumerate(lines[1:],1):
        s=key(line)
        if not s.startswith("danh sách") or len(line)>135 or any(word in s for word in ("đến","đi và","chuyển nhượng","triệu tập","dự kiến")):continue
        if club_for(line)!=club:continue
        other=SEASON.search(line)
        if other and other[1]!=season:continue
        j=i+1;rows=[];pos=set()
        while j<len(lines) and (m:=POSITION.match(lines[j])):
            role,num,listing=m.groups()
            names=[norm(n.strip(' .;')) for n in re.split('[,;]',listing)]
            if num and len(names)!=int(num):return [],"reported role count mismatch"
            if role.lower() in pos:return [],"duplicate position heading"
            pos.add(role.lower())
            for name in names:
                rows.append(dict(club=club[0],club_name=club[1],season=season,name=name,position=role.lower(),
                                 heading=line,line=lines[j],line_index=j,section_index=i))
            j+=1
        if len(pos)>=3:return rows,"roster"
    return [],"no explicit roster with three position groups"
