"""Archive explicitly listed Bóng đá articles and discover linked team previews."""
import argparse
import csv
import hashlib
import re
import time
from collections import deque
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlsplit
from urllib.robotparser import RobotFileParser

import requests
from lxml import html

HOST = "bongdaplus.vn"
AGENT = "FootballGraphCoursework/0.2"
SEASON_PREVIEW = re.compile(r"/(?:v-league|hang-nhat-quoc-gia)/gioi-thieu-[^/?#]+\.html$")

def allowed(url):
    location = urlsplit(url)
    return location.scheme == "https" and location.netloc == HOST and SEASON_PREVIEW.fullmatch(location.path) and not location.query

def collect(directory, limit):
    urls = deque((directory / "urls.txt").read_text().splitlines())
    cache = directory / "html"
    cache.mkdir(exist_ok=True)
    robots = RobotFileParser()
    session = requests.Session()
    session.headers["User-Agent"] = AGENT
    policy = session.get("https://" + HOST + "/robots.txt", timeout=20)
    policy.raise_for_status()
    robots.parse(policy.text.splitlines())
    seen = set()
    manifest = directory / "sources.tsv"
    fields = ["url", "raw_sha256", "retrieved_at"]
    saved = {}
    if manifest.exists():
        with manifest.open() as f:
            saved = {r["url"]: r for r in csv.DictReader(f, delimiter="\t")}
    with manifest.open("a", newline="") as output:
        writer = csv.DictWriter(output, fieldnames=fields, delimiter="\t")
        if output.tell() == 0:
            writer.writeheader()
        while urls and len(seen) < limit:
            url = urls.popleft()
            if url in seen or not allowed(url) or not robots.can_fetch(AGENT, url):
                continue
            seen.add(url)
            if url in saved:
                raw = (cache / saved[url]["raw_sha256"]).read_bytes()
                if hashlib.sha256(raw).hexdigest() != saved[url]["raw_sha256"]:
                    raise ValueError("Cache changed: " + url)
            else:
                time.sleep(1.5)
                response = session.get(url, timeout=20, allow_redirects=False)
                if response.status_code != 200:
                    print(response.status_code, url, flush=True)
                    continue
                raw = response.content
                digest = hashlib.sha256(raw).hexdigest()
                metadata = dict(url=url, raw_sha256=digest, retrieved_at=datetime.now(timezone.utc).isoformat())
                (cache / digest).write_bytes(raw)
                writer.writerow(metadata)
                output.flush()
            doc = html.fromstring(raw, parser=html.HTMLParser(encoding="UTF-8"))
            for href in doc.xpath("//a[@href]/@href"):
                candidate = urljoin(url, href).split("#")[0]
                if allowed(candidate) and candidate not in seen:
                    urls.append(candidate)
    print(f"{len(seen)} URLs processed", flush=True)

if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("directory", type=Path)
    p.add_argument("--limit", type=int, default=50)
    args = p.parse_args()
    collect(args.directory, args.limit)
