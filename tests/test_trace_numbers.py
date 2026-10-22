#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_trace_numbers.py — scripts/trace_numbers.py 的回归测试（标准库 unittest）

重点测两类容易错的地方：
  1. 数字边界——"3" 不能命中 "13"/"3.5"，"5.9" 不能命中 "5.95"。
     边界写错会让溯源结果虚高，用户以为有证据、其实没有。
  2. 排除规则——交付稿自身必须排除，否则每个数字都在草稿里"命中"自己，
     这个工具就变成了永远返回 HIT 的摆设。
"""
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
SPEC = importlib.util.spec_from_file_location("trace_numbers", ROOT / "scripts" / "trace_numbers.py")
trace_mod = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(trace_mod)


class TestTokenRegex(unittest.TestCase):
    def test_integer_does_not_match_inside_longer_number(self):
        pat = trace_mod.build_token_regex(["3"])
        self.assertIsNone(pat.search("13 片"))
        self.assertIsNone(pat.search("3.5 小时"))
        self.assertIsNotNone(pat.search("3 小时"))

    def test_decimal_does_not_match_prefix_of_longer_decimal(self):
        pat = trace_mod.build_token_regex(["5.9"])
        self.assertIsNone(pat.search("15.9"))
        self.assertIsNone(pat.search("5.95"))
        self.assertIsNotNone(pat.search("误差 5.9%"))

    def test_longer_token_wins_over_shorter(self):
        pat = trace_mod.build_token_regex(["5", "5.9"])
        self.assertEqual(pat.search("误差 5.9").group(0), "5.9")

    def test_token_with_dot_is_escaped(self):
        # 若 "." 没被转义，正则会变成"5 任意字符 9"，"5x9" 就会误命中
        pat = trace_mod.build_token_regex(["5.9"])
        self.assertIsNone(pat.search("5x9"))
        self.assertIsNotNone(pat.search("5.9"))


class TestTrace(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ws = Path(self.tmp.name)
        (self.ws / "results").mkdir()
        (self.ws / "results" / "summary.csv").write_text(
            "cell,mae\nB0005,5.9\nB0006,5.1\n", encoding="utf-8"
        )
        (self.ws / "docs").mkdir()
        (self.ws / "docs" / "debug.md").write_text(
            "首跑 33.6%，四轮归因后降到 5.9%。\nNASA 34 颗里只有 3/34 可用。\n",
            encoding="utf-8",
        )

    def tearDown(self):
        self.tmp.cleanup()

    def test_hit_and_miss(self):
        draft = "误差 5.9%；覆盖 174 人；提升 40%"
        r = trace_mod.trace(draft, self.ws)
        self.assertEqual(r["5.9"]["status"], "HIT")
        self.assertEqual(r["174"]["status"], "MISS")
        self.assertEqual(r["40"]["status"], "MISS")

    def test_hit_carries_file_and_line(self):
        r = trace_mod.trace("误差 5.9%", self.ws)
        files = {h["file"] for h in r["5.9"]["hits"]}
        self.assertIn("results/summary.csv", files)
        self.assertIn("docs/debug.md", files)

    def test_same_line_repeated_counted_once(self):
        r = trace_mod.trace("NASA 34 颗", self.ws)
        hits = r["34"]["hits"]
        self.assertEqual(len(hits), 1)
        self.assertEqual(hits[0]["count"], 2)

    def test_draft_itself_is_excluded(self):
        draft_path = self.ws / "draft.md"
        draft_path.write_text("误差 5.9%\n", encoding="utf-8")
        r = trace_mod.trace("误差 5.9%", self.ws, skip_path=draft_path)
        files = {h["file"] for h in r["5.9"]["hits"]}
        self.assertNotIn("draft.md", files)

    def test_excluded_dir_is_skipped(self):
        (self.ws / "node_modules").mkdir()
        (self.ws / "node_modules" / "x.md").write_text("5.9\n", encoding="utf-8")
        r = trace_mod.trace("误差 5.9%", self.ws)
        files = {h["file"] for h in r["5.9"]["hits"]}
        self.assertFalse(any("node_modules" in f for f in files))

    def test_max_hits_caps_output(self):
        for i in range(10):
            (self.ws / f"f{i}.md").write_text("5.9\n", encoding="utf-8")
        r = trace_mod.trace("误差 5.9%", self.ws, max_hits=2)
        self.assertEqual(len(r["5.9"]["hits"]), 2)

    def test_order_follows_draft(self):
        r = trace_mod.trace("先 40% 后 5.9%", self.ws)
        self.assertEqual(list(r.keys()), ["40", "5.9"])

    def test_no_significant_numbers_returns_empty(self):
        self.assertEqual(trace_mod.trace("排查了 3 小时", self.ws), {})

    def test_min_number_is_configurable(self):
        r = trace_mod.trace("样本 48 片", self.ws, min_number=100)
        self.assertEqual(r, {})

    def test_binary_files_are_skipped(self):
        (self.ws / "blob.png").write_bytes(b"\x89PNG\r\n\x1a\n5.9")
        r = trace_mod.trace("误差 5.9%", self.ws)
        files = {h["file"] for h in r["5.9"]["hits"]}
        self.assertNotIn("blob.png", files)


class TestSummarize(unittest.TestCase):
    def test_counts(self):
        r = {"a": {"status": "HIT", "hits": [1]}, "b": {"status": "MISS", "hits": []}}
        self.assertEqual(trace_mod.summarize(r), {"total": 2, "hit": 1, "miss": 1})


class TestCli(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.ws = Path(self.tmp.name)
        (self.ws / "data.md").write_text("误差 5.9%\n", encoding="utf-8")
        self.draft = self.ws / "draft.md"

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, argv):
        buf = io.StringIO()
        code = 0
        with redirect_stdout(buf):
            try:
                trace_mod.main(argv)
            except SystemExit as e:
                code = e.code
        return code, buf.getvalue()

    def test_all_hit_exits_zero(self):
        self.draft.write_text("误差 5.9%", encoding="utf-8")
        code, out = self._run([str(self.draft), str(self.ws)])
        self.assertEqual(code, 0)
        self.assertIn("命中 1 / 未命中 0", out)

    def test_miss_exits_one(self):
        self.draft.write_text("覆盖 174 人", encoding="utf-8")
        code, out = self._run([str(self.draft), str(self.ws)])
        self.assertEqual(code, 1)
        self.assertIn("[MISS]", out)

    def test_missing_draft_exits_two(self):
        code, out = self._run([str(self.ws / "nope.md"), str(self.ws)])
        self.assertEqual(code, 2)
        self.assertIn("交付稿不存在", out)

    def test_missing_workspace_exits_two(self):
        self.draft.write_text("误差 5.9%", encoding="utf-8")
        code, out = self._run([str(self.draft), str(self.ws / "nope")])
        self.assertEqual(code, 2)
        self.assertIn("工作区不存在", out)

    def test_json_output_is_parseable(self):
        self.draft.write_text("误差 5.9%", encoding="utf-8")
        code, out = self._run([str(self.draft), str(self.ws), "--json"])
        payload = json.loads(out)
        self.assertEqual(code, 0)
        self.assertEqual(payload["summary"]["hit"], 1)
        self.assertEqual(payload["numbers"]["5.9"]["status"], "HIT")


if __name__ == "__main__":
    unittest.main(verbosity=2)
