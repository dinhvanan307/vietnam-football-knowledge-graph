"""Kiểm tra pageid của người thực sự dẫn đến hồ sơ bóng đá, cache riêng với nguồn cạnh."""
from pathlib import Path
import json,re
from bongda.collect.thu_mua_giai import request,atomic
def main():
    root=Path("work/a2_identity"); path=root/"football_pages.json"
    out=json.loads(path.read_bytes()) if path.exists() else {}
    mapping=json.loads((root/"person_club_map.json").read_bytes())
    ids=set()
    for f in Path("work/a2_records").glob("*.json"):
        for row in json.loads(f.read_bytes())["rows"]:
            if row.get("role")=="Sponsor":continue
            mentions=[row["player"]] if row["kind"] in {"roster","staff"} else [e["player"] for e in row["events"]]
            for v in mentions:
                rec=mapping.get(v["key"],{})
                if rec.get("id") and not rec["dab"]:ids.add(str(rec["id"]))
    pending=sorted(ids-out.keys())
    for i in range(0,len(pending),35):
        block=pending[i:i+35]
        rsp=request(dict(action="query",pageids="|".join(block),prop="revisions",rvprop="content|ids",rvslots="main"))
        from hashlib import sha256
        atomic(root/("bio-"+sha256("|".join(block).encode()).hexdigest()[:16]+".json"),rsp.content)
        for page in rsp.json()["query"]["pages"]:
            rv=page.get("revisions",[])
            t=rv[0]["slots"]["main"]["content"] if rv else ""
            is_player=bool(re.search(r'(?i)\{\{\s*(?:infobox football biography|thông tin tiểu sử bóng đá|thông tin cầu thủ bóng đá|infobox football biography 2)\b',t)
                           or re.search(r'(?i)\[\[Thể loại:Cầu thủ (?:bóng đá|Câu lạc bộ|V.League)',t))
            out[str(page["pageid"])]=dict(football=is_player,title=page["title"],check_revid=rv[0]["revid"] if rv else None)
        atomic(path,json.dumps(out,ensure_ascii=False).encode())
    print("football_profiles",sum(x["football"] for x in out.values()),"checked",len(out))
if __name__=="__main__":main()
