"""Extract only explicit within-list associations between a named player and domestic club."""
import gzip,re,sqlite3,unicodedata
from collections import defaultdict
from urllib.parse import urlsplit
from lxml import html
from bongda.press_final.clubs import key,identify
from bongda.press_final.network import tidy,token
from bongda.press_final.editorial import person_name,meaningful_name
BODY='//*[@id="postContent" or @itemprop="articleBody" or @data-role="content" or contains(concat(" ",@class," ")," cms-body ") or contains(concat(" ",@class," ")," fck_detail ") or contains(concat(" ",@class," ")," entry-body ") or contains(concat(" ",@class," ")," post-content ") or contains(concat(" ",@class," ")," article-body ") or contains(concat(" ",@class," ")," article-content ") or contains(concat(" ",@class," ")," detail-content ")]'
POSITION=re.compile(r"^(?:(?:Danh sách|[–*·-]|Các)\s*)?(?:Thủ môn|Hậu vệ|Tiền vệ|Tiền đạo|Trung vệ|Cầu thủ)\s*(?:\(\s*\d+\s*\)|\d+)?\s*[:：–-]\s*",re.I)
GROUP=re.compile(r"([^();:]{2,350})\(([^()]{1,55})\)")
def dated(d):
    for v in d.xpath('//meta[@property="article:published_time" or @itemprop="datePublished" or @name="pubdate"]/@content')+d.xpath('//time[@datetime]/@datetime'):
        m=re.search(r"(?:19|20)\d{2}-\d\d-\d\d",v)
        if m:return m[0]
    for s in d.xpath('//script[@type="application/ld+json"]/text()'):
        m=re.search(r'"datePublished"\s*:\s*"((?:19|20)\d\d-\d\d-\d\d)',s)
        if m:return m[1]
def observed(g,name,club):
    if not person_name(name):return None
    k=key(name);ids=g.people.get(k,set())
    if len(ids)>1:return None
    if ids:
        who=next(iter(ids))
        existing=g.nodes[who]["canonical_name"].split(" (")[0]
        if g.version!="A9" and not existing.isascii() and not name.isascii() and unicodedata.normalize("NFC",existing).casefold()!=unicodedata.normalize("NFC",name).casefold():
            g.logs["accent_conflicts_held"]+=1;return None
        if set(g.nodes[who]["role"].split("|")).isdisjoint({"Player"}):return None
    else:
        who=g.node("p9_text_"+token(k),name,"Person","Player");g.people[k].add(who)
    g.teams[who].add(club);return who
def player_label(s):
    s=re.sub(r"^\s*(?:[-–.,;]|\d+[.)])\s*","",s).strip(" ,.;-–")
    s=re.sub(r"^(?:(?:thủ môn|hậu vệ|trung vệ|tiền vệ|tiền đạo|cầu thủ)\s+)","",s,flags=re.I)
    return s if re.fullmatch(r"[\wÀ-ỹĐđ '-]{4,48}",s) and meaningful_name(s) and person_name(s) else ""
def youth_club(label,day):
    # A province or a selection carrying only a province name is not proof of a club academy.
    k=key(label)
    explicit=k.startswith(("clb ","fc ")) or k.endswith(" fc") or k in {"hagl","ha gl","hoang anh gia lai","viettel","the cong viettel","slna","song lam nghe an","ha noi t t","shb da nang","becamex binh duong","pvf cand","cong an ha noi","hong linh ha tinh","dong a thanh hoa","dong tam long an","thep xanh nam dinh"}
    return identify(label,day) if explicit else None
def list_rows(lines,day):
    for line in lines:
        pos=POSITION.match(line)
        if not pos:continue
        text=line[pos.end():];seen=set()
        for m in GROUP.finditer(text):
            names,label=m.groups();label=re.sub(r"^cùng\s+","",label.strip(),flags=re.I)
            c=youth_club(label,day)
            if not c:continue
            # A printed club in parentheses closes exactly the preceding group.
            names=names.strip(" ,;.-–").replace(" và ",", ")
            parts=re.split(r"\s*,\s*",names)
            if not parts or not all(player_label(i) for i in parts):continue
            for raw in parts:
                n=player_label(raw)
                if (n,c) not in seen:
                    seen.add((n,c));yield n,c,line
def article_rows(d,day):
    nodes=d.xpath(BODY)
    if not nodes:return [],[]
    node=max(nodes,key=lambda el:len(el.xpath(".//p")))
    for br in node.xpath('.//br'):br.tail="\n"+(br.tail or "")
    lines=[]
    for el in node.xpath('.//p[not(descendant::p)]|.//li[not(descendant::li)]|.//h2|.//h3|.//div[not(*)]'):
        if el.xpath('ancestor::aside|ancestor::figcaption|ancestor::figure|ancestor::nav'):continue
        for t in el.text_content().splitlines():
            t=tidy(t)
            if t and (not lines or lines[-1]!=t):lines.append(t)
    out=list(list_rows(lines,day))
    for tbl in node.xpath('.//table'):
        headers=[];indexes=None
        for tr in tbl.xpath('.//tr'):
            vals=[tidy(x.text_content()) for x in tr.xpath('./td|./th')];vs=[key(v) for v in vals]
            if any(v in {"ho va ten","ho ten","ten cau thu","cau thu"} for v in vs) and any(v in {"clb","don vi","doi bong","cau lac bo","doi"} for v in vs):
                ni=next(i for i,v in enumerate(vs) if v in {"ho va ten","ho ten","ten cau thu","cau thu"})
                ci=next(i for i,v in enumerate(vs) if v in {"clb","don vi","doi bong","cau lac bo","doi"})
                indexes=(ni,ci);headers=vals;continue
            if not indexes or len(vals)!=len(headers):continue
            n=player_label(vals[indexes[0]]);c=youth_club(vals[indexes[1]],day)
            if n and c:
                quote=" | ".join(vals);lines.append(quote);out.append((n,c,quote))
    return lines,out
def add_youth(g,root):
    db=sqlite3.connect(f"file:{root/'docs.sqlite'}?mode=ro",uri=True)
    used={a["canonical_url"] for a in g.docs.values()}
    for url,sig,stamp in db.execute("SELECT url,sha,retrieved FROM docs ORDER BY url"):
        path=root/"raw"/(sig+".gz");d=html.fromstring(gzip.decompress(path.read_bytes()),parser=html.HTMLParser(encoding="utf-8"))
        h=d.xpath('//h1');pub=dated(d)
        if not h or not pub or pub>"2026-11-11":continue
        title=tidy(h[0].text_content());slug=key(title)
        if re.search(r"\bnu\b|futsal|sinh vien|bong chuyen|bong ro",slug):continue
        if not re.search(r"U[. -]?(?:1[579]|2[0-3])",title,re.I) and not re.search(r"doi tuyen|v league|hang nhat",slug):continue
        lines,rows=article_rows(d,pub)
        if not rows:continue
        aid=g.document(url,title,[title,*lines],path,stamp,pub,"editorial",urlsplit(url).netloc)
        for n,c,line in rows:
            who=observed(g,n,c)
            if who:
                g.club(c);g.link(who,"DUOC_BAO_GHI_NHAN_THUOC_CLB",c,pub[:4],pub[:4],aid,line,"nlp_danh_sach_ten_kem_clb")
    db.close()
