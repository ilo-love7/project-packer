#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_check_timeline.py — scripts/check_timeline.py 的回归测试（标准库 unittest）

重点测四类容易错的地方：
  1. 日期解析——"2024-2025" 不能把 2025 的前两位当成月份；"2026.10" 不能解析成 1 月。
  2. 噪音控制——在校期间实习、同期的两个项目、奖学金这类单点，都不该报成矛盾。
     一个天天喊"时间线矛盾"的检查器会被直接关掉。
  3. 真矛盾必须抓到——倒挂、两段都声称全职却重叠、开始时间在未来。
  4. 总时间轴——这是 SKILL 里"核对总时间轴"那句话的实体，必须把所有区间列出来。
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
SPEC = importlib.util.spec_from_file_location("check_timeline", ROOT / "scripts" / "check_timeline.py")
tl = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(tl)

TODAY = tl.month_index(2026, 10)


def entries(text):
    return tl.extract_entries(text, TODAY)


def codes(text, today=TODAY, gap=6):
    return [(lv, c) for lv, c, _m in tl.check(entries(text), today, gap)]


def only(text, code, today=TODAY, gap=6):
    return [m for lv, c, m in tl.check(entries(text), today, gap) if c == code]


class TestParsing(unittest.TestCase):
    def test_dotted_range(self):
        e = entries("- 项目 A  2024.09-2025.06")[0]
        self.assertEqual((e.start, e.end), (tl.month_index(2024, 9), tl.month_index(2025, 6)))

    def test_dash_range_with_spaces(self):
        e = entries("- 项目 A  2024-09 - 2025-06")[0]
        self.assertEqual((e.start, e.end), (tl.month_index(2024, 9), tl.month_index(2025, 6)))

    def test_chinese_month_range(self):
        e = entries("- 项目 A  2024年9月-2025年6月")[0]
        self.assertEqual((e.start, e.end), (tl.month_index(2024, 9), tl.month_index(2025, 6)))

    def test_year_only_range_does_not_eat_digits(self):
        e = entries("- 项目 A  2024-2025")[0]
        self.assertEqual(e.start, tl.month_index(2024, 1))
        self.assertEqual(e.end, tl.month_index(2025, 1))

    def test_open_ended_range(self):
        e = entries("- 在职  2025.03-至今")[0]
        self.assertEqual(e.start, tl.month_index(2025, 3))
        self.assertEqual(e.end, TODAY)
        self.assertTrue(e.is_open)

    def test_slash_separator(self):
        e = entries("- 项目 A  2024/09-2025/06")[0]
        self.assertEqual(e.start, tl.month_index(2024, 9))

    def test_point_date_is_marked(self):
        e = entries("- 一等奖学金  2024.05")[0]
        self.assertTrue(e.is_point)

    def test_label_falls_back_to_previous_line(self):
        e = entries("校园二手书交易服务（课程项目）\n2025.09-2025.12\n")[0]
        self.assertIn("校园二手书交易服务", e.label)

    def test_label_strips_markdown_markers(self):
        e = entries("· 实现接口 2025.09-2025.12")[0]
        self.assertEqual(e.label, "实现接口")

    def test_duplicate_entries_are_collapsed(self):
        text = "- 项目 A  2025.09-2025.12\n- 项目 A  2025.09-2025.12\n"
        self.assertEqual(len(entries(text)), 1)


class TestToday(unittest.TestCase):
    def test_month_is_not_truncated(self):
        # 2026.10 若按 0?[1-9] 优先匹配，会被解析成 1 月
        self.assertEqual(tl.parse_today("2026.10"), tl.month_index(2026, 10))

    def test_december(self):
        self.assertEqual(tl.parse_today("2026.12"), tl.month_index(2026, 12))

    def test_year_only_defaults_to_january(self):
        self.assertEqual(tl.parse_today("2026"), tl.month_index(2026, 1))

    def test_invalid_raises(self):
        with self.assertRaises(ValueError):
            tl.parse_today("去年")


class TestContradictions(unittest.TestCase):
    def test_reversed_range_is_error(self):
        msgs = only("- 项目 A  2025.12-2025.09", "REVERSED")
        self.assertEqual(len(msgs), 1)

    def test_future_start_is_warn(self):
        msgs = only("- 项目 A  2027.01-2027.06", "FUTURE")
        self.assertEqual(len(msgs), 1)

    def test_two_fulltime_overlaps_are_warned(self):
        text = "- 后端实习生（全职）  2025.03-2025.06\n- 数据实习生（全职）  2025.05-2025.08\n"
        self.assertIn(("WARN", "OVERLAP"), codes(text))

    def test_fulltime_plus_project_is_only_info(self):
        text = "- 后端实习生（全职）  2025.03-2025.06\n- 课程项目          2025.05-2025.09\n"
        self.assertIn(("INFO", "PARALLEL"), codes(text))
        self.assertNotIn(("WARN", "OVERLAP"), codes(text))


class TestNoiseControl(unittest.TestCase):
    def test_identical_ranges_are_not_reported(self):
        text = "- 项目 A（课程项目）  2025.09-2025.12\n- 项目 B（课程项目）  2025.09-2025.12\n"
        self.assertNotIn(("WARN", "OVERLAP"), codes(text))
        self.assertNotIn(("INFO", "PARALLEL"), codes(text))

    def test_education_overlap_is_silent(self):
        text = "- XX大学 计算机（本科）  2022.09-2026.06\n- 后端实习生（全职）      2025.03-2025.06\n"
        self.assertEqual(codes(text), [])

    def test_point_dates_do_not_overlap(self):
        text = "- 一等奖学金  2024.05\n- 竞赛二等奖  2024.05\n"
        self.assertNotIn(("INFO", "PARALLEL"), codes(text))

    def test_adjacent_ranges_are_not_overlap(self):
        text = "- 项目 A  2025.01-2025.06\n- 项目 B  2025.07-2025.12\n"
        self.assertEqual(codes(text), [])

    def test_gap_below_threshold_is_silent(self):
        text = "- 项目 A  2025.01-2025.06\n- 项目 B  2025.08-2025.12\n"
        self.assertEqual(only(text, "GAP"), [])

    def test_gap_above_threshold_is_reported(self):
        text = "- 项目 A  2023.01-2023.06\n- 项目 B  2025.08-2025.12\n"
        msgs = only(text, "GAP")
        self.assertEqual(len(msgs), 1)
        self.assertIn("25 个月", msgs[0])

    def test_table_rows_are_ignored(self):
        # 交付包的审计表里也有日期，当成区间会凭空造出重叠
        text = "| A | 时间线无矛盾 | pass | 2025.09-2025.12 与学籍时间一致 |\n| 2026.10.20 | 初稿 | — |\n"
        self.assertEqual(entries(text), [])

    def test_gap_threshold_is_configurable(self):
        text = "- 项目 A  2025.01-2025.06\n- 项目 B  2025.10-2025.12\n"
        self.assertEqual(only(text, "GAP", gap=6), [])
        self.assertEqual(len(only(text, "GAP", gap=2)), 1)


class TestCli(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, argv):
        buf = io.StringIO()
        code = 0
        with redirect_stdout(buf):
            try:
                tl.main(argv)
            except SystemExit as e:
                code = e.code
        return code, buf.getvalue()

    def _write(self, text, name="r.md"):
        p = self.dir / name
        p.write_text(text, encoding="utf-8")
        return p

    def test_clean_exits_zero(self):
        p = self._write("- 项目 A  2025.01-2025.06\n")
        code, out = self._run([str(p), "--today", "2026.10"])
        self.assertEqual(code, 0)
        self.assertIn("没有矛盾", out)

    def test_error_exits_two(self):
        p = self._write("- 项目 A  2025.12-2025.09\n")
        code, out = self._run([str(p), "--today", "2026.10"])
        self.assertEqual(code, 2)
        self.assertIn("[ERROR]", out)

    def test_warn_exits_one(self):
        p = self._write("- 后端实习生（全职）  2025.03-2025.06\n- 数据实习生（全职）  2025.05-2025.08\n")
        code, out = self._run([str(p), "--today", "2026.10"])
        self.assertEqual(code, 1)
        self.assertIn("[WARN]", out)

    def test_timeline_is_printed(self):
        p = self._write("- 项目 A  2025.01-2025.06\n- 项目 B  2025.08-2025.12\n")
        code, out = self._run([str(p), "--today", "2026.10"])
        self.assertIn("总时间轴", out)
        self.assertIn("2025.01 - 2025.06", out)
        self.assertIn("2025.08 - 2025.12", out)

    def test_json_output_is_parseable(self):
        p = self._write("- 项目 A  2025.12-2025.09\n")
        code, out = self._run([str(p), "--today", "2026.10", "--json"])
        payload = json.loads(out)
        self.assertEqual(code, 2)
        self.assertEqual(payload["summary"]["error"], 1)
        self.assertEqual(payload["entries"][0]["start"], "2025.12")

    def test_missing_file_exits_two(self):
        code, out = self._run([str(self.dir / "nope.md")])
        self.assertEqual(code, 2)
        self.assertIn("文件不存在", out)

    def test_empty_file_reports_nothing_found(self):
        p = self._write("没有任何日期的简历\n")
        code, out = self._run([str(p), "--today", "2026.10"])
        self.assertEqual(code, 0)
        self.assertIn("没有识别到任何时间区间", out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
