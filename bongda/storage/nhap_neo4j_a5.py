"""Nhập A5 hai lượt trong môi trường Compose riêng của gói bàn giao."""

import argparse
import json
from pathlib import Path

from bongda.core.ban_giao import sha
from bongda.storage.nhap_neo4j_a3 import import_snapshot


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "directory", type=Path, help="Thư mục chứa snapshot/, compose.yaml và .env của A5"
    )
    root = parser.parse_args().directory.resolve()
    snapshot = root / "snapshot"
    if json.loads((snapshot / "stats.json").read_bytes())["version"] != "A5":
        raise ValueError("Cần snapshot A5.")
    for name, digest in json.loads((snapshot / "checksums.json").read_bytes()).items():
        if sha((snapshot / name).read_bytes()) != digest:
            raise ValueError("Checksum A5 sai: " + name)
    import_snapshot(
        snapshot,
        uri="bolt://127.0.0.1:7691",
        env_file=root / ".env",
        path=root / "import",
        project="d22_staff_a5",
        report_dir=root,
    )


if __name__ == "__main__":
    main()
