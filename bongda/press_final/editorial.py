"""Vietnamese news-text extraction with explicit entities, tense and match context."""
from __future__ import annotations
import gzip,re,sqlite3,unicodedata
from collections import defaultdict
from datetime import date,timedelta
from pathlib import Path
from lxml import html
from bongda.press_final.network import tidy,token
from bongda.press_final.clubs import key,identify,ALIASES,NAMES,LEAGUES

CAP=r"[A-ZÀ-ÖØ-ÞĀ-ŽẠ-ỴĐ][^\W\d_]*(?:[-’'][^\W\d_]+)?"
FULL=CAP+r"(?:\s+(?:"+CAP+r"|de|da|dos)){2,4}"
FAMILY=set("nguyen tran le pham hoang huynh vo vu phan bui do dang ngo duong ly dinh truong doan mai trinh luong quach ta truong chau lam trieu ha ho diep ho duc chu hoanh to nong phung kieu mac loc giang ngoc quan vi luu ton cao tao".split())
WORDS_TO_AVOID=set("clb u cong ty cup giai doi vong tuyen soat trantruong hlv nam nu sao doi tuyen the thao fc tm hv td svd".split())
ROLE="(?:thủ môn|trung vệ|hậu vệ|tiền vệ|tiền đạo|cầu thủ|thủ quân|đội trưởng|HLV trưởng)"
CLUB_WORD=r"[\w.À-ỹ -]{2,38}"
PREFIX_ROLE=re.compile(r"(?<![\w])("+ROLE+r")\s+("+FULL+r")\s*(?:\(\s*(?:CLB\s+)?("+CLUB_WORD+r")\s*\)|(?:của|thuộc biên chế)\s+(?:CLB\s+)?("+CLUB_WORD+r"))",re.UNICODE)
PAREN=re.compile(r"(?<![\w])("+FULL+r")\s*\(\s*(?:CLB\s+)?("+CLUB_WORD+r")\s*\)")
DENY=re.compile(r"trước đây|từng |cựu |tin đồn|được cho là|đội hình dự kiến|dự đoán|có thể sẽ|muốn chiêu mộ",re.I)
def latin(s):
    return "".join(c for c in unicodedata.normalize("NFD",s.lower().replace("đ","d")) if not unicodedata.combining(c))
VALID_ALIASES=sorted(ALIASES,key=len,reverse=True)
TEAM_TOK=re.compile(r"(?<![a-z0-9])(?:"+"|".join(re.escape(a).replace(r"\ ",r"[ .–-]+") for a in VALID_ALIASES)+r")(?![a-z0-9])")
SCORE=re.compile(r"(?<!\d)(\d{1,2})\s*[-–:]\s*(\d{1,2})(?![\d/])")
def seenclubs(text,day):
    return [c for m in TEAM_TOK.finditer(latin(text)) if (c:=identify(m.group(),day))]
def person_name(s):
    k=key(s);parts=k.split()
    return 3<=len(parts)<=5 and parts[0] in FAMILY and not any(x in WORDS_TO_AVOID for x in parts[1:]) and not any(x in k for x in ("viet nam","nghe an","thanh hoa","ha noi","the cong","ho chi minh"))
def meaningful_name(s):
    return bool(re.fullmatch(r"[^\W\d_]+(?:[ ’'-][^\W\d_]+){1,5}",s)) and not re.search(r"HLV|CLB|dự bị|cầu thủ|\d",s,re.I)
def docdata(source,raw):
    d=html.fromstring(raw,parser=html.HTMLParser(encoding="utf-8"))
    titles=d.xpath('//h1')
    if not titles:return None
    title=tidy(titles[0].text_content())
    body=d.xpath('//*[@id="postContent"]') if source=="bongdaplus" else d.xpath('//*[contains(concat(" ",normalize-space(@class)," ")," cms-body ")]')
    if not body or len(body)!=1:return None
    stamp=d.xpath('//meta[@property="article:published_time" or @itemprop="datePublished"]/@content')
    if not stamp:return None
    pub=re.sub(r'([+-])(\d):',r'\g<1>0\2:',stamp[0]);day=pub[:10]
    if not re.fullmatch(r"\d{4}-\d\d-\d\d",day) or day>"2026-11-11":return None
    lines=[title]
    sap=d.xpath('//*[contains(@class,"article__sapo") or @id="newsSummary" or @id="postSapo"]')
    for node in sap[:1]:
        if tidy(node.text_content()):lines.append(tidy(node.text_content()))
    for br in body[0].xpath(".//br"):br.tail="\n"+(br.tail or "")
    for el in body[0].xpath(".//p[not(descendant::p)]|.//h2|.//h3|.//h4|.//div[not(*)]"):
        if el.xpath("ancestor::figure|ancestor::figcaption|ancestor::aside|ancestor::script"):continue
        for line in el.text_content().splitlines():
            val=tidy(line)
            if val and val!=lines[-1]:lines.append(val)
    return title,pub,lines

def archive_docs(root):
    for typ,directory in [("bongdaplus","thu_bao"),("sggp","thu_sggp")]:
        path=root/directory
        db=sqlite3.connect(f"file:{path/('archive.sqlite' if typ=='bongdaplus' else 'urls.sqlite')}?mode=ro",uri=True)
        query=("SELECT a.url,a.sha,a.downloaded,u.category FROM articles a JOIN urls u USING (url) WHERE u.category IN ('v-league','cup-quoc-gia','hang-nhat-quoc-gia','u17-viet-nam','u19-viet-nam','u21-viet-nam') ORDER BY a.url" if typ=="bongdaplus" else "SELECT url,sha,retrieved,'' FROM files ORDER BY url")
        for url,sig,stamp,cat in db.execute(query):
            pathraw=path/("html_gz" if typ=="bongdaplus" else "raw")/(sig+(".html.gz" if typ=="bongdaplus" else ".gz"))
            data=docdata(typ,gzip.decompress(pathraw.read_bytes()))
            if data:yield url,pathraw,stamp,cat,typ,*data
        db.close()

def match_of(g,title,lines,day):
    if re.search(r"nhận định|dự đoán|lịch thi đấu|trước trận|\d+[hg]\d*[, ]|vòng loại U|U[. ]?\d+",title,re.I):return None,None
    day_obj=date.fromisoformat(day);near={(day_obj-timedelta(days=k)).isoformat() for k in range(3)}
    candidates=defaultdict(list);headline_teams=set(seenclubs(title,day))
    for line in [title,*lines[1:4]]:
        if DENY.search(line) or re.search(r"mùa trước|lượt đi năm|trước đó.{0,18}đã|lần gặp gần nhất",line,re.I):continue
        teams=set(seenclubs(line,day)); scores={tuple(map(int,m.groups())) for m in SCORE.finditer(line) if int(m[1])<15 and int(m[2])<15}
        if len(teams)!=2 or not scores or (headline_teams and not headline_teams.intersection(teams)):continue
        pair=tuple(sorted(teams))
        for m in g.pairdates.get(pair,()):
            row=g.matchdata[m]
            if row["date"] in near and (row["score"] in scores or row["score"][::-1] in scores):candidates[m].append(line)
    if len(candidates)==1:
        mid,qs=next(iter(candidates.items()));return mid,min(qs,key=len)
    return None,None

def listed(line):
    p=line.split(":",1)
    if len(p)!=2 or len(p[0])>42:return None
    raw=p[1].strip().rstrip(".");parts=re.split(r"[,;](?![^()]*\))",raw)
    players=[]
    for s in parts:
        first=re.sub(r"\([^)]*\)","",s).strip(" .–-")
        first=re.sub(r"^\d+[. ):-]+","",first)
        if not re.fullmatch(r"[^\W\d_]+(?:[ ’'-][^\W\d_]+){0,5}",first):return None
        subs=[]
        for name,minute in re.findall(r"\(([^()\d,;]{2,50})[, ]+\s*(\d{1,3})(?:[’'′]|\s*phút)?\s*\)",s):
            name=tidy(name)
            if meaningful_name(name) and int(minute)<=125:subs.append(name)
        players.append((first,subs))
    return (p[0],players) if len(players)==11 else None

def lineups(lines,day,match):
    pair=set(match["pair"]);found={}
    for i,heading in enumerate(lines):
        h=key(heading)
        if len(h)>115 or not re.match(r"^doi hinh (?:thi dau|xuat phat|ra san|hai doi|chinh thuc)",h) or "du kien" in h or "du doan" in h:continue
        block={}
        for original in lines[i+1:i+5]:
            data=listed(original)
            if not data:continue
            label,players=data;club=identify(label,day)
            if club in pair:block[club]=(original,players)
        if set(block)==pair:found=block;break
    return found
def named_player(g,name,club,day,corpus,anchors,permit_new=True):
    name=tidy(name);k=key(name);known=g.people.get(k,set())
    if not k:return None
    if len(known)==1 and (person_name(name) or len(k.split())>=2):
        ident=next(iter(known))
        if club in g.teams[ident] or person_name(name):return ident
    if known:return None
    if person_name(name) and permit_new:
        ident=g.node("p9_text_"+token(k),name,"Person","Player");g.people[k].add(ident);g.teams[ident].add(club);return ident
    if len(k.split())<2:return None
    possible=set()
    for y in (int(day[:4])-1,int(day[:4]),int(day[:4])+1):
        possible.update(anchors.get((club,y,k),()))
    if len(possible)==1:return next(iter(possible))
    return None
def affiliations(lines,day):
    for line in lines:
        if len(line)>1250 or DENY.search(line) or re.search(r"đội tuyển U|đội U[. ]?\d+|sinh viên|bóng chuyền|futsal|phong trào",line,re.I):continue
        for m in PAREN.finditer(line):
            name,label=m.groups();club=identify(label,day)
            prior=line[max(0,m.start()-90):m.start()]
            if re.search(r"HLV|trọng tài|bác sĩ|chủ tịch|giám đốc|nhà báo|ông ",prior[-35:],re.I):continue
            if club and person_name(name) and re.search(ROLE+r"|đội hình|danh sách cầu thủ",prior,re.I):yield name,club,line
        for m in PREFIX_ROLE.finditer(line):
            role,name,label,phrase=m.groups()
            if role=="HLV trưởng" or not person_name(name):continue
            if label:club=identify(label,day)
            else:
                found=list(TEAM_TOK.finditer(latin(phrase or "")))
                club=identify(found[0].group(),day) if found and found[0].start()==0 else None
            if club:yield name,club,line

def add_text(g,root):
    anchors=defaultdict(set)
    def anchor(ident,club,yr):
        full=key(g.nodes[ident]["canonical_name"].split(" (")[0]).split()
        if len(full)>=3:anchors[club,yr," ".join(full[-2:])].add(ident)
    for f in g.facts.values():
        if f["relation_type"] not in {"CO_TEN_TRONG_DOI_HINH_MUA","CHUYEN_DEN_CLB","CHUYEN_DI_TU","DANG_KY_THI_DAU_CHO"}:continue
        year=re.search(r"20\d{2}",f["period"])
        if year:anchor(f["src_id"],f["dst_id"],int(year[0]))
    for url,path,stamp,cat,src,title,pub,lines in archive_docs(root):
        day=pub[:10]
        if re.search(r"phong trào|sinh viên|doanh nhân|bóng chuyền|futsal|quần vợt|học sinh",title,re.I):continue
        g.logs["editorials_read"]+=1
        # Only reported affiliation with a recognized professional club can add a player.
        aff=list(affiliations(lines,day))
        if re.search(r"U[. ]?\d{2}|nữ",title,re.I) or cat.startswith(("u17","u19","u21")):aff=[]
        mid,proof=match_of(g,title,lines,day)
        if not mid and not aff:continue
        aid=g.document(url,title,lines,path,stamp,pub,"editorial","Tạp chí Bóng đá" if src=="bongdaplus" else "Sài Gòn Giải Phóng")
        for name,club,line in aff:
            who=named_player(g,name,club,day,"",anchors)
            if who:
                g.club(club);g.link(who,"DUOC_BAO_GHI_NHAN_THUOC_CLB",club,day[:4],day[:4],aid,line,"nlp_ten_va_clb_trong_cau")
                g.teams[who].add(club);anchor(who,club,int(day[:4]))
        if not mid:continue
        game=g.matchdata[mid];ds=game["date"]
        for club in game["pair"]:g.link(club,"GOP_MAT_TRONG_TRAN",mid,mid,ds,aid,proof,"nlp_tuong_thuat_ket_qua")
        block=lineups(lines,day,game)
        for club,(line,players) in block.items():
            for starter,subs in players:
                for name,relation in [(starter,"DA_CHINH_TRONG_TRAN"),*((s,"VAO_SAN_THAY_NGUOI_TRONG_TRAN") for s in subs)]:
                    who=named_player(g,name,club,day,"",anchors)
                    if not who:continue
                    g.link(who,relation,mid,mid,ds,aid,line,"nlp_doi_hinh_trong_bai",dict(club_id=club))
                    g.teams[who].add(club)
