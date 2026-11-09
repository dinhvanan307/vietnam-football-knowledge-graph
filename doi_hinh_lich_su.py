"""Lấy danh sách đội hình các CLB ở bản lịch sử và chỉ nhận mùa giải ghi trong văn bản."""
import hashlib,json,re
from datetime import datetime,timezone
from pathlib import Path
import mwparserfromhell as mw
from thu_mua_giai import request,atomic
from doc_bien_ban import item,param,position
CLUBS=["Huế","Đắk Lắk","Cần Thơ","Đồng Tháp","Tây Ninh","Bình Phước","Long An","Nam Định","Đồng Nai","Phú Yên","Bình Định","Quảng Nam","Hải Phòng","Hoàng Anh Gia Lai","Sông Lam Nghệ An","Becamex Bình Dương","Than Quảng Ninh","Hà Nội T&T","Sanna Khánh Hòa BVN","SHB Đà Nẵng","Thanh Hóa","Sài Gòn","Thành phố Hồ Chí Minh","Viettel","Hà Nội (2016)","An Giang","Hà Tĩnh","Phố Hiến","Bà Rịa – Vũng Tàu","XSKT Cần Thơ"]
ROOT=Path("work/a2_clubwiki")
def collect(years=None,clubs=None):
    ROOT.mkdir(parents=True,exist_ok=True)
    for year in (years if years is not None else [2016,2014,2018,2019,2012]):
        for club in (clubs if clubs is not None else CLUBS):
            title="Câu lạc bộ bóng đá "+club
            key=hashlib.sha256((str(year)+"|"+title).encode()).hexdigest()[:20]
            cache=ROOT/(key+".json");meta=cache.with_suffix(".meta")
            if cache.exists() and meta.exists():continue
            r=request(dict(action="query",titles=title,redirects=1,prop="revisions",rvslots="main",
                           rvprop="ids|timestamp|content",rvstart=f"{year}-12-31T16:59:59Z",rvlimit=1))
            atomic(cache,r.content);atomic(meta,json.dumps({"requested":title,"cutoff_year":year,"retrieved_at":datetime.now(timezone.utc).isoformat()},ensure_ascii=False).encode())
            print(year,title,flush=True)

def roster_rows(page,text):
    found=[]
    for section in re.finditer(r"(?m)^(={2,5})\s*([^=\n]+?)\s*\1\s*$",text):
        heading=section[2]
        if not re.search(r"(?i)đội hình|danh sách cầu thủ|cầu thủ hiện tại",heading):continue
        nxt=re.search(r"(?m)^={2,5}[^=\n].*?={2,5}\s*$",text[section.end():])
        end=section.end()+(nxt.start() if nxt else len(text)-section.end())
        sub=text[section.start():end]
        first=re.search(r'(?i)\{\{\s*fs player\b',sub)
        if not first:continue
        lead=sub[:first.start()]
        m=re.search(r'(?i)(?:Giải bóng đá\s+(?:Vô địch|Hạng Nhất)\s+Quốc gia(?: Việt Nam)?|Hạng Nhất|V[.\s-]*League(?:\s*[12])?|mùa giải)\s*[-–:]?\s*(?:năm\s+)?(20\d{2}(?:[–/-]\d{2,4})?)',lead.split("<ref")[0])
        if not m:continue
        season=m[1].replace("/","–").replace("-","–")
        if int(season[:4])<2012 or int(season[:4])>2025:continue
        league="VL2" if re.search(r"(?i)hạng nhất|league\s*2",m[0]) else ("CLB" if m[0].lower().startswith("mùa giải") else "VL1")
        cursors={}
        for tpl in mw.parse(sub).filter_templates():
            if str(tpl.name).strip().lower()!="fs player":continue
            rep=str(tpl);offset=sub.find(rep,cursors.get(rep,0));cursors[rep]=offset+len(rep)
            player=item(param(tpl,"name"));pos=position(param(tpl,"pos"))
            if not player or pos not in {"GK","DF","MF","FW"} or offset<0:continue
            start=section.start()+offset
            found.append(dict(kind="roster",player=player,club={"kind":"link","key":page["title"],"name":page["title"]},
                              season=season,league=league,start=start,end=start+len(rep),
                              context=[section.start(),section.start()+first.start()],pos=pos,shirt=param(tpl,"no")))
    return found
if __name__=="__main__":collect()
