import json
import unittest
from pathlib import Path

import fetcher

FIX = Path(__file__).resolve().parent / "fixtures"


def _home_blocks():
    blob = (FIX / "home_blocks.txt").read_text(encoding="utf-8")
    macro = blob.split("MACRO>>", 1)[1].split("<<MACRO", 1)[0]
    pulse = blob.split("PULSE>>", 1)[1].split("<<PULSE", 1)[0]
    cross = json.loads(blob.split("CROSS>>", 1)[1])
    return macro, pulse, cross


class FetcherTest(unittest.TestCase):
    def test_strip_symbol(self):
        self.assertEqual(fetcher.strip_symbol("LB:SMH.US"), "SMH.US")
        self.assertEqual(fetcher.strip_symbol("BN:BTCUSDT"), "BTCUSDT")
        self.assertEqual(fetcher.strip_symbol("NVDA"), "NVDA")

    def test_json_array_at_handles_strings_with_brackets(self):
        s = '[{"a":"]not end["},{"b":2}] tail'
        out = fetcher._json_array_at(s, 0)
        self.assertEqual(json.loads(out), [{"a": "]not end["}, {"b": 2}])

    def test_parse_macro_tiles(self):
        macro, _, _ = _home_blocks()
        tiles = fetcher.parse_macro_tiles(macro)
        self.assertGreaterEqual(len(tiles), 1)
        spy = next(t for t in tiles if t["symbol"] == "SPY.US")
        self.assertEqual(spy["name"], "S&P 500")
        self.assertEqual(spy["price"], 772.28)
        self.assertAlmostEqual(spy["d1"], -0.14)
        self.assertAlmostEqual(spy["d5"], 2.67)

    def test_parse_pulse(self):
        _, pulse, _ = _home_blocks()
        p = fetcher.parse_pulse(pulse)
        labels = {c["label"] for c in p["counts"]}
        self.assertIn("突然走強", labels)
        strong = next(g for g in p["groups"] if g["title"] == "突然走強")
        first = strong["items"][0]
        self.assertEqual(first["ticker"], "WDAY")
        self.assertEqual(first["rank"], 72)
        self.assertEqual(first["excess"], "+1.2%")

    def test_cross_rows_shape(self):
        _, _, cross = _home_blocks()
        self.assertEqual(len(cross), 31)
        self.assertIn("rankDelta5d", cross[0])


if __name__ == "__main__":
    unittest.main()
