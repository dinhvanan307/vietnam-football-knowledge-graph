"""Private release inputs live outside version control."""
import os
from pathlib import Path

from bongda.paths import ROOT

DATA = Path(os.environ.get("A7_DATA_ROOT", ROOT / "work" / "a7")).resolve()
RELEASE = DATA / "A7_Ban_nop"
LOTS = {"B": "A7_bao_chi", "V": "A7_nghiem_thu", "N": "A7_kiem_tra_cuoi",
        "R": "A7_bo_sung", "S": "A7_tai_tro"}
