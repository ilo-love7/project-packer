#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
scan_privacy.py — 隐私与密钥扫描

SKILL.md 硬约束第 6 条要求：考古模式扫描工作区时，API 密钥、私有服务器路径、
他人姓名/联系方式等敏感信息不得进入任何交付物；证据指针写到文件级即可，路径
中的敏感段落脱敏。在此之前这条约束靠 agent 自觉，本脚本把它变成可执行的检查。

用法：
    python3 scripts/scan_privacy.py delivery.md
    python3 scripts/scan_privacy.py ./out --exclude draft
    python3 scripts/scan_privacy.py delivery.md --allow "138\\d{8}"   # 放行自己的手机号
    python3 scripts/scan_privacy.py delivery.md --json

重要设计：**命中内容一律打码后再输出**。一个会把你泄露的密钥完整打印到终端、
再被你粘进聊天窗口的工具，本身就是新的泄露渠道。

分级：
    ERROR  密钥 / 私钥 / URL 内嵌凭据 / 明文口令 —— 绝不允许出现在交付物里
    WARN   身份证号 / 手机号 / 内网 IP / 本机绝对路径 —— 必须确认或脱敏
    INFO   邮箱 —— 简历留自己的邮箱是正常的，确认不是他人的即可

退出码：0=无 ERROR 且无 WARN  1=有 WARN  2=有 ERROR
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import iter_files, read_text, relative_label  # noqa: E402

# (级别, 名称, 正则, 说明, 打码方式)
# 顺序即优先级：同一个字符串被多条规则命中时，只报最严重的那条。
#
# 打码方式按"这条信息有多危险"分三档：
#   secret  —— 真密钥，只留前 3 位，绝不输出完整值
#   middle  —— 手机号/身份证，保留头尾便于辨认是哪一个
#   plain   —— 内网 IP、邮箱、路径这类，完整显示才有用：用户需要看到
#              "是哪台机器、哪个邮箱"才改得动。这些不是凭证，风险等级不同。
RULES = [
    ("ERROR", "私钥块",
     re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |PGP |DSA )?PRIVATE KEY-----"),
     "私钥绝不能出现在交付物里", "secret"),
    ("ERROR", "GitHub PAT",
     re.compile(r"\bgithub_pat_[A-Za-z0-9_]{40,}"),
     "GitHub 细粒度令牌", "secret"),
    ("ERROR", "GitHub token",
     re.compile(r"\b(?:ghp|gho|ghu|ghs|ghr)_[A-Za-z0-9]{30,}"),
     "GitHub 个人访问令牌", "secret"),
    ("ERROR", "OpenAI 风格密钥",
     re.compile(r"\bsk-[A-Za-z0-9_\-]{20,}"),
     "sk- 前缀的模型 API 密钥", "secret"),
    ("ERROR", "AWS Access Key",
     re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
     "AWS 访问密钥 ID", "secret"),
    ("ERROR", "Slack token",
     re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}"),
     "Slack 令牌", "secret"),
    ("ERROR", "URL 内嵌凭据",
     re.compile(r"://[^/\s:@]{1,64}:[^/\s@]{1,64}@"),
     "把账号密码从 URL 里去掉，改用环境变量", "url"),
    ("ERROR", "明文口令赋值",
     re.compile(r"(?i)\b(?:password|passwd|pwd|secret|api[_-]?key|access[_-]?key)\s*[:=]\s*['\"]?[^\s'\"]{6,}"),
     "疑似明文口令或密钥赋值", "secret"),
    ("WARN", "身份证号",
     re.compile(r"(?<!\d)\d{17}[\dXx](?!\d)"),
     "18 位身份证号不应出现在任何交付物里", "middle"),
    ("WARN", "手机号",
     re.compile(r"(?<!\d)1[3-9]\d{9}(?!\d)"),
     "确认是不是你自己的；他人的手机号必须删", "middle"),
    ("WARN", "内网 IP",
     re.compile(r"\b(?:10\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}|192\.168)\.\d{1,3}\.\d{1,3}\b"),
     "私有服务器地址应脱敏", "plain"),
    ("WARN", "本机绝对路径",
     re.compile(r"(?:[A-Za-z]:\\Users\\[^\\\s]+|/home/[^/\s]+|/Users/[^/\s]+)"),
     "证据指针写到文件级即可，路径中的用户名脱敏", "user"),
    ("INFO", "邮箱",
     re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"),
     "简历留自己的邮箱是正常的；确认不是他人的", "plain"),
]

LEVEL_ORDER = {"ERROR": 0, "WARN": 1, "INFO": 2}


def mask(value, mode="secret"):
    """按危险等级打码。

    secret  —— 只留前 3 位，密钥的完整值绝不落到终端或日志里
    middle  —— 保留头尾，用户能认出是哪一条手机号/身份证
    user    —— 路径只把用户名那段遮掉，目录结构保留（否则用户找不到文件）
    url     —— 只遮密码，保留账号和协议，用户才知道该改哪个连接串
    plain   —— 完整显示
    """
    if mode == "plain":
        return value
    if mode == "url":
        return re.sub(r"(://[^/\s:@]{1,64}:)[^/\s@]{1,64}(@)", r"\1***\2", value)
    if mode == "middle":
        if len(value) <= 6:
            return "***"
        head, tail = value[:3], value[-4:]
        return f"{head}{'*' * (len(value) - 7)}{tail}"
    if mode == "user":
        return re.sub(r"((?:Users|home)[/\\])([^/\\\s]+)", r"\1***", value)
    n = len(value)
    if n <= 8:
        return f"***（共 {n} 字符）"
    return f"{value[:3]}***（共 {n} 字符）"


def scan_text(text, allow=None):
    """扫描一段文本，返回 findings 列表。

    每条 finding: {level, rule, line, masked, note}
    allow 是一组已编译的正则，命中的片段直接跳过（用于放行自己的联系方式）。
    """
    findings = []
    covered = []  # 已被更严重规则覆盖的 (line, start, end)，避免同一处重复报
    for lineno, line in enumerate(text.splitlines(), 1):
        for level, name, pattern, note, mask_mode in RULES:
            for m in pattern.finditer(line):
                if allow and any(a.search(m.group(0)) for a in allow):
                    continue
                if any(ln == lineno and s <= m.start() < e for ln, s, e in covered):
                    continue
                covered.append((lineno, m.start(), m.end()))
                findings.append({
                    "level": level,
                    "rule": name,
                    "line": lineno,
                    "masked": mask(m.group(0), mask_mode),
                    "note": note,
                })
    return findings


def sort_findings(findings):
    return sorted(findings, key=lambda f: (LEVEL_ORDER[f["level"]], f["line"]))


def summarize(findings):
    out = {"error": 0, "warn": 0, "info": 0}
    for f in findings:
        out[f["level"].lower()] += 1
    return out


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="扫描交付物里的密钥与隐私信息",
        epilog="命中内容一律打码输出；用 --allow 放行自己的联系方式。",
    )
    ap.add_argument("target", help="要扫描的文件或目录")
    ap.add_argument("--allow", action="append", default=[],
                    help="放行正则，命中的片段不报警，可重复（如自己的手机号）")
    ap.add_argument("--exclude", action="append", default=[],
                    help="额外跳过的目录名，可重复")
    ap.add_argument("--max-bytes", type=int, default=2_000_000,
                    help="跳过超过该字节数的文件（默认 2MB）")
    ap.add_argument("--json", action="store_true", help="以 JSON 输出")
    args = ap.parse_args(argv)

    target = Path(args.target)
    if not target.exists():
        print(f"[ERROR] 目标不存在: {target}")
        sys.exit(2)

    try:
        allow = [re.compile(p) for p in args.allow]
    except re.error as e:
        print(f"[ERROR] --allow 正则无效: {e}")
        sys.exit(2)

    all_findings = []
    scanned = 0
    for path in iter_files(target, set(args.exclude) or None, args.max_bytes):
        text = read_text(path)
        if text is None:
            continue
        scanned += 1
        for f in scan_text(text, allow):
            f["file"] = relative_label(path, target.parent if target.is_file() else target)
            all_findings.append(f)
    all_findings = sort_findings(all_findings)
    stats = summarize(all_findings)

    if args.json:
        print(json.dumps({"target": str(target), "files_scanned": scanned,
                          "findings": all_findings, "summary": stats},
                         ensure_ascii=False, indent=2))
    else:
        print(f"== 隐私扫描：{target}（{scanned} 个文件）==")
        if not all_findings:
            print("未发现密钥或敏感信息 ✅")
        for f in all_findings:
            print(f"[{f['level']}] {f['file']}:{f['line']} {f['rule']} → {f['masked']}")
            print(f"        {f['note']}")
        print(f"== 汇总：ERROR {stats['error']} / WARN {stats['warn']} / INFO {stats['info']} ==")

    if stats["error"]:
        sys.exit(2)
    sys.exit(1 if stats["warn"] else 0)


if __name__ == "__main__":
    main()
