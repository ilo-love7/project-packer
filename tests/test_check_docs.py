#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_check_docs.py — scripts/check_docs.py 的回归测试（标准库 unittest，零依赖）

思路：在临时目录里搭一份"最小可用仓库骨架"，然后逐项把它写错，断言对应
检查项必须报 FAIL。只测"能通过"是不够的——一个永远返回 PASS 的检查器
同样没用，所以每个用例都必须是「改坏 → 必须抓到」。
"""
import importlib.util
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SPEC = importlib.util.spec_from_file_location("check_docs", ROOT / "scripts" / "check_docs.py")
docs = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(docs)

SKILL_TMPL = """---
name: demo
version: {version}
description: demo
---

# demo

### 阶段 0：准备
### 阶段 1：执行
### 阶段 2：交付
"""

README_TMPL = """<div align="center">

# demo

![version](https://img.shields.io/badge/version-{badge}-blue)

</div>

```
demo/
├── SKILL.md                 # {stages}-stage workflow
├── references/
│   ├── templates.md
│   └── integrity-audit.md   # checklist (5 viewpoints, {items} items)
└── README.md
```

## A
## B

See [templates](references/templates.md).
"""

README_ZH_TMPL = """<div align="center">

# demo

![version](https://img.shields.io/badge/version-{badge}-blue)

</div>

```
├── SKILL.md                 # {stages} 阶段工作流
├── references/
│   ├── templates.md
│   └── integrity-audit.md   # 检查单（5 视角 {items} 条）
```

## 甲
## 乙

见 [模板](references/templates.md)。
"""

CHANGELOG_TMPL = """
<details>
<summary><b>v{version}</b> (2026-01-01)</summary>

notes

</details>
"""

TEMPLATES = """# 输出模板

## 1. 简历条目
## 7. 替代量化
## 9. 包装强度分级
"""


def build(tmp, *, version="2.2.2", badge="2.2.2", stages=3, items=2,
          audit_items=(1, 2), xref="第 7 节「替代量化」", h2_count=2, link="./README.md"):
    """在 tmp 下搭一份骨架；参数用于故意写坏某一项。"""
    tmp = Path(tmp)
    (tmp / "references").mkdir(parents=True, exist_ok=True)

    (tmp / "SKILL.md").write_text(SKILL_TMPL.format(version=version), encoding="utf-8")
    (tmp / "README.md").write_text(
        README_TMPL.format(badge=badge, stages=stages, items=items), encoding="utf-8"
    )
    (tmp / "README.zh-CN.md").write_text(
        README_ZH_TMPL.format(badge=badge, stages=stages, items=items), encoding="utf-8"
    )
    (tmp / "references" / "templates.md").write_text(TEMPLATES, encoding="utf-8")

    audit = "# 审计\n\n" + "\n".join(f"{n}. 检查项 {n}" for n in audit_items) + f"\n\n{xref}\n"
    (tmp / "references" / "integrity-audit.md").write_text(audit, encoding="utf-8")

    # 让 README 的二级标题数量可控
    readme = tmp / "README.md"
    body = readme.read_text(encoding="utf-8")
    head = body.split("## A")[0]
    extra = "\n".join(f"## 节 {i}" for i in range(h2_count))
    changelog = CHANGELOG_TMPL.format(version=version)
    readme.write_text(
        head + extra + f"\n\n见 [{link}]({link})。\n" + changelog, encoding="utf-8"
    )
    zh = tmp / "README.zh-CN.md"
    zb = zh.read_text(encoding="utf-8").split("## 甲")[0]
    zh.write_text(zb + extra.replace("节", "節") + "\n" + changelog, encoding="utf-8")
    return tmp


def fails(issues, code):
    return [m for lv, c, m in issues if c == code and lv == "FAIL"]


class TestBaseline(unittest.TestCase):
    def test_clean_fixture_passes(self):
        with tempfile.TemporaryDirectory() as d:
            issues = docs.check(build(d))
            self.assertEqual([m for lv, _, m in issues if lv == "FAIL"], [])


class TestC1Version(unittest.TestCase):
    def test_badge_mismatch_is_caught(self):
        with tempfile.TemporaryDirectory() as d:
            issues = docs.check(build(d, version="2.3.0", badge="2.2.2"))
            self.assertTrue(fails(issues, "C1"))

    def test_missing_badge_is_caught(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = build(d)
            (tmp / "README.md").write_text("# demo\n\n无徽章\n", encoding="utf-8")
            self.assertTrue(fails(docs.check(tmp), "C1"))


class TestC2Stages(unittest.TestCase):
    def test_wrong_stage_count_is_caught(self):
        with tempfile.TemporaryDirectory() as d:
            issues = docs.check(build(d, stages=6))  # 实际 3 个阶段
            self.assertTrue(fails(issues, "C2"))

    def test_gap_in_stage_numbering_is_caught(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = build(d)
            (tmp / "SKILL.md").write_text(
                "---\nname: demo\nversion: 2.2.2\n---\n\n### 阶段 0：甲\n### 阶段 2：丙\n",
                encoding="utf-8",
            )
            self.assertTrue(fails(docs.check(tmp), "C2"))

    def test_changelog_quoting_an_old_count_is_not_a_claim(self):
        """更新日志里写「README 曾宣称 6-stage」是引用旧值，不是当前声明。"""
        with tempfile.TemporaryDirectory() as d:
            tmp = build(d)
            readme = tmp / "README.md"
            readme.write_text(
                readme.read_text(encoding="utf-8")
                + "\n<details>\n<summary>v2.3.0</summary>\n\n"
                + "Fixed: the README advertised a \"6-stage workflow\" when SKILL.md had 3 stages.\n"
                + "</details>\n",
                encoding="utf-8",
            )
            self.assertEqual(fails(docs.check(tmp), "C2"), [])


class TestC3Items(unittest.TestCase):
    def test_wrong_item_count_is_caught(self):
        with tempfile.TemporaryDirectory() as d:
            issues = docs.check(build(d, items=21, audit_items=(1, 2)))
            self.assertTrue(fails(issues, "C3"))


class TestC4Numbering(unittest.TestCase):
    def test_duplicate_number_is_caught(self):
        with tempfile.TemporaryDirectory() as d:
            issues = docs.check(build(d, audit_items=(1, 2, 2, 3)))
            self.assertTrue(fails(issues, "C4"))

    def test_gap_in_numbering_is_caught(self):
        with tempfile.TemporaryDirectory() as d:
            issues = docs.check(build(d, audit_items=(1, 2, 4)))
            self.assertTrue(fails(issues, "C4"))


class TestC5Xref(unittest.TestCase):
    def test_wrong_section_name_is_caught(self):
        with tempfile.TemporaryDirectory() as d:
            issues = docs.check(build(d, xref="第 7 节「量化」"))
            self.assertTrue(fails(issues, "C5"))

    def test_nonexistent_section_is_caught(self):
        with tempfile.TemporaryDirectory() as d:
            issues = docs.check(build(d, xref="第 42 节「不存在」"))
            self.assertTrue(fails(issues, "C5"))

    def test_suffix_of_title_is_not_accepted(self):
        # 「量化」是「替代量化」的后缀，不是前缀——引用必须能唯一定位到标题
        with tempfile.TemporaryDirectory() as d:
            issues = docs.check(build(d, xref="第 7 节「量化」"))
            self.assertTrue(fails(issues, "C5"))


class TestC6Bilingual(unittest.TestCase):
    def test_heading_count_mismatch_is_caught(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = build(d)
            zh = tmp / "README.zh-CN.md"
            zh.write_text(zh.read_text(encoding="utf-8") + "## 多出来一节\n", encoding="utf-8")
            self.assertTrue(fails(docs.check(tmp), "C6"))


class TestC7Links(unittest.TestCase):
    def test_broken_relative_link_is_caught(self):
        with tempfile.TemporaryDirectory() as d:
            issues = docs.check(build(d, link="./nope.md"))
            self.assertTrue(fails(issues, "C7"))


class TestC8EvalNumbering(unittest.TestCase):
    def _with_evals(self, d, body):
        tmp = build(d)
        (tmp / "evals.md").write_text(body, encoding="utf-8")
        return tmp

    def test_gap_in_group_is_caught(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = self._with_evals(d, "### A1 甲\n### A2 乙\n### A4 丁\n")
            self.assertTrue(fails(docs.check(tmp), "C8"))

    def test_duplicate_number_is_caught(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = self._with_evals(d, "### A1 甲\n### A1 乙\n")
            self.assertTrue(fails(docs.check(tmp), "C8"))

    def test_groups_must_start_at_one(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = self._with_evals(d, "### A2 甲\n### A3 乙\n")
            self.assertTrue(fails(docs.check(tmp), "C8"))

    def test_out_of_order_groups_is_caught(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = self._with_evals(d, "### B1 甲\n### A1 乙\n")
            self.assertTrue(fails(docs.check(tmp), "C8"))

    def test_well_formed_evals_pass(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = self._with_evals(d, "### A1 甲\n### A2 乙\n### B1 丙\n")
            self.assertEqual(fails(docs.check(tmp), "C8"), [])

    def test_missing_evals_is_skipped_not_failed(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = build(d)  # 没有 evals.md
            self.assertEqual(fails(docs.check(tmp), "C8"), [])


class TestC9Changelog(unittest.TestCase):
    def test_missing_changelog_entry_is_caught(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = build(d)
            readme = tmp / "README.md"
            readme.write_text(
                readme.read_text(encoding="utf-8").replace("<b>v2.2.2</b>", "<b>v2.2.1</b>"),
                encoding="utf-8",
            )
            self.assertTrue(fails(docs.check(tmp), "C9"))

    def test_zh_changelog_is_checked_too(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = build(d)
            zh = tmp / "README.zh-CN.md"
            zh.write_text(
                zh.read_text(encoding="utf-8").replace("<b>v2.2.2</b>", "<b>v2.0.0</b>"),
                encoding="utf-8",
            )
            self.assertTrue(fails(docs.check(tmp), "C9"))


class TestC10Tree(unittest.TestCase):
    def test_file_missing_from_tree_is_caught(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = build(d)
            (tmp / "references" / "forgotten.md").write_text("# 新文档\n", encoding="utf-8")
            msgs = fails(docs.check(tmp), "C10")
            self.assertTrue(msgs)
            self.assertIn("forgotten.md", " ".join(msgs))

    def test_templates_dir_is_covered(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = build(d)
            (tmp / "templates").mkdir()
            (tmp / "templates" / "x.template.md").write_text("# x\n", encoding="utf-8")
            self.assertTrue(fails(docs.check(tmp), "C10"))


class TestC11BacktickPaths(unittest.TestCase):
    def test_dangling_path_is_caught(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = build(d)
            skill = tmp / "SKILL.md"
            skill.write_text(
                skill.read_text(encoding="utf-8") + "\n见 `references/ghost.md`。\n",
                encoding="utf-8",
            )
            self.assertTrue(fails(docs.check(tmp), "C11"))

    def test_existing_path_passes(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = build(d)
            skill = tmp / "SKILL.md"
            skill.write_text(
                skill.read_text(encoding="utf-8") + "\n见 `references/templates.md`。\n",
                encoding="utf-8",
            )
            self.assertEqual(fails(docs.check(tmp), "C11"), [])

    def test_glob_pattern_is_not_checked(self):
        # `example-*.md` 这类写法不是具体文件，不该报错
        with tempfile.TemporaryDirectory() as d:
            tmp = build(d)
            skill = tmp / "SKILL.md"
            skill.write_text(
                skill.read_text(encoding="utf-8") + "\n见 `references/*.md`。\n",
                encoding="utf-8",
            )
            self.assertEqual(fails(docs.check(tmp), "C11"), [])


class TestC12TemplateCoverage(unittest.TestCase):
    """交付模板必须列出全部交付检查脚本。

    这条检查的由来：模板 6.1 表停在最早的三个脚本，时间线与档案对账从没进过表，
    而 SKILL.md 说它们必跑。用户照模板填，那两项就永远没有记录。
    """

    def _with_template(self, tmp, body):
        (tmp / "templates").mkdir(exist_ok=True)
        (tmp / "templates" / "delivery.template.md").write_text(body, encoding="utf-8")
        return tmp

    def test_missing_script_is_caught(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = self._with_template(
                build(d),
                "| 机械层 | `lint_resume.py` |\n| 时间线 | `check_timeline.py` |\n",
            )
            msgs = fails(docs.check(tmp), "C12")
            self.assertEqual(len(msgs), 1)
            # 漏的是还没写进表里的那几个
            self.assertIn("trace_numbers", msgs[0])

    def test_all_five_scripts_pass(self):
        with tempfile.TemporaryDirectory() as d:
            body = "\n".join(f"| x | `{s}.py` |" for s in docs.DELIVERY_CHECKS)
            tmp = self._with_template(build(d), body)
            self.assertEqual(fails(docs.check(tmp), "C12"), [])

    def test_missing_template_is_skip_not_fail(self):
        with tempfile.TemporaryDirectory() as d:
            tmp = build(d)
            self.assertEqual(fails(docs.check(tmp), "C12"), [])

    def test_check_docs_itself_is_not_required(self):
        # check_docs.py 是仓库自检工具，不该出现在用户的交付检查表里
        self.assertNotIn("check_docs", docs.DELIVERY_CHECKS)


class TestRealRepo(unittest.TestCase):
    """仓库自身必须通过检查——否则说明文档确实不一致。"""

    def test_this_repo_is_consistent(self):
        bad = [m for lv, _, m in docs.check() if lv == "FAIL"]
        self.assertEqual(bad, [])


class TestCli(unittest.TestCase):
    def _run(self, argv):
        buf = io.StringIO()
        code = 0
        with redirect_stdout(buf):
            try:
                docs.main(argv)
            except SystemExit as e:
                code = e.code
        return code, buf.getvalue()

    def test_clean_exit_zero(self):
        code, out = self._run([])
        self.assertEqual(code, 0)
        self.assertIn("FAIL 0", out)

    def test_json_output_is_parseable(self):
        code, out = self._run(["--json"])
        payload = json.loads(out)
        self.assertEqual(code, 0)
        self.assertEqual(payload["summary"]["fail"], 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
