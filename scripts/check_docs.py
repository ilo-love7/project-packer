#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
check_docs.py — 文档一致性检查（离线、零依赖）

这个 skill 的"产品"就是一堆 Markdown，但它没有任何编译期错误——写错一个
数字（"21 条"实际 22 条、"6 阶段"实际 8 阶段）不会报错，只会悄悄误导用户
和 agent 自己。本脚本把这类不一致变成可执行的检查。

用法：
    python3 scripts/check_docs.py
    python3 scripts/check_docs.py --json

检查项：
  C1 版本号：SKILL.md frontmatter 的 version 与两版 README 徽章一致
  C2 阶段数：README 声明的阶段数与 SKILL.md 实际的「阶段 N」数量一致
  C3 审计条目：README 声明的条数与 integrity-audit.md 实际编号条目一致
  C4 编号完整性：审计清单编号从 1 连续、无重复、无跳号
  C5 章节引用：所有「第 N 节「名称」」引用与 templates.md 实际标题匹配
  C6 双语对齐：两版 README 的二级标题数量一致
  C7 相对链接：所有 ./xxx 链接指向的文件真实存在

退出码：0=全部通过  1=有 FAIL
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

STAGE_RE = re.compile(r"^### 阶段 (\d+)：", re.M)
SECTION_HEAD_RE = re.compile(r"^## (\d+)\. (.+)$", re.M)
AUDIT_ITEM_RE = re.compile(r"^(\d+)\. ", re.M)
VERSION_RE = re.compile(r"^version:\s*(\S+)\s*$", re.M)
BADGE_VERSION_RE = re.compile(r"badge/version-([0-9][0-9.]*)-")
README_STAGES_RE = re.compile(r"(\d+)\s*阶段|(\d+)-stage")
README_ITEMS_RE = re.compile(r"(\d+)\s*条|(\d+)\s+items")
XREF_RE = re.compile(r"第 (\d+) 节「([^」]+)」")
MD_LINK_RE = re.compile(r"\]\((\./[^)\s]+)\)")
HREF_RE = re.compile(r'href="(\./[^"]+)"')


def fenced_blocks(text):
    """返回所有围栏代码块的内容（``` 或 ~~~ 包裹）。

    阶段数、审计条数这类「声明」只认目录树代码块里的写法，不认正文散文。
    原因是更新日志里会出现「README 曾宣称 6-stage」这种引用旧值的句子，
    全文扫描会把它误判成当前声明。精确性优先于覆盖面。
    """
    blocks, buf, fence = [], None, None
    for line in text.splitlines():
        stripped = line.strip()
        if fence is None and stripped.startswith(("```", "~~~")):
            fence, buf = stripped[:3], []
        elif fence is not None and stripped.startswith(fence):
            blocks.append("\n".join(buf))
            fence, buf = None, None
        elif fence is not None:
            buf.append(line)
    return blocks


def declared_counts(text, marker, pattern):
    """在目录树代码块里，取包含 marker 的行中匹配 pattern 的数字集合。"""
    found = set()
    for block in fenced_blocks(text):
        for line in block.splitlines():
            if marker not in line:
                continue
            for groups in pattern.findall(line):
                for g in groups:
                    if g:
                        found.add(int(g))
    return found


def read(path, root=None):
    return (Path(root or ROOT) / path).read_text(encoding="utf-8")


def check(root=None):
    """返回 issues 列表 [(级别, 检查项, 消息)]，级别为 PASS / FAIL / SKIP。

    root 可指向一份 fixture 目录，便于单元测试构造"故意写错"的样本。
    """
    root = Path(root or ROOT)
    issues = []

    def add(level, code, msg):
        issues.append((level, code, msg))

    # C1 版本号
    skill = read("SKILL.md", root)
    m = VERSION_RE.search(skill)
    if not m:
        add("FAIL", "C1", "SKILL.md frontmatter 缺少 version 字段")
        skill_version = None
    else:
        skill_version = m.group(1)
        for readme in ("README.md", "README.zh-CN.md"):
            badges = set(BADGE_VERSION_RE.findall(read(readme, root)))
            if not badges:
                add("FAIL", "C1", f"{readme} 未找到版本徽章")
            elif badges != {skill_version}:
                add(
                    "FAIL",
                    "C1",
                    f"{readme} 徽章版本 {sorted(badges)} ≠ SKILL.md version {skill_version}",
                )
            else:
                add("PASS", "C1", f"{readme} 徽章版本与 SKILL.md 一致（{skill_version}）")

    # C2 阶段数
    stages = [int(n) for n in STAGE_RE.findall(skill)]
    n_stages = len(stages)
    if stages != list(range(n_stages)):
        add("FAIL", "C2", f"SKILL.md 阶段编号不连续：{stages}")
    for readme in ("README.md", "README.zh-CN.md"):
        text = read(readme, root)
        claimed = declared_counts(text, "SKILL.md", README_STAGES_RE)
        bad = {c for c in claimed if c != n_stages}
        if bad:
            add("FAIL", "C2", f"{readme} 声明阶段数 {sorted(bad)} ≠ SKILL.md 实际 {n_stages} 个")
        elif claimed:
            add("PASS", "C2", f"{readme} 阶段数声明正确（{n_stages}）")

    # C3 + C4 审计条目
    audit = read("references/integrity-audit.md", root)
    items = [int(n) for n in AUDIT_ITEM_RE.findall(audit)]
    n_items = len(items)
    if items != list(range(1, n_items + 1)):
        dup = sorted({n for n in items if items.count(n) > 1})
        missing = [n for n in range(1, max(items) + 1) if n not in items]
        detail = []
        if dup:
            detail.append(f"重复编号 {dup}")
        if missing:
            detail.append(f"跳号 {missing}")
        add("FAIL", "C4", f"integrity-audit.md 编号异常（共 {n_items} 条）：{'，'.join(detail)}")
    else:
        add("PASS", "C4", f"integrity-audit.md 编号 1-{n_items} 连续无重复")

    for readme in ("README.md", "README.zh-CN.md"):
        text = read(readme, root)
        claimed = declared_counts(text, "integrity-audit", README_ITEMS_RE)
        bad = {c for c in claimed if c != n_items}
        if bad:
            add("FAIL", "C3", f"{readme} 声明审计 {sorted(bad)} 条 ≠ 实际 {n_items} 条")
        elif claimed:
            add("PASS", "C3", f"{readme} 审计条数声明正确（{n_items}）")

    # C5 章节引用
    sections = {int(n): title.strip() for n, title in SECTION_HEAD_RE.findall(read("references/templates.md", root))}
    xref_files = ["SKILL.md", "references/templates.md"] + [
        str(p.relative_to(root)).replace("\\", "/")
        for p in sorted((root / "references").glob("*.md"))
        if p.name != "templates.md"
    ]
    seen = set()
    for f in dict.fromkeys(xref_files):
        for n, name in XREF_RE.findall(read(f, root)):
            seen.add((int(n), name, f))
    for n, name, f in sorted(seen):
        actual = sections.get(n)
        if actual is None:
            add("FAIL", "C5", f"{f} 引用第 {n} 节「{name}」，但 templates.md 没有第 {n} 节")
        elif not actual.startswith(name):
            # 只接受"实际标题的前缀"——这样「替代量化」能匹配「替代量化（无硬数字时用）」，
            # 但「量化」匹配不上，避免引用写窄了却蒙混过关。
            add("FAIL", "C5", f"{f} 引用第 {n} 节「{name}」，实际标题是「{actual}」")
    if seen:
        add("PASS", "C5", f"章节引用全部有效（{len(seen)} 处）")

    # C6 双语对齐
    h2 = lambda t: re.findall(r"^## (.+)$", t, re.M)
    en, zh = h2(read("README.md", root)), h2(read("README.zh-CN.md", root))
    if len(en) != len(zh):
        add("FAIL", "C6", f"两版 README 二级标题数不一致（EN {len(en)} / ZH {len(zh)}）")
    else:
        add("PASS", "C6", f"两版 README 章节数一致（{len(en)}）")

    # C7 相对链接
    broken = []
    for p in sorted(root.rglob("*.md")):
        if ".git" in p.parts:
            continue
        text = p.read_text(encoding="utf-8")
        for target in set(MD_LINK_RE.findall(text)) | set(HREF_RE.findall(text)):
            if not (p.parent / target.lstrip("./")).resolve().exists():
                broken.append(f"{p.relative_to(root)} → {target}")
    if broken:
        for b in broken:
            add("FAIL", "C7", f"相对链接失效：{b}")
    else:
        add("PASS", "C7", "相对链接全部有效")

    return issues


def main(argv=None):
    ap = argparse.ArgumentParser(description="project-packer 文档一致性检查")
    ap.add_argument("--json", action="store_true", help="以 JSON 输出")
    args = ap.parse_args(argv)

    issues = check()
    n_fail = sum(1 for lv, _, _ in issues if lv == "FAIL")

    if args.json:
        print(
            json.dumps(
                {
                    "issues": [{"level": lv, "code": c, "message": m} for lv, c, m in issues],
                    "summary": {"fail": n_fail, "pass": len(issues) - n_fail},
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print("== project-packer 文档一致性检查 ==")
        for lv, code, msg in issues:
            print(f"[{lv}] {code} {msg}")
        print(f"== 汇总：FAIL {n_fail} / PASS {len(issues) - n_fail} ==")

    sys.exit(1 if n_fail else 0)


if __name__ == "__main__":
    main()
