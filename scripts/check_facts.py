#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_facts.py — 事实档案 × 多版本简历的三向对账（离线、零依赖）

用法：
    python3 check_facts.py facts.md 简历-后端.md 简历-测试.md
    python3 check_facts.py facts.md "简历-*.md"          # 通配符
    python3 check_facts.py facts.md resumes/             # 目录（取 *.md）
    python3 check_facts.py facts.md 简历-后端.md --json

为什么需要这个工具：
  SKILL.md 硬约束 7 说「档案是唯一事实源，不允许两个版本并存」，
  multi-project.md 铁律 1 说「数字在所有版本里完全一致」，
  fact-file.md 规则 2 说「输出前 diff」。这三条在此之前全靠 agent 记得做。
  lint_resume.py --facts 只能拿一份稿对一份档案，查不出「两份简历互相打架」。

检查项：
  CONFLICT 同一指标在不同版本里数字不同，且措辞完全相同（高置信）    → ERROR
  SUSPECT  同一指标在不同版本里数字不同，措辞不同但上下文相同（待确认） → WARN
  ORPHAN   某版本里的数字不在事实档案中（该入档）                    → WARN
  IDLE     档案里有、但任何版本都没用到的数字（素材闲置）             → INFO

两级冲突判定的口径（重要，别高估它）：
  CONFLICT：把整行里所有数字替换成 # 得到「措辞骨架」，再记下该数字是行内第几个。
            骨架 + 序号都相同却写了不同数字 = 复制粘贴后顺手改了一个数。
            零误报，也是实际最常见、最危险的一类漂移。
  SUSPECT： 骨架不同（L1 完整版和 L2 精简版措辞本来就不一样），但数字前后各 6 个
            字符的局部上下文一致，且来自不同文件 = 疑似同一个指标。
            会有误报（两个项目恰好都写「准确率 95%」），所以只报警告、交人确认。
  两者都不覆盖的情况：同一指标换了说法、连单位词都换了。工具只报它确定的部分，
  剩下的交给语义层——把不确定的猜出来当错误报，用户会把整个工具关掉。

为什么 IDLE 是 INFO 而不是 WARN：
  档案本来就是全集，L4 档（只进面试、不上简历）的素材按设计就不出现在简历里。
  把"没用上"报成警告，每次跑都是一屏黄字，最后一定会被关掉。

退出码：0=干净  1=有 SUSPECT/ORPHAN  2=有 CONFLICT（或参数错误）
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lint_resume import (  # noqa: E402
    NUM_RE,
    _mask_dates,
    extract_numbers,
    is_significant_token,
)

# 完整日期（YYYY-MM-DD / YYYY.MM.DD / YYYY/MM/DD）要先整体吃掉。
# 否则 DATE_PATTERNS 只认到「2026-10」，剩下的「-22」会当成数字 22 报出来。
FULL_DATE_RE = re.compile(
    r"\b(?:19|20)\d{2}[-./]\s?(?:0?[1-9]|1[0-2])[-./]\s?(?:0?[1-9]|[12]\d|3[01])\b"
)

CONTEXT_CHARS = 6       # SUSPECT 判定的上下文窗口（数字前后各几个字符）
MAX_IDLE_SHOWN = 10
SNIPPET_WIDTH = 52


def mask_dates(text):
    """把各种日期替换成等长空格，保持字符下标不变。"""
    text = FULL_DATE_RE.sub(lambda m: " " * len(m.group(0)), text)
    return _mask_dates(text)


def _context(line, start, end):
    """取数字前后各 CONTEXT_CHARS 个字符，数字本身替换成 #。

    局部上下文相同 = 同一个指标位。窗口取 6 是因为中文指标名大多在 2-5 字，
    再宽就会把两条不同 bullet 的共同尾缀也算进来。
    """
    pre = NUM_RE.sub("#", line[max(0, start - CONTEXT_CHARS):start])
    post = NUM_RE.sub("#", line[end:end + CONTEXT_CHARS])
    return " ".join((pre + "#" + post).split())


def occurrences(text, min_number=10):
    """产出每个显著数字的出现记录。

    返回 [{"slot": (骨架, 序号), "ctx": str, "token": str, "line": int, "snippet": str}, ...]

    序号按行内**全部**数字匹配来数（含年份、含低信号数字），这样同一行在
    不同版本里即使某个数字被删掉，其余数字的序号也不会整体错位——
    只有真的在同一个位置上换了数字才会被判成 CONFLICT。
    """
    out = []
    masked = mask_dates(text)
    for lineno, line in enumerate(masked.splitlines(), 1):
        matches = list(NUM_RE.finditer(line))
        if not matches:
            continue
        skeleton = NUM_RE.sub("#", line).strip()
        for idx, m in enumerate(matches):
            if not is_significant_token(line, m, min_number):
                continue
            out.append(
                {
                    "slot": (skeleton, idx),
                    "ctx": _context(line, m.start(), m.end()),
                    "token": m.group(0),
                    "line": lineno,
                    "snippet": _snippet(line),
                }
            )
    return out


def _snippet(line, width=SNIPPET_WIDTH):
    """行内片段，太长的截断——骨架已经够长了，显示原文只会刷屏。"""
    s = " ".join(line.split())
    return s if len(s) <= width else s[:width] + "…"


def _group(versions, min_number, key_name):
    """按 slot 或 ctx 归组，返回 {键: {数字: [(文件, 行号, 片段), ...]}}。"""
    groups = {}
    for name, text in versions.items():
        for occ in occurrences(text, min_number):
            groups.setdefault(occ[key_name], {}).setdefault(occ["token"], []).append(
                (name, occ["line"], occ["snippet"])
            )
    return groups


def _conflicts(versions, min_number):
    """高置信冲突：整行骨架 + 序号相同，数字不同。"""
    out = []
    for (skeleton, idx), tokens in _group(versions, min_number, "slot").items():
        if len(tokens) < 2:
            continue
        out.append(
            {
                "level": "CONFLICT",
                "skeleton": skeleton,
                "position": idx + 1,
                "values": [
                    {"token": tok, "occurrences": occs} for tok, occs in sorted(tokens.items())
                ],
            }
        )
    out.sort(key=lambda c: min(o[1] for v in c["values"] for o in v["occurrences"]))
    return out


def _suspects(versions, min_number, already):
    """低置信冲突：局部上下文相同，但整行措辞不同，且跨文件。

    already 是高置信冲突已覆盖的 (文件, 行号, 数字) 集合，用来避免同一处报两遍。
    """
    out = []
    for ctx, tokens in _group(versions, min_number, "ctx").items():
        if len(tokens) < 2:
            continue
        files = {name for occs in tokens.values() for name, _l, _s in occs}
        if len(files) < 2:  # 单份简历内部不算跨版本漂移
            continue
        hits = {(n, l, t) for t, occs in tokens.items() for n, l, _s in occs}
        if hits <= already:  # 整组都已被 CONFLICT 报过
            continue
        out.append(
            {
                "level": "SUSPECT",
                "skeleton": ctx,
                "position": None,
                "values": [
                    {"token": tok, "occurrences": occs} for tok, occs in sorted(tokens.items())
                ],
            }
        )
    out.sort(key=lambda c: min(o[1] for v in c["values"] for o in v["occurrences"]))
    return out


def reconcile(facts_text, versions, min_number=10):
    """三向对账。versions 是 {文件名: 文本}。纯函数，便于测试。

    返回 {"conflict": [...], "suspect": [...], "orphan": {文件: [...]}, "idle": [...]}
    """
    facts_numbers = set(extract_numbers(facts_text))  # 档案侧宽松取全集
    facts_sig = {occ["token"] for occ in occurrences(facts_text, min_number)}

    conflict = _conflicts(versions, min_number)
    covered = {
        (n, l, v["token"])
        for c in conflict
        for v in c["values"]
        for n, l, _s in v["occurrences"]
    }
    suspect = _suspects(versions, min_number, covered)

    # ORPHAN：某版本有、档案没有
    orphan = {}
    for name, text in versions.items():
        miss = {}
        for occ in occurrences(text, min_number):
            if occ["token"] not in facts_numbers:
                miss.setdefault(occ["token"], occ)
        if miss:
            orphan[name] = list(miss.values())

    # IDLE：档案有、所有版本都没用
    used = set()
    for text in versions.values():
        used.update(occ["token"] for occ in occurrences(text, min_number))
    idle = sorted(facts_sig - used)

    return {"conflict": conflict, "suspect": suspect, "orphan": orphan, "idle": idle}


def collect_versions(paths):
    """把命令行给的路径展开成 {显示名: 文本}；目录取其中的 *.md。"""
    versions = {}
    for raw in paths:
        p = Path(raw)
        if p.is_dir():
            for f in sorted(p.glob("*.md")):
                versions[str(f)] = f.read_text(encoding="utf-8")
        else:
            versions[str(p)] = p.read_text(encoding="utf-8")
    return versions


def main(argv=None):
    ap = argparse.ArgumentParser(description="事实档案与多版本简历的三向对账")
    ap.add_argument("facts", help="事实档案 facts.md")
    ap.add_argument("versions", nargs="+", help="一份或多份简历/交付稿（也可给目录或通配符）")
    ap.add_argument("--min-number", type=float, default=10, help="显著性阈值（默认 10）")
    ap.add_argument("--json", action="store_true", help="以 JSON 输出")
    args = ap.parse_args(argv)

    facts_path = Path(args.facts)
    if not facts_path.exists():
        _fail(f"档案文件不存在: {facts_path}", args.json)
    facts_text = facts_path.read_text(encoding="utf-8")

    try:
        versions = collect_versions(args.versions)
    except OSError as e:
        _fail(f"读取简历失败: {e}", args.json)
    if not versions:
        _fail("没有找到任何简历文件", args.json)

    result = reconcile(facts_text, versions, args.min_number)
    n_conflict = len(result["conflict"])
    n_suspect = len(result["suspect"])
    n_orphan = sum(len(v) for v in result["orphan"].values())
    n_idle = len(result["idle"])

    if args.json:
        print(
            json.dumps(
                {
                    "facts": str(facts_path),
                    "versions": list(versions),
                    "conflict": _json_slots(result["conflict"]),
                    "suspect": _json_slots(result["suspect"]),
                    "orphan": {
                        k: [{"token": o["token"], "line": o["line"], "snippet": o["snippet"]} for o in v]
                        for k, v in result["orphan"].items()
                    },
                    "idle": result["idle"],
                    "summary": {
                        "conflict": n_conflict,
                        "suspect": n_suspect,
                        "orphan": n_orphan,
                        "idle": n_idle,
                    },
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        _print_report(facts_path, versions, result)

    if n_conflict:
        sys.exit(2)
    sys.exit(1 if (n_suspect or n_orphan) else 0)


def _json_slots(items):
    return [
        {
            "skeleton": c["skeleton"],
            "position": c["position"],
            "values": [
                {
                    "token": v["token"],
                    "occurrences": [
                        {"file": str(Path(n).name), "line": l, "snippet": s}
                        for n, l, s in v["occurrences"]
                    ],
                }
                for v in c["values"]
            ],
        }
        for c in items
    ]


def _print_report(facts_path, versions, result):
    print(f"== project-packer 档案对账：{facts_path.name} × {len(versions)} 份简历 ==")

    for c in result["conflict"]:
        print()
        print(f"[CONFLICT] 「{c['skeleton']}」第 {c['position']} 个数字")
        _print_values(c)
        print("           → 同一指标跨版本数字不一致，比措辞弱致命得多，先对齐再交稿")

    for c in result["suspect"]:
        print()
        print(f"[SUSPECT ] 疑似同一指标「{c['skeleton']}」")
        _print_values(c)
        print("           → 上下文相同但措辞不同，可能是两个项目，人工确认是否同源")

    for name, items in result["orphan"].items():
        print()
        print(f"[ORPHAN] {Path(name).name}：{len(items)} 个数字不在档案里")
        for o in items:
            print(f"           L{o['line']}  {o['token']}  「{o['snippet']}」")
        print("           → 先入档（数字 + 口径 + 证据指针）再定稿，否则下次包装又会漂")

    if result["idle"]:
        shown = result["idle"][:MAX_IDLE_SHOWN]
        tail = f" 等 {len(result['idle'])} 个" if len(result["idle"]) > MAX_IDLE_SHOWN else ""
        print()
        print(f"[IDLE] 档案里有 {len(result['idle'])} 个数字没进任何版本（素材闲置）")
        print(f"           {' / '.join(shown)}{tail}")
        print("           → 不算问题：L4 素材按设计不上简历，可留作面试垫话")

    if not (result["conflict"] or result["suspect"] or result["orphan"] or result["idle"]):
        print()
        print("档案与所有版本一致 ✅")

    print()
    print(
        f"== 汇总：CONFLICT {len(result['conflict'])} / SUSPECT {len(result['suspect'])} / "
        f"ORPHAN {sum(len(v) for v in result['orphan'].values())} / IDLE {len(result['idle'])} =="
    )


def _print_values(c):
    for v in c["values"]:
        for name, line, _snip in v["occurrences"]:
            print(f"           {Path(name).name}:L{line}  {v['token']}")


def _fail(message, as_json):
    if as_json:
        print(json.dumps({"error": message}, ensure_ascii=False))
    else:
        print(f"[ERROR] {message}")
    sys.exit(2)


if __name__ == "__main__":
    main()
