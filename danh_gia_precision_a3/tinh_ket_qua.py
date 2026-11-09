"""Tính precision từ nhãn đã đọc và ràng buộc một phía cho quần thể hữu hạn."""
import json
import math
import random
from collections import Counter
from chuan_bi import A3, HERE, SEED, N_SAMPLE, digest, lines, tsv, put_tsv, verify_inputs
from tinh_precision import hyper_tail, srs_lower_bound


def main():
    verify_inputs()
    frame = json.loads((HERE/"khung_mau.json").read_text())
    sample = (HERE/"mau_khoa.txt").read_text().splitlines()
    excluded = {r["fact_id"] for r in tsv(HERE/"canh_loai_khoi_khung.tsv")}
    population = {r["fact_id"] for r in tsv(A3/"facts.csv", ",")}
    eligible = sorted(population - excluded)
    assert frame["N"] == len(population) and frame["eligible"] == len(eligible)
    assert digest(("\n".join(eligible)+"\n").encode()) == frame["eligible_sha256"]
    assert digest((HERE/"mau_khoa.txt").read_bytes()) == frame["sample_sha256"]
    assert frame["seed"] == SEED and random.Random(SEED).sample(eligible, N_SAMPLE) == sample
    labels = tsv(HERE/"phieu_cham.tsv")
    packets = lines(HERE/"ho_so_nguon.jsonl")
    assert len(labels) == len(packets) == len(set(sample)) == N_SAMPLE
    detail = []
    proofs = set()
    docs = set()
    for packet, fid, label in zip(packets, sample, labels, strict=True):
        assert packet["fact_id"] == fid == label["fact_id"] and packet["no"] == label["ma"]
        assert label["nhan_codex"] in {"DUNG", "SAI", "CHUA_RO"} and label["ly_do"].strip()
        ev = packet["support"]
        proofs.update(e["evidence_id"] for e in ev)
        docs.update(e["article_id"] for e in ev)
        detail.append(dict(ma=packet["no"], fact_id=fid, chu_the=packet["src"], src_id=packet["src_id"],
                           quan_he=packet["relation_type"], doi_tuong=packet["dst"], dst_id=packet["dst_id"],
                           thoi_gian=packet["period"], khoa_su_kien=packet["event_key"],
                           nhan_codex=label["nhan_codex"], ly_do=label["ly_do"],
                           url_nguon=ev[0]["url"], ngu_canh=ev[0]["context"], bang_chung=ev[0]["quote"],
                           so_bang_chung=len(ev), cac_url_nguon=" ".join(sorted({e["url"] for e in ev})),
                           nguon_bo_sung=label["nguon_bo_sung"]))
    put_tsv(HERE/"doi_chieu_200_canh.tsv",detail)
    put_tsv(HERE/"canh_sai_va_chua_ro.tsv",[r for r in detail if r["nhan_codex"]!="DUNG"])
    counts = Counter(r["nhan_codex"] for r in detail)
    N, M = frame["N"], frame["eligible"]
    n, k = len(sample), len(sample)-counts["DUNG"]
    low = srs_lower_bound(M,n,k)
    lower_true = round(M*low)
    upper_errors = M-lower_true
    denom = math.comb(M,n)
    assert 20*hyper_tail(M,upper_errors,n,k)>denom
    assert 20*hyper_tail(M,upper_errors+1,n,k)<=denom
    null_errors = (M+9)//10
    rels = {}
    for row in detail:
        rels.setdefault(row["quan_he"], Counter())[row["nhan_codex"]] += 1
    results = dict(evaluator="Codex", human_double_review=False, population=N, eligible=M, excluded=N-M,
                   sample_size=n, labels=counts, sample_precision=counts["DUNG"]/n,
                   exact_95_lower_eligible=low, minimum_correct_eligible_95=lower_true,
                   upper_errors_eligible_95=upper_errors, one_sided_p_at_90=hyper_tail(M,null_errors,n,k)/denom,
                   exact_95_worst_case_lower_all=lower_true/N,
                   additional_excluded_correct_needed_for_90=(9*N)//10+1-lower_true,
                   support_ids=len(proofs), source_spans=len({(e["article_id"],e["start"],e["end"]) for p in packets for e in p["support"]}),
                   article_versions=len(docs), counts_by_relation=rels, counts_by_method=Counter(p["method"] for p in packets),
                   seed=SEED, sample_sha256=frame["sample_sha256"],
                   original_graph_sha256=frame["snapshot_facts_sha256"])
    (HERE/"ket_qua.json").write_text(json.dumps(results, ensure_ascii=False, indent=2)+"\n")
    print(json.dumps(results, ensure_ascii=False))


if __name__ == "__main__":
    main()
