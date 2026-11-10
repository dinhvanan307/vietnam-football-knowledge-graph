"""Dựng lại mẫu và tính precision từ bộ nhãn A3 công khai, chỉ dùng Python chuẩn."""
import csv
import hashlib
import json
import random
from collections import Counter
from urllib.parse import urlparse

from bongda.evaluate.overall.thong_ke import combine, stratum

from bongda.paths import RESULTS as PUBLIC_RESULTS

RESULTS = PUBLIC_RESULTS / "a3"
LAYERS = {
    "trong_khung": (16782, 200, 2026110803, "H", "inside", "old_sample_sha256"),
    "ngoai_khung": (1374, 100, 2026110804, "N", "outside", "sample_sha256"),
}


def read_tsv(name):
    with (RESULTS / name).open(encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file, delimiter="\t"))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def main():
    frame = read_tsv("khung_a3.tsv")
    reviewed = read_tsv("nhan_300.tsv")
    reference = json.loads((RESULTS / "precision_a3.json").read_bytes())
    graph = json.loads((RESULTS / "thong_ke_a3.json").read_bytes())
    require(len(frame) == len({r["fact_id"] for r in frame}) == graph["edges"], "Khung bị thiếu hoặc trùng cạnh")
    require(len(reviewed) == len({r["fact_id"] for r in reviewed}) == 300, "Phiếu thiếu hoặc trùng cạnh")
    stats = []
    for layer, (size, n, seed, prefix, result_key, hash_key) in LAYERS.items():
        ids = sorted(r["fact_id"] for r in frame if r["tang"] == layer)
        sample = [r for r in reviewed if r["tang"] == layer]
        require(len(ids) == size and len(sample) == n, f"Sai kích thước tầng {layer}")
        selected = random.Random(seed).sample(ids, n)
        require(selected == [r["fact_id"] for r in sample], f"Sai mẫu {layer}")
        digest = hashlib.sha256(("\n".join(selected) + "\n").encode()).hexdigest()
        require(digest == reference["audit"][hash_key], "Sai checksum mẫu")
        for number, row in enumerate(sample, 1):
            require(row["ma"] == f"{prefix}{number:03}", "Sai mã phiếu")
            require(row["quan_he"] in graph["relations"] and urlparse(row["url_nguon"]).hostname, "Thiếu quan hệ hoặc nguồn")
        counts = Counter(r["nhan_kiem_tra"] for r in sample)
        require(set(counts) <= {"DUNG", "SAI", "CHUA_RO"}, "Nhãn không hợp lệ")
        layer_stats = stratum(size, counts)
        require(layer_stats == reference[result_key], f"Sai thống kê tầng {layer}")
        stats.append(layer_stats)
        print(f"{layer}: {counts['DUNG']}/{n} đúng trong mẫu từ {size} cạnh")
    overall = combine(*stats)
    require(overall == reference["combined"], "Sai kết quả chung")
    print(f"Precision toàn A3 (ước lượng có trọng số): {overall['weighted_precision']:.2%}")
    print(f"Cận dưới một phía 95%: {overall['lower_95']:.2%}")
    print("Cận dưới vượt 90%:", "CÓ" if overall["threshold_exceeded"] else "KHÔNG")


if __name__ == "__main__":
    main()
