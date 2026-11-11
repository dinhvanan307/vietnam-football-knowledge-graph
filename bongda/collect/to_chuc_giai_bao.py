"""Archive a dated editorial article explicitly naming the organizer of three professional competitions."""
import argparse,json,hashlib
from pathlib import Path
from datetime import datetime,timezone
from bongda.collect.danh_sach_tre_bao import Client
URL="https://vnexpress.net/vpf-dong-y-voi-de-xuat-cua-hagl-4564430.html"
if __name__=="__main__":
 p=argparse.ArgumentParser();p.add_argument("out",type=Path);a=p.parse_args();a.out.mkdir(exist_ok=True,parents=True)
 if (a.out/"source.json").exists():raise FileExistsError("Use the archived source or a new directory")
 raw=Client().read(URL).content
 sig=hashlib.sha256(raw).hexdigest();(a.out/sig).write_bytes(raw)
 (a.out/"source.json").write_text(json.dumps(dict(url=URL,sha=sig,retrieved=datetime.now(timezone.utc).isoformat())))

