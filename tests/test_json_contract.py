#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_json_contract.py — 七个脚本的 `--json` 输出契约（标准库 unittest，零依赖）

运行：
    python3 -m unittest discover -s tests -v
    python3 tests/test_json_contract.py

为什么需要这组测试：`--json` 是给自动化用的接口——用户会写
`lint_resume.py x.md --json | jq '.summary.error'`，或者把结果塞进 CI。
在此之前七个脚本各自有 --json，但没有一条测试保证「输出能被机器解析」。
改一次打印语句（比如调试时顺手加了句 print）就会静默破坏下游，
而仓库自己的测试全部照过。

这里守的是三条最低契约，不是具体字段名：
  1. stdout 整体就是一个合法 JSON（前后不许有多余文本）
  2. 顶层是对象，且含一个集合型字段（issues / findings / entries / numbers / ...）
  3. 退出码在 0/1/2 之内（不是崩溃退出）

字段名会随需求变，这三条不该变。
"""
import importlib.util
import io
import json
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

COLLECTION_KEYS = ("issues", "findings", "entries", "numbers", "conflict", "suspect", "orphan")


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# (脚本名, 参数, 说明)
CASES = [
    ("lint_resume", ["references/example-software.md"], "机械层"),
    ("check_timeline", ["references/example-delivery.md", "--today", "2026.10"], "时间线"),
    ("trace_numbers", ["references/example-software.md", "references"], "溯源层"),
    ("scan_privacy", ["references/example-software.md"], "隐私层"),
    ("check_facts", ["references/example-facts.md", "references/example-software.md"], "档案对账"),
    ("check_docs", [], "文档一致性"),
    ("check_delivery", ["references/example-delivery.md"], "交付包结构"),
]


class TestJsonContract(unittest.TestCase):
    def run_json(self, name, args):
        mod = load(name)
        buf = io.StringIO()
        code = 0
        with redirect_stdout(buf):
            try:
                mod.main([*args, "--json"])
            except SystemExit as e:
                code = e.code or 0
        return code, buf.getvalue()

    def test_every_script_emits_parseable_json(self):
        for name, args, label in CASES:
            with self.subTest(script=name, layer=label):
                _code, out = self.run_json(name, args)
                try:
                    json.loads(out)
                except json.JSONDecodeError as e:
                    self.fail(f"{name} --json 的输出不是合法 JSON：{e}\n前 200 字：{out[:200]}")

    def test_stdout_is_json_only(self):
        # 整段解析成功即证明前后没有多余文本（调试 print 会在这里暴露）
        for name, args, _label in CASES:
            with self.subTest(script=name):
                _code, out = self.run_json(name, args)
                self.assertEqual(out.strip()[0], "{", f"{name} 的 JSON 输出前有多余文本")

    def test_top_level_is_an_object_with_a_collection(self):
        for name, args, _label in CASES:
            with self.subTest(script=name):
                _code, out = self.run_json(name, args)
                data = json.loads(out)
                self.assertIsInstance(data, dict, f"{name} 的顶层不是对象")
                self.assertTrue(
                    any(k in data for k in COLLECTION_KEYS),
                    f"{name} 的 JSON 缺少集合型字段，实际键：{sorted(data)}",
                )

    def test_exit_code_is_within_contract(self):
        for name, args, _label in CASES:
            with self.subTest(script=name):
                code, _out = self.run_json(name, args)
                self.assertIn(code, (0, 1, 2), f"{name} 的退出码 {code} 超出 0/1/2 契约")

    def test_json_flag_is_documented_in_help(self):
        # --help 里没有 --json，说明这个脚本放弃了机器可读输出
        for name, _args, _label in CASES:
            with self.subTest(script=name):
                mod = load(name)
                buf = io.StringIO()
                with redirect_stdout(buf):
                    try:
                        mod.main(["--help"])
                    except SystemExit:
                        pass
                self.assertIn("--json", buf.getvalue(), f"{name} 的 --help 里没有 --json")


if __name__ == "__main__":
    unittest.main(verbosity=2)
