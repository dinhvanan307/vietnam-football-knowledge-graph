"""Khóa mẫu giữ lại trước khi chấm và trích ngữ cảnh từ đúng phiên bản nguồn."""
import hashlib
import json
import random
from collections import Counter, defaultdict
import unicodedata

from bongda.paths import WORK, evaluation_dir
from bongda.evaluate.a2.chuan_bi_doi_chieu import tsv, put_tsv, lines, digest

HERE = evaluation_dir("a3")
A2 = WORK / "a2_final"
A3 = WORK / "a3_final"
SEED = 2026110803
N_SAMPLE = 200


def span(e):
    return e["article_id"], e["start"], e["end"]


def verify_inputs():
    for root in [A2, A3]:
        for name, h in json.loads((root / "checksums.json").read_text()).items():
            if digest((root / name).read_bytes()) != h:
                raise ValueError(name)


def main():
    HERE.mkdir(parents=True, exist_ok=True)
    verify_inputs()
    a3 = {a["article_id"]: a for a in lines(A3 / "articles.jsonl")}
    by_url = {a["canonical_url"]: a["article_id"] for a in a3.values()}
    facts = {f["fact_id"]: f for f in tsv(A3 / "facts.csv", ",")}
    f2 = {f["fact_id"]: f for f in tsv(A2 / "facts.csv", ",")}
    old_review = {r["fact_id"] for r in lines(evaluation_dir("a2") / "hoso_doi_chieu.jsonl")}
    pilot = {r["fact_id"] for r in tsv(WORK / "pilot_01/facts.csv", ",")}
    sheet = {r["fact_id"] for r in tsv(A3 / "mau_ra_soat.tsv")}
    changed = set()
    for d in lines(A3 / "doi_chieu_canh.jsonl"):
        changed.update([d["a2_fact_id"], *d["a3_fact_ids"], *d["related_a2_ids"]])
    bans = defaultdict(set)
    for ids, reason in [(old_review, "mau_A2"), (pilot, "pilot_da_duyet"), (sheet, "phieu_co_san_A3"), (changed, "doi_chieu_sua_A3")]:
        for fid in ids & facts.keys():
            bans[fid].add(reason)
    e2, e3 = lines(A2 / "evidence.jsonl"), lines(A3 / "evidence.jsonl")
    used = {span(e) for e in e2 if e["fact_id"] in old_review | pilot}
    for d in lines(A3 / "doi_chieu_bang_chung.jsonl"):
        used.add((by_url[d["article_url"]], d["start"], d["end"]))
    # Nếu cùng một biên bản được chép ở trang giải và trang kết quả, khóa cả hai.
    match_keys = set()
    for evidence, population in [(e2, f2), (e3, facts)]:
        for e in evidence:
            f = population[e["fact_id"]]
            if span(e) in used and f["relation_type"] == "DOI_DAU":
                match_keys.add(f["event_key"])
    blocked_matches = {span(e) for e in e3 if facts[e["fact_id"]]["relation_type"] == "DOI_DAU"
                       and facts[e["fact_id"]]["event_key"] in match_keys}
    rights = defaultdict(list)
    for e in e3:
        fid = e["fact_id"]
        rights[fid].append(e)
        if span(e) in used or span(e) in blocked_matches:
            bans[fid].add("trung_bang_chung_hoac_tran")
        if a3[e["article_id"]]["revid"] == "25288199" and facts[fid]["method"] == "wiki_roster_row":
            bans[fid].add("doi_chung_mua_Nam_Dinh")
    eligible = sorted(facts.keys() - bans.keys())
    sample = random.Random(SEED).sample(eligible, N_SAMPLE)
    ids_text = "".join(f"{x}\n" for x in sample)
    fixed = HERE / "mau_khoa.txt"
    if fixed.exists() and fixed.read_text() != ids_text:
        raise ValueError("Mẫu đã khóa thay đổi.")
    fixed.write_text(ids_text)
    put_tsv(HERE / "canh_loai_khoi_khung.tsv",
            [dict(fact_id=k, ly_do="|".join(sorted(bans[k]))) for k in sorted(bans)])
    population = dict(N=len(facts), eligible=len(eligible), excluded=len(bans), n=len(sample), seed=SEED,
                      sample_sha256=digest(ids_text.encode()), eligible_sha256=digest(("\n".join(eligible)+"\n").encode()),
                      snapshot_facts_sha256=digest((A3/"facts.csv").read_bytes()), threshold=0.90,
                      rule="DUNG/n; SAI và CHUA_RO đều tính 0; một phía 95%, siêu bội không hoàn lại",
                      old_reviewed=len(old_review), old_pilot=len(pilot), existing_sheet=len(sheet),
                      checked_match_keys=len(match_keys), blocked_counts={k:sum(k in v for v in bans.values()) for k in sorted(set.union(*bans.values()))},
                      eligible_by_relation=Counter(facts[k]["relation_type"] for k in eligible))
    (HERE / "khung_mau.json").write_text(json.dumps(population, ensure_ascii=False, indent=2)+"\n")
    nodes = {r["entity_id"]: r["canonical_name"] for r in tsv(A3 / "entities.csv", ",")}
    attrs = {r["fact_id"]: r for r in lines(A3 / "event_attributes.jsonl")}
    cache = {}
    packets = []
    for i, fid in enumerate(sample, 1):
        f = facts[fid]
        support = []
        for e in sorted(rights[fid], key=lambda r:(r["evidence_id"] != f["evidence_id"], r["evidence_id"])):
            aid = e["article_id"]
            a = a3[aid]
            if aid not in cache:
                data = (A3/"raw"/a["raw_sha256"]).read_bytes()
                assert digest(data) == a["raw_sha256"] and a["source_kind"] == "wiki"
                page = next(p for p in json.loads(data)["query"]["pages"] if str(p["pageid"])==a["pageid"])
                rev = next(r for r in page["revisions"] if str(r["revid"])==a["revid"])
                cache[aid] = unicodedata.normalize("NFC", rev["slots"]["main"]["content"])
                assert cache[aid] == a["clean_text"]
            raw = cache[aid]
            assert raw[e["start"]:e["end"]]==e["quote"]
            context = raw[e["context_start"]:e["context_end"]] if "context_start" in e else ""
            support.append(dict(**e, title=a["title"], revid=a["revid"], url=a["canonical_url"], context=context))
        packets.append(dict(no=f"H{i:03}", fact_id=fid, src=nodes[f["src_id"]], dst=nodes[f["dst_id"]],
                            src_id=f["src_id"], dst_id=f["dst_id"], event_key=f["event_key"], period=f["period"],
                            relation_type=f["relation_type"], method=f["method"], attributes=attrs.get(fid,{}), support=support))
    (HERE/"ho_so_nguon.jsonl").write_text("".join(json.dumps(r,ensure_ascii=False)+"\n" for r in packets))
    print(json.dumps(population, ensure_ascii=False))


if __name__ == "__main__":
    main()
