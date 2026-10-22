#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_lint_resume.py — scripts/lint_resume.py 的回归测试（标准库 unittest，零依赖）

运行：
    python3 -m unittest discover -s tests -v
    python3 tests/test_lint_resume.py

为什么需要这组测试：lint 是「机械层审计」，它的输出直接决定用户会不会
改稿。规则写错会同时产生两类事故——误报（用户关掉工具，审计形同虚设）
和漏报（红线词放行，交稿后被面试官问崩）。所以每条规则都要有正反用例。
"""
import importlib.util
import io
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location("lint_resume", ROOT / "scripts" / "lint_resume.py")
lint = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(lint)


def levels(issues, level=None):
    return [m for lv, _, m in issues if level is None or lv == level]


class TestDisplayWidth(unittest.TestCase):
    def test_ascii_counts_one(self):
        self.assertEqual(lint.display_width("abc"), 3)

    def test_cjk_counts_two(self):
        self.assertEqual(lint.display_width("中文"), 4)

    def test_mixed(self):
        # 误(2) 差(2) 空格(1) 5(1) .(1) 9(1) %(1) = 9
        self.assertEqual(lint.display_width("误差 5.9%"), 9)

    def test_fullwidth_punctuation_counts_two(self):
        self.assertEqual(lint.display_width("；"), 2)


class TestIterBullets(unittest.TestCase):
    def test_dash_star_dot(self):
        lines = ["- 第一条", "* 第二条", "· 第三条", "• 第四条"]
        bodies = [b for _, _, b in lint.iter_bullets(lines)]
        self.assertEqual(bodies, ["第一条", "第二条", "第三条", "第四条"])

    def test_ordered_lists(self):
        lines = ["1. 甲", "2、乙", "3) 丙"]
        bodies = [b for _, _, b in lint.iter_bullets(lines)]
        self.assertEqual(bodies, ["甲", "乙", "丙"])

    def test_plain_text_is_not_bullet(self):
        self.assertEqual(list(lint.iter_bullets(["普通一行文字"])), [])

    def test_date_line_is_not_mistaken_for_ordered_list(self):
        # 这是 `1. ` 必须带空格的原因：否则 "2024.09 到 2025.03" 会被当成 bullet
        self.assertEqual(list(lint.iter_bullets(["2024.09 到 2025.03"])), [])
        self.assertEqual(list(lint.iter_bullets(["2024.09"])), [])

    def test_bullet_without_space_after_dash(self):
        self.assertEqual([b for _, _, b in lint.iter_bullets(["-甲"])], ["甲"])

    def test_line_numbers_are_one_based(self):
        got = [(no, b) for no, _, b in lint.iter_bullets(["标题", "- 正文"])]
        self.assertEqual(got, [(2, "正文")])


class TestExtractNumbers(unittest.TestCase):
    def test_strips_all_date_formats(self):
        text = "2024.09 到 2025-03，共 2025年1月 起"
        self.assertEqual(lint.extract_numbers(text), {})

    def test_skips_bare_years(self):
        self.assertEqual(lint.extract_numbers("2025 年那会儿"), {})

    def test_keeps_meaningful_numbers(self):
        got = lint.extract_numbers("误差 5.9%，样本 48 片，提升 40%")
        self.assertEqual(set(got), {"5.9", "48", "40"})

    def test_counts_repeats(self):
        self.assertEqual(lint.extract_numbers("5.9 和 5.9")["5.9"], 2)


class TestSignificantNumbers(unittest.TestCase):
    def test_small_bare_integer_is_low_signal(self):
        sig, low = lint.extract_significant_numbers("排查了 3 小时")
        self.assertEqual(sig, {})
        self.assertEqual(low, 1)

    def test_percent_is_significant_even_when_small(self):
        sig, low = lint.extract_significant_numbers("提升 3%")
        self.assertEqual(set(sig), {"3"})
        self.assertEqual(low, 0)

    def test_decimal_is_significant(self):
        sig, _ = lint.extract_significant_numbers("误差 5.9")
        self.assertEqual(set(sig), {"5.9"})

    def test_large_integer_is_significant(self):
        sig, _ = lint.extract_significant_numbers("样本 48 片")
        self.assertEqual(set(sig), {"48"})

    def test_threshold_is_configurable(self):
        sig, low = lint.extract_significant_numbers("样本 48 片", min_number=100)
        self.assertEqual(sig, {})
        self.assertEqual(low, 1)


class TestR1VerbBlacklist(unittest.TestCase):
    def test_flags_bullet_starting_with_banned_verb(self):
        issues = lint.check("- 参与模型训练\n- 协助清洗数据")
        self.assertEqual(len(levels(issues, "WARN")), 2)

    def test_does_not_flag_verb_in_the_middle(self):
        # R1 只管句首。句中「参与」不归 R1，句中「主导」归 R7 的归属词规则，
        # 所以这里只能断言「没有 R1 告警」——早先写的是「没有任何 WARN」，
        # 那是在 R7 还不存在时才成立的过宽断言。
        issues = lint.check("- 主导并参与模型训练")
        self.assertEqual([m for m in levels(issues, "WARN") if m.startswith("R1")], [])

    def test_mid_line_ownership_word_falls_to_r7_not_r1(self):
        issues = lint.check("- 主导并参与模型训练")
        self.assertEqual(len([m for m in levels(issues, "WARN") if m.startswith("R7")]), 1)


class TestR2RedWords(unittest.TestCase):
    def test_red_word_is_error(self):
        issues = lint.check("- 自主研发了预测系统")
        self.assertEqual(len(levels(issues, "ERROR")), 1)

    def test_message_includes_line_snippet(self):
        issues = lint.check("- 自主研发了预测系统")
        self.assertIn("自主研发", levels(issues, "ERROR")[0])

    def test_all_configured_red_words_are_covered(self):
        for word in lint.RED_WORDS:
            issues = lint.check(f"- 这里写了{word}四个字")
            self.assertTrue(any(word in m for m in levels(issues, "ERROR")), f"{word} 未被拦截")


class TestR2QuotedExemption(unittest.TestCase):
    """引号内的红灯词是「引用」不是「主张」。

    交付包按阶段 5 规范必须包含审计报告，而审计报告的写法就是引用被否掉的
    原句（"初稿写了'自主研发'→ cut"）。不豁免的话，每个人都会在自己的审计
    表上被自己的稿子报错。
    """

    def test_word_inside_chinese_quotes_is_not_an_error(self):
        issues = lint.check('| "自主研发了搜索服务" | **cut** | 复现课程骨架 |')
        self.assertEqual(levels(issues, "ERROR"), [])

    def test_word_inside_corner_brackets_is_not_an_error(self):
        issues = lint.check("- 初稿写「自主研发」→ cut")
        self.assertEqual(levels(issues, "ERROR"), [])

    def test_word_inside_backticks_is_not_an_error(self):
        issues = lint.check("- 删掉 `自主研发` 这个说法")
        self.assertEqual(levels(issues, "ERROR"), [])

    def test_exemption_is_counted_in_info(self):
        issues = lint.check('- 删掉"自主研发"，改为"复现"')
        self.assertTrue(any("引号内" in m for m in levels(issues, "INFO")))

    def test_unquoted_word_still_errors_on_the_same_line(self):
        issues = lint.check('- 删掉"自主研发"，但正文里又写了自主研发系统')
        self.assertEqual(len(levels(issues, "ERROR")), 1)

    def test_quote_spans_do_not_swallow_the_whole_line(self):
        # 只有一个引号时不成对，不应把后面整行都当成引用
        issues = lint.check('- 他写了"然后 自主研发了系统')
        self.assertEqual(len(levels(issues, "ERROR")), 1)


class TestR3DateFormats(unittest.TestCase):
    def test_single_format_is_clean(self):
        issues = lint.check("2024.09 - 2025.03")
        self.assertFalse(any(m.startswith("R3") for m in levels(issues)))

    def test_mixed_formats_warn(self):
        issues = lint.check("2024.09 到 2025-03")
        self.assertTrue(any(m.startswith("R3") for m in levels(issues, "WARN")))


class TestR4BulletWidth(unittest.TestCase):
    def test_short_bullet_passes(self):
        issues = lint.check("- 复现论文管线，误差 5.9%")
        self.assertFalse(any(m.startswith("R4") for m in levels(issues)))

    def test_long_bullet_warns(self):
        issues = lint.check("- " + "很长的描述" * 40)
        self.assertTrue(any(m.startswith("R4") for m in levels(issues, "WARN")))

    def test_threshold_is_configurable(self):
        line = "- " + "字" * 60  # 显示宽度 120
        self.assertFalse(any(m.startswith("R4") for m in levels(lint.check(line))))
        self.assertTrue(
            any(m.startswith("R4") for m in levels(lint.check(line, max_width=100), "WARN"))
        )


class TestR4ProseExemption(unittest.TestCase):
    """交付包里的 STAR 段落也是 "- " 开头的列表项，但它们是口播稿不是简历条目。"""

    def test_long_sentence_ending_with_period_is_not_flagged(self):
        line = "- 【S 情境】" + "这是一段要念出来的口播稿，" * 10 + "讲完就结束。"
        issues = lint.check(line)
        self.assertFalse(any(m.startswith("R4") for m in levels(issues, "WARN")))
        self.assertTrue(any(m.startswith("R4 跳过") for m in levels(issues, "INFO")))

    def test_long_bullet_ending_with_semicolon_is_still_flagged(self):
        line = "- " + "很长的描述" * 40 + "；"
        self.assertTrue(any(m.startswith("R4") for m in levels(lint.check(line), "WARN")))

    def test_english_sentence_in_italics_is_not_flagged(self):
        line = "- *" + "I built the backend of a course project and measured it. " * 6 + "*"
        self.assertFalse(any(m.startswith("R4") for m in levels(lint.check(line), "WARN")))

    def test_short_prose_does_not_produce_info_noise(self):
        issues = lint.check("- 简短的一句。")
        self.assertFalse(any(m.startswith("R4 跳过") for m in levels(issues, "INFO")))


class TestR5FactsComparison(unittest.TestCase):
    def test_number_missing_from_facts_warns(self):
        issues = lint.check("- 误差 5.9%", facts_text="| 5.9 | 中位误差 |")
        self.assertEqual([m for m in levels(issues, "WARN") if m.startswith("R5")], [])

    def test_number_absent_from_facts_warns(self):
        issues = lint.check("- 提升 40%", facts_text="| 5.9 | 中位误差 |")
        self.assertTrue(any("R5 数字 40" in m for m in levels(issues, "WARN")))

    def test_low_signal_numbers_are_not_reported_as_orphans(self):
        issues = lint.check("- 排查了 3 小时", facts_text="| 5.9 | 中位误差 |")
        self.assertFalse(any(m.startswith("R5 数字") for m in levels(issues)))
        self.assertTrue(any("低信号数字" in m for m in levels(issues, "INFO")))

    def test_facts_side_is_permissive(self):
        # 档案里的小整数也应被收集，避免简历侧同名数字被误判为孤儿
        issues = lint.check("- 样本 12 片", facts_text="| 12 | 片数 |")
        self.assertFalse(any(m.startswith("R5 数字") for m in levels(issues)))

    def test_no_facts_means_no_r5(self):
        issues = lint.check("- 提升 40%")
        self.assertFalse(any(m.startswith("R5") for m in levels(issues)))


class TestR6Keywords(unittest.TestCase):
    def test_reports_coverage(self):
        issues = lint.check("熟悉 Python 与 SQL", keywords=["Python", "SQL", "Go"])
        msg = [m for m in levels(issues, "INFO") if m.startswith("R6 关键词覆盖")][0]
        self.assertIn("2/3", msg)
        self.assertIn("67%", msg)
        self.assertIn("Go", msg)

    def test_empty_keywords_skipped(self):
        issues = lint.check("随便写点", keywords=["", "  "])
        self.assertFalse(any(m.startswith("R6") for m in levels(issues)))


class TestMainCli(unittest.TestCase):
    def _write(self, content, name="resume.md"):
        tmp = Path(tempfile.mkdtemp()) / name
        tmp.write_text(content, encoding="utf-8")
        return tmp

    def _run(self, argv):
        buf = io.StringIO()
        code = 0
        with redirect_stdout(buf):
            try:
                lint.main(argv)
            except SystemExit as e:
                code = e.code
        return code, buf.getvalue()

    def test_clean_file_exits_zero(self):
        f = self._write("- 复现论文管线，误差 5.9%")
        code, out = self._run([str(f)])
        self.assertEqual(code, 0)
        self.assertIn("全部机械检查通过", out)

    def test_warn_exits_one(self):
        f = self._write("- 参与模型训练")
        code, _ = self._run([str(f)])
        self.assertEqual(code, 1)

    def test_error_exits_two(self):
        f = self._write("- 自主研发了系统")
        code, _ = self._run([str(f)])
        self.assertEqual(code, 2)

    def test_strict_promotes_warn_to_two(self):
        f = self._write("- 参与模型训练")
        code, _ = self._run([str(f), "--strict"])
        self.assertEqual(code, 2)

    def test_missing_file_exits_two(self):
        code, out = self._run(["/nonexistent/resume.md"])
        self.assertEqual(code, 2)
        self.assertIn("文件不存在", out)

    def test_json_output_is_parseable(self):
        import json

        f = self._write("- 自主研发了系统")
        code, out = self._run([str(f), "--json"])
        payload = json.loads(out)
        self.assertEqual(code, 2)
        self.assertEqual(payload["summary"]["error"], 1)
        self.assertEqual(payload["issues"][0]["level"], "ERROR")


class TestR7YellowWords(unittest.TestCase):
    """R7：黄灯词必须带限定词。

    这一组测试的重点不是「能不能抓到」，而是「会不会误报」——R7 只给 WARN，
    但 WARN 一多用户就会关掉工具。所以每个正例都配一个反例。
    """

    def r7(self, text):
        return [m for m in levels(lint.check(text), "WARN") if m.startswith("R7")]

    # —— 效果词要对照数字 ——
    def test_effect_word_without_numbers_warns(self):
        self.assertEqual(len(self.r7("- 优化了数据加载流程；")), 1)

    def test_effect_word_with_arrow_passes(self):
        self.assertEqual(self.r7("- 优化加载流程，耗时 480 秒→90 秒；"), [])

    def test_effect_word_with_percent_passes(self):
        self.assertEqual(self.r7("- 优化索引，查询耗时降低 61%；"), [])

    def test_effect_word_with_from_to_passes(self):
        self.assertEqual(self.r7("- 优化查询，中位耗时从 7 分 20 秒降到 2 分 10 秒；"), [])

    def test_effect_word_at_clause_end_is_not_a_claim(self):
        # 「做了一些优化，」是在陈述做了这件事的类别，不是在主张效果
        self.assertEqual(self.r7("- 对慢查询做了一些优化，思路来自导师评审；"), [])

    # —— 归属词要范围 ——
    def test_ownership_word_without_scope_warns(self):
        self.assertEqual(len(self.r7("- 主导了数据平台建设；")), 1)

    def test_ownership_word_with_headcount_passes(self):
        self.assertEqual(self.r7("- 主导 3 人小组完成数据平台建设；"), [])

    def test_ownership_word_with_team_scope_passes(self):
        self.assertEqual(self.r7("- 牵头跨部门协作，打通两个系统的数据口径；"), [])

    def test_ownership_word_describing_someone_else_is_not_flagged(self):
        # 审计说明里「活动确为副部长牵头 → pass」，是在描述事实，不是自己主张
        self.assertEqual(self.r7('- "主导"限真实主导：活动确为副部长牵头 → pass；'), [])

    # —— 程度词要覆盖面 ——
    def test_automation_without_degree_warns(self):
        self.assertEqual(len(self.r7("- 实现了流程自动化；")), 1)

    def test_automation_with_step_count_passes(self):
        self.assertEqual(self.r7("- 将 12 个手工步骤全部自动化；"), [])

    def test_automation_with_coverage_passes(self):
        self.assertEqual(self.r7("- 自动化覆盖率从 0 提升到 84%；"), [])

    # —— 豁免 ——
    def test_quoted_yellow_word_is_not_flagged(self):
        self.assertEqual(self.r7('- 审计表：初稿写"主导了平台建设" → fix；'), [])

    def test_prose_line_is_not_flagged(self):
        # 口播稿按 R4 的同一套判据豁免，代价是英文条目以句号结尾会漏检
        self.assertEqual(self.r7("- 我主导了这个项目，从选型一路做到上线。"), [])

    def test_english_effect_word_is_out_of_scope(self):
        # R7 只查中文黄灯词；英文版的对应检查在 english-resume.md 里人工过
        self.assertEqual(self.r7("- Optimized the loading pipeline;"), [])


class TestStructuralNumbers(unittest.TestCase):
    """结构性数字与标识符里的数字，不是数据。

    这三类假阳性是实测出来的：拿一份正常交付稿跑 `--facts`，19 条 R5 警告里
    有 5 条是「阶段 3.1」「p95」「被否决的说法」这类根本不是数据的东西。
    R5 的信噪比本来就是这套工具最脆的地方，多报几次用户就关掉了。
    """

    def sig(self, text):
        return [t for t, _s, _e in lint.iter_significant_tokens(text)]

    def test_heading_stage_number_is_not_data(self):
        self.assertEqual(self.sig("## 阶段 3.1：简历条目"), [])

    def test_cross_reference_is_not_data(self):
        self.assertEqual(self.sig("规范见第 3.4 节"), [])

    def test_number_after_ascii_letter_is_an_identifier(self):
        # p95 的 95、x86 的 86、H100 的 100 都是名字的一部分
        self.assertEqual(self.sig("p95 延迟 480ms"), ["480"])
        self.assertEqual(self.sig("x86 与 H100 两种机器"), [])
        self.assertEqual(self.sig("Python3.11 下跑通"), [])

    def test_unit_suffix_is_not_mistaken_for_an_identifier(self):
        # 480ms 的 480 后面跟着 m，但它确实是数据——所以判据只看前一个字符
        self.assertEqual(self.sig("中位耗时 480ms"), ["480"])

    def test_quoted_number_is_not_a_claim(self):
        self.assertEqual(self.sig('- 不说"性能提升 5.3 倍"，那是延迟比'), [])

    def test_same_value_outside_quotes_is_still_reported(self):
        text = '- 不说"提升 5.3 倍"：480/90 约等于 5.3，是延迟比'
        self.assertEqual(self.sig(text), ["480", "90", "5.3"])

    def test_stage_number_that_is_also_a_real_metric_survives(self):
        # 3.4 既是「阶段 3.4」的编号，也是「3.4 万条种子数据」的数据。
        # 判据按出现位置而不是按词，所以它必须留下来。
        text = "## 阶段 3.4：载体重定位\n\n- 服务 3.4 万条种子数据；"
        self.assertEqual(self.sig(text), ["3.4"])

    def test_low_signal_count_does_not_include_structural_numbers(self):
        # 结构性数字既不算显著也不算低信号，否则 INFO 那行会说谎
        text = "## 阶段 3.1\n\n## 阶段 3.2\n\n- 排查了 3 小时；"
        _sig, low = lint.extract_significant_numbers(text)
        self.assertEqual(low, 1)


class TestGoldenExamples(unittest.TestCase):
    """参考示例本身必须是干净的——否则规则或示例有一方错了。"""

    def test_battery_example_has_no_errors(self):
        text = (ROOT / "references" / "example-battery.md").read_text(encoding="utf-8")
        self.assertEqual(levels(lint.check(text), "ERROR"), [])

    def test_student_work_example_has_no_errors(self):
        text = (ROOT / "references" / "example-student-work.md").read_text(encoding="utf-8")
        self.assertEqual(levels(lint.check(text), "ERROR"), [])

    def test_software_example_has_no_errors(self):
        text = (ROOT / "references" / "example-software.md").read_text(encoding="utf-8")
        self.assertEqual(levels(lint.check(text), "ERROR"), [])

    def test_software_example_has_no_warnings_either(self):
        # 这个示例是"照着抄就能过 lint"的示范，所以要求比 ERROR-only 更严
        text = (ROOT / "references" / "example-software.md").read_text(encoding="utf-8")
        self.assertEqual(levels(lint.check(text), "WARN"), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
