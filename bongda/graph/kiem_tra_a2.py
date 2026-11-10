"""Kiểm tra raw → văn bản → evidence, nguồn, định danh và kích thước của snapshot A2."""
import argparse,csv,hashlib,json,random,re,unicodedata
from pathlib import Path
from collections import Counter,defaultdict
from bongda.core.ban_giao import jlines,table,verify,sha

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("bundle",type=Path);parser.add_argument("--require-target",action="store_true")
    a=parser.parse_args();root=a.bundle;verify(root,False,True)
    articles={r['article_id']:r for r in jlines(root/'articles.jsonl')};entities=table(root/'entities.csv');facts=table(root/'facts.csv')
    evidence=jlines(root/'evidence.jsonl');stats=json.loads((root/'stats.json').read_bytes())
    grouped=table(root/'article_event_map.tsv','\t')
    pending=[r for r in grouped if r['previous_group'].startswith('pending-')]
    assert len(pending)==186 and all(not r['story_group'].startswith('pending-') for r in grouped)
    assert all(articles[r['article_id']]['story_group']==r['story_group'] for r in grouped)
    assert len({r['article_id'] for r in grouped})==188
    spans=0;wiki=0
    for art in articles.values():
        if art['source_kind']!='wiki' or not art['story_group'].startswith('season:'):continue
        pages=json.loads((root/'raw'/art['raw_sha256']).read_bytes())['query']['pages']
        match=[rv for p in pages if str(p['pageid'])==art['pageid'] for rv in p['revisions'] if str(rv['revid'])==art['revid']]
        assert len(match)==1 and match[0]['timestamp']==art['revision_at'] and art['revision_at']<='2025-12-31T16:59:59Z'
        assert unicodedata.normalize('NFC',match[0]['slots']['main']['content'])==art['clean_text']
        wiki+=1
    for e in evidence:
        if 'context_start' in e:
            t=articles[e['article_id']]['clean_text'];i,j=e['context_start'],e['context_end']
            assert 0<=i<j<=e['start'] and t[i:j].strip()
            spans+=1
    event_evidence={r['evidence_id']:r for r in evidence}
    real_entities={e['entity_id']:e for e in entities}
    signed=Counter()
    for f in facts:
        e=event_evidence[f['evidence_id']];art=articles[e['article_id']]
        assert f['article_url']==art['canonical_url'] and f['quote']==e['quote']
        if f['method']=='wiki_roster_row':
            assert 'context_start' in e and 'fs player' in e['quote'].casefold()
        if f['method'] in {'wiki_match_result','wiki_match_event'}:
            assert '2012-01-01'<=f['period']<='2025-12-31'
        signed[f['method']]+=1
    duplicate_display=defaultdict(list)
    for e in entities:duplicate_display[e['type'],e['canonical_name'].casefold()].append(e['entity_id'])
    duplicate_display={str(k):v for k,v in duplicate_display.items() if len(v)>1}
    # Một mẫu đại diện theo từng quan hệ để hai người chấm độc lập.
    rng=random.Random(22);audit=[]
    for relation in sorted({f['relation_type'] for f in facts}):
        pool=[f for f in facts if f['relation_type']==relation]
        for f in rng.sample(sorted(pool,key=lambda r:r['fact_id']),min(8,len(pool))):
            e=event_evidence[f['evidence_id']];t=articles[e['article_id']]['clean_text']
            audit.append([f['fact_id'],relation,real_entities[f['src_id']]['canonical_name'],real_entities[f['dst_id']]['canonical_name'],
                          f['period'],f['article_url'],t[e['context_start']:e['context_end']] if 'context_start' in e else '',e['quote'],'',''])
    with (root/'mau_ra_soat.tsv').open('w',newline='',encoding='utf-8') as file:
        w=csv.writer(file,delimiter='\t');w.writerow(['fact_id','quan_he','nguon','dich','thoi_gian','url','ngu_canh','bang_chung','nhan_A','nhan_B']);w.writerows(audit)
    report=dict(documents=len(articles),raw_wiki_revisions_checked=wiki,source_counts=dict(Counter(a['source'] for a in articles.values())),
                pending_articles_grouped=len(pending),pending_group_count=len(set(r['story_group'] for r in pending)),all_press_groups=stats['press_groups'],
                distinct_nodes=len(real_entities),distinct_facts=len(facts),relationship_types=len(set(f['relation_type'] for f in facts)),
                methods=signed,evidence_offsets_checked=len(evidence),source_context_spans_checked=spans,duplicate_display_names=duplicate_display,
                semantic_precision="not_independently_measured")
    report['thresholds_pass']=report['distinct_nodes']>=2000 and report['distinct_facts']>=5000 and report['relationship_types']>=10
    (root/'qa.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n')
    if a.require_target and not report['thresholds_pass']:raise ValueError('Snapshot chưa đạt ngưỡng.')
    print(json.dumps({k:report[k] for k in ['distinct_nodes','distinct_facts','relationship_types','thresholds_pass']}))
if __name__=='__main__':main()
