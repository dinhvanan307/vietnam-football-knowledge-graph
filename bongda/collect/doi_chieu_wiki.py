"""Ánh xạ bản mẫu CLB và trang chuyển hướng vào pageid chung, lưu đáp ứng API."""
import json,re,hashlib
from pathlib import Path
from datetime import datetime,timezone
from bongda.collect.thu_mua_giai import request,atomic

CACHE=Path("work/a2_identity")
def key(s):return " ".join(s.replace("_"," ").split()).casefold()
def batch(titles,templates=False):
    collected={}
    for i in range(0,len(titles),45):
        names=titles[i:i+45]
        loc=CACHE/(("templates-" if templates else "ids-")+hashlib.sha256("|".join(names).encode()).hexdigest()[:20]+".json")
        if not loc.exists():
            kwargs=dict(action="query",titles="|".join(names),redirects=1)
            if templates:kwargs.update(prop="revisions",rvprop="content|ids|timestamp",rvslots="main")
            else:kwargs.update(prop="pageprops",ppprop="disambiguation|wikibase_item")
            raw=request(kwargs);atomic(loc,raw.content)
        q=json.loads(loc.read_bytes())["query"]
        pages={key(p["title"]):p for p in q["pages"]}
        mapping={key(d["from"]):key(d["to"]) for v in ("normalized","redirects") for d in q.get(v,[])}
        for n in names:
            k=key(n);visited=set()
            while k in mapping and k not in visited:
                visited.add(k);k=mapping[k]
            p=pages.get(k,{})
            if templates:
                raw=p.get("revisions",[{}])[0].get("slots",{}).get("main",{}).get("content","").split("<noinclude>")[0]
                match=re.search(r"\[\[([^|\]#]+)",raw)
                collected[n]=match[1].strip() if match else ""
            else:
                collected[n]={"id":p.get("pageid"),"title":p.get("title",n),"dab":"disambiguation" in p.get("pageprops",{}),"qid":p.get("pageprops",{}).get("wikibase_item")}
    return collected

def main():
    templates=set();names=set()
    for f in Path("work/a2_records").glob("*.json"):
        for r in json.loads(f.read_bytes())["rows"]:
            if r["kind"] in {"roster","staff"}:vs=[r["club"],r["player"]]
            else:vs=[r["team1"],r["team2"],*[e["player"] for e in r["events"]]]
            if r.get("venue"):vs.append(r["venue"])
            for v in vs:
                if v["kind"]=="template":templates.add("Bản mẫu:"+v["key"])
                else:names.add(v["key"])
    templates=sorted(templates);tpath=CACHE/"template_map.json";previous=json.loads(tpath.read_bytes()) if tpath.exists() else {}
    previous.update(batch(sorted(set(templates)-set(previous)),True))
    atomic(tpath,json.dumps(previous,ensure_ascii=False).encode())
    names.update(filter(None,previous.values()))
    names.update(["Câu lạc bộ bóng đá "+s for s in ["Công an Hà Nội","Hà Nội","Hải Phòng","Hoàng Anh Gia Lai","Becamex Bình Dương","Hồng Lĩnh Hà Tĩnh","Nam Định","Thể Công – Viettel","Sông Lam Nghệ An","Thành phố Hồ Chí Minh","Quảng Nam","Thanh Hóa","Bình Định","SHB Đà Nẵng","Phố Hiến"]])
    names.update(["Nguyễn Quang Hải (cầu thủ bóng đá, sinh 1997)","Nguyễn Quang Hải (cầu thủ bóng đá sinh năm 1997)","Nguyễn Văn Quyết","Phạm Tuấn Hải","Adriano Schmidt","Bùi Tiến Dụng","Đặng Tuấn Hưng","Kyle Colonna"])
    path=CACHE/"person_club_map.json";existing=json.loads(path.read_bytes()) if path.exists() else {}
    # Mỗi chunk được lưu riêng để tiếp tục khi mạng gián đoạn.
    existing.update(batch(sorted(x for x in names if x and x not in existing and len(x)<130 and "|" not in x)))
    atomic(path,json.dumps(existing,ensure_ascii=False).encode())
    print("titles",len(existing),"templates",len(previous),flush=True)
if __name__=="__main__":main()
