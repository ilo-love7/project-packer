#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_check_delivery.py — scripts/check_delivery.py 的回归测试（标准库 unittest，零依赖）

运行：
    python3 -m unittest discover -s tests -v
    python3 tests/test_check_delivery.py

为什么需要这组测试：交付包的结构问题是「用户看不见的错」——少一节、
留着占位符、把内部说明投出去，稿子本身读起来完全正常。检查器误报一次，
用户就再也不跑它；漏报一次，占位符就跟着简历投出去了。所以每条检查都要有正反用例。
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
SPEC = importlib.util.spec_from_file_location(
    "check_delivery", ROOT / "scripts" / "check_delivery.py"
)
delivery = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(delivery)

MACHINE_ROWS = "\n".join(
    f"| x | `{name}.py 本文件` | ok |" for name in delivery.DELIVERY_CHECKS
)

VALID = f"""# 测试项目 · 求职交付包

**元信息**

| 项 | 值 |
|---|---|
| 生成日期 | 2026-10-22 |

## 1. 简历段（可直接粘贴）

```text
测试项目（载体：个人项目）    2026.01-2026.06
· 重写加载链路，中位耗时 480ms→90ms；
```

## 2. ATS 纯文本版

```text
测试项目
· 重写加载链路，中位耗时 480ms→90ms；
```

## 3. 面试稿

### 3.1 STAR 故事

内容。

## 4. 证据清单

| 数字 | 证据指针 |
|---|---|
| 480ms | bench/before.txt |

## 5. 防守分评分卡

| 条目 | 分数 |
|---|---|
| 480→90 | 3 |

## 6. 审计报告

### 6.1 机器检查（逐项记结果）

| 检查 | 命令 | 结果 |
|---|---|---|
{MACHINE_ROWS}

### 6.2 语义审计

| 视角 | 结论 |
|---|---|
| 背调 | pass |

## 7. 修订记录

| 日期 | 改了什么 | 为什么 |
|---|---|---|
| 2026-10-22 | 初稿 | 首次交付 |
"""

TEMPLATE = "| 目标岗位 | [岗位名 + 公司类型] |\n\n```text\n[项目名]（[载体]）\n· [动词] [成果 X]；\n```\n\n- [ ] 勾选项不是占位符\n"


def issues(text, template=TEMPLATE):
    return delivery.check(text, template)


def by_code(items, code):
    return [m for _lv, _no, m in items if m.startswith(code)]


def levels(items, level):
    return [m for lv, _no, m in items if lv == level]


class TestD1Sections(unittest.TestCase):
    def test_valid_package_is_clean(self):
        self.assertEqual(issues(VALID), [])

    def test_missing_section_is_an_error(self):
        broken = VALID.replace("## 4. 证据清单", "## 4. 证据")
        broken = broken.replace("## 4. 证据", "## 四. 证据")  # 让第 4 节消失
        self.assertTrue(by_code(issues(broken), "D1"))

    def test_no_sections_at_all(self):
        msgs = by_code(issues("这是一段散文，没有节标题。"), "D1")
        self.assertEqual(len(msgs), 1)

    def test_optional_section_eight_is_allowed(self):
        with_eight = VALID + "\n## 8. 交付后动作\n\n回写档案。\n"
        self.assertEqual(issues(with_eight), [])


class TestD2Order(unittest.TestCase):
    def test_duplicated_number_is_an_error(self):
        broken = VALID.replace("## 5. 防守分评分卡", "## 4. 防守分评分卡")
        self.assertTrue(by_code(issues(broken), "D2"))

    def test_out_of_order_is_an_error(self):
        a = VALID.index("## 4. 证据清单")
        b = VALID.index("## 5. 防守分评分卡")
        end = VALID.index("## 6. 审计报告")
        swapped = VALID[:a] + VALID[b:end] + VALID[a:b] + VALID[end:]
        self.assertTrue(any("节序错乱" in m for m in by_code(issues(swapped), "D2")))

    def test_first_section_must_be_the_resume(self):
        broken = VALID.replace("## 1. 简历段（可直接粘贴）", "## 1. 元信息表")
        self.assertTrue(any("第 1 节应是简历段" in m for m in by_code(issues(broken), "D2")))


class TestD3Placeholders(unittest.TestCase):
    def test_template_placeholder_is_an_error(self):
        broken = VALID + "\n| [项目名] | [动词] |\n"
        self.assertEqual(len(levels(issues(broken), "ERROR")), 2)

    def test_self_made_placeholder_is_a_warning(self):
        # 模板里没有 [日期]，只能靠形状猜，所以降一级
        broken = VALID + "\n| [日期] | [改了什么] |\n"
        self.assertEqual(levels(issues(broken), "ERROR"), [])
        self.assertTrue(levels(issues(broken), "WARN"))

    def test_checkbox_is_not_a_placeholder(self):
        self.assertEqual(issues(VALID + "\n- [ ] 待确认\n- [x] 已确认\n"), [])

    def test_link_text_is_not_a_placeholder(self):
        self.assertEqual(issues(VALID + "\n见 [项目名](https://example.com)。\n"), [])

    def test_bare_digits_in_brackets_are_not_placeholders(self):
        # 脚注 [1] 和正则片段 [3-9] 都长得像占位符，但不是
        self.assertEqual(issues(VALID + "\n见 [1] 与 `1[3-9]\\d{9}`。\n"), [])

    def test_all_caps_token_is_flagged(self):
        # [N] 在真实模板里是占位符，但这个夹具模板没有它，所以按形状猜 → WARN
        self.assertTrue(levels(issues(VALID + "\n| [N] | [X] |\n"), "WARN"))

    def test_year_placeholder_shape_is_flagged(self):
        self.assertTrue(levels(issues(VALID + "\n| [YYYY.MM] |\n"), "WARN"))


class TestD4MachineCheck(unittest.TestCase):
    def test_missing_script_row_warns(self):
        broken = VALID.replace(f"| x | `check_timeline.py 本文件` | ok |\n", "")
        msgs = by_code(issues(broken), "D4")
        self.assertEqual(len(msgs), 1)
        self.assertIn("check_timeline", msgs[0])

    def test_absent_subsection_warns(self):
        broken = VALID.replace("### 6.1 机器检查（逐项记结果）", "### 6.9 语义审计")
        self.assertTrue(by_code(issues(broken), "D4"))

    def test_inapplicable_row_still_counts(self):
        # 写了「未启用」也算记过——要求是"不许静默跳过"，不是"必须跑过"
        broken = VALID.replace(
            f"| x | `check_facts.py 本文件` | ok |",
            f"| x | `check_facts.py 本文件` | 未启用：单版本 |",
        )
        self.assertEqual(by_code(issues(broken), "D4"), [])


class TestD5TemplateInstruction(unittest.TestCase):
    def test_leftover_instructions_are_an_error(self):
        broken = "> **怎么用这份模板**\n> 1. 复制后按节填。\n\n" + VALID
        self.assertTrue(by_code(issues(broken), "D5"))

    def test_clean_package_has_no_d5(self):
        self.assertEqual(by_code(issues(VALID), "D5"), [])


class TestCli(unittest.TestCase):
    def _run(self, text, *extra):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "delivery.md"
            p.write_text(text, encoding="utf-8")
            buf = io.StringIO()
            code = None
            with redirect_stdout(buf):
                try:
                    delivery.main([str(p), *extra])
                except SystemExit as e:
                    code = e.code
            return code, buf.getvalue()

    def test_exit_zero_when_clean(self):
        code, _out = self._run(VALID)
        self.assertEqual(code, 0)

    def test_exit_two_on_error(self):
        code, _out = self._run(VALID + "\n| [项目名] |\n")
        self.assertEqual(code, 2)

    def test_strict_turns_warning_into_failure(self):
        code, _out = self._run(VALID + "\n| [日期] |\n", "--strict")
        self.assertEqual(code, 2)

    def test_json_output_is_parseable(self):
        _code, out = self._run(VALID + "\n| [项目名] |\n", "--json")
        data = json.loads(out)
        self.assertEqual(data["summary"]["error"], 1)
        self.assertTrue(data["issues"][0]["message"].startswith("D3"))


class TestRealExample(unittest.TestCase):
    """填满的参考交付包必须零告警——否则规则或示例有一方错了。"""

    def test_example_delivery_is_clean(self):
        text = (ROOT / "references" / "example-delivery.md").read_text(encoding="utf-8")
        tpl = (ROOT / "templates" / "delivery.template.md").read_text(encoding="utf-8")
        self.assertEqual(delivery.check(text, tpl), [])

    def test_template_itself_is_not_a_delivery_package(self):
        # 模板必然留着占位符和说明，它不是交付包，报错是预期行为
        tpl = (ROOT / "templates" / "delivery.template.md").read_text(encoding="utf-8")
        self.assertTrue(levels(delivery.check(tpl, tpl), "ERROR"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
