"""Recompute A7 acceptance metrics from the published evidence table."""
import csv
import json
from collections import Counter, defaultdict

from bongda.paths import RESULTS
from bongda.a7.score import metrics

DIRECTORY = RESULTS / "a7"


def read_json(name):
    return json.loads((DIRECTORY / name).read_bytes())


def check(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    reference = read_json("nghiem_thu.json")
    counts = defaultdict(Counter)
    articles = defaultdict(set)
    with (DIRECTORY / "doi_chieu.tsv").open(encoding="utf-8", newline="") as stream:
        for row in csv.DictReader(stream, delimiter="\t"):
            relation, result = row["quan_he"], row["ket_qua"]
            check(result in {"TP", "FP", "FN"}, "Nhãn không hợp lệ")
            check(row["lo"] in reference["per_type"][relation]["assessed_lots"], "Nhầm lô đánh giá")
            check(row["url"].startswith("https://") and row["doan"], "Thiếu nguồn đối chiếu")
            counts[relation][result] += 1
            if result in {"TP", "FP"}:
                articles[relation].add(row["bai"])
    for relation, expected in reference["per_type"].items():
        c = counts[relation]
        observed = metrics(c["TP"], c["FP"], c["FN"])
        check(all(expected[k] == v for k, v in observed.items()), relation)
        threshold = (observed["precision"] > 0.90 and c["TP"] + c["FP"] >= 5
                     and len(articles[relation]) >= 3)
        check(expected["articles_predicted"] == len(articles[relation]), "Sai số bài")
        check(threshold and expected["pass_gate"] == threshold, "Chưa đạt ngưỡng")
        print(f"{relation}: Đạt kiểm tra ({observed['precision']:.2%} precision)")
    totals = sum(counts.values(), Counter())
    check(metrics(totals["TP"], totals["FP"], totals["FN"]) == reference["micro"], "Sai tổng micro")
    stats = read_json("thong_ke.json")
    report = read_json("neo4j_check.json")
    first, second = report["import_runs"]
    for run in (first, second):
        check((run["nodes"], run["edges"], run["relations"]) ==
              (stats["nodes"], stats["edges"], stats["types"]), "Sai thống kê Neo4j")
    check(report["before"]["nodes"] == report["before"]["edges"] == 0, "Sai trạng thái đầu")
    check((first["created_nodes"], first["created_edges"]) == (stats["nodes"], stats["edges"]), "Sai lượt nhập đầu")
    check(second["created_nodes"] == second["created_edges"] == 0, "Lượt hai tạo bản ghi mới")
    check(report["full_property_comparison"] and first["graph_sha256"] == second["graph_sha256"], "Khác dữ liệu sau hai lượt")
    print(f"Neo4j: Đạt kiểm tra ({stats['nodes']} nút, {stats['edges']} cạnh, {len(stats['types'])} loại quan hệ)")


if __name__ == "__main__":
    main()
