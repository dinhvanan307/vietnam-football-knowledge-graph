"""Các bảng có tiêu đề cột tường minh về đội bóng, HLV trưởng và đội trưởng."""
import re
from doc_bien_ban import item

def cells(block):
    vals=[]
    for line in block.splitlines():
        s=line.strip()
        if s.startswith("|") and not s.startswith(("|-","|}")):
            vals.extend(x.strip() for x in s[1:].split("||"))
        elif s and vals:vals[-1]+=" "+s
    return vals
def entry(s):
    s=re.sub(r"(?is)<ref\b.*?(?:/>|</ref>)","",s)
    s=re.sub(r"(?i)\{\{(?:flagicon|flag|cờ|quốc kỳ)\|[^{}]*\}\}","",s)
    s=re.sub(r"^\s*(?:align|style|bgcolor)\s*=[^|]+\|","",s)
    return item(s.strip().strip("'").strip())
def staff_rows(text):
    for table in re.finditer(r"(?ms)^\{\|[^\n]*wikitable.*?^\|\}",text):
        body=table[0];parts=list(re.finditer(r"(?ms)^\|-[^\n]*\n(.*?)(?=^\|-|^\|\})",body))
        for ix,part in enumerate(parts):
            h=part[1].strip()
            if not h.startswith("!"):continue
            headers=[x.strip().casefold() for line in h.splitlines() if line.strip().startswith("!") for x in line.strip()[1:].split("!!")]
            teams=[k for k,title in enumerate(headers) if title in ("đội","đội bóng","câu lạc bộ","clb")]
            if len(teams)!=1:continue
            roles={k:role for k,title in enumerate(headers) for role,labels in
                   [("Coach",{"huấn luyện viên","huấn luyện viên trưởng","hlv trưởng"}),("Captain",{"đội trưởng"}),
                    ("Sponsor",{"nhà tài trợ chính","nhà tài trợ trang phục thi đấu","nhà tài trợ áo đấu","nhà tài trợ chính trên áo đấu"})] if title in labels}
            if not roles:continue
            for row in parts[ix+1:]:
                if re.search(r"(?i)rowspan|colspan",row[1]):continue
                values=cells(row[1])
                if len(values)!=len(headers):continue
                club=entry(values[teams[0]])
                if not club:continue
                for col,role in roles.items():
                    actor=entry(values[col])
                    if actor:
                        yield dict(kind="staff",role=role,player=actor,club=club,start=table.start()+row.start(1),
                                   end=table.start()+row.end(1),context=[table.start()+part.start(1),table.start()+part.end(1)])
            break
