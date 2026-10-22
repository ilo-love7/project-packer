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
│   └── integrity-audit.md   # 检查单（5 视角 {items} 条）
```

## 甲
## 乙

见 [模板](references/templates.md)。
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
    readme.write_text(head + extra + f"\n\n见 [{link}]({link})。\n", encoding="utf-8")
    zh = tmp / "README.zh-CN.md"
    zb = zh.read_text(encoding="utf-8").split("## 甲")[0]
    zh.write_text(zb + extra.replace("节", "節") + "\n", encoding="utf-8")
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
