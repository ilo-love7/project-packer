#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_delivery.py — 交付包结构检查（离线、零依赖）

用法：
    python3 scripts/check_delivery.py 交付包.md
    python3 scripts/check_delivery.py 交付包.md --template templates/delivery.template.md
    python3 scripts/check_delivery.py 交付包.md --json
    python3 scripts/check_delivery.py 交付包.md --strict

检查项：
  D1 节齐全：`## 1.` 到 `## 7.` 全部存在（`## 8.` 交付后动作可选）    → ERROR
  D2 节序：节号从 1 递增不重复，第 1 节必须是简历段                    → ERROR
  D3 占位符：模板自带的占位符还留着                                    → ERROR
             自己造的方括号占位符（如 `[日期]`）                        → WARN
  D4 机器检查表：6.1 必须逐项列出全部交付检查脚本                       → WARN
  D5 模板指令残留：还留着「怎么用这份模板」那段说明                     → ERROR

为什么要有这个工具：阶段 5 有两句话是硬要求——「节序不要改」「占位符必须全部替换」——
但在本工具之前，五个脚本没有一个看交付包的结构。实测：往一份合格交付包里插回
`[日期] [改了什么] [为什么]`，`lint_resume` / `check_timeline` / `scan_privacy`
三个工具全部放行（ERROR 0 / WARN 0）。结构问题的后果不是"难看"，
是用户把内部指令和占位符一起投给招聘方。

D3 为什么分两级：模板自带的占位符（`[项目名]`、`[动词]`、`[YYYY.MM-YYYY.MM]`）
是确定的——它就在模板里，出现了就是没替换，判 ERROR。用户自己造的方括号
（`[日期]`）只能靠形状猜，所以给 WARN。代价写在明处：一段合法中文注释
（`[注：本机压测口径]`）会被判成占位符，看到 WARN 请自己确认一次。

D3 不查什么：markdown 链接文字（`[文字](url)`）、列表复选框（`- [ ]` / `- [x]`）、
纯数字方括号（`[1]` 脚注、`[3-9]` 这类正则片段）。这几类长得像占位符但不是。

退出码：0=干净  1=有 WARN  2=有 ERROR（--strict 下 WARN 也算 2）
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from check_docs import DELIVERY_CHECKS  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_TEMPLATE = ROOT / "templates" / "delivery.template.md"

SECTION_RE = re.compile(r"^## (\d+)\.\s*(.*)$", re.M)
SUBSECTION_RE = re.compile(r"^### (\d+)\.(\d+)\s*(.*)$", re.M)
BRACKET_RE = re.compile(r"\[([^\[\]\n]{0,40})\]")
CHECKBOX_LINE_RE = re.compile(r"^\s*[-*]\s*\[[ xX]\]")
CJK_RE = re.compile(r"[\u4e00-\u9fff]")
DIGITS_ONLY_RE = re.compile(r"^[\d.\-–~]+$")

MANDATORY_SECTIONS = (1, 2, 3, 4, 5, 6, 7)
RESUME_SECTION = 1
MACHINE_CHECK_SECTION = "6.1"
TEMPLATE_INSTRUCTION = "怎么用这份模板"


def template_placeholders(template_text):
    """从模板里抽出「确定的占位符」词表。

    这是本工具最可靠的一条判据：占位符不需要猜，模板自己列了一份。
    排除链接文字、空 token、复选框和纯数字——它们不是占位符。
    """
    out = set()
    for m in BRACKET_RE.finditer(template_text):
        tok = m.group(1).strip()
        if m.end() < len(template_text) and template_text[m.end()] in "([":
            continue
        if not tok or tok.lower() == "x" or DIGITS_ONLY_RE.match(tok):
            continue
        out.add(tok)
    return out


def looks_like_placeholder(tok):
    """自己造的占位符只能靠形状认：含中文、或全大写短 token、或含 YYYY/MM。"""
    if not tok or DIGITS_ONLY_RE.match(tok):
        return False
    if CJK_RE.search(tok):
        return True
    if re.fullmatch(r"[A-Z]{1,3}", tok):
        return True
    return "YYYY" in tok or "MM" in tok


def _line_of(text, pos):
    return text.count("\n", 0, pos) + 1


def sections(text):
    """返回 [(节号, 标题, 行号)]。"""
    return [
        (int(m.group(1)), m.group(2).strip(), _line_of(text, m.start()))
        for m in SECTION_RE.finditer(text)
    ]


def machine_check_block(text):
    """截取 6.1 那一小节的内容，用于确认五项检查都记了。"""
    start = None
    for m in SUBSECTION_RE.finditer(text):
        if f"{m.group(1)}.{m.group(2)}" == MACHINE_CHECK_SECTION:
            start = m.end()
            break
    if start is None:
        return ""
    rest = text[start:]
    stop = re.search(r"^(?:###|\#\#)\s", rest, re.M)
    return rest[: stop.start()] if stop else rest


def check(text, template_text=None):
    """执行全部检查，返回 issues 列表 [(级别, 行号或'-', 消息)]。"""
    issues = []

    # D1 + D2：节齐全与节序
    secs = sections(text)
    nums = [n for n, _t, _l in secs]
    if not secs:
        issues.append(("ERROR", "-", "D1 没有任何「## N.」形式的节标题 → 这不是一份交付包"))
        return issues

    missing = [n for n in MANDATORY_SECTIONS if n not in nums]
    if missing:
        issues.append(
            ("ERROR", "-", f"D1 缺少第 {', '.join(map(str, missing))} 节 → 按模板补齐，节序不要改")
        )

    dup = sorted({n for n in nums if nums.count(n) > 1})
    if dup:
        issues.append(("ERROR", "-", f"D2 节号重复：{', '.join(map(str, dup))}"))

    if nums != sorted(nums):
        issues.append(("ERROR", "-", f"D2 节序错乱（实际顺序 {nums}）→ 恢复为 1→7 的模板节序"))

    first_no, first_title, first_line = secs[0]
    if first_no != RESUME_SECTION or "简历" not in first_title:
        issues.append(
            ("ERROR", first_line, f"D2 第 1 节应是简历段，实际是「{first_title}」→ 简历段必须在最前")
        )

    # D3：占位符
    tpl_tokens = template_placeholders(template_text) if template_text else set()
    hard, soft = [], []
    for no, line in enumerate(text.splitlines(), 1):
        is_checkbox = bool(CHECKBOX_LINE_RE.match(line))
        for m in BRACKET_RE.finditer(line):
            tok = m.group(1).strip()
            if is_checkbox and tok.lower() in ("", "x"):
                continue
            if m.end() < len(line) and line[m.end()] in "([":  # 链接文字
                continue
            if tok in tpl_tokens:
                hard.append((no, tok))
            elif looks_like_placeholder(tok):
                soft.append((no, tok))

    for no, tok in hard:
        issues.append(("ERROR", no, f"D3 模板占位符未替换：[{tok}] → 换成真实内容再交稿"))
    for no, tok in soft:
        issues.append(("WARN", no, f"D3 疑似残留占位符：[{tok}] → 确认是占位符就替换，是正常注释就忽略"))

    # D4：6.1 机器检查表要逐项记
    block = machine_check_block(text)
    if not block:
        issues.append(("WARN", "-", f"D4 找不到 {MACHINE_CHECK_SECTION} 机器检查小节 → 按模板补上五项记录"))
    else:
        absent = [s for s in DELIVERY_CHECKS if s not in block]
        if absent:
            issues.append(
                ("WARN", "-", f"D4 {MACHINE_CHECK_SECTION} 未记录：{', '.join(absent)} → 逐项记结果，不适用的写「未启用」")
            )

    # D5：模板说明残留
    if TEMPLATE_INSTRUCTION in text:
        issues.append(
            ("ERROR", _line_of(text, text.index(TEMPLATE_INSTRUCTION)),
             f"D5 还留着「{TEMPLATE_INSTRUCTION}」的说明 → 那是给写作者看的，投出去会暴露内部流程")
        )

    return issues


def main(argv=None):
    ap = argparse.ArgumentParser(description="project-packer 交付包结构检查")
    ap.add_argument("delivery", help="交付包文件（md）")
    ap.add_argument("--template", default=str(DEFAULT_TEMPLATE), help="交付模板路径，用于提取占位符词表")
    ap.add_argument("--json", action="store_true", help="以 JSON 输出")
    ap.add_argument("--strict", action="store_true", help="WARN 也视为失败（退出码 2）")
    args = ap.parse_args(argv)

    path = Path(args.delivery)
    if not path.exists():
        _fail(f"文件不存在: {path}", args.json)
    text = path.read_text(encoding="utf-8")

    tpl_path = Path(args.template)
    if not tpl_path.exists():
        _fail(f"模板文件不存在: {tpl_path}", args.json)
    template_text = tpl_path.read_text(encoding="utf-8")

    issues = check(text, template_text)

    n_err = sum(1 for lv, _, _ in issues if lv == "ERROR")
    n_warn = sum(1 for lv, _, _ in issues if lv == "WARN")

    if args.json:
        print(
            json.dumps(
                {
                    "file": str(path),
                    "issues": [{"level": lv, "line": no, "message": msg} for lv, no, msg in issues],
                    "summary": {"error": n_err, "warn": n_warn},
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print(f"== project-packer 交付包结构检查：{path.name} ==")
        if not issues:
            print("结构检查通过 ✅")
        for lv, no, msg in issues:
            loc = f"L{no}" if no != "-" else "--"
            print(f"[{lv}] {loc} {msg}")
        print(f"== 汇总：ERROR {n_err} / WARN {n_warn} ==")

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
