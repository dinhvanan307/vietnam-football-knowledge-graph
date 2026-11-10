"""Thu bản sửa đổi lịch sử của hồ sơ cầu thủ. Có thể chạy lại để tiếp tục."""
import argparse
import json
import random
import time
from datetime import datetime, timezone
from pathlib import Path
import requests

API = "https://vi.wikipedia.org/w/api.php"
CUTOFF = "2025-12-31T16:59:59Z"
CATEGORY = "Thể loại:Cầu thủ bóng đá nam Việt Nam"

def query(session, **params):
    for attempt in range(4):
        time.sleep(4)
        try:
            response = session.get(API, params={"action": "query", "format": "json", "formatversion": 2,
                                   "maxlag": 5, **params}, timeout=(8, 25))
            if response.status_code == 429:
                delay = response.headers.get("Retry-After", "")
                time.sleep(max(30 * (attempt + 1), int(delay) if delay.isdigit() else 60))
            response.raise_for_status()
            payload = response.json()
            if "error" in payload:
                raise ValueError(str(payload["error"]))
            return response.content, payload
        except (requests.RequestException, ValueError):
            if attempt == 3:
                raise
            time.sleep(2 ** (attempt + 1))

def save(path, data):
    temporary = path.with_suffix(".part")
    temporary.write_bytes(data)
    temporary.replace(path)

def records(out):
    for stamp in sorted(out.glob("*.time")):
        path = stamp.with_suffix(".json")
        for page in json.loads(path.read_bytes())["query"]["pages"]:
            revisions = page.get("revisions", [])
            if not revisions or revisions[0]["timestamp"] > CUTOFF:
                continue
            content = revisions[0]["slots"]["main"]["content"]
            if len(content) >= 500 and not content.lstrip().startswith("#"):
                yield page, path, stamp.read_text()

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("out", type=Path)
    parser.add_argument("--limit", type=int, default=180)
    parser.add_argument("--pin", nargs="*", type=int, default=[])
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    with requests.Session() as session:
        session.headers["User-Agent"] = "FootballGraphCoursework/0.1 (Vietnamese football research; local educational use)"
        for pageid in args.pin:
            path=args.out/f"{pageid}.json"; stamp=path.with_suffix(".time")
            if path.exists() and stamp.exists(): continue
            raw,_=query(session,pageids=pageid,prop="revisions",rvprop="ids|timestamp|content",
                        rvslots="main",rvstart=CUTOFF,rvlimit=1)
            save(path,raw);save(stamp,datetime.now(timezone.utc).isoformat().encode())
        index = args.out / "category.json"
        if not index.exists():
            raw, _ = query(session, list="categorymembers", cmtitle=CATEGORY, cmnamespace=0, cmlimit=500)
            save(index, raw)
        members = json.loads(index.read_bytes())["query"]["categorymembers"]
        members.sort(key=lambda page: page["pageid"])
        random.Random(22).shuffle(members)
        # Một truy vấn lấy tối đa 20 trang. Chỉ dùng phiên bản <= CUTOFF.
        # Chốt raw nguyên văn cả response, evidence tra pageid + revid trong đó.
        for i in range(0, len(members), 20):
            if len({p["pageid"] for p, _, _ in records(args.out)}) >= args.limit:
                break
            path = args.out / f"batch-{i:03}.json"
            retrieved = path.with_suffix(".time")
            if not (path.exists() and retrieved.exists()):
                ids = "|".join(str(p["pageid"]) for p in members[i:i + 20])
                raw, _ = query(session, pageids=ids, prop="revisions", rvprop="ids|timestamp|content", rvslots="main")
                save(path, raw)
                save(retrieved, datetime.now(timezone.utc).isoformat().encode())
        good = len({p["pageid"] for p, _, _ in records(args.out)})
        print(f"historical_profiles={good}, target={args.limit}")

if __name__ == "__main__":
    main()
