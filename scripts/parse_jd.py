#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
parse_jd.py — 从 JD 原文里抽出技能词，直接喂给 lint_resume.py（离线、零依赖）

用法：
    python3 parse_jd.py jd.txt
    python3 parse_jd.py jd.txt --keywords-only     # 只打印逗号串，方便管道
    python3 parse_jd.py jd.txt --json
    python3 parse_jd.py jd.txt --extra "因果推断,增量实验"

为什么需要这个工具：
  lint_resume.py 的 --keywords 要用户自己把 JD 拆成逗号串。可真实动作是把 JD
  整段粘进来——拆词这一步以前全靠 agent 手工做，做得好不好全看当次状态。
  这个脚本把拆词变成可复跑的一步。

分词策略（不依赖任何分词库）：
  1. 词典命中：内置一份常见岗位词汇（硬技能 / 工具与平台 / 软技能），
     中文按子串匹配，英文按词边界匹配。
  2. 英文启发式：词典之外，形似技术词的英文 token 也算——含数字（S3、Vue3）、
     含 +#.（C++、C#、.NET）、全大写（SQL、AWS）、驼峰（FastAPI）。
     用停用词表压掉 the/and/you 这类噪音。
  3. 中文词典之外的新词抽不出来——这是已知边界。JD 里出现词典没有的中文术语时，
     用 --extra 补，或者看输出里的「未归类候选」自行判断。

输出按类别分组，每组按出现次数降序——出现 3 次的词是核心要求，
出现 1 次的多半是加分项，这个顺序直接对应证据映射表的优先级。

退出码：0=抽到关键词  1=没抽到  2=参数或路径错误
"""
import argparse
import json
import re
import sys
from pathlib import Path

# 词典只是"常见岗位的起点"，不是完备词表。宁可漏，不可错——
# 错一个词会直接污染 R6 的关键词覆盖率，而漏掉的词用户能一眼看出来。
VOCAB = {
    "硬技能": [
        "数据分析", "数据挖掘", "机器学习", "深度学习", "强化学习", "自然语言处理",
        "计算机视觉", "推荐系统", "搜索算法", "特征工程", "模型调优", "模型部署",
        "因果推断", "统计建模", "时间序列", "异常检测", "用户画像", "指标体系",
        "数据可视化", "埋点", "数据清洗", "数据仓库", "数据治理", "数据建模",
        "报表开发", "用户增长", "增长黑客", "漏斗分析", "留存分析", "A/B 测试",
        "AB 测试", "灰度发布", "性能优化", "高并发", "分布式", "微服务", "消息队列",
        "缓存", "数据库设计", "索引优化", "分库分表", "服务治理", "容灾", "限流",
        "熔断", "单元测试", "集成测试", "自动化测试", "性能测试", "接口测试",
        "测试用例", "缺陷管理", "持续集成", "持续交付", "代码评审", "重构",
        "架构设计", "需求分析", "产品设计", "竞品分析", "用户调研", "交互设计",
        "原型设计", "数据看板", "运营策略", "活动策划", "内容运营", "社群运营",
        "渠道投放", "品牌传播", "文案撰写", "财务分析", "估值建模", "尽职调查",
        "风险控制", "合规审查", "合同审核", "供应链管理", "库存管理", "项目管理",
        "敏捷开发", "看板管理", "里程碑管理", "预算管理", "团队管理", "绩效考核",
        "员工培训", "薪酬设计", "组织发展", "前端开发", "后端开发", "全栈开发",
        "移动端开发", "小程序开发", "接口设计", "协议设计", "并发编程", "内存优化",
    ],
    "工具与平台": [
        "Python", "Java", "C++", "C#", "Golang", "Go语言", "Rust", "Scala", "MATLAB",
        "JavaScript", "TypeScript", "SQL", "MySQL", "PostgreSQL", "Oracle", "MongoDB",
        "Redis", "Elasticsearch", "Kafka", "RabbitMQ", "Spark", "Hadoop", "Hive",
        "Flink", "Airflow", "ClickHouse", "Docker", "Kubernetes", "K8s", "Jenkins",
        "Git", "GitHub", "GitLab", "Linux", "Nginx", "Spring", "SpringBoot", "Django",
        "Flask", "FastAPI", "React", "Vue", "Angular", "Node.js", "TensorFlow",
        "PyTorch", "Keras", "scikit-learn", "XGBoost", "LightGBM", "Pandas", "NumPy",
        "Tableau", "PowerBI", "Excel", "SPSS", "SAS", "Figma", "Axure", "Jira",
        "Confluence", "Postman", "JMeter", "Locust", "Selenium", "Prometheus",
        "Grafana", "AWS", "Azure", "GCP", "阿里云", "腾讯云", "华为云",
    ],
    "软技能": [
        "沟通协调", "跨团队协作", "跨部门沟通", "逻辑思维", "问题解决", "抗压能力",
        "学习能力", "自驱力", "责任心", "结果导向", "数据驱动", "用户思维",
        "商业敏感度", "表达能力", "汇报能力", "时间管理", "多任务并行", "推动落地",
        "独立负责", "团队协作", "主动性强", "owner 意识",
    ],
}

# 英文停用词：压掉 JD 里大量无害的普通词。全大写形式单独列，
# 因为启发式会把全大写当成技术词信号（SQL/AWS 就是这么进来的）。
STOPWORDS = {
    "the", "and", "for", "you", "your", "our", "we", "will", "are", "was", "with",
    "have", "has", "had", "this", "that", "from", "not", "all", "any", "can", "may",
    "should", "would", "could", "about", "into", "over", "more", "than", "such",
    "they", "their", "them", "there", "here", "what", "when", "which", "who", "how",
    "job", "role", "team", "work", "working", "ability", "good", "strong", "plus",
    "and/or", "etc", "eg", "ie", "or", "of", "to", "in", "on", "at", "by", "is",
    "be", "as", "it", "an", "a", "if", "so", "do", "does", "no", "yes", "new",
    # 全大写的组织/文档类缩写：启发式会把全大写当技术词，这些必须挡掉
    "jd", "hr", "cv", "faq", "pdf", "url", "http", "https", "ceo", "cto", "coo",
    "vp", "hq", "okr", "kpi", "roi", "pr", "qa", "pm", "ui", "ux",
}

EN_TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z0-9+#.]{1,19}")
CJK_RUN_RE = re.compile(r"[\u4e00-\u9fff]{2,}")
CJK_STRIP_RE = re.compile(r"[\s，。、；：！？（）()【】\[\]「」《》/·,.;:!?\"'“”‘’—\-]+")


def _norm_space(text):
    """把各种空白压成单个空格，让子串匹配不受排版影响。"""
    return re.sub(r"\s+", " ", text)


def _vocab_index():
    """{小写词: (类别, 原词)}，用于大小写无关的命中。"""
    idx = {}
    for cat, words in VOCAB.items():
        for w in words:
            idx.setdefault(w.lower(), (cat, w))
    return idx


def _is_techy(token):
    """形似技术词：含数字 / 含 +#. / 全大写 / 驼峰。"""
    if any(ch.isdigit() for ch in token):
        return True
    if any(ch in "+#." for ch in token):
        return True
    if token.isupper() and len(token) >= 2:
        return True
    return bool(re.search(r"[a-z][A-Z]", token))


def extract(text, extra=None):
    """返回 {类别: [(词, 次数), ...]}，每组按次数降序、同次数按首次出现顺序。

    extra 是用户补的词表（逗号分隔字符串或列表），优先级高于内置词典。
    """
    text = _norm_space(text)
    idx = _vocab_index()
    counts = {}   # 原词 -> [次数, 在 JD 里首次出现的位置, 类别]

    # 1. 词典命中（中文子串 + 英文词边界）
    for word, (cat, canon) in idx.items():
        if re.search(r"[a-z]", word):
            ms = list(re.finditer(rf"(?<![A-Za-z]){re.escape(word)}(?![A-Za-z])", text, re.I))
            hits, pos = len(ms), (ms[0].start() if ms else -1)
        else:
            hits, pos = text.count(canon), text.find(canon)
        if hits:
            counts[canon] = [hits, pos, cat]

    # 2. 英文启发式：词典外的技术词
    for m in EN_TOKEN_RE.finditer(text):
        tok = m.group(0).rstrip(".")
        low = tok.lower()
        if low in STOPWORDS or low in idx or len(low) < 2:
            continue
        if not _is_techy(tok):
            continue
        if tok in counts:
            counts[tok][0] += 1
        else:
            counts[tok] = [1, m.start(), "工具与平台"]

    # 3. 用户补充词。已经在词典里命中的词不重复登记——否则同一个词会在
    #    硬技能和补充里各出现一次，拼出来的 --keywords 串里就有两个一样的。
    for word in _as_list(extra):
        if not word:
            continue
        n = text.lower().count(word.lower())
        if not n:
            continue
        if word in counts:
            counts[word][0] = max(counts[word][0], n)
        else:
            counts[word] = [n, text.lower().find(word.lower()), "补充"]

    grouped = {}
    for word, (n, first, cat) in counts.items():
        grouped.setdefault(cat, []).append((word, n, first))
    for cat in grouped:
        grouped[cat].sort(key=lambda x: (-x[1], x[2]))
    return {cat: [(w, n) for w, n, _f in items] for cat, items in grouped.items()}


def _as_list(extra):
    if not extra:
        return []
    if isinstance(extra, str):
        return [w.strip() for w in re.split(r"[,，、]", extra) if w.strip()]
    return [w.strip() for w in extra if w.strip()]


def keyword_list(grouped, max_per_group=None):
    """把分组结果摊平成逗号串（顺序：硬技能 → 工具 → 软技能 → 补充）。"""
    order = ["硬技能", "工具与平台", "软技能", "补充"]
    cats = [c for c in order if c in grouped] + [c for c in grouped if c not in order]
    out = []
    for cat in cats:
        words = [w for w, _n in grouped[cat]]
        if max_per_group:
            words = words[:max_per_group]
        out += words
    return ",".join(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description="从 JD 原文抽技能词")
    ap.add_argument("jd", help="JD 文本文件（md/txt）")
    ap.add_argument("--extra", help="补充词表，逗号分隔")
    ap.add_argument("--top", type=int, default=0, help="每组最多取前 N 个词（0=不限）")
    ap.add_argument("--keywords-only", action="store_true", help="只打印逗号串")
    ap.add_argument("--json", action="store_true", help="以 JSON 输出")
    args = ap.parse_args(argv)

    path = Path(args.jd)
    if not path.exists():
        _fail(f"JD 文件不存在: {path}", args.json)
    try:
        text = path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError) as e:
        _fail(f"读取失败: {e}", args.json)

    grouped = extract(text, args.extra)
    if not grouped:
        if args.json:
            print(json.dumps({"file": str(path), "keywords": "", "groups": {}}, ensure_ascii=False))
        else:
            print("[WARN] 没抽到关键词。JD 可能过短，或术语都不在词典里 → 用 --extra 补")
        sys.exit(1)

    kws = keyword_list(grouped, args.top or None)
    total = sum(len(v) for v in grouped.values())

    if args.json:
        print(
            json.dumps(
                {
                    "file": str(path),
                    "total": total,
                    "groups": {c: [{"word": w, "count": n} for w, n in v] for c, v in grouped.items()},
                    "keywords": kws,
                },
                ensure_ascii=False,
                indent=2,
            )
        )
        return
    if args.keywords_only:
        print(kws)
        return

    print(f"== JD 关键词：{path.name}（{total} 个）==")
    for cat, items in grouped.items():
        print()
        print(f"{cat}（{len(items)}）")
        line, width = "  ", 0
        for word, n in items:
            piece = f"{word} ×{n}" if n > 1 else word
            if width + len(piece) + 3 > 96:
                print(line)
                line, width = "  ", 0
            line += piece + " · "
            width += len(piece) + 3
        print(line.rstrip(" · "))
    print()
    print("--keywords 参数（可直接粘进 lint_resume.py）：")
    print(f'  --keywords "{kws}"')


def _fail(message, as_json):
    if as_json:
        print(json.dumps({"error": message}, ensure_ascii=False))
    else:
        print(f"[ERROR] {message}")
    sys.exit(2)


if __name__ == "__main__":
    main()
