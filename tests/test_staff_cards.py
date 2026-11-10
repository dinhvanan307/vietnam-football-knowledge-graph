import unittest
from importlib.util import find_spec


@unittest.skipUnless(find_spec("mwparserfromhell"), "Cần bộ thư viện xử lý Wikipedia")
class StaffCardTests(unittest.TestCase):
    def test_same_match_preserves_player_card(self):
        from bongda.extract.doc_bien_ban import extract

        box = """{{football box
|date=12 tháng 3 năm 2024
|team1={{HNFC}}
|team2={{HLHT}}
|score=2–1
|goals1=*[[Nguyễn Văn Quyết]] {{yel|71}}
|goals2=*CBPTKT Nguyễn Thanh Thế {{yel|90+4}}
*[[Người A|CB KT Nguyễn Văn A]] {{yel|66}}
*[[CBCM Nguyễn Văn B|Nguyễn Văn B]] {{yel|88}}
*CB.PT.KT Nguyễn Văn C {{yel|52}}
*CB PTKT Nguyễn Văn D {{yel|62}}
*CBKT Nguyễn Văn E {{yel|45}}
*cbcm Nguyễn Văn G {{yel|30}}
*[[Nguyễn Văn Quyết]] {{goal|10}}
}}"""
        (match,) = extract({"title": "Cúp Quốc gia"}, box)
        self.assertEqual(
            [(v["player"]["name"], v["minute"]) for v in match["events"]],
            [("Nguyễn Văn Quyết", "71"), ("Nguyễn Văn Quyết", "10")],
        )

    def test_cached_role_alias_never_resolves_to_player(self):
        from bongda.graph.mo_rong_a import Resolver

        resolver = object.__new__(Resolver)
        for key, display in [
            ("Nguyễn Văn Việt", "CBPTKT Nguyễn Văn Việt"),
            ("cán bộ phân tích kỹ thuật Nguyễn Văn Việt", "Nguyễn Văn Việt"),
        ]:
            with self.subTest(key=key, display=display):
                actor = {"kind": "link", "name": display, "key": key}
                self.assertIsNone(resolver.observe(actor))
                self.assertIsNone(resolver.person(actor))

    def test_acronym_only_matches_whole_tokens(self):
        from bongda.extract.doc_bien_ban import has_staff_title

        self.assertFalse(has_staff_title("Nguyễn Văn Việt"))
        self.assertFalse(has_staff_title("CBKTran"))
        self.assertTrue(has_staff_title("CB\u00a0PTKT Đậu Ngọc Tân"))

    def test_archive_matches_link_display_without_removing_another_player(self):
        from bongda.graph.tao_a5 import check_card

        box = """{{football box
|date=3 tháng 7 năm 2022
|team1={{PHFC}}
|team2={{QNFC}}
|score=1–0
|goals2=*[[Nguyễn Đại Đồng|CBPTKT Nguyễn Đại Đồng]] {{yel|90+2}}
*Nguyễn Văn Quyết {{yel|20}}
}}"""
        article = {
            "article_id": "article-1",
            "pageid": "10",
            "revid": "11",
            "title": "Mùa 2022",
            "canonical_url": "https://vi.wikipedia.org/w/index.php?oldid=11",
            "clean_text": box,
        }
        raw = {"pageid": 10, "revisions": [{"revid": 11, "slots": {"main": {"content": box}}}]}
        evidence = {"evidence_id": "e", "start": 0, "end": len(box), "quote": box}
        fact = {
            "fact_id": "f",
            "relation_type": "NHAN_THE_VANG_KHI_GAP",
            "event_key": "2022-07-03:home:away",
            "dst_id": "home",
            "period": "2022-07-03",
        }
        clubs = {k: {"canonical_name": k} for k in ("home", "away")}
        node = {"entity_id": "p", "canonical_name": "Nguyễn Đại Đồng", "role": "Player"}
        result = check_card(node, fact, evidence, article, raw, clubs)
        self.assertEqual(
            (result["minute"], result["name_in_source"]), ("90+2", "CBPTKT Nguyễn Đại Đồng")
        )
        self.assertEqual(box[result["start"] : result["end"]], result["source_line"])
        node["canonical_name"] = "Nguyễn Văn Quyết"
        self.assertIsNone(check_card(node, fact, evidence, article, raw, clubs))
