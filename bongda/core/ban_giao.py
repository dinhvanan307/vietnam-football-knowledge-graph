"""Bàn giao A: đóng gói bản chụp đã lấy hợp lệ; kiểm tra cấu trúc, không chấm độ đúng."""
import argparse, csv, hashlib, json, re, shutil, sys, tempfile, unicodedata
from collections import Counter
from datetime import date, datetime
from pathlib import Path
from urllib.parse import urlparse

from ontology import ENDS, ENTITY
TYPES = set(ENDS)
def require(ok,msg):
    if not ok: raise ValueError(msg)
def sha(b): return hashlib.sha256(b).hexdigest()
def enc(x): return json.dumps(x, ensure_ascii=False,sort_keys=True)
def table(p,sep=","):
    with p.open(encoding="utf-8-sig",newline="") as f: return list(csv.DictReader(f,delimiter=sep))
def jlines(p):
    # NDJSON uses ASCII LF; U+2028/U+2029 are legal inside a JSON string.
    with p.open(encoding="utf-8") as records:
        return [json.loads(s) for s in records if s.strip()]
def idx(rows,key):
    ret={}
    for r in rows:
        k=r[key];require(k and k not in ret, f"ID rỗng hoặc trùng: {key}={k}");ret[k]=r
    return ret
def iso(s,day=False):
    if day and len(s)==10: date.fromisoformat(s);return
    t=datetime.fromisoformat(s.replace("Z","+00:00"))
    require(t.utcoffset() is not None, "Thiếu múi giờ: "+s)
def tag_url(a,demo):
    u=urlparse(a["canonical_url"]);require(u.scheme=="https" and u.hostname,"URL không hợp lệ")
    require((a["record_kind"]=="fixture" if demo else a["record_kind"]=="real"),"Nhầm dữ liệu thật và dữ liệu giả")
    require((u.hostname.endswith(".invalid") if demo else not u.hostname.endswith(".invalid")),"Tên miền không phù hợp chế độ")
def verify(root,demo,graph=False):
    m=json.loads((root/"manifest.json").read_text(encoding="utf-8"))
    require(m["schema_version"]=="1" and m["record_kind"]==("fixture" if demo else "real"),"Sai schema/chế độ")
    require(sha((root/"articles.jsonl").read_bytes())==m["articles_sha256"],"articles.jsonl đã thay đổi")
    arts=idx(jlines(root/"articles.jsonl"),"article_id")
    require(len(arts)==m["article_count"] and len(arts)>0,"Số văn bản không khớp")
    for a in arts.values():
        tag_url(a,demo);iso(a["retrieved_at"]);require(a["source"] and a["story_group"] and a["title"] and a["clean_text"].strip(),"Thiếu metadata/nội dung")
        if a["published_at"]:iso(a["published_at"],True)
        if a["source_kind"]=="wiki":
            require(a["pageid"].isdigit() and a["revid"].isdigit() and a["revision_at"],"Thiếu thông tin bản Wiki")
            iso(a["revision_at"])
        else:require(a["source_kind"]=="press" and a["published_at"],"Thiếu loại nguồn/ngày báo")
        require(sha(a["clean_text"].encode())==a["clean_sha256"],"Sai hash văn bản")
        require(re.fullmatch(r"[0-9a-f]{64}",a["raw_sha256"]),"Sai dạng hash raw")
        require(sha((root/"raw"/a["raw_sha256"]).read_bytes())==a["raw_sha256"],"Sai hash raw")
    out={"article_versions":len(arts),"unique_urls":len({a["canonical_url"] for a in arts.values()}),"story_groups":len({a["story_group"] for a in arts.values()})}
    if graph:
        nodes=idx(table(root/"entities.csv"),"entity_id"); facts=idx(table(root/"facts.csv"),"fact_id"); ev=idx(jlines(root/"evidence.jsonl"),"evidence_id");seen=set();connected=set()
        require(nodes and facts and ev,"Bộ graph trống")
        if not demo:
            require(not any(k.startswith("demo-") for k in [*nodes,*facts,*ev]) and all(f["method"]!="fixture" for f in facts.values()),"Fixture lẫn vào bộ thật")
        for n in nodes.values():require(n["type"] in ENTITY and n["canonical_name"].strip(),"Node thiếu tên/sai loại")
        for v in ev.values():
            require(v["fact_id"] in facts and v["article_id"] in arts,"Bằng chứng tham chiếu ID lạ")
            t=arts[v["article_id"]]["clean_text"];i,j=v["start"],v["end"]
            require(isinstance(i,int) and isinstance(j,int) and 0<=i<j<=len(t) and t[i:j]==v["quote"],"Vị trí/câu bằng chứng không khớp")
        for k,f in facts.items():
            s,o=f["src_id"],f["dst_id"];t=f["relation_type"]
            require(s in nodes and o in nodes and s!=o and t in TYPES,"Sai đầu cạnh hoặc type")
            domain, target = ENDS[t]
            require(nodes[s]["type"] in domain and nodes[o]["type"] in target, "Sai chiều hoặc loại thực thể: "+k)
            require(f["status"]=="accepted" and f["method"] and f["event_key"].strip(),"facts.csv chỉ chứa fact đủ điều kiện")
            key=(s,t,o,f["event_key"]);require(key not in seen,"Trùng khóa sự kiện");seen.add(key)
            v=ev.get(f["evidence_id"]);require(v and v["fact_id"]==k and v["role"]=="supports","Thiếu bằng chứng xác nhận")
            connected.update((s,o))
        out.update(connected_entities=len(connected),accepted_facts=len(facts),types=dict(Counter(f["relation_type"] for f in facts.values())))
    print(("DEMO / " if demo else "")+"PASS kiểm tra cấu trúc:",enc(out))
def pack(tsv,dest,demo):
    require(not dest.exists(),"Thư mục đích đã tồn tại; hãy dùng tên lô mới")
    rows=table(tsv,"\t");require(rows,"Bảng nguồn trống");dest.parent.mkdir(parents=True,exist_ok=True)
    stage=Path(tempfile.mkdtemp(prefix=".batch-",dir=dest.parent))
    try:
        (stage/"raw").mkdir(); records=[]
        for r in rows:
            a={k:r[k].strip() for k in "source source_kind canonical_url title published_at retrieved_at story_group pageid revid revision_at".split()}
            raw=(tsv.parent/r["raw_file"]).read_bytes()
            clean=unicodedata.normalize("NFC",(tsv.parent/r["text_file"]).read_text(encoding="utf-8")).strip()
            require(raw and clean,"Tệp gốc hoặc bài sạch rỗng")
            a.update(raw_sha256=sha(raw),clean_sha256=sha(clean.encode()),clean_text=clean,record_kind="fixture" if demo else "real")
            key=[a[k] for k in ("canonical_url","revid","raw_sha256","clean_sha256")]
            a["article_id"]="a_"+sha(enc(key).encode())[:24]
            (stage/"raw"/a["raw_sha256"]).write_bytes(raw);records.append(a)
        data=stage/"articles.jsonl";data.write_text("".join(enc(a)+"\n" for a in records),encoding="utf-8")
        manifest={"schema_version":"1","record_kind":"fixture" if demo else "real","article_count":len(records),"articles_sha256":sha(data.read_bytes())}
        (stage/"manifest.json").write_text(enc(manifest)+"\n",encoding="utf-8");verify(stage,demo);stage.rename(dest)
    finally:
        if stage.exists():shutil.rmtree(stage)
def main():
    ap=argparse.ArgumentParser(description=__doc__);sub=ap.add_subparsers(dest="op",required=True)
    q=sub.add_parser("pack");q.add_argument("input",type=Path);q.add_argument("output",type=Path)
    c=sub.add_parser("check");c.add_argument("folder",type=Path);c.add_argument("--graph",action="store_true")
    for x in (q,c): x.add_argument("--demo",action="store_true")
    a=ap.parse_args()
    if a.op=="pack":pack(a.input,a.output,a.demo)
    else: verify(a.folder,a.demo,a.graph)
if __name__=="__main__":
    try:main()
    except (OSError,ValueError,KeyError,TypeError) as e:sys.exit("FAIL: "+str(e))
