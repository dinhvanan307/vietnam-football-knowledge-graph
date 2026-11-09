"""Lấy các bản sửa đổi Wikipedia tiếng Việt tính đến cuối 2025. Cache raw để chạy lại."""
import json, re, time
from pathlib import Path
from datetime import datetime, timezone
import requests
from requests.utils import unquote

BASE="https://vi.wikipedia.org/w/api.php"
CUT="2025-12-31T16:59:59Z"
ROOT=Path("work/a2_wiki")
ROOT.mkdir(parents=True,exist_ok=True)
session=requests.Session()
session.headers["User-Agent"]="FootballGraphCoursework/0.2 (Vietnamese football research, local student project)"
def request(params):
    for attempt in range(6):
        time.sleep(2.5)
        r=session.get(BASE,params={**params,"format":"json","formatversion":2,"maxlag":5},timeout=(10,55))
        if r.status_code==429 or r.status_code>=500:
            delay=r.headers.get("Retry-After","")
            time.sleep(max(30, int(delay) if delay.isdigit() else 40*(attempt+1)))
            continue
        r.raise_for_status()
        data=r.json()
        if data.get("error",{}).get("code")=="maxlag":
            time.sleep(20);continue
        if "error" in data:raise ValueError(data["error"])
        return r
    raise RuntimeError("Wikipedia đang giới hạn truy cập.")
def atomic(p,b):
    tmp=p.with_suffix(".part");tmp.write_bytes(b);tmp.replace(p)
def fetch(title):
    import hashlib
    k=hashlib.sha256(title.encode()).hexdigest()[:16]
    loc=ROOT/(k+".json");meta=ROOT/(k+".meta")
    if not (loc.exists() and meta.exists()):
        r=request(dict(action="query",titles=title,redirects=1,prop="revisions",rvprop="ids|timestamp|content",
                       rvslots="main",rvstart=CUT,rvlimit=1))
        atomic(loc,r.content);atomic(meta,json.dumps({"requested":title,"retrieved_at":datetime.now(timezone.utc).isoformat()},ensure_ascii=False).encode())
    p=json.loads(loc.read_bytes())["query"]["pages"][0];rv=p.get("revisions",[])
    return p,rv[0]["slots"]["main"]["content"] if rv else ""
def main():
    seasons=[str(y) for y in range(2012,2024)]+["2023–24","2024–25","2025–26"]
    init=[f"Giải bóng đá {level} Quốc gia {s}" for s in seasons for level in ["Vô địch","Hạng Nhất"]]
    # Kết quả của từng mùa dẫn sang trang đội hình và trang trận đấu chi tiết.
    seen=set();queue=list(init)
    while queue:
        title=queue.pop(0)
        if title in seen:continue
        seen.add(title)
        p,t=fetch(title)
        if not t:continue
        print(p["pageid"],p["title"],len(t),flush=True)
        for m in re.findall(r"(?i)\{\{(?:main|bài chính|chính|xem thêm)\s*\|([^{}]+)\}\}",t):
            for link in m.split("|"):
                if re.search("danh sách cầu thủ tham dự|kết quả chi tiết",link,re.I) and re.search("quốc gia",link,re.I):
                    queue.append(link.strip())
    # Một số trang mùa giải cũ không liên kết đến bài danh sách.
    for season in seasons:
        for level in ("Vô địch","Hạng Nhất"):
            for title in [f"Danh sách cầu thủ tham dự Giải bóng đá {level} Quốc gia {season}",
                          f"Giải bóng đá {level} Quốc gia {season} (kết quả chi tiết)"]:
                if title not in seen:
                    p,t=fetch(title);seen.add(title)
                    if t:print(p["pageid"],p["title"],len(t),flush=True)
if __name__=="__main__": main()
