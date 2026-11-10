"""Build a reviewer queue, never import an unreviewed prediction into Neo4j."""
import argparse,csv,json
from pathlib import Path
def make(lot,pred,out):
    articles=list(map(json.loads,lot.read_text().splitlines()));out.mkdir(parents=True,exist_ok=True)
    def emit(name,fields,rows):
        # Preserve filled-in reviewer work if a user reruns the command.
        dest=out/name;import io
        buf=io.StringIO(newline='');w=csv.writer(buf,delimiter='\t');w.writerow(fields);w.writerows(rows)
        data=buf.getvalue().encode()
        if dest.exists():
            if dest.read_bytes()!=data:raise FileExistsError(f'Use a new output directory to preserve {dest}')
        else:dest.write_bytes(data)
    blind=[];queue=[]
    for a in articles:
        aid=a['article_id'];blocks=a['clean_text'].split('\n\n')
        for i,b in enumerate(blocks,1):
            blind.append([aid,a['canonical_url'],i,b,'','','','',''])
        d=json.loads((pred/(aid+'.json')).read_text())['baseline']
        for eid,row in d.items():
            refs=row['refs'];assert refs and all(1<=int(i)<=len(blocks) for i in refs)
            queue.append([aid,eid,row['name'],'nt-vn',a['canonical_url'],','.join(map(str,refs)),'\n'.join(blocks[i-1] for i in refs),'CHO_DUYET','','',''])
    emit('phieu_B_trong.tsv',['bai','url','so_doan','noi_dung','ten_nguoi','dot_tuyen','doi','quyet_dinh','ghi_chu'],blind)
    emit('goi_y_cho_duyet.tsv',['bai','goi_y_id','ten_in','doi_dich_goi_y','nguon','doan','noi_dung','trang_thai','dot_tuyen_xac_nhan','nguoi_duyet','ghi_chu'],queue)
if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--lot',type=Path,required=True);p.add_argument('--pred',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args();make(a.lot,a.pred,a.out)
