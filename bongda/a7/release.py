"""Build an immutable additive release from source-reviewed predictions, after scoring."""
import csv,hashlib,json,os,re,shutil,sys,tempfile,unicodedata
from collections import Counter
from pathlib import Path
from bongda.a7.paths import RELEASE as B, DATA as P, LOTS
from bongda.core.ban_giao import sha, verify, table, jlines, enc

def dump(p,data):p.write_text(json.dumps(data,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
def tsv(p,data,sep='\t'):
    with p.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(data[0]),delimiter=sep);w.writeheader();w.writerows(data)
def jl(p,data):p.write_text(''.join(enc(r)+'\n' for r in data))
def key(prefix,fields):return prefix+sha(enc(fields).encode())[:20]

OLD=P/'A6_3_Ban_nop/snapshot'
HOLD={
    ('B09','Geovane Magno'):'Ba ID Geovane có trong A6.3, cần hợp nhất có chứng cứ trước khi ghi giao dịch.',
    ('S05','Huda'):'Nguồn nhắc thời kỳ từ 2006–07; không định được khoảng trong giai đoạn sự kiện của bản nộp.',
    ('V22','Hồ Tuấn Tài'):'Đoạn hồi tưởng chỉ có khoảng từ 2023 đến 2025, không định được mùa giao kết.',
    ('V22','Bùi Tấn Trường'):'Đoạn hồi tưởng chỉ có khoảng từ 2023 đến 2025, không định được mùa giao kết.',
    ('B18','2022-03-wc-qualifying'):'Bài chỉ định năm triệu tập lần đầu của Schmidt, thiếu chi tiết để gán chắc một đợt trong năm.',
    ('R06','Trần Đình Đồng'):'Ngày ghi trên bài khác ngày 01/03 trong nguồn khác. Không dùng làm chứng cứ định ngày.',
}
def read(path):return json.loads(path.read_bytes())
def freeze():
    for name,h in read(OLD/'checksums.json').items():
        if sha((OLD/name).read_bytes())!=h:raise ValueError('Parent snapshot changed')
    scorefile=B/'nghiem_thu.json';gate=read(scorefile)['per_type']
    if set(gate)!=set(['TAI_TRO','KY_HOP_DONG_VOI','DUOC_TRIEU_TAP_VAO','KY_LUAT']):raise ValueError('Gate incomplete')
    nodes={r['entity_id']:r for r in table(OLD/'entities.csv')};facts={r['fact_id']:r for r in table(OLD/'facts.csv')}
    events={(r['src_id'],r['relation_type'],r['dst_id'],r['event_key']):r['fact_id'] for r in facts.values()}
    evid={r['evidence_id']:r for r in jlines(OLD/'evidence.jsonl')};meta={r['fact_id']:r for r in jlines(OLD/'event_attributes.jsonl')}
    arts={r['article_id']:r for r in jlines(OLD/'articles.jsonl')};before=set(facts);audit=[];raws={}
    methods={s:Counter() for s in ['new','support_existing','support_new','hold']}
    with tempfile.TemporaryDirectory(dir=B) as tmp:
        dest=Path(tmp)/'snapshot';dest.mkdir()
        shutil.copytree(OLD/'raw',dest/'raw')
        for oldlog in OLD.glob('*.tsv'):shutil.copyfile(oldlog,dest/oldlog.name)
        for pref,source in LOTS.items():
            lot=P/source;out=lot/'duyet_A7';judged=read(out/'precision.json')
            if sha((out/'cham_tung_canh.tsv').read_bytes())!=judged['details_sha256']:raise ValueError('Changed reviews')
            intake={r['canonical_url']:r for r in table(lot/'nguon/intake.tsv','\t')}
            articles={a['article_id']:a for a in jlines(lot/'articles.jsonl')}
            for r in table(out/'cham_tung_canh.tsv','\t'):
                if r['status']!='TP':continue
                aid=r['bai'];rel=r['rel'];a=articles[aid];src=r['src_id'];dst=r['dst_id'];period=r['period'];evkey=r['gold_event']
                auditrow=dict(bai=aid,index=r['index'],rel=rel,src_id=src,dst_id=dst,event_key=evkey,period=period,action='',reason='',fact_id='',url=a['canonical_url'])
                why=HOLD.get((aid,r['gold_name'])) or HOLD.get((aid,evkey))
                if not gate[rel]['pass_gate']:why='Loại quan hệ không vượt ngưỡng trên lô kiểm độc lập.'
                if why:
                    methods['hold'][rel]+=1;audit.append(dict(auditrow,action='hold',reason=why));continue
                # Recheck the original model output, not just the scored table.
                prediction=out/'pred'/(aid+'.json')
                if sha(prediction.read_bytes())!=judged['pred_sha256'][aid]:raise ValueError('Changed predictions')
                edge=read(prediction)['edges'][int(r['index'])]
                if edge['rel']!=rel or ','.join(map(str,edge['refs']))!=r['refs']:raise ValueError('Prediction provenance mismatch')
                for endpoint in [src,dst]:
                    if endpoint.startswith('new:'):
                        _,kind,_=endpoint.split(':',2)
                        nid=key('firm-a7-' if kind=='Organization' else 'p-a7-',[endpoint])
                        node=dict(entity_id=nid,type=kind,canonical_name=r['gold_name'],role='Company' if kind=='Organization' else 'Player')
                        if nid in nodes and nodes[nid]!=node:raise ValueError(('Inconsistent label',node,nodes[nid]))
                        nodes[nid]=node
                        if src==endpoint:src=nid
                        else:dst=nid
                assert src in nodes and dst in nodes
                raw=intake[a['canonical_url']];rawfile=lot/'nguon'/raw['raw_file']
                if sha(rawfile.read_bytes())!=a['raw_sha256']:raise ValueError('Archived original changed')
                if not (dest/'raw'/a['raw_sha256']).exists():shutil.copyfile(rawfile,dest/'raw'/a['raw_sha256'])
                clean=unicodedata.normalize('NFC',a['clean_text']);article_id='a_'+sha(enc([a['canonical_url'],'',a['raw_sha256'],sha(clean.encode())]).encode())[:24]
                if article_id not in arts:
                    arts[article_id]=dict(article_id=article_id,source=a['source'],source_kind='press',canonical_url=a['canonical_url'],title=a['title'],published_at=re.sub(r'([+-])(\d):(\d\d)$',r'\g<1>0\g<2>:\g<3>',a['date']),retrieved_at=raw['retrieved_at'],story_group='press-a7-'+article_id,record_kind='real',pageid='',revid='',revision_at='',clean_text=clean,raw_sha256=a['raw_sha256'],clean_sha256=sha(clean.encode()))
                # Carry the model's complete supporting span; exact NFC offsets are checked by the graph validator.
                ps=list(re.finditer(r'[^\n]+',clean));ids=edge['refs'];i=ps[min(ids)-1].start();j=ps[max(ids)-1].end();quote=clean[i:j]
                sig=(src,rel,dst,evkey);fid=events.get(sig);action='support_existing' if fid in before else 'support_new' if fid else 'new'
                if not fid:fid=key('f_',list(sig));events[sig]=fid
                eid=key('e_',[fid,article_id,i,j]);evid[eid]=dict(evidence_id=eid,fact_id=fid,article_id=article_id,role='supports',start=i,end=j,quote=quote)
                if action=='new':
                    facts[fid]=dict(fact_id=fid,src_id=src,dst_id=dst,relation_type=rel,event_key=evkey,period=period,status='accepted',method='press_nlp_a7_reviewed',evidence_id=eid,article_id=article_id,article_url=a['canonical_url'],quote=quote)
                    meta[fid]=dict(fact_id=fid,extraction_model=edge.get('model') or 'gemini-3.5-flash-lite',source_event=edge['event'],paragraphs=ids)
                    if reviewer := os.getenv('A7_REVIEWER'):
                        meta[fid]['reviewed_by'] = reviewer
                    else:
                        meta[fid]['review_status'] = 'Đạt kiểm tra'
                methods[action][rel]+=1
                audit.append(dict(auditrow,src_id=src,dst_id=dst,action=action,reason='Đối chiếu đúng người, quan hệ, đợt và bằng chứng.',fact_id=fid))
        jl(dest/'articles.jsonl',[arts[k] for k in sorted(arts)])
        dump(dest/'manifest.json',dict(schema_version='1',record_kind='real',article_count=len(arts),articles_sha256=sha((dest/'articles.jsonl').read_bytes())))
        tsv(dest/'entities.csv',[nodes[k] for k in sorted(nodes)],',');tsv(dest/'facts.csv',[facts[k] for k in sorted(facts)],',')
        jl(dest/'evidence.jsonl',[evid[k] for k in sorted(evid)]);jl(dest/'event_attributes.jsonl',[meta[k] for k in sorted(meta)])
        tsv(dest/'doi_chieu_nhap_A7.tsv',audit)
        assert all(facts[r['fact_id']]==r for r in table(OLD/'facts.csv'))
        assert all(nodes[r['entity_id']]==r for r in table(OLD/'entities.csv'))
        stats=dict(version='A7',parent='A6.3',nodes=len(nodes),edges=len(facts),types=Counter(f['relation_type'] for f in facts.values()),articles=len(arts),primary_sources=Counter(arts[f['article_id']]['source_kind'] for f in facts.values()),added_nodes=len(nodes)-len(table(OLD/'entities.csv')),added_edges=len(facts)-len(before),added_source_articles=len(arts)-len(jlines(OLD/'articles.jsonl')),import_actions=methods,parent_facts_sha256=sha((OLD/'facts.csv').read_bytes()),gate_sha256=sha(scorefile.read_bytes()))
        dump(dest/'stats.json',stats);verify(dest,False,True)
        dump(dest/'checksums.json',{p.name:sha(p.read_bytes()) for p in dest.iterdir() if p.is_file()})
        existing=B/'snapshot'
        if existing.exists():
            if (existing/'checksums.json').read_bytes()!=(dest/'checksums.json').read_bytes():raise ValueError('A7 already exists with different output')
        else:dest.rename(existing)
        print(json.dumps(stats,ensure_ascii=False))
if __name__=='__main__':freeze()
