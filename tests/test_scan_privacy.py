#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_scan_privacy.py — scripts/scan_privacy.py 的回归测试（标准库 unittest）

样本密钥一律用字符串拼接构造，不写完整字面量。原因很实际：如果测试文件里
躺着一个形似真密钥的字符串，那么这个仓库自己跑一次 scan_privacy 就会报警，
用户会以为是误报、进而怀疑整个工具。
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
SPEC = importlib.util.spec_from_file_location("scan_privacy", ROOT / "scripts" / "scan_privacy.py")
sp = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sp)

# 全部用拼接构造，避免仓库被自己的扫描器报警。
# 这不是洁癖：一个隐私扫描器的仓库里如果躺着形似真密钥的字符串，
# 用户跑一次就会以为是误报，然后开始怀疑整个工具。
COLON = chr(58)  # ":"
AT = chr(64)     # "@"
FAKE_SK = "sk-" + "A" * 32
FAKE_GH = "ghp_" + "B" * 36
FAKE_AWS = "AKIA" + "C" * 16
FAKE_PHONE = "138" + "1234" + "5678"
FAKE_ID = "110101" + "19900307" + "1234"
FAKE_PEM = "-----BEGIN " + "RSA " + "PRIVATE KEY-----"
FAKE_URL_CRED = "://" + "admin" + COLON + "hunter2" + AT
FAKE_PG_URL = "postgres" + FAKE_URL_CRED + "db" + COLON + "5432/x"
FAKE_PWD_ASSIGN = "pass" + "word=" + FAKE_PHONE + "abc"


def rules_hit(text):
    return [f["rule"] for f in sp.scan_text(text)]


class TestMask(unittest.TestCase):
    def test_secret_keeps_only_prefix(self):
        out = sp.mask(FAKE_SK, "secret")
        self.assertTrue(out.startswith("sk-"))
        self.assertNotIn("A" * 10, out)

    def test_middle_keeps_head_and_tail(self):
        self.assertEqual(sp.mask(FAKE_PHONE, "middle"), "138****5678")

    def test_plain_shows_value(self):
        self.assertEqual(sp.mask("192.168.1.42", "plain"), "192.168.1.42")

    def test_user_masks_only_username(self):
        path = "D:" + chr(92) + "Users" + chr(92) + "zhangsan" + chr(92) + "logs"
        out = sp.mask(path, "user")
        self.assertNotIn("zhangsan", out)
        self.assertIn("logs", out)

    def test_url_masks_only_password(self):
        self.assertEqual(sp.mask(FAKE_URL_CRED, "url"), "://admin:***" + AT)

    def test_short_value_is_fully_masked(self):
        self.assertEqual(sp.mask("abc", "secret"), "***（共 3 字符）")


class TestRules(unittest.TestCase):
    def test_each_error_rule_fires(self):
        cases = {
            "私钥块": FAKE_PEM,
            "GitHub token": FAKE_GH,
            "AWS Access Key": FAKE_AWS,
            "OpenAI 风格密钥": FAKE_SK,
            "Slack token": "xoxb-" + "1" * 12,
            "URL 内嵌凭据": FAKE_PG_URL,
        }
        for rule, sample in cases.items():
            self.assertIn(rule, rules_hit(sample), f"{rule} 未命中")

    def test_pii_rules_fire(self):
        self.assertIn("手机号", rules_hit(f"电话 {FAKE_PHONE}"))
        self.assertIn("身份证号", rules_hit(f"证件 {FAKE_ID}"))
        self.assertIn("内网 IP", rules_hit("部署在 192.168.1.42"))
        self.assertIn("邮箱", rules_hit("联系 me@example.com"))

    def test_public_ip_is_not_flagged(self):
        self.assertNotIn("内网 IP", rules_hit("部署在 8.8.8.8"))

    def test_clean_text_has_no_findings(self):
        self.assertEqual(sp.scan_text("复现论文管线，官方划分中位误差 5.9%。"), [])

    def test_error_wins_over_warn_on_same_span(self):
        # 同一处既像手机号又是密钥片段时，只报 ERROR，不重复刷屏
        findings = sp.scan_text(FAKE_PWD_ASSIGN)
        self.assertTrue(all(f["level"] == "ERROR" for f in findings), findings)


class TestAllow(unittest.TestCase):
    def test_allow_suppresses_own_phone(self):
        import re

        findings = sp.scan_text(f"我的手机 {FAKE_PHONE}", allow=[re.compile(FAKE_PHONE)])
        self.assertEqual(findings, [])

    def test_allow_does_not_suppress_others(self):
        import re

        findings = sp.scan_text("他人手机 13900001111", allow=[re.compile(FAKE_PHONE)])
        self.assertEqual([f["rule"] for f in findings], ["手机号"])


class TestSorting(unittest.TestCase):
    def test_error_before_warn_before_info(self):
        text = f"联系 me@example.com\n电话 {FAKE_PHONE}\n密钥 {FAKE_SK}"
        levels = [f["level"] for f in sp.sort_findings(sp.scan_text(text))]
        self.assertEqual(levels, ["ERROR", "WARN", "INFO"])


class TestCli(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.file = self.dir / "delivery.md"

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, argv):
        buf = io.StringIO()
        code = 0
        with redirect_stdout(buf):
            try:
                sp.main(argv)
            except SystemExit as e:
                code = e.code
        return code, buf.getvalue()

    def test_clean_file_exits_zero(self):
        self.file.write_text("复现论文管线，误差 5.9%。\n", encoding="utf-8")
        code, out = self._run([str(self.file)])
        self.assertEqual(code, 0)
        self.assertIn("未发现", out)

    def test_warn_exits_one(self):
        self.file.write_text(f"电话 {FAKE_PHONE}\n", encoding="utf-8")
        code, _ = self._run([str(self.file)])
        self.assertEqual(code, 1)

    def test_error_exits_two(self):
        self.file.write_text(f"密钥 {FAKE_SK}\n", encoding="utf-8")
        code, _ = self._run([str(self.file)])
        self.assertEqual(code, 2)

    def test_output_never_contains_the_raw_secret(self):
        self.file.write_text(f"密钥 {FAKE_SK}\n", encoding="utf-8")
        _code, out = self._run([str(self.file)])
        self.assertNotIn(FAKE_SK, out)

    def test_directory_is_scanned_recursively(self):
        (self.dir / "sub").mkdir()
        (self.dir / "sub" / "a.md").write_text(f"密钥 {FAKE_SK}\n", encoding="utf-8")
        code, out = self._run([str(self.dir)])
        self.assertEqual(code, 2)
        self.assertIn("sub/a.md", out.replace("\\", "/"))

    def test_bad_allow_regex_exits_two(self):
        self.file.write_text("x", encoding="utf-8")
        code, out = self._run([str(self.file), "--allow", "("])
        self.assertEqual(code, 2)
        self.assertIn("正则无效", out)

    def test_json_output_is_parseable(self):
        self.file.write_text(f"密钥 {FAKE_SK}\n", encoding="utf-8")
        code, out = self._run([str(self.file), "--json"])
        payload = json.loads(out)
        self.assertEqual(code, 2)
        self.assertEqual(payload["summary"]["error"], 1)


class TestRepoIsClean(unittest.TestCase):
    """仓库自身不应含任何形似真密钥的字符串。

    只断言 ERROR 级别：WARN 会命中测试样本（假手机号、假内网 IP）和
    扫描器自己源码里的正则定义——这属于"照镜子"，属预期行为，不该
    为了让它消失而把规则改弱。
    """

    def test_repo_has_no_error_level_findings(self):
        findings = []
        for p in ROOT.rglob("*"):
            if not p.is_file() or ".git" in p.parts:
                continue
            if p.suffix.lower() not in {".py", ".md", ".yml", ".yaml", ".txt", ".toml"}:
                continue
            try:
                text = p.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            findings += sp.scan_text(text)
        errors = [(f["rule"], f["line"]) for f in findings if f["level"] == "ERROR"]
        self.assertEqual(errors, [], f"仓库里出现了形似密钥的字符串: {errors}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
