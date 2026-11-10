"""Xem nguồn của từng cạnh; full mở toàn bộ chứng cứ thay vì dòng tóm tắt."""
import difflib
import sys
import re
import unicodedata
import json
from bongda.paths import evaluation_dir
import mwparserfromhell as mw

def compact(s):
    return " ".join(s.split())
def norm(s):
    return re.sub(r"\W+", " ", "".join(c for c in unicodedata.normalize("NFD",s.lower().replace("đ","d")) if not unicodedata.combining(c))).strip()
def visible(s):
    return re.sub(r"\[\[([^]|]+)\|([^]]+)\]\]", r"\2", s).replace("[[","").replace("]]","")
def view(r):
    src, dst = r["src"], r["dst"]
    print(r["no"],r["relation_type"],src,"→",dst,r["period"],end=" | ")
    outputs=[]
    for e in r["support"]:
        q=e["quote"]; rel=r["relation_type"]
        if r["method"] in {"wiki_match_event","wiki_match_result","wiki_match_venue"}:
            t=mw.parse(q).filter_templates()[0]; p={str(x.name).strip().casefold():str(x.value).strip() for x in t.params}
            def g(*names):return next((p[n] for n in names if n in p),"")
            h=visible(g("team1","đội 1"));a=visible(g("team2","đội 2"));day=visible(g("ngày","date"))
            head=f"{day} {h}/{a}"
            if rel=="THI_DAU_TAI_SAN":
                outputs.append(head+" @"+visible(g("sân vận động","stadium")));continue
            if rel=="DOI_DAU":
                outputs.append(head+" "+g("tỉ số","tỷ số","score"));continue
            events=[]
            for n in (1,2):
                fragment=g("goals"+str(n),"bàn thắng "+str(n),"bàn thắng cho đội "+str(n),"bàn thắng"+str(n))
                for entry in re.split(r"(?i)<br\s*/?>|\n",fragment):
                    actor=visible(entry.split("{{")[0]); sim=difflib.SequenceMatcher(None,norm(src.split("(")[0]),norm(re.sub(r"\(\d+\)", "",actor))).ratio()
                    events.append((sim, n, compact(entry)))
            best=max([score for score,n,line in events] or [0])
            selectable=[f"{n}:{line}" for score,n,line in events if score>=max(best-0.07,0)]
            outputs.append(head+" "+" / ".join(selectable))
        elif rel=="DANG_KY_THI_DAU_CHO":
            c=e["context"].split("<ref")[0].split("{{Fs start")[0]
            outputs.append(e["title"]+" "+compact(c)[:370]+" "+q)
        else:outputs.append(e["title"]+" "+e["context"]+" "+q)
    print(" ; ".join(dict.fromkeys(compact(x) for x in outputs)))
if __name__=="__main__":
    lo,hi=map(int,sys.argv[1:3])
    rows=[json.loads(l) for l in (evaluation_dir("a3")/"ho_so_nguon.jsonl").read_text().splitlines()]
    for r in rows[lo-1:hi]:
        if sys.argv[3:]==["full"]:print(json.dumps(r,ensure_ascii=False))
        else:view(r)
