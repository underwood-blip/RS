import unittest

from tests.util import make_snapshot


class QueryTest(unittest.TestCase):
    def setUp(self):
        import query
        self.q = query
        self.snap = make_snapshot()

    def test_find_symbol_by_bare_ticker(self):
        hits = self.q.find_symbols(self.snap, "ARM")
        self.assertTrue(hits)
        self.assertEqual(hits[0]["symbol"].split(".")[0], "ARM")

    def test_find_symbol_by_name(self):
        hits = self.q.find_symbols(self.snap, "Arm Holdings")
        self.assertTrue(any(h["symbol"].split(".")[0] == "ARM" for h in hits))

    def test_find_symbol_cross(self):
        hits = self.q.find_symbols(self.snap, "SMH")
        self.assertTrue(hits)
        self.assertEqual(hits[0]["tab"], "cross")

    def test_top_sorted_desc(self):
        rows = self.q.top(self.snap, "stocks", 3)
        self.assertEqual(len(rows), 3)
        self.assertGreaterEqual(rows[0]["score"], rows[1]["score"])

    def test_bottom_sorted_asc(self):
        rows = self.q.top(self.snap, "stocks", 3, reverse=False)
        self.assertLessEqual(rows[0]["score"], rows[-1]["score"])

    def test_cross_top(self):
        rows = self.q.cross_top(self.snap, 1)
        self.assertEqual(rows[0]["name"], "半導體")

    def test_parse_tab_arg(self):
        self.assertEqual(self.q.parse_tab_arg("美股"), "stocks")
        self.assertEqual(self.q.parse_tab_arg("crypto"), "crypto")
        self.assertIsNone(self.q.parse_tab_arg("nope"))


if __name__ == "__main__":
    unittest.main()
