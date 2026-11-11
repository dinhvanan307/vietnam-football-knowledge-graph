"""Archive public VnExpress V.League match sheets and domestic transfer tables."""
import argparse,hashlib,json,re,time,unicodedata
from pathlib import Path
from urllib.parse import urlsplit
from urllib.robotparser import RobotFileParser
from datetime import datetime,timezone
import requests

FRONT="https://vnexpress.net/the-thao/du-lieu-bong-da/"
API="https://gw.vnexpress.net/football/"
def slug(name):
    text=unicodedata.normalize("NFD",name.lower().replace("đ","d"))
    return re.sub(r"[^\w-]","", "".join(c for c in text if not unicodedata.combining(c)).replace(" ","-"))
def collect(root):
    root.mkdir(parents=True,exist_ok=True)
    (root/"data").mkdir(exist_ok=True)
    session=requests.Session();agent="FootballGraphCoursework/0.3";session.headers.update({"User-Agent":agent,"Referer":"https://vnexpress.net/"})
    policies={}
    for host in ["vnexpress.net","gw.vnexpress.net"]:
        r=session.get("https://"+host+"/robots.txt",timeout=15)
        rule=RobotFileParser();rule.parse(r.text.splitlines() if r.status_code==200 else [])
        if r.status_code not in (200,404):r.raise_for_status()
        policies[host]=rule
    def get(url):
        if not policies[urlsplit(url).hostname].can_fetch(agent,url):raise ValueError("robots.txt: "+url)
        r=session.get(url,timeout=(6,20));r.raise_for_status();return r
    def save(key,page,endpoint):
        meta=root/(key+".json")
        if meta.exists():return json.loads((root/"data"/json.loads(meta.read_text())["json_sha"]).read_bytes())
        for tries in range(3):
            try:
                view=get(page);time.sleep(.45);r=get(endpoint);data=r.json()
                if data["code"]!=200 or len(view.content)<8000 or "/the-thao/du-lieu-bong-da/" not in view.url:return {}
                a,b=[hashlib.sha256(x).hexdigest() for x in (view.content,r.content)]
                for sig,body in [(a,view.content),(b,r.content)]: (root/"data"/sig).write_bytes(body)
                info=dict(page=page,endpoint=endpoint,page_sha=a,json_sha=b,retrieved_at=datetime.now(timezone.utc).isoformat())
                meta.write_text(json.dumps(info,ensure_ascii=False));time.sleep(.6);return data
            except requests.RequestException as exc:
                if tries==2:print(key,str(exc)[:90],flush=True);return {}
                time.sleep(2)
    page=FRONT+"giai-dau/vleague"
    teams=save("clubs",page,API+"team/league?league_id=340")["data"]["340"]["data"]
    ids={}
    for t in teams:ids[t['team_id']]=t['name'].strip()
    matches=save("fixtures",page,API+"fixture?league_id=340")["data"]["340"]["data"]
    # Other domestic professional clubs explicitly named as endpoints of moves
    # in the first-division clubs' transfer tables. Foreign endpoints are excluded.
    domestic_peers={9166,13270,3676,3679,3677,9165,21052,9169,16401,9162,9164,9163,11354,9159,9168,25022,21051}
    for index in range(2):
        peers={}
        for i,name in sorted(ids.items()):
            data=save("transfer_"+str(i),FRONT+f"doi-bong/{slug(name)}-{i}/chuyen-nhuong",API+f"team/transfer?team_id={i}")
            for move in data.get("data",{}).get(str(i),{}).get("data",[]):
                for role in ("team_out","team_in"):
                    team=move.get(role) or {}
                    if team.get("team_id") in domestic_peers and team.get("team_name"):
                        peers[team["team_id"]]=team["team_name"].strip()
        ids.update(peers)
    for m in matches:
        if m["status_short"] not in ("FT","AET","PEN") or m["league_id"]!=340:continue
        i=m["fixture_id"];link=FRONT+f"tran-dau/{i}/{slug(m['home_team']['team_name'])}-{slug(m['away_team']['team_name'])}"
        save("events_"+str(i),link,API+f"fixture/event?fixture_id={i}")
        save("squad_"+str(i),link,API+f"fixture/stats?fixture_id={i}")
    print("Archived",len(list(root.glob("*.json"))),"pages and feeds",flush=True)
if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__);p.add_argument("root",type=Path);collect(p.parse_args().root)
