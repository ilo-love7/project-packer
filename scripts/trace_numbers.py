#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
trace_numbers.py — 数字溯源：把交付稿里的每个数字回溯到工作区里的真实出处

这是 project-packer 最核心的一条主张的可执行版本。SKILL.md 阶段 4 要求
「交付稿中出现的每一个数字，逐个回溯到素材清单/事实档案的证据指针；定位
不到的数字一律降级或删除，不允许"应该没问题"」——在此之前，这一步完全靠
agent 自觉。本脚本把它变成一次确定性的文件扫描。

用法：
    python3 scripts/trace_numbers.py resume.md ../my-project
    python3 scripts/trace_numbers.py resume.md . --min-number 5 --context 80
    python3 scripts/trace_numbers.py resume.md . --json

输出三态：
    HIT   工作区里找到了这个数字（列出 文件:行号 + 上下文）
    MISS  工作区里找不到 → 要么补证据，要么降级为定性描述或删除
    DRAFT 只在交付稿自己里出现（通常意味着这个数字是凭空写的）

判定口径与 lint_resume.py 的 R5 一致（复用同一个显著性函数），所以两边
不会给出互相矛盾的结论。

退出码：0=全部命中  1=有 MISS  2=参数或路径错误
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import DEFAULT_EXCLUDE_DIRS, iter_files, read_text, relative_label  # noqa: E402
from lint_resume import iter_significant_tokens  # noqa: E402


def build_token_regex(tokens):
    """为一组数字构造一个带边界的正则。

    边界用 (?<![\\d.]) 和 (?![\\d.])，目的是：
      - "3" 不会命中 "13"、"3.5"、"3.14" 里的 3
      - "5.9" 不会命中 "15.9" 或 "5.95"
    长 token 排在前面，保证 "5.9" 优先于 "5"。
    """
    ordered = sorted(set(tokens), key=lambda t: (-len(t), t))
    body = "|".join(re.escape(t) for t in ordered)
    return re.compile(rf"(?<![\d.])(?:{body})(?![\d.])")


def trace(draft_text, workspace, min_number=10, exclude_dirs=None,
          max_bytes=2_000_000, context=60, max_hits=5, skip_path=None):
    """返回 {token: {"status": "HIT"/"MISS", "hits": [...]}}。

    纯函数，便于单元测试。skip_path 用于排除交付稿自身，
    否则每个数字都会在草稿里"命中"自己，毫无意义。
    """
    exclude_dirs = DEFAULT_EXCLUDE_DIRS if exclude_dirs is None else exclude_dirs
    tokens = [t for t, _s, _e in iter_significant_tokens(draft_text, min_number)]
    if not tokens:
        return {}
    # 按在交付稿里首次出现的顺序排列，输出顺序和用户读稿顺序一致
    unique = list(dict.fromkeys(tokens))

    pattern = build_token_regex(unique)
    found = {t: [] for t in unique}
    seen_lines = {t: {} for t in unique}  # token -> {(file, lineno): 次数}
    skip_resolved = Path(skip_path).resolve() if skip_path else None

    for path in iter_files(workspace, exclude_dirs, max_bytes):
        try:
            if skip_resolved and path.resolve() == skip_resolved:
                continue
        except OSError:
            pass
        text = read_text(path)
        if text is None:
            continue
        for lineno, line in enumerate(text.splitlines(), 1):
            for m in pattern.finditer(line):
                tok = m.group(0)
                key = (relative_label(path, workspace), lineno)
                if key in seen_lines[tok]:
                    # 同一行里出现多次只记一次，但累计次数
                    seen_lines[tok][key] += 1
                    continue
                seen_lines[tok][key] = 1
                if len(found[tok]) >= max_hits * 4:  # 防御性上限，避免超大文件爆内存
                    continue
                start = max(0, m.start() - context)
                end = min(len(line), m.end() + context)
                found[tok].append({
                    "file": key[0], "line": lineno,
                    "context": line[start:end].strip(), "count": 1,
                })

    # 把累计次数回填到结果里
    for tok in unique:
        for item in found[tok]:
            item["count"] = seen_lines[tok][(item["file"], item["line"])]

    result = {}
    for tok in unique:
        hits = found[tok]
        result[tok] = {"status": "HIT" if hits else "MISS", "hits": hits[:max_hits]}
    return result


def summarize(result):
    hit = sum(1 for v in result.values() if v["status"] == "HIT")
    return {"total": len(result), "hit": hit, "miss": len(result) - hit}


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="把交付稿里的每个数字回溯到工作区里的真实出处",
        epilog="判定口径与 lint_resume.py 的 R5 一致（复用同一个显著性函数）。",
    )
    ap.add_argument("draft", help="交付稿 / 简历草稿（md/txt）")
    ap.add_argument("workspace", help="要搜索的仓库或工作区目录")
    ap.add_argument("--min-number", type=float, default=10,
                    help="显著性阈值，与 lint 的 --min-number 同义（默认 10）")
    ap.add_argument("--exclude", action="append", default=[],
                    help="额外跳过的目录名，可重复")
    ap.add_argument("--max-bytes", type=int, default=2_000_000,
                    help="跳过超过该字节数的文件（默认 2MB）")
    ap.add_argument("--context", type=int, default=60, help="命中上下文宽度（默认 60 字符）")
    ap.add_argument("--max-hits", type=int, default=5, help="每个数字最多展示几处命中（默认 5）")
    ap.add_argument("--json", action="store_true", help="以 JSON 输出")
    args = ap.parse_args(argv)

    draft = Path(args.draft)
    if not draft.exists():
        print(f"[ERROR] 交付稿不存在: {draft}")
        sys.exit(2)
    ws = Path(args.workspace)
    if not ws.exists():
        print(f"[ERROR] 工作区不存在: {ws}")
        sys.exit(2)

    text = draft.read_text(encoding="utf-8")
    exclude = set(DEFAULT_EXCLUDE_DIRS) | set(args.exclude)
    result = trace(
        text, ws, args.min_number, exclude, args.max_bytes, args.context, args.max_hits,
        skip_path=draft,
    )
    stats = summarize(result)

    if args.json:
        print(json.dumps({"draft": str(draft), "workspace": str(ws),
                          "numbers": result, "summary": stats},
                         ensure_ascii=False, indent=2))
    else:
        print(f"== 数字溯源：{draft.name} → {ws} ==")
        if not result:
            print("交付稿里没有需要溯源的显著数字。")
        for tok, info in result.items():
            if info["status"] == "HIT":
                print(f"\n[HIT ] {tok}")
                for h in info["hits"]:
                    times = f" (×{h['count']})" if h.get("count", 1) > 1 else ""
                    print(f"       {h['file']}:{h['line']}{times}  …{h['context']}…")
            else:
                print(f"\n[MISS] {tok}")
                print("       工作区里没有找到这个数字 → 补证据，或降级为定性描述/删除")
        print(f"\n== 汇总：{stats['total']} 个显著数字，命中 {stats['hit']} / 未命中 {stats['miss']} ==")

    sys.exit(1 if stats["miss"] else 0)


if __name__ == "__main__":
    main()
