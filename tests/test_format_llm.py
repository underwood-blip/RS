import unittest

from tests.util import make_snapshot

import format as fmt
import llm
import query


class FormatTest(unittest.TestCase):
    def setUp(self):
        self.snap = make_snapshot()

    def test_overview_contains_key_sections(self):
        text = fmt.overview(self.snap)
        self.assertIn("今日市場概況", text)
        self.assertIn("S&P 500", text)
        self.assertIn("跨市場最強", text)

    def test_top_list(self):
        rows = query.top(self.snap, "stocks", 2)
        text = fmt.top_list(rows, "測試排行")
        self.assertIn("測試排行", text)
        self.assertIn(rows[0]["symbol"], text)

    def test_symbol_detail(self):
        hits = query.find_symbols(self.snap, "ARM")
        text = fmt.symbol_detail(hits[0])
        self.assertIn("LazyRS 分數", text)

    def test_pulse_text(self):
        text = fmt.pulse_text(self.snap)
        self.assertIn("RS Pulse", text)
        self.assertIn("WDAY", text)

    def test_compare(self):
        a = query.find_symbols(self.snap, "ARM", 1)[0]
        b = query.find_symbols(self.snap, "MSTR", 1)[0]
        text = fmt.compare_text(a, b)
        self.assertIn("相對較強", text)


class RuleAnswerTest(unittest.TestCase):
    def setUp(self):
        self.snap = make_snapshot()

    def test_symbol_question_routes_to_detail(self):
        out = llm.rule_answer("ARM 現在怎樣", self.snap)
        self.assertIn("LazyRS 分數", out)

    def test_pulse_question(self):
        out = llm.rule_answer("今天有什麼異動", self.snap)
        self.assertIn("RS Pulse", out)

    def test_market_question_defaults_to_overview(self):
        out = llm.rule_answer("現在市場如何", self.snap)
        self.assertIn("今日市場概況", out)


class LlmAnswerTest(unittest.TestCase):
    def setUp(self):
        self.snap = make_snapshot()

    def test_answer_without_key_is_rule_based(self):
        from unittest import mock
        with mock.patch.object(llm.config, "LLM_API_KEY", ""):
            out = llm.answer("ARM 怎樣", self.snap, use_llm=True)
        self.assertEqual(len(out), 1)
        self.assertIn("LazyRS 分數", out[0])

    def test_answer_uses_llm_when_available(self):
        from unittest import mock
        with mock.patch.object(llm.config, "LLM_API_KEY", "fake"), \
             mock.patch.object(llm, "_ask", return_value="最強的是半導體"):
            out = llm.answer("最強是什麼", self.snap, use_llm=True)
        self.assertEqual(out, ["最強的是半導體"])

    def test_answer_degrades_on_failure(self):
        from unittest import mock
        with mock.patch.object(llm.config, "LLM_API_KEY", "fake"), \
             mock.patch.object(llm, "_ask", side_effect=RuntimeError("boom")):
            out = llm.answer("ARM 怎樣", self.snap, use_llm=True)
        self.assertIn("規則輸出", out[0])
        self.assertIn("LazyRS 分數", out[0])

    def test_build_context_has_data(self):
        ctx = llm.build_context(self.snap, "半導體")
        self.assertIn("指數/商品", ctx)
        self.assertIn("美股前5", ctx)


if __name__ == "__main__":
    unittest.main()
