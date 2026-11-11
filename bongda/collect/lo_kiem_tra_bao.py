"""Lock a new, deterministic batch from never-downloaded SGGP articles; do not add it to the training graph."""
import argparse,gzip,hashlib,json,random,sqlite3
from pathlib import Path
from bongda.collect.danh_sach_tre_bao import Client
from bongda.core.ban_giao import jlines
def run(root,snapshot,out,exclude=None,seed=6111147):
    out.mkdir(exist_ok=True,parents=True);f=out/"locked.json"
    db=sqlite3.connect(f"file:{root/'thu_sggp'/'urls.sqlite'}?mode=ro",uri=True)
    excluded={a["canonical_url"] for a in jlines(snapshot/"articles.jsonl")}
    for directory,dbn,tbl in [("thu_sggp","urls.sqlite","files"),("doi_tre","docs.sqlite","docs"),("thu_bao","archive.sqlite","articles")]:
        cd=sqlite3.connect(f"file:{root/directory/dbn}?mode=ro",uri=True);excluded.update(r[0] for r in cd.execute(f"SELECT url FROM {tbl}"));cd.close()
    if exclude:excluded.update(json.loads(exclude.read_text())["urls"])
    if not f.exists():
        pool=sorted(u[0] for u in db.execute("SELECT url FROM urls") if u[0] not in excluded)
        urls=random.Random(seed).sample(pool,min(36,len(pool)))
        f.write_text(json.dumps(dict(pool=len(pool),seed=seed,urls=urls,rule="First 36 uniform URLs without replacement in unopened SGGP football title index; no replacements. Limit evaluation to club participation in a reported, completed men's professional match."),indent=2))
    reader=Client();docs=[]
    for i,url in enumerate(json.loads(f.read_text())["urls"],1):
        path=out/f"{i:02}.html.gz"
        if not path.exists():
            try:
                with gzip.open(path.with_suffix(".tmp"),"wb") as fp:fp.write(reader.read(url).content)
                path.with_suffix(".tmp").rename(path)
            except Exception as exc:print(i,str(exc)[:120],flush=True);continue
        docs.append([i,url,hashlib.sha256(gzip.decompress(path.read_bytes())).hexdigest()])
    (out/"raw_sha.json").write_text(json.dumps(docs,ensure_ascii=False,indent=2));print(len(docs),"articles",flush=True)
if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);[p.add_argument(k,type=Path) for k in ("root","snapshot","out")];p.add_argument("--exclude",type=Path);p.add_argument("--seed",type=int,default=6111147);a=p.parse_args();run(a.root,a.snapshot,a.out,a.exclude,a.seed)
