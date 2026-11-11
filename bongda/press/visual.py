"""Render the offline press evidence explorer from a verified snapshot."""
import argparse
import json
from pathlib import Path

from bongda.core.ban_giao import table, jlines
from bongda.press.build import verify_news

LABELS = {
    "CHU_TICH_CUA": "là chủ tịch của", "CO_TEN_TRONG_DOI_HINH_MUA": "có tên trong đội hình mùa",
    "DAN_DAT": "dẫn dắt", "DUOC_CHO_MUON_DEN": "được cho mượn đến",
    "DUOC_TRIEU_TAP_VAO": "được triệu tập vào", "GIA_HAN_VOI": "gia hạn với",
    "KY_HOP_DONG_VOI": "ký hợp đồng với", "KY_LUAT": "kỷ luật",
    "SU_DUNG_SAN_NHA": "sử dụng sân nhà", "TAI_TRO": "tài trợ", "THAM_GIA_GIAI": "tham gia giải",
    "THANH_LY_VOI": "thanh lý với", "THI_DAU_CHO": "thi đấu cho",
}
KINDS = dict(Person="Người", Club="CLB", NationalTeam="Đội tuyển", Organization="Tổ chức",
             Competition="Giải đấu", Stadium="Sân vận động")

def render(snapshot, output, *, verify=verify_news, version="A8", extra=None):
    verify(snapshot)
    entities = list(table(snapshot / "entities.csv"))
    nodes = [[n["entity_id"], n["canonical_name"], ("Trận đấu" if n["type"]=="Match" else KINDS[n["type"]])] for n in entities]
    node_index = {n[0]: i for i,n in enumerate(nodes)}
    articles = list(jlines(snapshot / "articles.jsonl"))
    sources = [[a["source"], a["title"], a["canonical_url"]] for a in articles]
    article_index = {a["article_id"]: i for i,a in enumerate(articles)}
    quotes = {}
    edges = []
    for r in table(snapshot / "facts.csv"):
        q = quotes.setdefault(r["quote"], len(quotes))
        edges.append([node_index[r["src_id"]], node_index[r["dst_id"]], r["relation_type"],
                      r["period"], article_index[r["article_id"]], q, r["fact_id"]])
    all_labels={**LABELS,**(extra or {})}
    labels = {r: all_labels[r] for r in sorted({e[2] for e in edges})}
    graph = dict(nodes=nodes,edges=edges,sources=sources,quotes=list(quotes),labels=labels)
    template = (Path(__file__).parents[1] / "a7/ban_do.template.html").read_text()
    template = template.replace("ĐỀ TÀI 22 · A7","ĐỀ TÀI 22 · BÁO CHÍ TRONG NƯỚC · A8")
    template = template.replace("Sổ quan hệ A7","Sổ quan hệ báo chí A8")
    template = template.replace("Mỗi mũi tên là một sự kiện có nguồn.","Mỗi mũi tên có bằng chứng từ báo chí trong nước.")
    template = template.replace("Mở nguồn gốc ↗","Đọc bài báo ↗")
    template=template.replace("A8",version)
    output.write_text(template.replace("DATA_HERE", json.dumps(graph,ensure_ascii=False,separators=(",",":")).replace("<",r"\u003c")))

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("snapshot",type=Path)
    parser.add_argument("output",type=Path)
    args = parser.parse_args()
    render(args.snapshot,args.output)
