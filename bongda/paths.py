"""Đường dẫn kho mã, kết quả công khai và dữ liệu đánh giá cục bộ."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / "work"
RESULTS = ROOT / "results"

# Bản checkout trước khi tái cấu trúc có thể đã chứa phiếu riêng ở các đường dẫn cũ.
# Dùng lại thư mục có phiếu thật; checkout mới luôn ghi vào work/evaluation.
_EVALUATIONS = {
    "a2": ("danh_gia_precision", "phieu_cham_codex.tsv"),
    "a3": ("danh_gia_precision_a3", "phieu_cham.tsv"),
    "overall": ("danh_gia_toan_bo_a3", "phieu_cham_ngoai.tsv"),
}


def evaluation_dir(stage):
    folder, label = _EVALUATIONS[stage]
    current = WORK / "evaluation" / stage
    previous = ROOT / folder
    if not (current / label).is_file() and (previous / label).is_file():
        return previous
    return current
