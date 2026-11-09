"""Phân tích dòng đăng ký đội hình và mẫu biên bản trận đấu trên Wikipedia tiếng Việt."""
from collections import Counter
from pathlib import Path
import json,re,unicodedata
import mwparserfromhell as mw

def read_pages(root):
    seen=set()
    for f in sorted(root.glob("*.json")):
        if not f.with_suffix(".meta").exists():continue
        p=json.loads(f.read_bytes())["query"]["pages"][0];revs=p.get("revisions",[])
        if not revs:continue
        r=revs[0];identity=(p["pageid"],r["revid"])
        if identity in seen:continue
        seen.add(identity)
        yield p,r,unicodedata.normalize("NFC",r["slots"]["main"]["content"]),f

def param(t,*names):
    for n in names:
        if t.has(n):return str(t.get(n).value).strip()
    folded={n.casefold() for n in names}
    for field in t.params:
        if str(field.name).strip().casefold() in folded:return str(field.value).strip()
    return ""

def item(s):
    s=s.strip().strip("'").strip()
    m=re.fullmatch(r'\[\[([^\]|#]+)(?:\|([^\]]+))?\]\]',s)
    if m:return {"kind":"link","key":m[1].strip(),"name":(m[2] or m[1]).strip()}
    m=re.fullmatch(r'\{\{([^{}|]+)\}\}',s)
    if m:return {"kind":"template","key":m[1].strip(),"name":m[1].strip()}
    if s and len(s)<85 and not re.search(r"[<>{}\[\]|*#/=\n]",s):
        return {"kind":"text","key":s,"name":s}
    return None

def position(s):
    val=s.strip().upper()
    return {"TM":"GK","HV":"DF","TV":"MF","TĐ":"FW","TD":"FW"}.get(val,val)

def roster(t,tex,alltext,offset):
    name=param(t,"name");person=item(name);pos=position(param(t,"pos"))
    if not person or pos not in {"GK","DF","MF","FW"}:return
    for h in reversed(list(re.finditer(r"(?m)^(={2,6})\s*(.+?)\s*\1\s*$",alltext[:offset]))[-2:]):
        val=h[2].strip()
        if val.casefold() in {"đội hình","các đội tham dự","danh sách đăng ký","danh sách cầu thủ"}:continue
        club=item(val)
        if club:
            yield dict(kind="roster",player=person,club=club,start=offset,end=offset+len(tex),context=[h.start(),h.end()],pos=pos,shirt=param(t,"no"))
        break

def date_vi(raw,season):
    import datetime
    s=re.sub(r"<!--.*?-->","",raw).replace("[[","").replace("]]","").strip()
    m=re.search(r"(?i)\{\{(?:start date|ngày bắt đầu)\s*\|\s*(?:df=y\s*\|\s*)?(20\d\d)\s*\|\s*(\d{1,2})\s*\|\s*(\d{1,2})",s)
    if m:y,mo,d=map(int,m.groups())
    else:
        m=re.search(r"(\d{1,2})\s*(?:tháng|/|-)\s*(\d{1,2})\s*(?:năm|/|-)\s*(20\d\d)",s,re.I)
        if not m:return None
        d,mo,y=map(int,m.groups())
    try:result=datetime.date(y,mo,d)
    except ValueError:return None
    return result.isoformat() if 2012<=y<=2025 else None

BOX_NAMES={"football box","footballbox","football box collapsible","footballbox collapsible","hộp thông tin trận đấu bóng đá","hộp thông tin trận đấu bóng đá có thể cuộn lại"}
def extract(p,text):
    # Đối chiếu nguyên văn từng template để giữ offset Unicode đúng bản đã nhận.
    title=p["title"];out=[];cursors={}
    for t in mw.parse(text).filter_templates():
        name=str(t.name).strip().casefold()
        if name not in BOX_NAMES|{"fs player"}:continue
        rep=str(t);idx=text.find(rep,cursors.get(rep,0));cursors[rep]=idx+len(rep)
        if idx<0:raise ValueError("Không tìm được template nguồn")
        if name=="fs player":
            out.extend(roster(t,rep,text,idx));continue
        day=date_vi(param(t,"date","ngày"),title)
        score=param(t,"score","tỷ số","tỉ số")
        teams=[item(param(t,*params)) for params in [("team1","đội 1"),("team2","đội 2")]]
        score_match=re.match(r"^(?:'{2,3})?(\d{1,2})\s*[-–—]\s*(\d{1,2})(?=\s|<|'|$)",score)
        if not day or not score_match or not all(teams):continue
        vals=dict(kind="match",date=day,team1=teams[0],team2=teams[1],score=score_match[0].strip("'"),start=idx,end=idx+len(rep),events=[])
        venue=param(t,"stadium","sân vận động")
        vm=re.match(r"\s*(\[\[(?:Sân vận động|Sân bóng đá)[^]\n]+\]\])",venue,re.I)
        if vm:vals["venue"]=item(vm[1])
        for j in (1,2):
            fragment=param(t,"goals"+str(j),"bàn thắng "+str(j),"bàn thắng"+str(j),"bàn thắng cho đội "+str(j))
            for line in re.split(r"(?i)<br\s*/?>|\n",fragment):
                if re.search(r"(?i)\b(?:hlv|gđkt|giám đốc|huấn luyện viên|trợ l[íý]|trưởng đoàn|bác s[ĩỹ]|quan chức|nhân viên|vật lý trị liệu|lãnh đội|chuyên gia|phiên dịch)\b",line):continue
                # Chỉ nhận một tên cầu thủ rõ ràng đứng trước mẫu sự kiện.
                m=re.fullmatch(r"\s*[*:]?\s*(\[\[[^]\n]+\]\]|[\wÀ-ỹ'’ .-]+?)\s*(?:\(\d{1,3}\)\s*)?((?:\{\{[^{}]+\}\}\s*)+)\s*",line)
                if not m:continue
                actor=item(m[1]);markers=mw.parse(m[2]).filter_templates()
                if not actor:continue
                for marker in markers:
                    k=str(marker.name).strip().lower()
                    k={"bàn thắng":"goal","thẻ vàng":"yel"}.get(k,k)
                    if k not in {"goal","yel"}:continue
                    minute=param(marker,"1")
                    if not re.fullmatch(r"\d{1,3}(?:\+\d{1,2})?",minute):continue
                    # Bỏ cả marker phản lưới và trường hợp không rõ ai được tính bàn.
                    if re.search(r"(?i)\bog\b|own|phản lưới",str(marker).replace(".","")):continue
                    if k=="goal" and any(str(x.value).strip() and not re.fullmatch(r"(?i)\d{1,3}(?:\+\d{1,2})?|pen\.?|phạt đền",str(x.value).strip()) for x in marker.params):continue
                    vals["events"].append(dict(side=j,kind=k,player=actor,minute=minute))
        out.append(vals)
    return out
if __name__=="__main__":
    from doi_hinh_lich_su import roster_rows
    from nhan_su_mua_giai import staff_rows
    root=Path("work/a2_records");root.mkdir(exist_ok=True)
    for folder in ["work/a2_wiki","work/a2_clubwiki"]:
        for p,r,t,f in read_pages(Path(folder)):
            path=root/f"{p['pageid']}-{r['revid']}.json"
            rows=(extract(p,t)+list(staff_rows(t))) if folder.endswith("a2_wiki") else roster_rows(p,t)
            tmp=path.with_suffix(".part")
            tmp.write_text(json.dumps({"title":p["title"],"pageid":p["pageid"],"revid":r["revid"],"raw":f.name,"rows":rows},ensure_ascii=False))
            tmp.replace(path)
            if rows:print(p["title"],dict(Counter(row["kind"] for row in rows)),flush=True)
