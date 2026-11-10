"""Chuẩn bị phiếu đối chiếu từ snapshot khóa. Không sử dụng luật đã sinh cạnh để gán nhãn."""
import csv, json, hashlib, re, unicodedata
from collections import defaultdict, Counter
from lxml import html
from mwparserfromhell import parse

from bongda.paths import WORK, evaluation_dir

OUT = evaluation_dir("a2")
ROOT = WORK / "a2_final"
CONTROL_SEED=2026110802
def tsv(p,sep="\t"):
    with p.open(encoding="utf-8",newline="") as f:return list(csv.DictReader(f,delimiter=sep))
def lines(p):return [json.loads(s) for s in p.read_text().splitlines() if s]
def digest(b):return hashlib.sha256(b).hexdigest()
def put_tsv(p,rows):
    with p.open("w",encoding="utf-8",newline="") as fp:
        w=csv.DictWriter(fp,fieldnames=list(rows[0]),delimiter="\t");w.writeheader();w.writerows(rows)
def flat(x):return re.sub(r"\s+","",unicodedata.normalize("NFC",x))
def select():
    import random
    sample=tsv(ROOT/"mau_ra_soat.tsv")
    facts=tsv(ROOT/"facts.csv",",");byid={f["fact_id"]:f for f in facts}
    control=random.Random(CONTROL_SEED).sample(sorted(byid),100)
    return sample,facts,control
def raw_text(a):
    raw=(ROOT/"raw"/a["raw_sha256"]).read_bytes()
    assert digest(raw)==a["raw_sha256"]
    if a["source_kind"]=="wiki":
        pages=json.loads(raw)["query"]["pages"]
        r=next(r for p in pages if str(p["pageid"])==a["pageid"] for r in p["revisions"] if str(r["revid"])==a["revid"])
        return unicodedata.normalize("NFC",r["slots"]["main"]["content"])
    return html.fromstring(raw.decode("utf-8")).text_content()
def main():
    OUT.mkdir(parents=True, exist_ok=True)
    sample,facts,control=select();byid={f["fact_id"]:f for f in facts}
    entities={x["entity_id"]:x["canonical_name"] for x in tsv(ROOT/"entities.csv",",")}
    arts={a["article_id"]:a for a in lines(ROOT/"articles.jsonl")}
    evidence=defaultdict(list)
    for e in lines(ROOT/"evidence.jsonl"):evidence[e["fact_id"]].append(e)
    inputs=[(f"S{i:02}",x["fact_id"]) for i,x in enumerate(sample,1)]+[(f"C{i:03}",k) for i,k in enumerate(control,1)]
    packet=[];cache={}
    for no,k in inputs:
        f=byid[k];pieces=[]
        for e in sorted(evidence[k],key=lambda x:(x["evidence_id"]!=f["evidence_id"],x["evidence_id"])):
            a=arts[e["article_id"]];text=a["clean_text"];q=e["quote"]
            assert text[e["start"]:e["end"]]==q
            if a["article_id"] not in cache:cache[a["article_id"]]=raw_text(a)
            raw=cache[a["article_id"]]
            c=text[e["context_start"]:e["context_end"]] if "context_start" in e else ""
            if a["source_kind"]=="press":
                supported=flat(q) in flat(raw)
            else:
                supported=(raw[e["start"]:e["end"]]==q and (not c or raw[e["context_start"]:e["context_end"]]==c)) if a["story_group"].startswith("season:") else flat(q) in flat(parse(raw).strip_code())
            pieces.append(dict(article_id=a["article_id"],url=a["canonical_url"],title=a["title"],published_at=a["published_at"],context=c,quote=q,raw_check=supported,start=e["start"],end=e["end"]))
        packet.append(dict(no=no,**{x:f[x] for x in ("fact_id","src_id","dst_id","relation_type","method","period")},src=entities[f["src_id"]],dst=entities[f["dst_id"]],support=pieces))
    (OUT/"hoso_doi_chieu.jsonl").write_text("".join(json.dumps(r,ensure_ascii=False)+"\n" for r in packet))
    print(len(sample),len(control),sum(not e["raw_check"] for r in packet for e in r["support"]),"raw misses",len(set(x["fact_id"] for x in sample) & set(control)),"overlap")
if __name__=="__main__":main()
