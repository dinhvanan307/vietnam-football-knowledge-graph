"""Recalculate published contract scores from adjudicated events in the three press batches."""

import csv
import json
from collections import Counter
from pathlib import Path


DATA = Path(__file__).resolve().parents[2] / "results" / "contracts"
SYSTEMS = {
    "lo_1": {"baseline": "luat_cu", "reader": "K1_doc_tung_cau"},
    "lo_2": {"baseline": "cu", "rules_v1": "moi"},
    "lo_3": {"rules_v1": "cu", "rules_v2": "moi", "reader": "K1_doc_tung_cau"},
}


def rows(filename):
    with (DATA / filename).open(encoding="utf-8", newline="") as stream:
        return list(csv.DictReader(stream, delimiter="\t"))


def metrics(counts):
    tp, fp, fn = (counts[outcome] for outcome in ("TP", "FP", "FN"))

    def ratio(a, b):
        return a / b if b else None

    return dict(
        TP=tp,
        FP=fp,
        FN=fn,
        precision=ratio(tp, tp + fp),
        recall=ratio(tp, tp + fn),
        F1=ratio(2 * tp, 2 * tp + fp + fn),
    )


def check(expected, actual, label):
    for field, value in actual.items():
        if expected[field] != value:
            raise ValueError(f"{label}.{field}: {value} differs from {expected[field]}")


def main():
    expected = json.loads((DATA / "metrics.json").read_text(encoding="utf-8"))
    articles = rows("articles.tsv")
    urls = {
        (a["lot"], a["article_id"]): a["url"] for a in articles if a["status"] == "cham"
    }
    if len(set(urls.values())) != len(urls):
        raise ValueError("Duplicate URL among retained articles")
    reviews = rows("reviews.tsv")
    events = rows("events.tsv")
    if any(
        (r["lot"], r["article_id"]) not in urls
        or r["system"] not in SYSTEMS[r["lot"]]
        or r["outcome"] not in ("TP", "FP", "FN")
        for r in reviews
    ):
        raise ValueError("Unexpected event in reviews.tsv")
    if any(event["url"] not in set(urls.values()) for event in events):
        raise ValueError("Reference event lacks a retained source")
    pooled = Counter()
    reader_articles = 0
    for lot, systems in SYSTEMS.items():
        total = sum(batch == lot for batch, _ in urls)
        for name, original in systems.items():
            group = [r for r in reviews if (r["lot"], r["system"]) == (lot, name)]
            counts = Counter(r["outcome"] for r in group)
            gold = Counter(
                urls[lot, r["article_id"]] for r in group if r["outcome"] != "FP"
            )
            if gold != Counter(e["url"] for e in events if e["lot"] == lot):
                raise ValueError(f"Reference event counts differ for {lot}/{name}")
            active = {r["article_id"] for r in group if r["outcome"] != "FN"}
            result = dict(
                articles=total,
                articles_predicted=len(active),
                articles_with_gold=len(gold),
                **metrics(counts),
            )
            check(expected["batches"][lot][original], result, f"{lot}/{name}")
            if name == "reader":
                pooled.update(counts)
                reader_articles += total
            print(
                f"{lot:5} {name:8} {counts['TP']:2} TP  {counts['FP']:2} FP  {counts['FN']:2} FN"
            )
    check(
        expected,
        {"scored_articles": len(urls), "reader_articles": reader_articles},
        "coverage",
    )
    check(expected["reader_micro"], metrics(pooled), "reader_micro")
    direct = {"NEU_RO_DA_KY", "CLB_CONG_BO_HOP_DONG"}
    strict_ref = Counter(
        (e["url"], e["player"], e["club_id"])
        for e in events
        if "reader" in SYSTEMS[e["lot"]] and e["evidence_type"] in direct
    )
    strict_pred = Counter(
        (urls[r["lot"], r["article_id"]], r["player"], r["club_id"])
        for r in reviews
        if r["system"] == "reader" and r["outcome"] != "FN" and r["explicit"] == "1"
    )
    correct = (strict_ref & strict_pred).total()
    check(
        expected["strict_reader_posthoc"],
        metrics(
            {
                "TP": correct,
                "FP": strict_pred.total() - correct,
                "FN": strict_ref.total() - correct,
            }
        ),
        "strict_reader",
    )
    if Counter(e["evidence_type"] for e in events) != expected["evidence_counts"]:
        raise ValueError("Unexpected evidence categories")
    print(f"{len(urls)} bài, {len(events)} thương vụ. Gộp lượt đọc: {dict(pooled)}.")


if __name__ == "__main__":
    main()
