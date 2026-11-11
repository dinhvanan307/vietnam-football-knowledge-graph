"""Alternative reader for post-match reports. Return at most one main event, with an explicit supporting span."""
import gzip,re
from datetime import date,timedelta
from lxml import html
from bongda.press_final.editorial import docdata,seenclubs,SCORE,match_of
from bongda.press_final.network import tidy
from bongda.press_final.clubs import key
PRE=re.compile(r"nhan dinh|du doan|\bse dien ra\b|\btruoc tran\b|du suc thang hang|tim loi thoat|tin chuyen nhuong|dieu chinh ngoai binh|giai quyet khung hoang|bo cuoc|tranh tai vao|thay tuong sau|ky hop dong|lich thi dau|trong tai bat chinh|tai ngo.*chung ket|chuan bi|\bcanh bao\b")
RESULT=re.compile(r"thang|thua|hoa [01234]|hoa tran|chia diem|gi[aà]nh diem|nguoc dong|hat trick|lap cu dup|that bai|thu[n]?g luoi|ghi ban|danh bai|chien thang|lan luot|so mot|dau bang|chung cuoc|trang tay|gianh.*diem|ban thang|giu.*diem|mat diem|khong thang|go hoa|cam hoa|thang tien|thang loi")
def read_sggp(raw):
    res=docdata("sggp",raw)
    if not res:return None
    t,p,ls=res
    d=html.fromstring(raw,parser=html.HTMLParser(encoding="utf-8"))
    bs=d.xpath('//*[contains(concat(" ",normalize-space(@class)," ")," cms-body ")]')
    if not bs:return res
    b=bs[0]
    for e in list(b.xpath('.//script|.//style|.//nav|.//aside|.//figure|.//figcaption|.//iframe|.//*[contains(@class,"related")]')):
        e.drop_tree()
    for e in b.xpath('.//br'):e.tail="\n"+(e.tail or "")
    for e in b.xpath('.//p|.//div|.//h2|.//h3|.//li'):
        e.tail="\n"+(e.tail or "")
    # Flatten text nodes including direct children; the legacy SGGP CMS often omits <p>.
    body=[tidy(v) for v in b.text_content().splitlines() if tidy(v)]
    return t,p,list(dict.fromkeys([t,*ls[1:2],*body]))
def resolve(g,title,lines,day):
    h=key(title);lead=" ".join(lines[1:3])[:550];txt=key(lead)
    if PRE.search(h) or not RESULT.search(h+" "+txt) or any(w in h+" "+txt for w in ["futsal","sinh vien","bong chuyen","bong ro"]):return None,None
    if re.search(r"dieu chinh|doi ngoai binh|bo nhiem|bi danh gia|kha nang|tiet lo|doi lich|doi san|danh gia suc manh",h):return None,None
    direct,proof=match_of(g,title,lines,day)
    focus=set(seenclubs(title,day))
    if len(focus)>2:return None,None
    near={(date.fromisoformat(day)-timedelta(days=j)).isoformat() for j in range(3)};candidate={}
    for a,pair in g.pairdates.items():
        if focus and not focus.issubset(a):continue
        for m in pair:
            game=g.matchdata[m]
            if game["date"] not in near:continue
            score=game["score"]
            for j,line in enumerate(lines[:18]):
                # Keep both teams and result in one local passage (also permits a boundary after the lead).
                for text in [line," ".join(lines[j:j+2])]:
                    if len(text)>3200:continue
                    for sentence in re.split(r"(?<=[.!?])\s+(?=[A-ZÀ-ỴĐ(])",text):
                        clubs=set(seenclubs(sentence,day));sv={tuple(map(int,x.groups())) for x in SCORE.finditer(sentence)}
                        if not set(a).issubset(clubs):continue
                        exact=len(clubs)==2
                        numeric=score in sv or score[::-1] in sv
                        if not numeric and (sv or not exact or not RESULT.search(key(sentence))):continue
                        if not focus and (not exact or not numeric or j>2):continue
                        if re.search(r"\b(?:mùa trước|trước đây|lượt đi mùa trước|chuẩn bị gặp|sẽ gặp|sắp tới|ở vòng tiếp theo|bóng chuyền|futsal)\b",sentence,re.I):continue
                        grade=(6*numeric+3*exact+3*(j<3)+1*(len(focus)==2),-min(j,8))
                        if m not in candidate or grade>candidate[m][0]:candidate[m]=(grade,sentence)
    if not candidate:return direct,proof
    order=sorted(candidate,key=lambda k:candidate[k][0],reverse=True)
    if len(order)>1 and candidate[order[0]][0]==candidate[order[1]][0]:return None,None
    m=order[0];return m,candidate[m][1]
