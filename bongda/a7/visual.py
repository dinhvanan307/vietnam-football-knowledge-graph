import json,csv
from pathlib import Path
from bongda.a7.paths import RELEASE as B
S=B/'snapshot'
kinds={'Person':'Người','Club':'CLB','NationalTeam':'Đội tuyển','Organization':'Tổ chức','Competition':'Giải đấu','Stadium':'Sân vận động'}
labels=dict(zip('CHU_TICH_CUA DANG_KY_THI_DAU_CHO DAN_DAT DOI_DAU DOI_TRUONG_CUA DUOC_CHO_MUON_DEN DUOC_TRIEU_TAP_VAO GHI_BAN_VAO_LUOI GIA_HAN_VOI KY_HOP_DONG_VOI KY_LUAT NHAN_THE_VANG_KHI_GAP SU_DUNG_SAN_NHA TAI_TRO THAM_GIA_GIAI THANH_LY_VOI THI_DAU_CHO THI_DAU_TAI_SAN'.split(),'là chủ tịch của|đăng ký thi đấu cho|dẫn dắt|đối đầu|là đội trưởng của|được cho mượn đến|được triệu tập vào|ghi bàn vào lưới|gia hạn với|ký hợp đồng với|kỷ luật|nhận thẻ vàng khi gặp|dùng sân nhà|tài trợ|tham gia giải|thanh lý với|thi đấu cho|thi đấu tại sân'.split('|'),strict=True))
nodes=[[r['entity_id'],r['canonical_name'],kinds.get(r['type'],r['type'])] for r in csv.DictReader((S/'entities.csv').open())];ni={r[0]:i for i,r in enumerate(nodes)}
arts=list(map(json.loads,(S/'articles.jsonl').read_text().splitlines()));sources=[[a['source'],a['title'],a['canonical_url']] for a in arts];ai={a['article_id']:i for i,a in enumerate(arts)}
quotes={};edges=[]
for r in csv.DictReader((S/'facts.csv').open()):
 q=r['quote'].strip();i=quotes.setdefault(q,len(quotes));edges.append([ni[r['src_id']],ni[r['dst_id']],r['relation_type'],r['period'],ai[r['article_id']],i,r['fact_id']])
assert set(labels)=={e[2] for e in edges}
payload=json.dumps(dict(nodes=nodes,edges=edges,sources=sources,quotes=list(quotes),labels=labels),ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')
(B/'Ban_do_bong_da.html').write_text(Path(__file__).with_name('ban_do.template.html').read_text().replace('DATA_HERE',payload))
