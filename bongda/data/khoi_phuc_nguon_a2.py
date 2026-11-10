"""Khôi phục các file nguồn cache từ raw của snapshot đã đóng gói, chạy offline."""
import json,os,shutil
from pathlib import Path
from bongda.core.ban_giao import jlines,sha

def link(src,dst):
    if dst.exists():
        if sha(dst.read_bytes())!=sha(src.read_bytes()):raise ValueError(f"Tệp có nội dung khác {dst}")
        return
    dst.parent.mkdir(parents=True,exist_ok=True)
    try:os.link(src,dst)
    except OSError:shutil.copyfile(src,dst)

def main():
    final=Path("work/a2_final")
    for a in jlines(Path("work/pilot_01/articles.jsonl")):
        n=a["raw_sha256"];link(final/"raw"/n,Path("work/pilot_01/raw")/n)
    for row in jlines(final/"source_index.jsonl"):
        out=Path(row["folder"])/row["name"]
        link(final/"raw"/row["sha256"],out)
        out.with_suffix(".meta").write_text(json.dumps(row["meta"],ensure_ascii=False))
    print("Đã khôi phục nguồn cho pilot và kho Wikipedia.")
if __name__=="__main__":main()
