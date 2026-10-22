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
  C1  版本号：SKILL.md frontmatter 的 version 与两版 README 徽章一致
  C2  阶段数：README 声明的阶段数与 SKILL.md 实际的「阶段 N」数量一致
  C3  审计条目：README 声明的条数与 integrity-audit.md 实际编号条目一致
  C4  编号完整性：审计清单编号从 1 连续、无重复、无跳号
  C5  章节引用：所有「第 N 节「名称」」引用与 templates.md 实际标题匹配
  C6  双语对齐：两版 README 的二级标题数量一致
  C7  相对链接：所有 ./xxx 链接指向的文件真实存在
  C8  用例编号：evals.md 的分组编号从 1 连续、组别按字母顺序（缺文件则 SKIP）
  C9  更新日志：SKILL.md 的 version 在两版 README 的 changelog 里有对应条目
  C10 目录树完整：references/ 与 templates/ 下每个文件都出现在两版 README 里
  C11 路径引用：SKILL.md 里反引号标注的 references/scripts/templates 路径真实存在
  C12 模板覆盖：templates/delivery.template.md 的机器检查表列出全部检查脚本

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
EVAL_ITEM_RE = re.compile(r"^### ([A-Z])(\d+)\s", re.M)
# SKILL.md 里用反引号标注的路径。不含 * 是为了放过 glob 写法（如 example-*.md）。
BACKTICK_PATH_RE = re.compile(r"`((?:references|scripts|templates)/[A-Za-z0-9_./-]+)`")
CHANGELOG_ENTRY_RE = "summary><b>v{}<"

# 面向用户交付的机器检查脚本。check_docs.py 不在此列——它是本仓库的自检工具，
# 用户的交付包里不需要记录它。
DELIVERY_CHECKS = (
    "lint_resume",
    "check_timeline",
    "trace_numbers",
    "scan_privacy",
    "check_facts",
)


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

    # C8 用例编号：evals.md 每个分组从 1 连续，组别按字母顺序
    evals_path = root / "evals.md"
    if not evals_path.exists():
        add("SKIP", "C8", "没有 evals.md，跳过用例编号检查")
    else:
        pairs = [(ltr, int(n)) for ltr, n in EVAL_ITEM_RE.findall(read("evals.md", root))]
        if not pairs:
            add("SKIP", "C8", "evals.md 里没有「### A1 …」形式的用例编号")
        else:
            letters = list(dict.fromkeys(ltr for ltr, _ in pairs))
            problems = []
            if letters != sorted(letters):
                problems.append(f"分组顺序异常 {letters}")
            for ltr in letters:
                nums = [n for x, n in pairs if x == ltr]
                if nums != list(range(1, len(nums) + 1)):
                    dup = sorted({n for n in nums if nums.count(n) > 1})
                    detail = f"（重复 {dup}）" if dup else ""
                    problems.append(f"{ltr} 组编号 {nums}{detail}")
            if problems:
                add("FAIL", "C8", f"evals.md 用例编号异常：{'；'.join(problems)}")
            else:
                add("PASS", "C8", f"evals.md 用例编号连续（{len(letters)} 组 / {len(pairs)} 条）")

    # C9 更新日志：升了版本却没写日志，是纯 Markdown 项目最容易漏的一步
    if skill_version:
        entry = CHANGELOG_ENTRY_RE.format(skill_version)
        for readme in ("README.md", "README.zh-CN.md"):
            if entry in read(readme, root):
                add("PASS", "C9", f"{readme} 更新日志含 v{skill_version}")
            else:
                add("FAIL", "C9", f"{readme} 更新日志缺少 v{skill_version} 条目")

    # C10 目录树完整：新增 references/ 文件却忘了写进目录树，C7 查不出来
    doc_files = []
    for sub in ("references", "templates"):
        d = root / sub
        if d.is_dir():
            doc_files += sorted(d.glob("*.md"))
    if not doc_files:
        add("SKIP", "C10", "没有 references/ 或 templates/ 目录，跳过目录树检查")
    else:
        for readme in ("README.md", "README.zh-CN.md"):
            text = read(readme, root)
            missing = [f.name for f in doc_files if f.name not in text]
            if missing:
                add("FAIL", "C10", f"{readme} 目录树漏了：{', '.join(missing)}")
            else:
                add("PASS", "C10", f"{readme} 目录树覆盖全部 {len(doc_files)} 个文档")

    # C11 SKILL.md 里反引号标注的路径必须真实存在
    dangling = [
        p for p in sorted(set(BACKTICK_PATH_RE.findall(skill))) if not (root / p).exists()
    ]
    if dangling:
        for p in dangling:
            add("FAIL", "C11", f"SKILL.md 引用了不存在的路径：{p}")
    else:
        add("PASS", "C11", "SKILL.md 的路径引用全部存在")

    # C12 交付模板的机器检查表必须覆盖全部检查脚本
    # 这一条是被真实漂移逼出来的：时间线当年以「① 附加」插进阶段 4，没有重编号，
    # 结果 templates/delivery.template.md 的 6.1 表停在最早的三个脚本（机械/溯源/隐私），
    # 时间线与档案对账从没进过表。用户照模板填，那两项就永远不会被记录——
    # 而 SKILL.md 说它们「必跑」。模板才是用户真正复制的东西，它漏了等于要求漏了。
    # 用显式清单而不是 glob：check_docs.py 是本仓库的自检工具，不属于交付检查。
    # 新增面向交付的检查脚本时，把名字加进这里。
    tpl = root / "templates" / "delivery.template.md"
    if not tpl.exists():
        add("SKIP", "C12", "没有 templates/delivery.template.md，跳过")
    else:
        body = tpl.read_text(encoding="utf-8")
        missing = [s for s in DELIVERY_CHECKS if s not in body]
        if missing:
            add("FAIL", "C12", f"交付模板 6.1 未覆盖：{', '.join(missing)}")
        else:
            add("PASS", "C12", f"交付模板覆盖全部 {len(DELIVERY_CHECKS)} 个交付检查脚本")

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
