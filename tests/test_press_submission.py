import json,tempfile,unittest
from pathlib import Path
from types import SimpleNamespace
from collections import defaultdict
from bongda.core.ban_giao import jlines
from bongda.press_final.editorial import listed
from bongda.press_final.match_text import resolve
from bongda.press_final.youth import youth_club
class PressBoundaries(unittest.TestCase):
    def test_ndjson_preserves_unicode_line_separator(self):
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/"docs";p.write_text(json.dumps({"quote":"Hà Nội\u2028mở tỷ số"},ensure_ascii=False)+"\n")
            self.assertEqual(jlines(p)[0]["quote"],"Hà Nội\u2028mở tỷ số")
    def test_province_is_not_an_academy(self):
        self.assertIsNone(youth_club("Nghệ An","2023-01-01"))
        self.assertIsNone(youth_club("Đà Nẵng","2023-01-01"))
        self.assertEqual(youth_club("SHB Đà Nẵng","2023-01-01"),"c-dn")
        self.assertIsNone(youth_club("Đại học Văn Lang","2024-05-09"))
    def test_report_is_not_preview(self):
        key=("c-hn","c-hp");g=SimpleNamespace(pairdates={key:{"m"}},matchdata={"m":{"date":"2024-05-04","score":(2,0),"pair":key}})
        self.assertEqual(resolve(g,"Dự đoán Hà Nội thắng Hải Phòng",["Hà Nội thắng Hải Phòng 2-0"],"2024-05-04"),(None,None))
        t="Hà Nội thắng Hải Phòng 2-0"
        self.assertEqual(resolve(g,t,[t],"2024-05-04")[0],"m")
    def test_partial_lineup_is_not_starting_eleven(self):
        self.assertIsNone(listed("CLB Hà Nội: Văn Quyết, Hùng Dũng"))
