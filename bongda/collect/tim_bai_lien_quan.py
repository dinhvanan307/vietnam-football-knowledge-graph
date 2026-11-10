"""Tạo danh sách URL báo từ tài liệu đã tải. Chỉ giữ URL bài bóng đá trong hai miền."""
import argparse
import csv
import json
import random
import re
from pathlib import Path
from urllib.parse import urljoin, urlparse
from lxml import html

TOPIC = re.compile(r"v-league|doi-tuyen-viet-nam|tuyen-viet-nam|u-?23-viet-nam|clb-(?:ha-noi|nam-dinh|hagl|thanh-hoa|binh-dinh|binh-duong|ha-tinh|hai-phong|khanh-hoa)|cong-an-ha-noi|song-lam-nghe-an|slna|the-cong-viettel|giai-hang-nhat")
SOURCES = {"tuoitre.vn":"Tuổi Trẻ","thanhnien.vn":"Thanh Niên"}
def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument("output", type=Path)
    ap.add_argument("--wiki", required=True, type=Path)
    ap.add_argument("--press", nargs="+", required=True, type=Path)
    ap.add_argument("--exclude", nargs="*", default=[], type=Path)
    ap.add_argument("--limit", type=int, default=100)
    a=ap.parse_args()
    links=set()
    seen=set()
    for path in a.exclude:
        with path.open(encoding="utf-8") as f:
            seen.update(row["url"] for row in csv.DictReader(f,delimiter="\t"))
    for path in a.wiki.glob("*.json"):
        if path.name=="category.json": continue
        for page in json.loads(path.read_bytes())["query"]["pages"]:
            for rev in page.get("revisions", []):
                links.update(re.findall(r'https?://(?:www\.)?(?:tuoitre\.vn|thanhnien\.vn)/[^<\s|}\]"\x27]+', rev["slots"]["main"]["content"]))
    for folder in a.press:
        for row in csv.DictReader((folder/"intake.tsv").open(encoding="utf-8"), delimiter="\t"):
            url=row["canonical_url"]; seen.add(url)
            links.update(urljoin(url, s) for s in html.parse(str(folder/row["raw_file"])).xpath("//a/@href"))
    candidates=[]
    for url in sorted(links - seen):
        u=urlparse(url)
        if u.scheme!="https" or u.hostname not in SOURCES or u.query or u.fragment: continue
        if not u.path.endswith((".htm",".html")) or not TOPIC.search(u.path): continue
        if u.path.count("/")!=1 or not re.search(r"\d{7,}\.(?:htm|html)$",u.path):continue
        if re.search(r"18526[01]|-2026[01]|-10026|-tags|-tag|futsal|bong-da-nu|u-?17-|u-?19-",u.path): continue
        candidates.append(url)
    random.Random(22).shuffle(candidates)
    with a.output.open('x',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=["url","source"],delimiter="\t");w.writeheader()
        for url in candidates[:a.limit]:
            w.writerow({"url":url,"source":SOURCES[urlparse(url).hostname]})
    print(f"selected={min(len(candidates),a.limit)}, available={len(candidates)}")
if __name__=="__main__": main()
