"""Phiếu rút gọn cho người chấm; hồ sơ JSONL chứa toàn bộ chứng cứ."""
import re,sys,json
from bongda.paths import evaluation_dir
import mwparserfromhell as mw
def display(s):
    return re.sub(r"\s+"," ",s).strip()
def summary(row):
    typ=row["relation_type"];res=[]
    for e in row["support"]:
        q=e["quote"]
        if typ in {"DOI_DAU","NHAN_THE_VANG_KHI_GAP","GHI_BAN_VAO_LUOI","THI_DAU_TAI_SAN"}:
            box=mw.parse(q).filter_templates()[0]
            fields={str(p.name).strip().lower():str(p.value).strip() for p in box.params}
            def g(*ns):return next((fields[n] for n in ns if n in fields),"")
            date=g("date","ngày");a=g("team1","đội 1");b=g("team2","đội 2")
            head=f"{date} {a} / {b} [{g('score','tỉ số','tỷ số')}]"
            if typ=="THI_DAU_TAI_SAN":res.append(head+" @"+g("stadium","sân vận động"));continue
            if typ=="DOI_DAU":res.append(head);continue
            ev=[]
            for n in (1,2):
                es=g("goals"+str(n),"bàn thắng "+str(n),"bàn thắng cho đội "+str(n))
                for s in re.split(r"(?i)<br\s*/?>|\n",es):
                    tag=r"\{\{(?:goal|bàn thắng)\s*\|" if typ=="GHI_BAN_VAO_LUOI" else r"\{\{(?:yel|thẻ vàng)\s*\|"
                    if re.search(tag,s,re.I):
                        ev.append(f"{n}:{s.strip(' *')}")
            res.append(head+" "+", ".join(ev))
        elif typ=="DANG_KY_THI_DAU_CHO":
            res.append(f'{e["title"]} {e["context"].split("<ref")[0]} {q}')
        else:res.append(e["title"]+" "+q)
    return [display(t) for t in res]
if __name__=="__main__":
 packet=[json.loads(s) for s in (evaluation_dir("a2")/'hoso_doi_chieu.jsonl').read_text().splitlines()]
 lo,hi=map(int,sys.argv[1:3]);prefix=sys.argv[3] if len(sys.argv)>3 else 'C'
 for r in packet:
    if r['no'][0]!=prefix or not lo<=int(r['no'][1:])<=hi:continue
    out=summary(r)
    print(r['no'],r['src'],'→',r['dst'],r['relation_type'],r['period'],'|', (' / '.join(out) if r['relation_type']!='THI_DAU_TAI_SAN' else ' ; '.join(out))[:2000])
