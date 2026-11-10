from pathlib import Path
import csv,hashlib,json,re,unicodedata
from urllib.parse import urlsplit,unquote
from datetime import datetime,timezone
import argparse
from bongda.a7.paths import DATA as P
cli = argparse.ArgumentParser(description='Lọc trùng URL và văn bản rồi khóa lô báo')
cli.add_argument('lot_dir', type=Path)
cli.add_argument('prefix', help='Tiền tố mã bài, ví dụ N')
args = cli.parse_args()
B = args.lot_dir.resolve()
def rows(path):return list(csv.DictReader(path.open(encoding='utf-8-sig'),delimiter='\t'))
def url(s):
 u=urlsplit(s);return u.netloc.removeprefix('www.')+unquote(u.path).rstrip('/')
def sha(b):return hashlib.sha256(b).hexdigest()
def sh(s):
 w=re.findall(r'\w+',unicodedata.normalize('NFC',s.casefold()))
 return set(zip(w,w[1:],w[2:],w[3:],w[4:]))
archive={}; fixed_urls=set()
def record(u,s):
 if not u or 'wikipedia.org' in u:return
 fixed_urls.add(url(u))
 if s:archive.setdefault((url(u),sha(s.encode())),sh(s))
for f in [P/'Sua_loi_can_bo_A5/snapshot/articles.jsonl',P/'Nang_cap_NLP/dev.jsonl',P/'Nang_cap_NLP/test_final.jsonl',P/'Nang_cap_NLP/test.jsonl',P/'Kiem_thu_trieu_tap/lot_moi.jsonl']:
 for l in f.read_text().splitlines():
  a=json.loads(l);record(a['canonical_url'],a['clean_text'])
for f in sorted(P.rglob('intake.tsv')):
 if B in f.parents:continue
 for r in rows(f):
  u=r.get('canonical_url');t=r.get('text_file')
  if u and 'wikipedia.org' not in u:
   path=f.parent/(t or '');record(u,path.read_text() if path.is_file() else '')
for f in sorted(P.rglob('seeds*.tsv')):
 if B in f.parents:continue
 for r in rows(f):record(r.get('url') or r.get('canonical_url'),'')
narch=len(archive);nurl=len(fixed_urls)
intake={url(r['canonical_url']):r for r in rows(B/'nguon/intake.tsv')}
kept=[];log=[]
import csv
redirects=dict(csv.reader((B/'nguon/redirects.tsv').open(),delimiter='\t'))
for seed in rows(B/'seeds.tsv'):
 u=url(redirects.get(seed['url'],seed['url']));r=intake.get(u)
 if not r:log.append(dict(url=seed['url'],status='source_not_available'));continue
 raw=(B/'nguon'/r['raw_file']).read_bytes();s=(B/'nguon'/r['text_file']).read_text()
 h=sha(s.encode());ss=sh(s);jac,closest=max(((len(ss&v)/len(ss|v),k[0]) for k,v in archive.items() if ss|v),default=(0,''))
 reason='old_or_duplicate_url' if u in fixed_urls else 'duplicate_text' if h in {k[1] for k in archive} else 'near_duplicate' if jac>=0.5 else 'keep'
 log.append(dict(url=r['canonical_url'],status=reason,max_jaccard=round(jac,5),closest=closest))
 if reason=='keep':
  aid=f'{args.prefix}{len(kept)+1:02}'
  kept.append(dict(article_id=aid,canonical_url=r['canonical_url'],source=r['source'],date=r['published_at'],title=r['title'],clean_text=s,text_sha256=h,raw_sha256=sha(raw)))
  record(r['canonical_url'],s)
def save(f,o):f.write_text(json.dumps(o,ensure_ascii=False,indent=2)+'\n')
with (B/'articles.jsonl').open('x') as fp:
 for a in kept:fp.write(json.dumps(a,ensure_ascii=False)+'\n')
save(B/'khoa_mau.json',dict(utc=datetime.now(timezone.utc).isoformat(),historical_distinct_urls=nurl,historical_url_text_pairs=narch,screen=log,lot_sha256=sha((B/'articles.jsonl').read_bytes()),n=len(kept)))
print(nurl,narch,len(kept))
for a in kept:print(a['article_id'],a['title'])
