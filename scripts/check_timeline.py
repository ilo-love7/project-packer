#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_timeline.py — 总时间轴与区间矛盾检查（离线、零依赖）

用法：
    python3 check_timeline.py resume.md
    python3 check_timeline.py 交付包.md --gap-months 3
    python3 check_timeline.py resume.md --today 2026.10
    python3 check_timeline.py resume.md --json

为什么需要这个工具：
  SKILL.md 硬约束 5 说「多段经历时间线不得矛盾（核对总时间轴）」。
  lint_resume.py 的 R3 只查日期**格式**混用，不看区间之间的关系。
  「核对总时间轴」这句话以前是一句要求，不是一件事——这个脚本把它变成
  一个可以直接看的输出：所有区间排成一列，重叠、倒挂、空档一目了然。

检查项：
  REVERSED 区间倒挂（结束早于开始）                              → ERROR
  FUTURE   开始时间在未来                                        → WARN
  OVERLAP  两段「占满时间」的经历重叠（都标了全职/实习/在职）      → WARN
  PARALLEL 两段经历部分重叠，但不是都占满时间（在校期间做项目）    → INFO
  GAP      相邻经历之间空档超过阈值（默认 6 个月）                → INFO

为什么重叠只在一部分情况下报 WARN：
  在校期间同时有课程项目、竞赛、学生工作是常态，把它们报成"时间线矛盾"
  等于每次跑都刷一屏黄字。真正会矛盾的是**两段都声称占满时间**的经历——
  比如「2025.03-06 全职实习」和「2025.03-06 在职工作」。所以只有两段的
  标签都命中全职类词时才升级为 WARN，其余降为 INFO 并说明是并行经历。
  区间完全相同的一律不报：同期的两个课程项目本来就该同区间。

退出码：0=干净  1=有 WARN  2=有 ERROR（或参数错误）
"""
import argparse
import json
import re
import sys
from datetime import date
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lint_resume import display_width  # noqa: E402

# 时间 token：年份 + 可选月份（支持 2024.09 / 2024-09 / 2024/9 / 2024年9月），
# 以及"至今"类词。月份必须 <=12 且后面不接数字，否则 "2024-2025" 会把
# 2025 的前两位当成月份。
TOKEN_RE = re.compile(
    r"(?P<year>(?:19|20)\d{2})(?:\s*[.\-/年]\s*(?P<month>0?[1-9]|1[0-2])\s*月?(?![0-9]))?"
    r"|(?P<now>至今|现在|目前|present|now|current|(?<!至)今(?![天年]))",
    re.I,
)
# 两个 token 之间只有这些字符，才算一个区间（"2025.09 - 2025.12"）
SEP_RE = re.compile(r"^\s*[-–—~～至到]\s*$")

# 标签里出现这些词，说明这段经历声称占满时间
FULLTIME_HINTS = ("全职", "实习", "在职", "任职", "工作经历", "正式员工", "full-time", "fulltime")
# 教育背景是"背景区间"，不是与他人竞争时间的经历：和它重叠永远正常，
# 报出来只会让每份学生简历都刷三条 INFO。
EDUCATION_HINTS = (
    "大学", "学院", "本科", "硕士", "博士", "研究生", "高中", "中学", "学校",
    "university", "college", "bachelor", "master", "phd",
)
# 明显不是"经历"的行，不当作标签向下传递
LABEL_STOPWORDS = ("技能", "证书", "自我评价", "联系方式")

MAX_LISTED = 12


def month_index(year, month):
    return year * 12 + (month - 1)


def from_month_index(idx):
    y, m = divmod(idx, 12)
    return y, m + 1


def fmt(idx):
    y, m = from_month_index(idx)
    return f"{y}.{m:02d}"


def pad(text, width=19):
    """按显示宽度补齐——「2025.03 - 至今」里两个汉字占 4 列，
    用 str 的 <19 补出来的表格是歪的。"""
    return text + " " * max(1, width - display_width(text))


def clean_label(text):
    """去掉 Markdown 列表符号、标题井号、结尾的分隔符。"""
    s = text.strip()
    s = re.sub(r"^[#>\s]*[-*·•+]?\s*", "", s)
    s = re.sub(r"[\s|｜:：\-–—]+$", "", s)
    return s.strip()


def parse_today(text):
    """--today 支持 2026.10 / 2026-10 / 2026；默认取系统当前月。

    月份分支必须写成 (1[0-2]|0?[1-9]) 且带 (?!\\d)：反过来写的话
    "2026.10" 会先被 0?[1-9] 吃掉 "1"，月份变成 1 月。
    """
    if not text:
        t = date.today()
        return month_index(t.year, t.month)
    m = re.match(r"^\s*((?:19|20)\d{2})(?:[.\-/年]\s*(1[0-2]|0?[1-9])(?!\d))?", text)
    if not m:
        raise ValueError(f"无法解析 --today：{text}")
    return month_index(int(m.group(1)), int(m.group(2) or 1))


class Entry:
    __slots__ = ("start", "end", "label", "line", "is_open")

    def __init__(self, start, end, label, line, is_open=False):
        self.start, self.end, self.label, self.line, self.is_open = start, end, label, line, is_open

    def key(self):
        return (self.start, self.end, self.label)

    @property
    def is_point(self):
        """单点日期（奖学金、证书）：能进总时间轴，但不参与重叠与空档计算。"""
        return self.start == self.end and not self.is_open

    @property
    def is_reversed(self):
        return self.end < self.start


def _token_span(line, match, today):
    """把一个 token 转成 (月份下标, 是否为"至今")；年份 token 返回 None 表示不可用。"""
    if match.group("now"):
        return today, True
    year = int(match.group("year"))
    month = int(match.group("month") or 1)
    return month_index(year, month), False


def extract_entries(text, today):
    """从文本里抽出所有时间区间与单点。返回 [Entry]。"""
    entries, last_label = [], ""
    for lineno, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line:
            continue
        # 表格行不是"经历"：交付包的审计表、修订记录里到处是日期，
        # 当成区间会凭空造出一堆重叠和倒挂。简历的时间线只写在正文行里。
        if line.startswith("|"):
            continue
        toks = list(TOKEN_RE.finditer(line))
        if not toks:
            cleaned = clean_label(line)
            if cleaned and not any(w in cleaned for w in LABEL_STOPWORDS):
                last_label = cleaned
            continue

        head = clean_label(line[: toks[0].start()])
        label = head or last_label or "（未命名）"

        i = 0
        while i < len(toks):
            t = toks[i]
            if i + 1 < len(toks):
                between = line[t.end(): toks[i + 1].start()]
                start_ok = t.group("year")  # 区间起点必须是具体年份，"至今-2025" 不算
                if start_ok and SEP_RE.match(between):
                    start, _ = _token_span(line, t, today)
                    end, is_open = _token_span(line, toks[i + 1], today)
                    entries.append(Entry(start, end, label, lineno, is_open))
                    i += 2
                    continue
            if t.group("year"):
                at, _ = _token_span(line, t, today)
                entries.append(Entry(at, at, label, lineno))
            i += 1
    return _dedupe(entries)


def _dedupe(entries):
    """同一个 (起点, 终点, 标签) 只留一条——交付包里同一段经历会出现多次。"""
    seen, out = set(), []
    for e in entries:
        if e.key() in seen:
            continue
        seen.add(e.key())
        out.append(e)
    return sorted(out, key=lambda e: (e.start, e.end))


def _is_fulltime(label):
    low = label.lower()
    return any(h in low for h in FULLTIME_HINTS)


def _is_education(label):
    low = label.lower()
    return any(h in low for h in EDUCATION_HINTS)


def check(entries, today, gap_months=6):
    """返回 issues 列表 [(级别, 代码, 消息)]。纯函数，便于测试。"""
    issues = []

    for e in entries:
        if e.is_reversed:
            issues.append(
                ("ERROR", "REVERSED", f"区间倒挂：{fmt(e.start)}-{fmt(e.end)}「{e.label}」结束早于开始")
            )
        elif e.start > today:
            issues.append(("WARN", "FUTURE", f"开始时间在未来：{fmt(e.start)}「{e.label}」"))

    # 只拿"经历区间"参与重叠与空档：排除单点、倒挂、教育背景。
    # 教育是背景跨度（在校 4 年），和任何一段经历重叠都是正常的。
    spans = [e for e in entries if not e.is_point and not e.is_reversed and not _is_education(e.label)]

    for a, b in combinations(spans, 2):
        if a.end < b.start or b.end < a.start:
            continue
        if (a.start, a.end) == (b.start, b.end):
            continue  # 同区间：同期的两个项目，正常
        months = min(a.end, b.end) - max(a.start, b.start) + 1
        span = f"{fmt(max(a.start, b.start))}-{fmt(min(a.end, b.end))} 重叠 {months} 个月"
        pair = f"「{a.label}」×「{b.label}」"
        if _is_fulltime(a.label) and _is_fulltime(b.label):
            issues.append(
                ("WARN", "OVERLAP", f"{span}：{pair} 两段都声称占满时间 → 确认是否矛盾")
            )
        else:
            issues.append(("INFO", "PARALLEL", f"{span}：{pair} 并行经历，不一定是问题"))

    ordered = sorted(spans, key=lambda e: e.start)
    reach = ordered[0].end if ordered else None
    for e in ordered[1:]:
        gap = e.start - reach - 1
        if gap >= gap_months:
            issues.append(
                ("INFO", "GAP", f"空档 {gap} 个月：{fmt(reach)} 之后到 {fmt(e.start)}「{e.label}」")
            )
        reach = max(reach, e.end)

    return issues


def main(argv=None):
    ap = argparse.ArgumentParser(description="总时间轴与区间矛盾检查")
    ap.add_argument("file", help="简历或交付稿（md/txt）")
    ap.add_argument("--today", help="当前月份，如 2026.10（默认取系统日期）")
    ap.add_argument("--gap-months", type=int, default=6, help="空档提示阈值（默认 6 个月）")
    ap.add_argument("--json", action="store_true", help="以 JSON 输出")
    args = ap.parse_args(argv)

    path = Path(args.file)
    if not path.exists():
        _fail(f"文件不存在: {path}", args.json)
    try:
        today = parse_today(args.today)
    except ValueError as e:
        _fail(str(e), args.json)

    text = path.read_text(encoding="utf-8")
    entries = extract_entries(text, today)
    issues = check(entries, today, args.gap_months)

    n_err = sum(1 for lv, _c, _m in issues if lv == "ERROR")
    n_warn = sum(1 for lv, _c, _m in issues if lv == "WARN")
    n_info = sum(1 for lv, _c, _m in issues if lv == "INFO")

    if args.json:
        print(
            json.dumps(
                {
                    "file": str(path),
                    "today": fmt(today),
                    "entries": [
                        {
                            "start": fmt(e.start),
                            "end": fmt(e.end),
                            "open": e.is_open,
                            "label": e.label,
                            "line": e.line,
                        }
                        for e in entries
                    ],
                    "issues": [{"level": lv, "code": c, "message": m} for lv, c, m in issues],
                    "summary": {"error": n_err, "warn": n_warn, "info": n_info},
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print(f"== project-packer 时间线：{path.name}（今天 {fmt(today)}）==")
        if not entries:
            print()
            print("没有识别到任何时间区间。日期格式支持 2024.09 / 2024-09 / 2024年9月 / 至今。")
        else:
            print()
            print("总时间轴")
            for e in entries:
                if e.is_point:
                    span = fmt(e.start)
                else:
                    span = f"{fmt(e.start)} - {'至今' if e.is_open else fmt(e.end)}"
                print(f"  {pad(span)} {e.label}")
            print()
            if not issues:
                print("区间之间没有矛盾 ✅")
            for lv, code, msg in issues:
                print(f"[{lv}] {code} {msg}")
        print()
        print(f"== 汇总：ERROR {n_err} / WARN {n_warn} / INFO {n_info} ==")

    if n_err:
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
