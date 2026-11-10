"""Xác minh đối tượng trong cột tài trợ là doanh nghiệp, lưu mã phiên bản kiểm tra."""
import json,re,hashlib
from pathlib import Path
from bongda.collect.thu_mua_giai import request,atomic
def main():
    directory=Path("work/a2_identity");lookup=json.loads((directory/"person_club_map.json").read_bytes())
    out=directory/"company_pages.json";known=json.loads(out.read_bytes()) if out.exists() else {}
    ids=set()
    for f in Path("work/a2_records").glob("*.json"):
        for r in json.loads(f.read_bytes())["rows"]:
            if r.get("role")!="Sponsor":continue
            record=lookup.get(r["player"]["key"],{})
            if record.get("id") and not record.get("dab"):ids.add(str(record["id"]))
    names=sorted(ids-known.keys())
    for i in range(0,len(names),35):
        selected="|".join(names[i:i+35]);rsp=request(dict(action="query",pageids=selected,prop="revisions",rvprop="ids|content",rvslots="main"))
        atomic(directory/("org-"+hashlib.sha256(selected.encode()).hexdigest()[:12]+".json"),rsp.content)
        for p in rsp.json()["query"]["pages"]:
            r=p.get("revisions",[]);text=r[0]["slots"]["main"]["content"] if r else ""
            ok=bool(re.search(r"(?i)\{\{\s*(?:infobox company|thông tin công ty|thông tin doanh nghiệp|hộp thông tin công ty|infobox bank)\b",text))
            known[str(p["pageid"])]=dict(company=ok,title=p["title"],revid=r[0]["revid"] if r else None)
        atomic(out,json.dumps(known,ensure_ascii=False).encode())
    if not out.exists():atomic(out,b"{}")
    print("verified_company_pages",sum(v["company"] for v in known.values()))
if __name__=="__main__":main()
