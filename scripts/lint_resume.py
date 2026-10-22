#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
lint_resume.py — project-packer 机械层审计（离线、零依赖、可复跑）

用法：
    python3 lint_resume.py resume.md
    python3 lint_resume.py resume.md --facts facts.md
    python3 lint_resume.py resume.md --keywords "Python,A/B测试,SQL"
    python3 lint_resume.py resume.md --facts facts.md --keywords "Python,SQL"
    python3 lint_resume.py resume.md --json          # 机器可读输出
    python3 lint_resume.py resume.md --strict        # WARN 也返回退出码 2

检查项：
  R1 动词黑名单：bullet 以 参与/协助/了解/熟悉/负责 等开头        → WARN
  R2 红灯词：自主研发/显著优于/远超/行业领先/国内首创/填补空白      → ERROR
  R3 日期格式混用（YYYY.MM / YYYY-MM / YYYY年M月）               → WARN
  R4 bullet 过长（显示宽度 > 阈值，约超 2 行）                    → WARN
  R5 数字与事实档案比对（给了 --facts 时）：简历数字未见于档案      → WARN
  R6 关键词覆盖（给了 --keywords 时）：输出覆盖率与缺失清单        → INFO

关于 R4 的宽度：用「显示宽度」而非字符数。一个中文字符占 2 个西文宽度，
所以中文 75 字和英文 150 字符在简历上都约等于 2 行。默认阈值 150，
可用 --max-width 调整。

关于 R5 的信噪比：简历里大量数字是顺带的（"排查了 3 小时"），逐一比对
事实档案会淹没有效告警。因此只有「带小数点 / 带百分号 / 数值 ≥ 阈值」
的数字才进入比对，其余记为低信号数字只统计不告警。阈值用 --min-number
调整（默认 10）。

退出码：0=干净  1=有 WARN  2=有 ERROR（--strict 下 WARN 也算 2）
语义层审计（追问树、口径、归属）仍由 agent 按 integrity-audit.md 执行，
本脚本只负责机器能确定的检查，两层互补。
"""
import argparse
import json
import re
import sys
import unicodedata
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
BULLET_RE = re.compile(r"^\s*(?:[-*·•]\s*|\d+\.\s+|\d+[、)）]\s*)\s*(.*)$")
DATE_PATTERNS = [
    (re.compile(r"\b(19|20)\d{2}\.\s?(0?[1-9]|1[0-2])\b"), "YYYY.MM"),
    (re.compile(r"\b(19|20)\d{2}-(0?[1-9]|1[0-2])\b"), "YYYY-MM"),
    (re.compile(r"(19|20)\d{2}\s?年\s?(0?[1-9]|1[0-2])\s?月"), "YYYY年M月"),
]
NUM_RE = re.compile(r"\d+(?:\.\d+)?")
YEAR_RANGE = range(1900, 2101)
PERCENT_CHARS = "%％"

# 成对引号：命中片段被这样包起来，说明是在**引用**这个词，不是在主张它。
# 典型场景是交付包里的审计表：「初稿写了"自主研发"→ cut」。
# 不豁免的话，每个用户都会在自己的审计报告上被自己的稿子报错。
QUOTE_PAIRS = {
    '"': '"', "'": "'",
    "\u201c": "\u201d",  # “ ”
    "\u2018": "\u2019",  # ‘ ’
    "\u300c": "\u300d",  # 「 」
    "\u300e": "\u300f",  # 『 』
    "`": "`",
    "\u300a": "\u300b",  # 《 》
}


def _quoted_spans(line):
    """返回行内被成对引号包住的区间列表 [(start, end), ...]。"""
    spans, i = [], 0
    while i < len(line):
        close = QUOTE_PAIRS.get(line[i])
        if close:
            j = line.find(close, i + 1)
            if j != -1:
                spans.append((i + 1, j))
                i = j + 1
                continue
        i += 1
    return spans


def _is_quoted(line, start, end, spans=None):
    """命中片段是否落在某个引号区间内（在引用，不是在主张）。"""
    spans = _quoted_spans(line) if spans is None else spans
    return any(s <= start and end <= e for s, e in spans)


def display_width(text):
    """按终端/排版显示宽度计数：全角与宽字符算 2，其余算 1。"""
    return sum(2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1 for ch in text)


def iter_bullets(lines):
    for no, raw in enumerate(lines, 1):
        m = BULLET_RE.match(raw)
        if m:
            yield no, raw.rstrip("\n"), m.group(1).strip()


def _strip_dates(text):
    for pat, _ in DATE_PATTERNS:
        text = pat.sub(" ", text)
    return text


def _mask_dates(text):
    """把日期替换成等长的空格，从而在屏蔽日期后仍保持字符下标不变。

    trace_numbers.py 需要「这个数字在第几个字符」来截取上下文，
    所以不能用 _strip_dates 那种会改变长度的替换。
    """
    for pat, _ in DATE_PATTERNS:
        text = pat.sub(lambda m: " " * len(m.group(0)), text)
    return text


def extract_numbers(text):
    """提取全部有审计意义的数字（先剥离日期，再跳过年份）。返回 {数字字符串: 次数}

    这是「宽松」模式，用于事实档案侧——档案是全集，宁多勿漏。
    """
    found = {}
    for tok in NUM_RE.findall(_strip_dates(text)):
        val = float(tok)
        if val.is_integer() and int(val) in YEAR_RANGE:
            continue
        found[tok] = found.get(tok, 0) + 1
    return found


def iter_significant_tokens(text, min_number=10):
    """按出现顺序产出「值得逐一对账」的数字：(token, start, end)。

    显著判定（任一成立）：带小数点 / 紧跟百分号 / 数值 >= min_number。
    这条规则是为了压掉「排查了 3 小时」这类顺带数字的噪音。
    start/end 是在原文中的下标，调用方可以据此截取上下文。
    """
    masked = _mask_dates(text)
    for m in NUM_RE.finditer(masked):
        tok = m.group(0)
        val = float(tok)
        if val.is_integer() and int(val) in YEAR_RANGE:
            continue
        has_decimal = "." in tok
        is_percent = m.end() < len(masked) and masked[m.end()] in PERCENT_CHARS
        if has_decimal or is_percent or val >= min_number:
            yield tok, m.start(), m.end()


def extract_significant_numbers(text, min_number=10):
    """只提取「值得逐一对账」的数字。返回 ({数字: 次数}, 低信号数字个数)"""
    sig = {}
    total = 0
    for tok, _s, _e in iter_significant_tokens(text, min_number):
        sig[tok] = sig.get(tok, 0) + 1
        total += 1
    masked = _mask_dates(text)
    low = 0
    for m in NUM_RE.finditer(masked):
        tok = m.group(0)
        val = float(tok)
        if val.is_integer() and int(val) in YEAR_RANGE:
            continue
        has_decimal = "." in tok
        is_percent = m.end() < len(masked) and masked[m.end()] in PERCENT_CHARS
        if not (has_decimal or is_percent or val >= min_number):
            low += 1
    return sig, low


def check(text, facts_text=None, keywords=None, max_width=150, min_number=10):
    """执行全部检查，返回 issues 列表 [(级别, 行号或'-', 消息)]。

    纯函数，不读命令行、不打印，便于单元测试直接调用。
    """
    lines = text.splitlines()
    issues = []

    # R1 + R4：bullet 检查
    for no, _raw, body in iter_bullets(lines):
        for verb in VERB_BLACKLIST:
            if body.startswith(verb):
                issues.append(("WARN", no, f"R1 动词黑名单：以「{verb}」开头 → 改为具体动词+动作"))
                break
        w = display_width(body)
        if w > max_width:
            issues.append(
                ("WARN", no, f"R4 bullet 过长（显示宽度 {w} > {max_width}）→ 拆条或压缩到 2 行内")
            )

    # R2：红灯词（附命中行片段，便于定位）
    # 被成对引号包住的命中算「引用」不算「主张」——交付包的审计表会大量出现
    # 这种写法（"初稿写了『自主研发』→ cut"），全报会把审计报告本身刷红。
    quoted = 0
    for word, why in RED_WORDS.items():
        for i, line in enumerate(lines, 1):
            spans = _quoted_spans(line)
            start = line.find(word)
            while start != -1:
                if _is_quoted(line, start, start + len(word), spans):
                    quoted += 1
                else:
                    snippet = line.strip()
                    if display_width(snippet) > 60:
                        snippet = snippet[:28] + "…"
                    issues.append(("ERROR", i, f"R2 红灯词「{word}」：{why}｜{snippet}"))
                start = line.find(word, start + 1)
    if quoted:
        issues.append(
            ("INFO", "-", f"R2 另有 {quoted} 处红灯词出现在引号内（视为引用，未计入错误）")
        )

    # R3：日期格式混用
    used = set()
    for pat, name in DATE_PATTERNS:
        if pat.search(text):
            used.add(name)
    if len(used) > 1:
        issues.append(("WARN", "-", f"R3 日期格式混用（{' / '.join(sorted(used))}）→ 统一为 YYYY.MM"))

    # R5：数字 vs 事实档案
    if facts_text is not None:
        fact_nums = set(extract_numbers(facts_text))  # 档案侧宽松取全集
        resume_nums, low_count = extract_significant_numbers(text, min_number)
        orphan = {n: c for n, c in resume_nums.items() if n not in fact_nums}
        for n in sorted(orphan, key=lambda x: (-orphan[x], x)):
            issues.append(
                ("WARN", "-", f"R5 数字 {n} 未出现在事实档案中 → 人工核对口径，取不到证据就删")
            )
        if low_count:
            issues.append(
                (
                    "INFO",
                    "-",
                    f"R5 另有 {low_count} 个低信号数字（整数 < {min_number} 且无百分号）未参与比对",
                )
            )

    # R6：关键词覆盖
    if keywords:
        kws = [k.strip() for k in keywords if k.strip()]
        if kws:
            lowered = text.lower()
            hit = [k for k in kws if k.lower() in lowered]
            miss = [k for k in kws if k.lower() not in lowered]
            cov = len(hit) / len(kws) * 100
            issues.append(
                ("INFO", "-", f"R6 关键词覆盖 {len(hit)}/{len(kws)}（{cov:.0f}%），缺失: {', '.join(miss) if miss else '无'}")
            )
            issues.append(
                ("INFO", "-", "R6 缺词三分类：真缺→给补做方案 / 有而不叫这名→诚实换词 / 写不出→放弃，不堆砌")
            )

    return issues


def main(argv=None):
    ap = argparse.ArgumentParser(description="project-packer 机械层简历审计")
    ap.add_argument("resume", help="简历/交付稿文件（md/txt）")
    ap.add_argument("--facts", help="事实档案 facts.md，启用 R5 数字比对")
    ap.add_argument("--keywords", help="逗号分隔的 JD 关键词，启用 R6 覆盖率")
    ap.add_argument("--max-width", type=int, default=150, help="R4 显示宽度阈值（默认 150，约 2 行）")
    ap.add_argument("--min-number", type=float, default=10, help="R5 显著性阈值（默认 10）")
    ap.add_argument("--json", action="store_true", help="以 JSON 输出，便于接入自动化")
    ap.add_argument("--strict", action="store_true", help="WARN 也视为失败（退出码 2）")
    args = ap.parse_args(argv)

    path = Path(args.resume)
    if not path.exists():
        _fail(f"文件不存在: {path}", args.json)
    text = path.read_text(encoding="utf-8")

    facts_text = None
    if args.facts:
        fpath = Path(args.facts)
        if not fpath.exists():
            _fail(f"档案文件不存在: {fpath}", args.json)
        facts_text = fpath.read_text(encoding="utf-8")

    kws = args.keywords.split(",") if args.keywords else None
    issues = check(text, facts_text, kws, args.max_width, args.min_number)

    n_err = sum(1 for lv, _, _ in issues if lv == "ERROR")
    n_warn = sum(1 for lv, _, _ in issues if lv == "WARN")
    n_info = sum(1 for lv, _, _ in issues if lv == "INFO")

    if args.json:
        print(
            json.dumps(
                {
                    "file": str(path),
                    "issues": [{"level": lv, "line": no, "message": msg} for lv, no, msg in issues],
                    "summary": {"error": n_err, "warn": n_warn, "info": n_info},
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print(f"== project-packer lint：{path.name} ==")
        if not issues:
            print("全部机械检查通过 ✅")
        for lv, no, msg in issues:
            loc = f"L{no}" if no != "-" else "--"
            print(f"[{lv}] {loc} {msg}")
        print(f"== 汇总：ERROR {n_err} / WARN {n_warn} / INFO {n_info} ==")

    if n_err:
        sys.exit(2)
    if n_warn and args.strict:
        sys.exit(2)
    sys.exit(1 if n_warn else 0)


def _fail(message, as_json):
    if as_json:
        print(json.dumps({"error": message}, ensure_ascii=False))
    else:
        print(f"[ERROR] {message}")
    sys.exit(2)


if __name__ == "__main__":
    main()
