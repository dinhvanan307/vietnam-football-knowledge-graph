"""Discover publisher article URLs from Common Crawl's public sorted index.
Only URL metadata is read here. Article evidence is subsequently fetched from the newspaper.
"""
import argparse,gzip,json,re,time
from pathlib import Path
import requests
from bongda.collect.tuong_thuat_bao import ARTICLE,HOST,CATEGORIES,EXCLUDE,SCORE,REPORT,open_db
from urllib.parse import urlsplit
ROOT="https://data.commoncrawl.org/cc-index/collections/"
def discover(root,collections):
    db=open_db(root);sess=requests.Session();sess.headers["User-Agent"]="FootballGraphCoursework/0.3"
    for crawl in collections:
        base=ROOT+crawl+"/indexes/";index=base+"cluster.idx"
        def read(url,lo,hi):
            r=sess.get(url,headers={"Range":f"bytes={lo}-{hi}","Accept-Encoding":"identity"},timeout=(8,32))
            if r.status_code!=206:raise ValueError(f"{r.status_code} on index range {url}")
            return r
        try:
            length=int(read(index,0,99).headers["Content-Range"].split("/")[-1])
            def window(key):
                lo=0;hi=length
                while hi-lo>16000:
                    mid=(lo+hi)//2;seg=read(index,mid,min(length-1,mid+1400)).content
                    sep=seg.find(b"\n")+1
                    if sep==0:raise ValueError("oversized index line")
                    line=seg[sep:].split(b"\t",1)[0]
                    if line < key:lo=mid+sep
                    else:hi=mid+sep
                return lo,hi
            key=b"vn,bongdaplus)/";lo,_=window(key);_,hi=window(b"vn,bongdaplus)0")
            size=400000; groups=set()
            data=b"".join(read(index,k,min(hi+2048,length-1,k+size-1)).content for k in range(max(0,lo-2000),min(hi+2049,length),size))
            lines=data.splitlines()
            prev=None
            for row in lines:
                fields=row.split(b"\t")
                if len(fields)<4:continue
                keyfile=fields[0].split(b" ",1)[0]
                entry=(fields[1].decode(),int(fields[2]),int(fields[3]))
                if keyfile.startswith(key):
                    if prev:groups.add(prev)
                    groups.add(entry)
                prev=entry
            total=0
            for name,offset,size in sorted(groups):
                comp=read(base+name,offset,offset+size-1).content
                for line in gzip.decompress(comp).splitlines():
                    if not line.startswith(key):continue
                    item=json.loads(line.split(b" ",2)[2]);u=urlsplit(item["url"]);m=ARTICLE.fullmatch(u.path)
                    if not m or m[1]=="bong-da-phong-trao" or item.get("status")!="200":continue
                    slug=u.path.rsplit("/",1)[1]
                    rank=0 if SCORE.search(slug) and not EXCLUDE.search(slug) else 1 if REPORT.search(slug) and not EXCLUDE.search(slug) else 5
                    db.execute("INSERT OR IGNORE INTO urls VALUES(?,?,?,?)",(HOST+u.path,m[1],rank,slug[-9:-5]));total+=1
                db.commit();time.sleep(.18)
            print(crawl,"blocks",len(groups),"indexed",total,flush=True)
        except Exception as exc: print(crawl,str(exc)[:180],flush=True)
if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("root",type=Path);p.add_argument("collections",nargs="+");a=p.parse_args();discover(a.root,a.collections)
