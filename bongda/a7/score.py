"""Evaluate complete frozen output before deciding which predictions can be released."""
import argparse,csv,hashlib,json,math,random,statistics
from collections import Counter,defaultdict
from pathlib import Path
from bongda.a7.paths import ROOT
from bongda.a7.gold import namekey,rows,out,rels
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def verify(b,f):
    for line in (b/f).read_text().splitlines():
        digest,p=line.split(None,1)
        legacy = Path(p.strip())
        if legacy.parts[:2] == ('..', 'vietnam-football-knowledge-graph'):
            artifact = ROOT.joinpath(*legacy.parts[2:])
        else:
            artifact = b / legacy
        if sha(artifact)!=digest:raise ValueError('Checksum mismatch: '+p)
def metrics(tp,fp,fn):
    return dict(TP=tp,FP=fp,FN=fn,precision=tp/(tp+fp) if tp+fp else None,recall=tp/(tp+fn) if tp+fn else None,F1=2*tp/(2*tp+fp+fn) if tp+fp+fn else None)
def score(b,folder=None,output=None):
    folder=folder or b/"pred";output=output or b;output.mkdir(exist_ok=True)
    verify(b,'khoa_trich.sha256');verify(b,'khoa_nhan.sha256')
    lot={a['article_id']:a for a in map(json.loads,(b/'articles.jsonl').read_text().splitlines())}
    gold=rows(b/'nhan_chuan.tsv');aliases={}
    for r in rows(b/'tuong_duong.tsv'):
        aliases['new:'+r['kind']+':'+namekey(r['alternate'])]='new:'+r['kind']+':'+namekey(r['canonical'])
    if {p.stem for p in folder.glob('*.json')}!=set(lot):raise ValueError('Incomplete lot')
    detail=[];counts={typ:Counter() for typ in rels.values()};stats=defaultdict(lambda:defaultdict(Counter))
    overrides={}
    manual=output/'verifier_notes.tsv'
    if manual.exists():overrides={(r['bai'],int(r['n'])):r['reason'] for r in rows(manual)}
    used=set()
    for aid,a in lot.items():
        raw=json.loads((folder/(aid+'.json')).read_text())
        for n,e in enumerate(raw['edges']):
            sid=aliases.get(e['src_id'],e['src_id']);tid=aliases.get(e['dst_id'],e['dst_id'])
            # The gold review freezes aliases for genuinely new organisations. Some extractors
            # remove legal prefixes from their provisional ID, while retaining the original
            # printed company name. Accept either predeclared spelling only for OPEN identities.
            # Never use this to redirect an existing graph ID or forgive a duplicate of one.
            if e['rel']=='TAI_TRO' and e['src_id'].startswith('new:Organization:'):
                literal='new:Organization:'+namekey(e['src'])
                allowed={g['src_id'] for g in gold if g['rel']==e['rel'] and g['src_id'].startswith('new:Organization:')}
                frozen=aliases.get(literal,literal)
                if frozen in allowed:sid=frozen
            matches=[(j,g) for j,g in enumerate(gold) if j not in used and (aid,e['rel'],sid,tid)==(g['bai'],g['rel'],g['src_id'],g['dst_id']) and set(e['refs'])&set(map(int,g['refs'].split(',')))]
            if len(matches)>1:
                desc=e['event']+' '+e.get('when','')
                if aid=='B03':matches=[(j,g) for j,g in matches if g['period'] in desc and not all(y in desc for y in ['2022','2023'])]
                if aid=='N19':matches=[(j,g) for j,g in matches if ('2020' in desc or 'hủy' in desc.casefold())==('2020' in g['event_key'])]
                if aid=='V10':matches=[(j,g) for j,g in matches if ('úc' in desc.casefold() or 'trung quốc' in desc.casefold())==('australia' in g['event_key'])]
                if aid=='B18':matches=[(j,g) for j,g in matches if ('2022' in desc)==('2022' in g['period'])]
            if (aid,n) in overrides:matches=[]
            g={}
            if len(matches)==1:
                j,g=matches[0];used.add(j)
            state='TP' if g else 'FP'
            counts[e['rel']][state]+=1;stats[aid][e['rel']][state]+=1
            detail.append(dict(bai=aid,index=n,status=state,rel=e['rel'],src_id=sid,dst_id=tid,src=e['src'],dst=e['dst'],event=e['event'],refs=','.join(map(str,e['refs'])),gold_event=g.get('event_key',''),period=g.get('period',''),gold_name=g.get('display',''),url=a['canonical_url'],note=overrides.get((aid,n),'') ))
    for j,g in enumerate(gold):
        if j in used:continue
        counts[g['rel']]['FN']+=1;stats[g['bai']][g['rel']]['FN']+=1
        detail.append(dict(bai=g['bai'],index='',status='FN',rel=g['rel'],src_id=g['src_id'],dst_id=g['dst_id'],src='',dst='',event='',refs=g['refs'],gold_event=g['event_key'],period=g['period'],gold_name=g['display'],url=g['url'],note=''))
    result={}
    for typ,c in counts.items():
        s=metrics(c['TP'],c['FP'],c['FN'])
        docs=sum(bool(stats[a][typ]['TP']+stats[a][typ]['FP']) for a in lot)
        s['articles_predicted']=docs;s['pass_gate']=bool(s['precision'] is not None and s['precision']>.90 and c['TP']+c['FP']>=5 and docs>=3)
        result[typ]=s
    total=sum(counts.values(),Counter());out(output/'cham_tung_canh.tsv',detail)
    per=[dict(bai=a,rel=t,**metrics(c['TP'],c['FP'],c['FN'])) for a in lot for t in rels.values() for c in [stats[a][t]]];out(output/'cham_theo_bai.tsv',per)
    report=dict(n=len(lot),gold=len(gold),per_type=result,micro=metrics(total['TP'],total['FP'],total['FN']),
                lot_sha256=sha(b/'articles.jsonl'),gold_sha256=sha(b/'nhan_chuan.tsv'),details_sha256=sha(output/'cham_tung_canh.tsv'),pred_sha256={p.stem:sha(p) for p in sorted(folder.glob('*.json'))})
    (output/'precision.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('lot_dir',type=Path);p.add_argument('--pred',type=Path);p.add_argument('--out',type=Path);args=p.parse_args();score(args.lot_dir.resolve(),args.pred,args.out)
