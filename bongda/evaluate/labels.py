"""Read source-review labels from current and archived handoff formats."""
from pathlib import Path

LABEL = "nhan_kiem_tra"


def review_sheet(folder: Path) -> Path:
    current = folder / "phieu_cham.tsv"
    if current.is_file():
        return current
    archived = sorted(folder.glob("phieu_cham_*.tsv"))
    if len(archived) > 1:
        raise ValueError(f"Nhiều phiếu chấm trong {folder}")
    return archived[0] if archived else current


def normalize_label(row: dict) -> dict:
    if LABEL not in row:
        old = [k for k in row if k.startswith("nhan_") and k not in {"nhan_A", "nhan_B"}
               and row[k] in {"DUNG", "SAI", "CHUA_RO"}]
        if len(old) == 1:
            row[LABEL] = row.pop(old[0])
    return row
