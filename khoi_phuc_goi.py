"""Khôi phục riêng dữ liệu đã khóa từ các ZIP bàn giao của nhóm."""
import argparse
import hashlib
import shutil
import tempfile
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
# (SHA-256 của ZIP, thư mục bao ngoài, các đường dẫn được phép khôi phục)
PACKAGES = {
    "Ban_giao_A2_2026-11-08.zip": (
        "732021caed9c9a6d3c11f7b56fd9e18da94db9b8708eda44a6a73610bdf143c4",
        "D22_A2",
        ("work/a2_final", "work/a2_identity", "work/pilot_01",
         "templates/article_events_02.tsv", "templates/reviews_pilot.tsv"),
    ),
    "Ban_giao_A3_2026-11-08.zip": (
        "0b2cbb37f82610dc4ee1b7874fd892ae16151c842165c3d93ae591df2103b970",
        "D22_A3", ("work/a3_final",),
    ),
    "Danh_gia_precision_A2.zip": (
        "45eccd0f87c6a995073bf048a93c128924d37091cd67d5f857f680faaa93ac93",
        "", ("danh_gia_precision/phieu_cham_codex.tsv",),
    ),
    "Danh_gia_precision_A3.zip": (
        "f1013ea40ff0be90ae916a97a6059c3e7779cfe07256efa575e53ecdb207eb91",
        "", ("danh_gia_precision_a3/phieu_cham.tsv",),
    ),
    "Danh_gia_toan_bo_A3.zip": (
        "08420702ed8cd98107a7a51a45bee5f94f036131516aad53369086272fba7588",
        "", ("danh_gia_toan_bo_a3/phieu_cham_ngoai.tsv",),
    ),
}


def digest(file):
    return hashlib.file_digest(file, "sha256").hexdigest()


def restore(path):
    expected, prefix, allowed = PACKAGES[path.name]
    restored = 0
    with path.open("rb") as source:
        if digest(source) != expected:
            raise ValueError(f"SHA-256 không khớp: {path.name}")
        source.seek(0)
        with zipfile.ZipFile(source) as archive:
            for entry in archive.infolist():
                if entry.is_dir():
                    continue
                member = Path(entry.filename)
                if not member.is_relative_to(prefix):
                    continue
                name = member.relative_to(prefix)
                if not any(name.is_relative_to(p) for p in allowed):
                    continue
                dest = ROOT / name
                if not dest.resolve().is_relative_to(ROOT):
                    raise ValueError(f"Đường dẫn ngoài repo: {name}")
                with archive.open(entry) as data:
                    if dest.exists():
                        with dest.open("rb") as existing:
                            if digest(existing) != digest(data):
                                raise FileExistsError(f"File local đã thay đổi: {name}")
                        continue
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    with tempfile.NamedTemporaryFile(dir=dest.parent, delete=False) as tmp:
                        staged = Path(tmp.name)
                        try:
                            shutil.copyfileobj(data, tmp)
                            tmp.close()
                            # hardlink tạo đích nguyên tử và từ chối ghi đè.
                            dest.hardlink_to(staged)
                        finally:
                            staged.unlink(missing_ok=True)
                    restored += 1
    print(f"{path.name}: khôi phục {restored} file mới")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archives", nargs="+", type=Path)
    args = parser.parse_args()
    for path in args.archives:
        if path.name not in PACKAGES:
            parser.error(f"Gói không có trong danh mục A3: {path.name}")
        restore(path)


if __name__ == "__main__":
    main()
