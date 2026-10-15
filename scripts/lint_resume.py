#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
lint_resume.py — project-packer 机械层审计（离线、零依赖、可复跑）

用法：
    python3 lint_resume.py resume.md
    python3 lint_resume.py resume.md --facts facts.md
    python3 lint_resume.py resume.md --keywords "Python,A/B测试,SQL"
    python3 lint_resume.py resume.md --facts facts.md --keywords "Python,SQL"

检查项：
  R1 动词黑名单：bullet 以 参与/协助/了解/熟悉/负责 等开头        → WARN
  R2 红灯词：自主研发/显著优于/远超/行业领先/国内首创/填补空白      → ERROR
  R3 日期格式混用（YYYY.MM / YYYY-MM / YYYY年M月）               → WARN
  R4 bullet 超长（>100 字符，约超 2 行）                         → WARN
  R5 数字与事实档案比对（给了 --facts 时）：简历数字未见于档案      → WARN
  R6 关键词覆盖（给了 --keywords 时）：输出覆盖率与缺失清单        → INFO

退出码：0=干净  1=有 WARN  2=有 ERROR
语义层审计（追问树、口径、归属）仍由 agent 按 integrity-audit.md 执行，
本脚本只负责机器能确定的检查，两层互补。
"""
import argparse
import re
import sys
from pathlib import Path

VERB_BLACKLIST = ["参与", "协助", "了解", "熟悉", "负责", "接触", "学习到了"]
RED_WORDS = {
    "自主研发": "若事实为复现/借鉴必须改写（复现≠自研）",
    "显著优于": "无同口径统计依据禁止使用",
    "远超": "需同口径对比依据",
    "行业领先": "无依据的绝对化表述",
    "国内首创": "无依据的绝对化表述",
    "填补空白": "无依据的绝对化表述",
}
BULLET_RE = re.compile(r"^\s*(?:[-*·•]|\d+[.、)]\s)\s*(.*)$")
DATE_PATTERNS = [
    (re.compile(r"\b(19|20)\d{2}\.\s?(0?[1-9]|1[0-2])\b"), "YYYY.MM"),
    (re.compile(r"\b(19|20)\d{2}-(0?[1-9]|1[0-2])\b"), "YYYY-MM"),
    (re.compile(r"(19|20)\d{2}\s?年\s?(0?[1-9]|1[0-2])\s?月"), "YYYY年M月"),
]
NUM_RE = re.compile(r"\d+(?:\.\d+)?")
YEAR_RANGE = range(1900, 2101)


def iter_bullets(lines):
    for no, raw in enumerate(lines, 1):
        m = BULLET_RE.match(raw)
        if m:
            yield no, raw.rstrip("\n"), m.group(1).strip()


def extract_numbers(text):
    """提取有审计意义的数字（先剥离日期，再跳过年份）。返回 {数字字符串: 出现次数}"""
    for pat, _ in DATE_PATTERNS:
        text = pat.sub(" ", text)  # 剥离 YYYY.MM / YYYY-MM / YYYY年M月，避免日期误报
    found = {}
    for tok in NUM_RE.findall(text):
        val = float(tok)
        if val.is_integer() and int(val) in YEAR_RANGE:
            continue  # 裸年份跳过
        found[tok] = found.get(tok, 0) + 1
    return found


def main():
    ap = argparse.ArgumentParser(description="project-packer 机械层简历审计")
    ap.add_argument("resume", help="简历/交付稿文件（md/txt）")
    ap.add_argument("--facts", help="事实档案 facts.md，启用 R5 数字比对")
    ap.add_argument("--keywords", help="逗号分隔的 JD 关键词，启用 R6 覆盖率")
    args = ap.parse_args()

    path = Path(args.resume)
    if not path.exists():
        print(f"[ERROR] 文件不存在: {path}")
        sys.exit(2)
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    issues = []  # (级别, 行号或'-', 消息)

    # R1 + R4：bullet 检查
    for no, raw, body in iter_bullets(lines):
        for verb in VERB_BLACKLIST:
            if body.startswith(verb):
                issues.append(("WARN", no, f"R1 动词黑名单：以「{verb}」开头 → 改为具体动词+动作"))
                break
        if len(body) > 100:
            issues.append(("WARN", no, f"R4 bullet 超长（{len(body)} 字符 > 100）→ 拆条或压缩到 2 行内"))

    # R2：红灯词
    for word, why in RED_WORDS.items():
        for i, line in enumerate(lines, 1):
            if word in line:
                issues.append(("ERROR", i, f"R2 红灯词「{word}」：{why}"))

    # R3：日期格式
    used = set()
    for pat, name in DATE_PATTERNS:
        if pat.search(text):
            used.add(name)
    if len(used) > 1:
        issues.append(("WARN", "-", f"R3 日期格式混用（{' / '.join(sorted(used))}）→ 统一为 YYYY.MM"))

    # R5：数字 vs 事实档案
    if args.facts:
        fpath = Path(args.facts)
        if not fpath.exists():
            print(f"[ERROR] 档案文件不存在: {fpath}")
            sys.exit(2)
        fact_nums = set(extract_numbers(fpath.read_text(encoding="utf-8")))
        resume_nums = extract_numbers(text)
        orphan = {n: c for n, c in resume_nums.items() if n not in fact_nums}
        if orphan:
            for n in sorted(orphan, key=lambda x: -orphan[x]):
                issues.append(("WARN", "-", f"R5 数字 {n} 未出现在事实档案中 → 人工核对口径，取不到证据就删"))

    # R6：关键词覆盖
    if args.keywords:
        kws = [k.strip() for k in args.keywords.split(",") if k.strip()]
        hit = [k for k in kws if k.lower() in text.lower()]
        miss = [k for k in kws if k.lower() not in text.lower()]
        cov = len(hit) / len(kws) * 100 if kws else 100
        issues.append(("INFO", "-", f"R6 关键词覆盖 {len(hit)}/{len(kws)}（{cov:.0f}%），缺失: {', '.join(miss) if miss else '无'}"))
        issues.append(("INFO", "-", "R6 缺词三分类：真缺→给补做方案 / 有而不叫这名→诚实换词 / 写不出→放弃，不堆砌"))

    # 输出
    n_err = sum(1 for lv, _, _ in issues if lv == "ERROR")
    n_warn = sum(1 for lv, _, _ in issues if lv == "WARN")
    print(f"== project-packer lint：{path.name} ==")
    if not issues:
        print("全部机械检查通过 ✅")
    for lv, no, msg in issues:
        loc = f"L{no}" if no != "-" else "--"
        print(f"[{lv}] {loc} {msg}")
    print(f"== 汇总：ERROR {n_err} / WARN {n_warn} ==")
    sys.exit(2 if n_err else 1 if n_warn else 0)


if __name__ == "__main__":
    main()
