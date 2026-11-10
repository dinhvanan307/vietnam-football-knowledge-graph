"""Resolve the parties to a club sponsorship deal from typed model proposals."""
import argparse,json,re,unicodedata
from pathlib import Path
import kiem_chung_su_kien as v3
from trich_xuat import anchored,norm,exact_name
import bao_bon_quan_he as base
COMPANIES={
    'scg':'firm-w3130564','siam cement group':'firm-w3130564',
    'thaco':'firm-w2417064','truong hai thaco':'firm-w2417064',
    'hanaka':'o-hanaka','nutifood':'firm-w18044912','becamex idc':'firm-w3374682',
}
HISTORIC_CLUBS={'khanh hoa':'club-w2452083','sanna khanh hoa':'club-w2452083','sai gon':'club-w445434','than quang ninh':'club-w372882','hai phong':'c-hp','ha noi':'c-hn','hoang anh gia lai':'c-hagl','song lam nghe an':'c-slna','binh dinh':'c-binhdinh','da nang':'c-dn','hue':'club-w524030','thanh hoa':'c-th','binh duong':'c-bd'}
LEGAL=r'^(?:(?:tổng công ty|công ty|ctcp|tập đoàn|nhãn hàng|thương hiệu)(?: cổ phần| cp| tnhh| tnhh mtv)?\s+)+'
def names(company):
    full=unicodedata.normalize('NFC',company).strip()
    forms=[full,re.sub(LEGAL,'',full,flags=re.I)]
    for x in re.findall(r'\(([^()]+)\)',full):forms.append(x)
    return [s.strip() for s in forms if s.strip()]
def identify_company(name,catalog):
    forms=names(name);words=' '+norm(name)+' '
    for alias,eid in COMPANIES.items():
        if ' '+alias+' ' in words:return eid
    if re.search(r'\bvp\s*milk\b',words):return 'new:Organization:vpmilk'
    cid=catalog.actor_id(name,'Organization',{'clean_text':'','date':'2020'},name)
    if cid in catalog.nodes and catalog.nodes[cid]['type']=='Organization':return cid
    return 'new:Organization:'+exact_name(forms[1])
def confirmed(text):
    text=unicodedata.normalize('NFC',text).casefold()
    if re.search(r'(?:mong muốn|dự kiến|kêu gọi|tìm kiếm|đề xuất|đăng ký tham gia|ngỏ ý|nếu|chưa ký).{0,50}tài trợ',text) and not re.search(r'(?:đã|chính thức|ký kết|ra mắt|công bố).{0,30}tài trợ',text):return False
    return bool(re.search(r'nhà tài trợ|(?:đã |sẽ )?tài trợ (?:chính |kinh phí |số tiền |cho |từ |để |[0-9])|(?:hợp đồng|thỏa thuận|gói|kinh phí|lễ ký kết|việc) tài trợ|tài trợ.{0,35}(?:clb|đội bóng|câu lạc bộ)|đồng hành.{0,16}(?:cùng|với)',text))
def extract(a,doc,reg):
    blocks=a['clean_text'].split('\n\n');out=[];year=int(a['date'][:4])
    for e in doc['draft']:
        if e['rel']!=base.S:continue
        actor,club=e['actor'],e['club']
        club_form=norm(re.sub(r'^(?:câu lạc bộ(?: bóng đá)?|clb(?: bóng đá)?)\s+|\s+fc$','',club,flags=re.I))
        cid=HISTORIC_CLUBS.get(club_form) if year>2012 else None
        refs=sorted(set(e['refs']+[e['anchor']]))
        if not refs or any(i<1 or i>len(blocks) for i in refs):continue
        context=' '.join(blocks[i-1] for i in refs)
        cid=cid or reg.club(club,context,a)
        if not cid or not actor:continue
        sponsor=identify_company(actor,reg)
        if not any(anchored(v,context) for v in names(actor)):
            near=[i for i,t in enumerate(blocks,1) if min(abs(i-j) for j in refs)<=2 and any(anchored(v,t) for v in names(actor))]
            if not near:continue
            refs=sorted(set(refs+[near[0]]));context=' '.join(blocks[i-1] for i in refs)
        description=unicodedata.normalize('NFC',e['event']).casefold()
        if re.search(r'tài trợ (?:cho )?(?:giải đấu|giải vô địch|đội tuyển|hợp đồng giữ chân|học viện)(?!.*(?:và|lẫn) (?:clb|đội bóng))|có thể|kêu gọi|đang (?:đàm phán|tìm kiếm)|dự kiến tài trợ',description):continue
        if not confirmed(context):continue
        if not (anchored(club,context) or any(' '+n+' ' in ' '+norm(context)+' ' for n in reg.clubforms[cid]|{club_form} if len(n)>2)):continue
        item=dict(src=actor,dst=club,rel=base.S,src_id=sponsor,dst_id=cid,refs=refs,anchor=e['anchor'],event=e['event'],when=e['when'] if v3.clean(e['when']) in v3.clean(context) else '')
        if not any((x['src_id'],x['dst_id'])==(sponsor,cid) and set(refs)&set(x['refs']) for x in out):out.append(item)
    return out
def main():
    cli=argparse.ArgumentParser()
    for arg in ['lot','graph','cache','out']:cli.add_argument(arg,type=Path)
    a=cli.parse_args();reg=v3.Resolver(a.graph);a.out.mkdir(exist_ok=True)
    for article in map(json.loads,a.lot.read_text().splitlines()):
        path=a.cache/(article['article_id']+'.json');data=json.loads(path.read_text())
        out=dict(edges=extract(article,data,reg),model=data['model'],input_sha=article['text_sha256'],proposal_sha=base.sha(path.read_bytes()),code_sha=base.sha(Path(__file__).read_bytes()))
        (a.out/path.name).write_text(base.packed(out))
if __name__=='__main__':main()
