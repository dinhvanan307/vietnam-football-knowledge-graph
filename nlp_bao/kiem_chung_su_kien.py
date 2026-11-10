"""Deterministic evidence and identity checks on cached typed Gemini proposals (no API)."""
import argparse,csv,json,re,unicodedata
from collections import defaultdict
from pathlib import Path
import bao_su_kien as v2
import bao_bon_quan_he as base
from trich_xuat import read_graph,norm,anchored
YOUTH=r'\b(?:u[\s.\-]?(?:1[6-9]|2[0-3])|olympic|sea games|futsal)\b|tuyển nữ'
SENIOR=r'\b(?:đội tuyển|tuyển|đt)\s+(?:bóng đá\s+)?(?:nam\s+)?(?:việt nam|vn|quốc gia)\b|đtqg'
RENEW=r'gia hạn|tái ký|(?:ký|gắn bó|ở lại|giữ chân).{0,45}(?:thêm \d+ năm|ở lại|kéo dài hợp đồng)|tái ký'
STAFF=r'(?:hlv(?: trưởng| thủ môn)?|trợ lý(?: hlv)?|cán bộ(?: phân tích kỹ thuật| chuyên môn)?|trưởng đoàn|giám đốc(?: kỹ thuật)?)'
def clean(s):return unicodedata.normalize('NFC',s).casefold()
def shortclub(s):
    return re.sub(r'^(?:câu lạc bộ(?: bóng đá)?|clb)\s+','',clean(s)).strip()
class Resolver(v2.Catalog):
    def __init__(self,graph):
        super().__init__(graph)
        self.clubforms=defaultdict(set)
        for alias,eid in self.alias.items():
            if self.nodes.get(eid,{}).get('type')=='Club':self.clubforms[eid].add(norm(shortclub(alias)))
        for eid,aliases in self.reg.clubs.items():
            if eid in self.nodes:self.clubforms[eid].update(aliases)
        self.registered=defaultdict(set)
        for f in read_graph(graph.parent/'facts.csv',','):
            if f['relation_type']=='DANG_KY_THI_DAU_CHO':self.registered[f['src_id']].add(f['dst_id'])
        self.compact=defaultdict(set)
        for eid,node in self.nodes.items():
            if 'Player' in node['role']:self.compact[norm(base.bare(node['canonical_name'])).replace(' ','')].add(eid)
    def club(self,name,ctx,article):
        cid=self.identify(name,'Club',article['clean_text'],ctx,int(article['date'][:4]))
        if cid:return cid
        label=norm(shortclub(name));ids={eid for eid,forms in self.clubforms.items() if label in forms}
        return next(iter(ids)) if len(ids)==1 else None
    def person(self,name,context,article,cid=None):
        eid=self.actor_id(name,'Person',article,context)
        if eid in self.nodes and 'Player' in self.nodes[eid]['role']:return eid
        n=norm(name);compact=self.compact.get(n.replace(' ',''),set())
        if len(compact)==1:return next(iter(compact))
        words=n.split()
        if len(words)>=3:
            candidates={i for i,r in self.nodes.items() if 'Player' in r['role']
                        and len((k:=norm(base.bare(r['canonical_name'])).split()))>=2 and words[:len(k)]==k}
            sameclub={i for i in candidates if cid and cid in self.registered[i]}
            if len(sameclub)==1:return next(iter(sameclub))
            if candidates:return None
        if eid and eid.startswith('new:') and len(words)>=3:return eid
        return None
def senior_ok(a,context,event):
    title=clean(a['title']);lead=clean(a['clean_text'].split('\n\n')[0]);ev=clean(event)
    if re.search(YOUTH,ev) and not re.search(SENIOR,ev):return False
    if re.search(YOUTH,title+' '+lead) and not re.search(SENIOR,title+' '+lead):return False
    if re.search(r'(?:đội tuyển|tuyển|đt)\s+(?:iraq|thái lan|nhật bản|hàn quốc|indonesia|malaysia|nga)\s+(?:đã |vừa )?(?:gọi|triệu tập)',title+' '+ev):return False
    return bool(re.search(SENIOR,clean(a['clean_text']+' '+a['title'])))
def review(a,draft,catalog):
    text=a['clean_text'];blocks=text.split('\n\n');accepted=[];held=[]
    senior_cues=r'có mặt|đều có tên|danh sách|triệu tập|gọi (?:bổ sung|trở lại)|hội quân|tập trung'
    extra=[]
    for i,p in enumerate(blocks,1):
        line=clean(p)
        if not senior_ok(a,p,'') or re.search(YOUTH,line):continue
        # A source enumeration must be tied to an announced camp. A roster of the starting eleven is not a call-up.
        if not re.search(r'trong danh sách.{0,150}(?:đều có mặt|gồm|có mặt là)|(?:có tên|được gọi|được triệu tập) (?:gồm|là|có)|(?:thủ môn|hậu vệ|tiền vệ|tiền đạo)\s*:',line):continue
        if re.search(r'dự kiến|khả năng|nếu |đội hình ra sân|đăng ký thi đấu|có thể|không có tên|chưa công bố',line):continue
        if not re.search(r'(?:công bố|triệu tập|quyết định gọi)',clean(' '.join(blocks[:3]))):continue
        for m in catalog.reg.callups.matcher.finditer(unicodedata.normalize('NFC',p)):
            name=m.group();extra.append(dict(rel=base.C,actor=name,club='',anchor=i,refs=[i],when='',event='Danh sách tập trung được nêu trong bài: '+a['title']))
    for row in [*draft,*extra]:
        rel=row['rel'];name=row['actor'].strip()
        refs=sorted(set([row['anchor'],*row['refs']]))
        if not refs or not all(type(i)==int and 1<=i<=len(blocks) for i in refs):continue
        ctx=' '.join(blocks[i-1] for i in refs)
        if not anchored(name,ctx):
            # Recover a paragraph containing the full name when the proposed evidence cites its abbreviation.
            last=' '.join(name.split()[-2:])
            if len(name.split())<3 or not anchored(last,ctx):continue
            nearby=[i for i,p in enumerate(blocks,1) if anchored(name,p) and min(abs(i-j) for j in refs)<=2]
            if not nearby:continue
            refs=sorted(set(refs+[nearby[0]]));ctx=' '.join(blocks[i-1] for i in refs)
        ev=clean(row['event']);local=clean(blocks[row['anchor']-1]);proof=clean(ctx)
        if rel==base.C:
            if not senior_ok(a,ctx,ev) or not re.search(senior_cues,proof+' '+ev):continue
            if re.search(r'(dự kiến|đề xuất|có thể|chưa).{0,30}(?:triệu tập|gọi lên)',ev):continue
            src=catalog.person(name,ctx,a);dst='nt-vn'
        elif rel==base.D:
            if not re.search(r'vff|lđbđ|liên đoàn bóng đá',clean(text)):continue
            if not re.search(r'treo giò|kỷ luật|đình chỉ|phạt|cấm thi đấu',proof):continue
            if re.search(r'cấm (?:làm nhiệm vụ|chỉ đạo)|đình chỉ làm nhiệm vụ.{0,20}(?:hlv|trợ lý)|kỷ luật nội bộ',ev):continue
            if re.search(STAFF+r'\s+'+re.escape(clean(name))+r'(?!\w)',proof):continue
            src='o-vff';dst=catalog.person(name,ctx,a)
            if re.search(r'giải u[\s.]*19',proof) and dst in catalog.nodes and (m:=re.search(r'sinh (\d{4})',catalog.nodes[dst]['canonical_name'])) and int(a['date'][:4])-int(m[1])>20:continue
        else:
            dst=catalog.club(row['club'],ctx,a)
            if not dst:continue
            if not anchored(row['club'],ctx) and not any(re.search(r'\b'+re.escape(f)+r'\b',norm(ctx)) for f in catalog.clubforms[dst] if len(f)>=3):continue
            if rel==base.K:
                if re.search(RENEW+'|cho mượn|được mượn',ev) or re.search(RENEW,local) and not re.search(r'cựu|trước khi',local):continue
                if re.search(STAFF+r'\s+'+re.escape(clean(name))+r'(?!\w)',proof):continue
                if re.search(r'dự kiến|đặt cọc|sơ bộ|đàm phán|thử việc',ev) and not re.search(r'đã ký|hoàn tất|chính thức ký',ev):continue
                src=catalog.person(name,ctx,a,dst)
            else:
                if not re.search(r'tài trợ|đồng hành',proof):continue
                if re.search(r'tài trợ (?:bản |cho bản )?hợp đồng|đề xuất tài trợ|đang đàm phán|muốn tài trợ',ev):continue
                if re.search(r'chưa (?:có|ký) hợp đồng.{0,40}tài trợ',local):continue
                src=catalog.actor_id(name,'Organization',a,ctx)
        if not src or not dst or src==dst:continue
        name_src='VFF' if rel==base.D else name;name_dst=name if rel==base.D else 'Đội tuyển Việt Nam' if rel==base.C else row['club']
        if any((e['src_id'],e['rel'],e['dst_id'])==(src,rel,dst) and set(e['refs'])&set(refs) and (row in extra or clean(e['event'])==ev) for e in accepted):continue
        accepted.append(dict(src_id=src,dst_id=dst,src=name_src,dst=name_dst,rel=rel,refs=refs,anchor=row['anchor'],event=row['event'],when=row['when'] if clean(row['when']) in proof else ''))
    return accepted
def run(lot,graph,cache,dest):
    cat=Resolver(graph);dest.mkdir(exist_ok=True)
    for a in map(json.loads,lot.read_text().splitlines()):
        raw=cache/(a['article_id']+'.json')
        if not raw.exists():raise ValueError('Missing cached proposal '+a['article_id'])
        doc=json.loads(raw.read_text())
        p=dest/raw.name;result=dict(edges=review(a,doc['draft'],cat),model=doc['model'],input_sha=a['text_sha256'],proposal_sha=base.sha(raw.read_bytes()),code_sha=base.sha(Path(__file__).read_bytes()))
        p.write_text(base.packed(result))
if __name__=='__main__':
    cli=argparse.ArgumentParser(description=__doc__)
    for arg in ['lot','graph','cache','out']:cli.add_argument(arg,type=Path)
    a=cli.parse_args();run(a.lot,a.graph,a.cache,a.out)
