"""Ước lượng precision hai tầng, hạ cận bằng siêu bội và Bonferroni."""
import json
from collections import Counter

from chuan_bi_ngoai import A3, FIRST, HERE, SEED, SIZE, digest, lines, lock_sample, put_tsv, tsv
from thong_ke import combine, stratum


def main():
    facts, ids = lock_sample()
    old = tsv(FIRST/"doi_chieu_200_canh.tsv")
    old_labels = tsv(FIRST/"phieu_cham.tsv")
    held = (FIRST/"mau_khoa.txt").read_text().splitlines()
    assert [r["fact_id"] for r in old] == held == [r["fact_id"] for r in old_labels]
    assert all(r["nhan_codex"] == label["nhan_codex"] for r,label in zip(old,old_labels,strict=True))
    labels = tsv(HERE/"phieu_cham_ngoai.tsv")
    packets = lines(HERE/"ho_so_ngoai.jsonl")
    assert len(ids)==len(labels)==len(packets)==SIZE
    new = []
    for p, label, fid in zip(packets,labels,ids,strict=True):
        assert p["fact_id"] == label["fact_id"] == fid and p["no"] == label["ma"]
        assert label["nhan_codex"] in {"DUNG","SAI","CHUA_RO"} and label["ly_do"].strip()
        ev = p["support"]
        new.append(dict(ma=p["no"], fact_id=fid, chu_the=p["src"], src_id=p["src_id"],
                        quan_he=p["relation_type"], doi_tuong=p["dst"], dst_id=p["dst_id"], thoi_gian=p["period"],
                        khoa_su_kien=p["event_key"], nhan_codex=label["nhan_codex"],ly_do=label["ly_do"],
                        url_nguon=ev[0]["url"],ngu_canh=ev[0]["context"],bang_chung=ev[0]["quote"],
                        so_bang_chung=len(ev),cac_url_nguon=" ".join(sorted({e["url"] for e in ev})),
                        nguon_bo_sung=label["nguon_bo_sung"]))
    put_tsv(HERE/"doi_chieu_100_canh.tsv",new)
    combined = [dict(tang=name, **r) for name,rows in [("trong_khung",old),("ngoai_khung",new)] for r in rows]
    assert len(combined) == len({r["fact_id"] for r in combined}) == 300
    put_tsv(HERE/"doi_chieu_300_canh.tsv",combined)
    put_tsv(HERE/"sai_va_chua_ro.tsv",[r for r in combined if r["nhan_codex"]!="DUNG"])
    reasons = {r["fact_id"]:r["ly_do"].split("|") for r in tsv(FIRST/"canh_loai_khoi_khung.tsv")}
    inner = stratum(len(facts)-len(reasons),Counter(r["nhan_codex"] for r in old))
    outer = stratum(len(reasons),Counter(r["nhan_codex"] for r in new))
    overall = combine(inner,outer)
    overall["min_correct_95"] = int(overall["min_correct_95"])
    stricter = Counter(outer["labels"])
    assert new[8]["ma"]=="N009" and new[8]["nhan_codex"]=="DUNG"
    stricter.subtract({"DUNG":1})
    stricter.update({"SAI":1})
    sensitivity = combine(inner,stratum(len(reasons),stricter))
    other = dict(seed=SEED, sample_sha256=digest((HERE/"mau_khoa_ngoai.txt").read_bytes()),
                 frame_sha256=digest((FIRST/"canh_loai_khoi_khung.tsv").read_bytes()),
                 graph_facts_sha256=digest((A3/"facts.csv").read_bytes()),
                 old_sample_sha256=digest((FIRST/"mau_khoa.txt").read_bytes()),
                 support_evidence_count=sum(len(p["support"]) for p in packets),
                 distinct_spans=len({(e["article_id"],e["start"],e["end"]) for p in packets for e in p["support"]}),
                 source_versions=len({e["article_id"] for p in packets for e in p["support"]}),
                 outer_by_relation=Counter(p["relation_type"] for p in packets),
                 outer_by_method=Counter(p["method"] for p in packets),
                 outer_by_prior_status=Counter(reason for fid in ids for reason in reasons[fid]))
    result=dict(inside=inner,outside=outer, combined=overall,counts=Counter(r["nhan_codex"] for r in combined),
                n009_stricter=dict(weighted_precision=sensitivity["weighted_precision"],lower_95=sensitivity["lower_95"]),
                audit=other)
    (HERE/"ket_qua_toan_bo.json").write_text(json.dumps(result,ensure_ascii=False,indent=2)+"\n")
    print(json.dumps(result,ensure_ascii=False))


if __name__ == "__main__":
    main()
