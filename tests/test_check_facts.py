#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_check_facts.py — scripts/check_facts.py 的回归测试（标准库 unittest）

重点测四类容易错的地方：
  1. 两级冲突判定的分界——措辞完全相同必须报 CONFLICT（高置信、退出码 2），
     措辞不同但上下文相同只能报 SUSPECT（退出码 1）。混了就会要么漏报要么狼来了。
  2. 单文件不报 SUSPECT——同一份简历里两个相近的指标位不是"跨版本漂移"。
  3. 不重复报——同一处既满足 CONFLICT 又满足 SUSPECT 时只报 CONFLICT。
  4. 日期处理——完整日期（2026-10-22）必须整体吃掉，否则日号 22 会被当成数字。
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
SPEC = importlib.util.spec_from_file_location("check_facts", ROOT / "scripts" / "check_facts.py")
cf = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(cf)

FACTS = """# 事实档案（最后更新：2026-10-22）

## 电池项目
- 时间：2024.09 - 2025.03

| 数字 | 口径 | 证据指针 | 取证方式 | 防守分 |
|---|---|---|---|---|
| 5.9% | 官方划分中位误差 | results/summary.csv | 读第 4 列中位数 | 3 |
| 174 | 打卡活动参与人数 | signin.csv | 统计去重行数 | 2 |
| 61% | 单元测试覆盖率 | coverage.txt | 读 Total 行 | 2 |
"""


class TestConflict(unittest.TestCase):
    def test_identical_wording_different_number_is_conflict(self):
        a = "- 中位误差 5.9%，覆盖 174 人，覆盖率 61%；"
        b = "- 中位误差 6.4%，覆盖 174 人，覆盖率 61%；"
        r = cf.reconcile(FACTS, {"A.md": a, "B.md": b})
        self.assertEqual(len(r["conflict"]), 1)
        self.assertEqual(r["conflict"][0]["position"], 1)
        tokens = {v["token"] for v in r["conflict"][0]["values"]}
        self.assertEqual(tokens, {"5.9", "6.4"})

    def test_identical_wording_same_number_is_clean(self):
        a = "- 中位误差 5.9%，覆盖 174 人，覆盖率 61%；"
        r = cf.reconcile(FACTS, {"A.md": a, "B.md": a})
        self.assertEqual(r["conflict"], [])
        self.assertEqual(r["suspect"], [])

    def test_second_number_slot_also_detected(self):
        a = "- 中位误差 5.9%，覆盖 174 人；"
        b = "- 中位误差 5.9%，覆盖 240 人；"
        r = cf.reconcile(FACTS, {"A.md": a, "B.md": b})
        self.assertEqual(len(r["conflict"]), 1)
        self.assertEqual(r["conflict"][0]["position"], 2)
        self.assertEqual({v["token"] for v in r["conflict"][0]["values"]}, {"174", "240"})


class TestSuspect(unittest.TestCase):
    def test_different_wording_same_context_is_suspect(self):
        a = "- 中位误差 5.9%，覆盖 174 人，覆盖率 61%；"
        b = "- 中位误差 6.4%，覆盖 174 人；"
        r = cf.reconcile(FACTS, {"A.md": a, "B.md": b})
        self.assertEqual(r["conflict"], [])
        self.assertEqual(len(r["suspect"]), 1)
        self.assertEqual({v["token"] for v in r["suspect"][0]["values"]}, {"5.9", "6.4"})

    def test_single_file_never_suspect(self):
        # 同一份简历内部两个相近指标位不是跨版本漂移
        text = "- 中位误差 5.9%，覆盖 174 人；\n- 中位误差 6.4%，覆盖 240 人；"
        r = cf.reconcile(FACTS, {"A.md": text})
        self.assertEqual(r["suspect"], [])

    def test_conflict_is_not_double_reported_as_suspect(self):
        a = "- 中位误差 5.9%，覆盖 174 人；"
        b = "- 中位误差 6.4%，覆盖 174 人；"
        r = cf.reconcile(FACTS, {"A.md": a, "B.md": b})
        self.assertEqual(len(r["conflict"]), 1)
        self.assertEqual(r["suspect"], [])

    def test_unrelated_projects_with_different_metrics_not_flagged(self):
        a = "- 二手书服务：接口 p95 从 480ms 降到 90ms；"
        b = "- 二手书服务：接口 p95 从 480ms 降到 120ms；"
        r = cf.reconcile(FACTS, {"A.md": a, "B.md": b})
        # 措辞完全相同 → 归 CONFLICT，不该同时出现在 SUSPECT
        self.assertEqual(len(r["conflict"]), 1)
        self.assertEqual(r["suspect"], [])


class TestOrphanAndIdle(unittest.TestCase):
    def test_number_missing_from_facts_is_orphan(self):
        r = cf.reconcile(FACTS, {"A.md": "- 覆盖 174 人，另有 40% 提升；"})
        self.assertIn("A.md", r["orphan"])
        tokens = {o["token"] for o in r["orphan"]["A.md"]}
        self.assertIn("40", tokens)
        self.assertNotIn("174", tokens)

    def test_unused_facts_number_is_idle(self):
        r = cf.reconcile(FACTS, {"A.md": "- 覆盖 174 人；"})
        self.assertIn("5.9", r["idle"])
        self.assertIn("61", r["idle"])
        self.assertNotIn("174", r["idle"])

    def test_idle_counts_across_versions_union(self):
        r = cf.reconcile(FACTS, {"A.md": "- 误差 5.9%；", "B.md": "- 覆盖率 61%；"})
        self.assertEqual(r["idle"], ["174"])


class TestNumberHandling(unittest.TestCase):
    def test_full_date_day_is_not_a_number(self):
        r = cf.reconcile(FACTS, {"A.md": "- 最后更新 2026-10-22，误差 5.9%；"})
        tokens = {o["token"] for o in cf.occurrences("- 最后更新 2026-10-22，误差 5.9%；")}
        self.assertEqual(tokens, {"5.9"})
        self.assertEqual(r["orphan"], {})

    def test_low_signal_number_ignored(self):
        self.assertEqual(cf.occurrences("- 排查了 3 小时"), [])

    def test_year_is_not_significant(self):
        self.assertEqual(cf.occurrences("- 2024 年做的项目"), [])

    def test_min_number_is_configurable(self):
        self.assertEqual(cf.occurrences("- 样本 48 片", min_number=100), [])

    def test_significance_agrees_with_lint(self):
        # 两个工具对"哪些数字算数"必须只有一个答案
        from lint_resume import extract_significant_numbers

        text = "- 误差 5.9%，覆盖 174 人，排查了 3 小时，2024 年完成，另有 40% 提升"
        mine = {o["token"] for o in cf.occurrences(text)}
        theirs, _low = extract_significant_numbers(text)
        self.assertEqual(mine, set(theirs))


class TestCli(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        (self.dir / "facts.md").write_text(FACTS, encoding="utf-8")
        self.a = self.dir / "简历-后端.md"
        self.b = self.dir / "简历-测试.md"

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, argv):
        buf = io.StringIO()
        code = 0
        with redirect_stdout(buf):
            try:
                cf.main(argv)
            except SystemExit as e:
                code = e.code
        return code, buf.getvalue()

    def test_conflict_exits_two(self):
        self.a.write_text("- 中位误差 5.9%，覆盖 174 人；", encoding="utf-8")
        self.b.write_text("- 中位误差 6.4%，覆盖 174 人；", encoding="utf-8")
        code, out = self._run([str(self.dir / "facts.md"), str(self.a), str(self.b)])
        self.assertEqual(code, 2)
        self.assertIn("[CONFLICT]", out)
        self.assertIn("CONFLICT 1", out)

    def test_orphan_only_exits_one(self):
        self.a.write_text("- 覆盖 240 人；", encoding="utf-8")
        code, out = self._run([str(self.dir / "facts.md"), str(self.a)])
        self.assertEqual(code, 1)
        self.assertIn("[ORPHAN]", out)

    def test_clean_exits_zero(self):
        self.a.write_text("- 误差 5.9%，覆盖 174 人，覆盖率 61%；", encoding="utf-8")
        code, out = self._run([str(self.dir / "facts.md"), str(self.a)])
        self.assertEqual(code, 0)
        self.assertIn("一致", out)

    def test_directory_argument_expands(self):
        self.a.write_text("- 中位误差 5.9%，覆盖 174 人；", encoding="utf-8")
        self.b.write_text("- 中位误差 6.4%，覆盖 174 人；", encoding="utf-8")
        code, out = self._run([str(self.dir / "facts.md"), str(self.dir)])
        self.assertEqual(code, 2)
        self.assertIn("× 3 份简历", out)  # facts.md 自己也在目录里，属预期

    def test_missing_facts_exits_two(self):
        code, out = self._run([str(self.dir / "nope.md"), str(self.a)])
        self.assertEqual(code, 2)
        self.assertIn("档案文件不存在", out)

    def test_json_output_is_parseable(self):
        self.a.write_text("- 中位误差 5.9%，覆盖 174 人；", encoding="utf-8")
        self.b.write_text("- 中位误差 6.4%，覆盖 174 人；", encoding="utf-8")
        code, out = self._run([str(self.dir / "facts.md"), str(self.a), str(self.b), "--json"])
        payload = json.loads(out)
        self.assertEqual(code, 2)
        self.assertEqual(payload["summary"]["conflict"], 1)
        self.assertEqual(payload["conflict"][0]["position"], 1)
        self.assertIn("file", payload["conflict"][0]["values"][0]["occurrences"][0])


if __name__ == "__main__":
    unittest.main(verbosity=2)
