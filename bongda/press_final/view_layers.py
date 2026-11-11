"""Build the offline A10 explorer. All joins use fact and entity IDs."""
import argparse,json
from pathlib import Path
from collections import defaultdict
from bongda.core.ban_giao import table
from bongda.press.visual import LABELS
from bongda.press_final.verify import verify_snapshot as verify

def run(root):
    s=root/'snapshot';verify(s);p=root/'phan_lop'
    facts={r['fact_id']:r for r in table(s/'facts.csv')}
    names={r['entity_id']:r['canonical_name'] for r in table(s/'entities.csv')}
    lanes=[]; lookup={}
    for layer in ('xa_hoi','boi_canh'):
        lane=[]
        for r in table(p/(layer+'.tsv'),'\t'):
            f=facts[r['fact_id']]; idx=len(lane); lookup[r['fact_id']]=(len(lanes),idx)
            lane.append([r['source'],r['target'],LABELS.get(r['relation'],dict(GHI_NHAN_HLV_TRUONG_MUA='được ghi nhận là HLV trưởng',TO_CHUC_GIAI='tổ chức giải',CHUYEN_DEN_CLB='chuyển đến',CHUYEN_DI_TU='chuyển đi từ',DA_CHINH_TRONG_TRAN='đá chính trong trận',GOP_MAT_TRONG_TRAN='góp mặt trong trận',THUOC_GIAI_DAU='thuộc giải đấu',CO_TEN_TRONG_DANH_SACH_CLB='có tên trong danh sách CLB',DUOC_BAO_GHI_NHAN_THUOC_CLB='được báo ghi nhận thuộc CLB',DANG_KY_DU_BI_TRONG_TRAN='đăng ký dự bị trong trận',VAO_SAN_THAY_NGUOI_TRONG_TRAN='vào sân thay người trong trận').get(r['relation'],r['relation'])),r['period'],r['business'],r['support'],r['primary_url'],f['quote'],r['fact_id']])
        lanes.append(lane)
    witnesses=defaultdict(list)
    for r in table(p/'dong_doi_chung_cu.tsv','\t'):
        witnesses[r['player1'],r['player2']].append([names[r['club']],names[r['match']],lookup[r['fact1']][1],lookup[r['fact2']][1]])
    lanes.append([[r['name1'],r['name2'],'cùng đá chính',r['matches']+' trận','đồng đội','suy_ra',witnesses[r['player1'],r['player2']]] for r in table(p/'dong_doi.tsv','\t')])
    template=Path(__file__).with_name('layers.html').read_text()
    data=json.dumps(lanes,ensure_ascii=False,separators=(',',':')).replace('<',r'\u003c')
    (root/'Mo_ban_do.html').write_text(template.replace('PAYLOAD_HERE',data))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('root',type=Path);run(p.parse_args().root)
