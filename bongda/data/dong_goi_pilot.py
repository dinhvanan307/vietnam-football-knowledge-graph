"""Hợp nhất các lô báo và Wikipedia, cố định văn bản và đóng gói để bàn giao B."""
import argparse
import csv
import json
import os
import re
from pathlib import Path
from lxml import html
from trafilatura import extract
import mwparserfromhell as mw
from bongda.core.ban_giao import pack, sha
from bongda.collect.thu_wiki import records

FIELDS = "source source_kind canonical_url title published_at retrieved_at story_group pageid revid revision_at raw_file text_file".split()

def clean_news(raw, initial):
    # Bài cũ của Thanh Niên có nội dung trong div thay vì p.
    if len(initial) >= 600: return initial
    root = html.fromstring(raw)
    boxes = root.xpath('//*[@data-role="content"]')
    if not boxes: return initial
    body = extract(html.tostring(boxes[0], encoding="unicode"), include_tables=False,
                   include_comments=False) or ""
    return initial + "\n\n" + body if len(body) > len(initial) else initial

def wiki_text(wikitext):
    # Loại chú thích, bảng, danh mục và phần tài liệu tham khảo khỏi văn xuôi.
    wikitext=re.split(r"(?im)^==\s*(?:Tham khảo|Chú thích|Liên kết ngoài|Xem thêm|Thống kê sự nghiệp)\s*==",wikitext)[0]
    wikitext=re.sub(r"(?ms)^\{\|.*?^\|\}", "", wikitext)
    code=mw.parse(wikitext)
    for tag in list(code.filter_tags()):
        if str(tag.tag).strip().lower() in {"ref","gallery","table"}:
            try: code.remove(tag)
            except ValueError: pass
    text=code.strip_code(normalize=True,collapse=True)
    lines=[" ".join(line.split()) for line in text.splitlines()]
    return "\n".join(line for line in lines if line and not line.startswith(("Thể loại:", "Tập tin:", "Tệp:", "|")))

def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("dest", type=Path)
    p.add_argument("--wiki", required=True, type=Path)
    p.add_argument("--press", nargs="+", required=True, type=Path)
    opt=p.parse_args()
    intake=opt.dest.with_name(opt.dest.name+"-intake")
    if opt.dest.exists() or intake.exists():p.error("Dùng tên mới cho mỗi snapshot.")
    intake.mkdir(parents=True); texts=intake/"text";texts.mkdir()
    rows=[]; dropped=[];urls=set();hashes=set()
    def add(row,raw,txt):
        clean=" ".join(txt.split())
        key=sha(clean.encode())
        if len(clean)<300 or row["canonical_url"] in urls or key in hashes:
            dropped.append([row["canonical_url"],"short_or_duplicate"]);return
        urls.add(row["canonical_url"]);hashes.add(key)
        path=texts/(key+".txt");path.write_text(txt.strip(),encoding="utf-8")
        rows.append({**row,"text_file":str(path.relative_to(intake)),"raw_file":os.path.relpath(raw.resolve(),intake.resolve())})
    for folder in opt.press:
        with (folder/"intake.tsv").open(encoding="utf-8") as f:
            for row in csv.DictReader(f,delimiter="\t"):
                if re.search(r"\bu[. -]?(?:17|19|21)\b|\bfutsal\b|\bbóng đá nữ\b|^highlight\b|công nghệ VAR ở Indonesia", row["title"], re.I):
                    dropped.append([row["canonical_url"],"not_in_pilot_scope"]);continue
                raw=folder/row["raw_file"]
                txt=clean_news(raw.read_bytes(),(folder/row["text_file"]).read_text())
                add(row,raw,txt)
    seen=set()
    for page,raw,when in records(opt.wiki):
        if page["pageid"] in seen:continue
        seen.add(page["pageid"])
        rev=page["revisions"][0];txt=wiki_text(rev["slots"]["main"]["content"])
        add(dict(source="Wikipedia tiếng Việt", source_kind="wiki",
                 canonical_url=f"https://vi.wikipedia.org/w/index.php?oldid={rev['revid']}",
                 published_at="",retrieved_at=when,title=page["title"],story_group=f"wiki-profile-{page['pageid']}",
                 pageid=str(page["pageid"]),revid=str(rev["revid"]),revision_at=rev["timestamp"]),raw,txt)
    tsv=intake/"intake.tsv"
    with tsv.open('w',encoding='utf-8',newline='') as f:
        w=csv.DictWriter(f,fieldnames=FIELDS,delimiter="\t");w.writeheader();w.writerows(rows)
    (intake/"excluded.json").write_text(json.dumps(dropped,ensure_ascii=False,indent=2))
    pack(tsv,opt.dest,False)
if __name__=="__main__":main()
