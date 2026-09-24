import unittest

from tests.util import make_snapshot

import bot


class FakeEngine:
    def __init__(self, snap):
        self._snap = snap
        self.forced = False
        self.use_llm = False

    def snapshot(self, force=False):
        if force:
            self.forced = True
        return self._snap


class BotHandleTest(unittest.TestCase):
    def setUp(self):
        self.snap = make_snapshot()
        self.engine = FakeEngine(self.snap)

    def test_help(self):
        out = bot.handle(self.engine, "/help")
        self.assertIn("RS Terminal", out[0])

    def test_market(self):
        out = bot.handle(self.engine, "/market")
        self.assertIn("今日市場概況", out[0])

    def test_top_with_tab_and_n(self):
        out = bot.handle(self.engine, "/top 美股 2")
        self.assertIn("前 2", out[0])

    def test_bottom(self):
        out = bot.handle(self.engine, "/bottom stocks 2")
        self.assertIn("最弱排行", out[0])

    def test_sym(self):
        out = bot.handle(self.engine, "/sym ARM")
        self.assertIn("LazyRS 分數", out[0])

    def test_pulse(self):
        out = bot.handle(self.engine, "/pulse")
        self.assertIn("RS Pulse", out[0])

    def test_refresh_forced(self):
        out = bot.handle(self.engine, "/refresh")
        self.assertTrue(self.engine.forced)
        self.assertIn("已重新抓取", out[0])

    def test_compare(self):
        out = bot.handle(self.engine, "/compare ARM MSTR")
        self.assertIn("相對較強", out[0])

    def test_unknown_command(self):
        out = bot.handle(self.engine, "/nope")
        self.assertIn("未知指令", out[0])

    def test_free_text_rule_fallback(self):
        out = bot.handle(self.engine, "ARM 表現如何")
        self.assertTrue(out)


if __name__ == "__main__":
    unittest.main()
