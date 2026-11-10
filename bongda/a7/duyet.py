"""Replay the final extractors, score every prediction, and apply the predeclared import rule."""
import collections,json,sys
from pathlib import Path
from bongda.a7.paths import RELEASE as B, DATA as P, ROOT as REPO, LOTS
from bongda.a7 import score
sys.path.insert(0, str(REPO / 'nlp_bao'))
import bao_bon_quan_he as base
import kiem_chung_su_kien as general
import tai_tro_clb as sponsors
def build():
    B.mkdir(parents=True, exist_ok=True)
    graph=P/'A6_3_Ban_nop/snapshot/entities.csv';reg=general.Resolver(graph)
    for prefix,name in LOTS.items():
        folder=P/name
        cache=folder/({'B':'pred_A7v2','V':'pred'}.get(prefix,'proposals'))
        snapshots=folder/'duyet_A7';snapshots.mkdir(exist_ok=True);pr=snapshots/'pred';pr.mkdir(exist_ok=True)
        required=score.sha(Path(general.v2.__file__));module_sha=score.sha(Path(general.__file__));sponsor_sha=score.sha(Path(sponsors.__file__))
        for a in map(json.loads,(folder/'articles.jsonl').read_text().splitlines()):
            raw=cache/(a['article_id']+'.json');proposal=json.loads(raw.read_bytes())
            seal=base.sha((base.sha(Path(general.v2.__file__).read_bytes()+Path(base.__file__).read_bytes()+graph.read_bytes())+a['text_sha256']).encode())
            if proposal['seal']!=seal:raise ValueError('Stale input or extractor '+a['article_id'])
            edges=[e for e in general.review(a,proposal['draft'],reg) if e['rel']!=base.S] if prefix!='S' else []
            edges+=sponsors.extract(a,proposal,reg)
            data=dict(edges=edges,model=proposal['model'],lot=a['text_sha256'],proposal_sha=score.sha(raw),code=[required,module_sha,sponsor_sha])
            (pr/raw.name).write_text(base.packed(data))
        score.score(folder,pr,snapshots)
    scores={}
    for rel in base.KINDS:
        parts=['S'] if rel==base.S else ['N','R'] if rel==base.D else ['N']
        considered=[json.loads((P/LOTS[k]/'duyet_A7/precision.json').read_bytes())['per_type'][rel] for k in parts]
        totals={key:sum(r[key] for r in considered) for key in ['TP','FP','FN','articles_predicted']}
        m=score.metrics(totals['TP'],totals['FP'],totals['FN'])
        scores[rel]=dict(**m,articles_predicted=totals['articles_predicted'],assessed_lots=parts,
                         pass_gate=bool(m['precision'] is not None and m['precision']>.90 and m['TP']+m['FP']>=5 and totals['articles_predicted']>=3))
    total={k:sum(s[k] for s in scores.values()) for k in ('TP','FP','FN')}
    out=dict(per_type=scores,micro=score.metrics(total['TP'],total['FP'],total['FN']),rule='observed precision > 0.90; >=5 predictions in >=3 articles per relation; exact IDs and event under the adjudication protocol')
    (B/'nghiem_thu.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
if __name__=='__main__':build()
