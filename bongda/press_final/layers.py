"""Version A10: extend a frozen press graph, then export disjoint actor/context views and independent provenance."""
import argparse,csv,json,math,os,re,shutil,tempfile
from pathlib import Path
from collections import Counter,defaultdict
from itertools import combinations
from lxml import html
from bongda.core.ban_giao import table,jlines,idx,sha
from bongda.press.build import write_csv,write_lines
from bongda.press_final.network import Graph,token,tidy
from bongda.press_final.clubs import key
from bongda.press_final.verify import verify_snapshot
from bongda.press_final.compact import export
from bongda.press_final.release import LABELS
from bongda.press.visual import render
ACTORS={"Person","Club","NationalTeam","Organization"}
COACH="GHI_NHAN_HLV_TRUONG_MUA"
GROUPS={
 "hợp đồng":("KY_HOP_DONG_VOI","THANH_LY_VOI","GIA_HAN_VOI","DUOC_CHO_MUON_DEN"),
 "chuyển nhượng":("CHUYEN_DEN_CLB","CHUYEN_DI_TU"),"triệu tập":("DUOC_TRIEU_TAP_VAO",),"kỷ luật":("KY_LUAT",),"tài trợ":("TAI_TRO",),
 "huấn luyện và quản lý":("DAN_DAT",COACH,"CHU_TICH_CUA","TO_CHUC_GIAI"),"nhân sự CLB":("THI_DAU_CHO","CO_TEN_TRONG_DOI_HINH_MUA","DUOC_BAO_GHI_NHAN_THUOC_CLB","CO_TEN_TRONG_DANH_SACH_CLB"),
 "trận, giải và sân":("GOP_MAT_TRONG_TRAN","THUOC_GIAI_DAU","THAM_GIA_GIAI","SU_DUNG_SAN_NHA"),
 "đội hình trận":("DA_CHINH_TRONG_TRAN","DANG_KY_DU_BI_TRONG_TRAN","VAO_SAN_THAY_NGUOI_TRONG_TRAN")}
FAMILIES={r:k for k,vs in GROUPS.items() for r in vs}
SCOPE_REVIEW={ # spellings and homonyms encountered in the frozen source texts
  "Kiatisak Semanuang":"Kiatisuk Senamuang"}
def jwrite(file,data):file.write_text(json.dumps(data,ensure_ascii=False,indent=2,sort_keys=True)+"\n")
def tsv(file,data,fields):write_csv(file,data,fields,"\t")
def graph_from(s):
 class Release(Graph):
  def __init__(self):
   self.version="A10";self.logs=Counter();self.conflicts=set()
   self.nodes=idx(table(s/"entities.csv"),"entity_id");self.facts=idx(table(s/"facts.csv"),"fact_id");self.docs=idx(jlines(s/"articles.jsonl"),"article_id");self.emap=idx(jlines(s/"evidence.jsonl"),"evidence_id");self.attrs=idx(jlines(s/"event_attributes.jsonl"),"fact_id")
   self.raw={k:s/"raw"/v["raw_sha256"] for k,v in self.docs.items()}
   self.raw.update({a["public_page_sha"]:s/"raw"/a["public_page_sha"] for a in self.docs.values() if a.get("public_page_sha")})
 return Release()
def build(parent,root):
 s=parent/"snapshot";new=root/"snapshot"
 if new.exists():raise FileExistsError(new)
 verify_snapshot(s);g=graph_from(s);base=set(g.facts);groups=defaultdict(set);held=[]
 for f in g.facts.values():
  if f["relation_type"]=="CO_TEN_TRONG_DOI_HINH_MUA":groups[f["article_id"]].add((f["dst_id"],f["period"]))
 for aid,group in sorted(groups.items()):
  if len(group)!=1:raise ValueError("Multiple teams in roster profile")
  club,season=next(iter(group));a=g.docs[aid]
  heads=[l for l in a["clean_text"].splitlines() if re.fullmatch(r"HLV(?: trưởng| của [^:]{1,32}| CLB [^:]{1,32}| B\.Bình Dương)?: [^:\d]{4,54}",l)]
  names={SCOPE_REVIEW.get(l.split(": ",1)[1],l.split(": ",1)[1]) for l in heads}
  if len(names)!=1:
   held.append((aid,club,season,"Thiếu một tên HLV nhất quán"));continue
  nm=next(iter(names));same=[n for n in g.nodes.values() if key(n["canonical_name"])==key(nm)]
  if any("Coach" not in x["role"].split("|") for x in same):
   held.append((aid,club,season,"Trùng tên với cầu thủ: "+nm));continue
  ident=same[0]["entity_id"] if len(same)==1 else None
  if len(same)>1:held.append((aid,club,season,"Nhiều mã người: "+nm));continue
  if not ident:ident=g.node("p10_hlv_"+token(nm),nm,"Person","Coach")
  fid=g.link(ident,COACH,club,season,season,aid,heads[0],"nlp_muc_hlv_truong",dict(observation="Vai trò khi báo giới thiệu mùa; không suy ra thời hạn hợp đồng."))
 m=json.loads((root/"nguon_moi/source.json").read_text());path=root/"nguon_moi"/m["sha"];raw=path.read_bytes();assert sha(raw)==m["sha"]
 d=html.fromstring(raw,parser=html.HTMLParser(encoding="utf-8"));title=tidy(d.xpath("string(//h1)"))
 pub=d.xpath('//meta[@property="article:published_time" or @itemprop="datePublished"]/@content')[0]
 lines=[tidy(x.text_content()) for x in d.xpath('//article//p')];quote=next(x for x in lines if "VPF - đơn vị tổ chức V-League, hạng Nhất và Cup Quốc gia)" in x).split(")")[0]+")"
 aid=g.document(m["url"],title,[title,*lines],path,m["retrieved"],pub,"editorial","VnExpress")
 vpf=g.node("o10-vpf","Công ty Cổ phần Bóng đá chuyên nghiệp Việt Nam (VPF)","Organization","Organizer")
 for c in ["g-vl1","g9-vl2","g9-cup"]:g.link(vpf,"TO_CHUC_GIAI",c,"2023","2023",aid,quote,"nlp_to_chuc_giai_trong_cau")
 with tempfile.TemporaryDirectory(dir=root) as t:
  dest=Path(t)/"snapshot";g.dump(dest);verify_snapshot(dest);dest.rename(new)
 qa=root/"kiem_tra";qa.mkdir(exist_ok=True)
 tsv(qa/"cho_dinh_danh.tsv",[dict(zip(["article_id","club","season","reason"],r)) for r in held],["article_id","club","season","reason"])
 rows=[]
 for k in sorted(g.facts.keys()-base):
  f=g.facts[k];a=g.docs[f["article_id"]];rows.append(dict(fact_id=k,source=g.nodes[f["src_id"]]["canonical_name"],relation=f["relation_type"],target=g.nodes[f["dst_id"]]["canonical_name"],period=f["period"],title=a["title"],quote=f["quote"],url=f["article_url"]))
 tsv(qa/"canh_moi.tsv",rows,list(rows[0]))
 # All unchanged IDs carry exactly their original properties and evidence.
 assert all(g.facts[f["fact_id"]]==f for f in table(s/"facts.csv"))
 layers(root)
def layers(root):
 s=root/"snapshot";integrity=verify_snapshot(s);n=idx(table(s/"entities.csv"),"entity_id");f=idx(table(s/"facts.csv"),"fact_id");docs=idx(jlines(s/"articles.jsonl"),"article_id");ev=jlines(s/"evidence.jsonl");meta=idx(jlines(s/"event_attributes.jsonl"),"fact_id")
 p=root/"phan_lop";p.mkdir(exist_ok=True);support=defaultdict(set);by=defaultdict(list);refs=[]
 for e in ev:
  a=docs[e["article_id"]];mode=a.get("source_format","editorial");support[e["fact_id"]].add(mode)
  refs.append(dict(fact_id=e["fact_id"],evidence_id=e["evidence_id"],article_id=e["article_id"],url=a["canonical_url"],format=mode,publication=a["published_at"],start=e["start"],end=e["end"]))
 tsv(p/"bang_chung.tsv",refs,list(refs[0]));groups=defaultdict(dict);nodebands=defaultdict(set);edgegroups=defaultdict(set)
 for k,x in f.items():
  a,b=x["src_id"],x["dst_id"];rel=x["relation_type"]
  band="xa_hoi" if n[a]["type"] in ACTORS and n[b]["type"] in ACTORS else "boi_canh"
  nodebands[band].update([a,b]);edgegroups[band].add(rel)
  es=support[k];src="ca_hai" if len(es)==2 else ("bai_viet" if "editorial" in es else "bang_bao")
  by[band].append(dict(fact_id=k,src_id=a,source=n[a]["canonical_name"],relation=rel,dst_id=b,target=n[b]["canonical_name"],period=x["period"],business=FAMILIES[rel],support=src,primary_url=x["article_url"]))
  if rel=="DA_CHINH_TRONG_TRAN" and meta.get(k,{}).get("club_id"):groups[b,meta[k]["club_id"]][a]=k
 for band,rows in by.items():
  tsv(p/(band+".tsv"),rows,list(rows[0]));tsv(p/("nut_"+band+".tsv"),[n[i] for i in sorted(nodebands[band])],list(next(iter(n.values()))))
 both_sides=defaultdict(set)
 for (m,c),ps in groups.items():
  for a in ps:both_sides[m,a].add(c)
 rows=[];pairs=defaultdict(set)
 for (m,c),ps in sorted(groups.items()):
  if len(ps)>11:continue
  for a,b in combinations(sorted(w for w in ps if len(both_sides[m,w])==1),2):
   pairs[a,b].add(m);rows.append(dict(player1=a,player2=b,club=c,match=m,fact1=ps[a],fact2=ps[b]))
 tsv(p/"dong_doi_chung_cu.tsv",rows,list(rows[0]));pitems=[dict(player1=a,player2=b,name1=n[a]["canonical_name"],name2=n[b]["canonical_name"],matches=len(ms)) for (a,b),ms in sorted(pairs.items(),key=lambda t:(-len(t[1]),t[0]))];tsv(p/"dong_doi.tsv",pitems,list(pitems[0]))
 actors={i for i,x in n.items() if x["type"] in ACTORS}
 stats=dict(version="A10",graph=integrity,actor_inventory=len(actors),actor_only_context=len(actors-nodebands["xa_hoi"]),both_layers_nodes=len(nodebands["xa_hoi"]&nodebands["boi_canh"]),roles=dict(Counter(role for x in n.values() for role in x["role"].split("|"))),layers={k:dict(nodes=len(nodebands[k]),edges=len(v),types=len(edgegroups[k]),source_support=dict(Counter(x["support"] for x in v)),families=dict(Counter(x["business"] for x in v))) for k,v in by.items()},projection_pairs=len(pitems),projection_witnesses=len(rows),projection_people=len({i for pair in pairs for i in pair}),unique_urls=len({r["url"] for r in refs}))
 assert set.union(*nodebands.values())==set(n) and len(f)==sum(len(v) for v in by.values())
 jwrite(root/"thong_ke_lop.json",stats)
 export(s,root/"graph")
if __name__=="__main__":
 p=argparse.ArgumentParser(description=__doc__);p.add_argument("parent",type=Path);p.add_argument("output",type=Path);a=p.parse_args();build(a.parent,a.output)

