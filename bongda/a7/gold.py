"""Compile the source review without using any predictor outputs."""
from pathlib import Path
import csv,json,re,unicodedata
from collections import Counter,defaultdict
from bongda.a7.paths import DATA as P
rels=dict(K='KY_HOP_DONG_VOI',C='DUOC_TRIEU_TAP_VAO',D='KY_LUAT',S='TAI_TRO')
def namekey(x):return ' '.join(re.findall(r'[^\W_]+',unicodedata.normalize('NFC',x).casefold()))
def rows(path,sep='\t'):
    with path.open(encoding='utf-8-sig',newline='') as f:return list(csv.DictReader(f,delimiter=sep))
def out(path,data):
    with path.open('w',newline='') as f:
        w=csv.DictWriter(f,list(data[0]),delimiter='\t');w.writeheader();w.writerows(data)
def loadlot(B):return {a['article_id']:a for a in map(json.loads,(B/'articles.jsonl').read_text().splitlines())}
def compile_labels(B):
    lot=loadlot(B);nodes=rows(P/'A6_3_Ban_nop/snapshot/entities.csv',',')
    exact={namekey(r['canonical_name']):r['entity_id'] for r in nodes}
    bare=defaultdict(set)
    for r in nodes:bare[namekey(re.sub(r'\s*\([^)]*\)\s*$','',r['canonical_name']))].add(r['entity_id'])
    gold=[];seen=set();coverage=set()
    for line in (B/'cham_mu.txt').read_text().splitlines():
        if not line or line.startswith('#'):continue
        aid,data=line.split(' ',1);coverage.add(aid)
        if data=='-':continue
        typ,ref,dest,key,period,names=data.split('|')
        refs=list(map(int,ref.split(',')))
        assert max(refs)<=len(lot[aid]['clean_text'].split('\n\n'))
        for name in names.split(';'):
            n=namekey(name);subject=exact.get(n)
            if not subject and len(bare[n])==1:subject=next(iter(bare[n]))
            if not subject:
                assert not bare[n],name
                subject='new:'+('Organization' if typ=='S' else 'Person')+':'+n
            src,dst=(dest,subject) if typ=='D' else (subject,dest)
            sig=(aid,rels[typ],src,dst,key);assert sig not in seen;seen.add(sig)
            gold.append(dict(bai=aid,rel=rels[typ],src_id=src,dst_id=dst,display=name,event_key=key,period=period,refs=ref,url=lot[aid]['canonical_url']))
    assert coverage==set(lot)
    out(B/'nhan_chuan.tsv',gold);print(Counter(r['rel'] for r in gold))
if __name__=='__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('lot_dir', type=Path)
    compile_labels(parser.parse_args().lot_dir)
