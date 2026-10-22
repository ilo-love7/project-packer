#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
test_parse_jd.py — scripts/parse_jd.py 的回归测试（标准库 unittest）

重点测三类容易错的地方：
  1. 英文词边界——"Java" 不能命中 "JavaScript"，否则 JD 里写 JavaScript
     会被当成 Java 要求，覆盖率虚高。
  2. 停用词过滤——启发式把全大写当技术词，"THE"/"AND" 这类必须挡掉，
     否则关键词表里会混进一堆无意义的词，覆盖率反而下降。
  3. 排序——出现次数多的排前面，次数相同按在 JD 里出现的先后。
     这个顺序直接对应证据映射表的优先级，错了会误导用户先补不重要的词。
"""
import importlib.util
import io
import json
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
SPEC = importlib.util.spec_from_file_location("parse_jd", ROOT / "scripts" / "parse_jd.py")
pj = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(pj)


def words(grouped):
    return {w for items in grouped.values() for w, _n in items}


def flat(grouped):
    return [w for items in grouped.values() for w, _n in items]


class TestVocab(unittest.TestCase):
    def test_chinese_term_is_matched(self):
        self.assertIn("沟通协调", words(pj.extract("要求具备良好的沟通协调能力")))

    def test_english_term_is_matched_case_insensitively(self):
        self.assertIn("Python", words(pj.extract("熟悉 python 编程")))

    def test_java_does_not_match_inside_javascript(self):
        got = words(pj.extract("熟悉 JavaScript"))
        self.assertIn("JavaScript", got)
        self.assertNotIn("Java", got)

    def test_chinese_count_is_recorded(self):
        g = pj.extract("性能优化，还是性能优化")
        self.assertIn(("性能优化", 2), g["硬技能"])

    def test_etl_is_picked_by_heuristic(self):
        # ETL 不在词典里，靠"全大写"启发式进来
        self.assertIn("ETL", words(pj.extract("参与 ETL 链路建设")))


class TestHeuristic(unittest.TestCase):
    def test_techy_tokens_are_captured(self):
        got = words(pj.extract("熟悉 S3、C++、AWS、FastAPI"))
        for tok in ("S3", "C++", "AWS", "FastAPI"):
            self.assertIn(tok, got)

    def test_plain_english_is_ignored(self):
        self.assertEqual(pj.extract("the and you our team work"), {})

    def test_stopwords_block_allcaps_noise(self):
        got = words(pj.extract("JD HR CV FAQ PDF"))
        self.assertEqual(got, set())

    def test_short_token_is_ignored(self):
        # 单字母不抽，否则 "R" 会命中任何含 r 的地方
        self.assertEqual(pj.extract("R"), {})


class TestOrdering(unittest.TestCase):
    def test_more_frequent_comes_first(self):
        g = pj.extract("Redis Kafka Redis")
        tools = [w for w, _n in g["工具与平台"]]
        self.assertEqual(tools[:2], ["Redis", "Kafka"])

    def test_ties_follow_text_position(self):
        g = pj.extract("Kafka 与 Redis")
        tools = [w for w, _n in g["工具与平台"]]
        self.assertEqual(tools[:2], ["Kafka", "Redis"])

    def test_groups_are_ordered_for_output(self):
        g = pj.extract("沟通协调 Python 性能优化")
        kws = pj.keyword_list(g).split(",")
        self.assertLess(kws.index("性能优化"), kws.index("Python"))
        self.assertLess(kws.index("Python"), kws.index("沟通协调"))


class TestExtra(unittest.TestCase):
    def test_extra_adds_term_not_in_vocab(self):
        g = pj.extract("需要增量实验能力", extra="增量实验")
        self.assertEqual(g["补充"], [("增量实验", 1)])

    def test_extra_does_not_duplicate_vocab_term(self):
        # 因果推断本来就在词典里，补词不该让它出现两次
        g = pj.extract("需要因果推断能力", extra="因果推断")
        self.assertEqual(flat(g).count("因果推断"), 1)
        self.assertNotIn("补充", g)

    def test_extra_absent_from_jd_is_dropped(self):
        g = pj.extract("需要数据分析能力", extra="增量实验")
        self.assertNotIn("增量实验", words(g))

    def test_extra_accepts_chinese_comma(self):
        g = pj.extract("需要增量实验", extra="增量实验、因果推断")
        self.assertIn("增量实验", words(g))


class TestKeywordString(unittest.TestCase):
    def test_top_limits_each_group(self):
        g = {"硬技能": [("甲", 3), ("乙", 2), ("丙", 1)]}
        self.assertEqual(pj.keyword_list(g, 2), "甲,乙")

    def test_unknown_category_is_appended_last(self):
        g = {"硬技能": [("甲", 1)], "其他": [("乙", 1)]}
        self.assertEqual(pj.keyword_list(g), "甲,乙")


class TestCli(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name)
        self.jd = self.dir / "jd.txt"
        self.jd.write_text("要求熟悉 Python 与 SQL，具备沟通协调能力。\n", encoding="utf-8")

    def tearDown(self):
        self.tmp.cleanup()

    def _run(self, argv):
        buf = io.StringIO()
        code = 0
        with redirect_stdout(buf):
            try:
                pj.main(argv)
            except SystemExit as e:
                code = e.code
        return code, buf.getvalue()

    def test_keywords_only_prints_one_line(self):
        code, out = self._run([str(self.jd), "--keywords-only"])
        self.assertEqual(code, 0)
        self.assertEqual(out.strip().split(",")[0], "Python")

    def test_report_contains_keywords_flag(self):
        code, out = self._run([str(self.jd)])
        self.assertEqual(code, 0)
        self.assertIn("--keywords", out)

    def test_json_output_is_parseable(self):
        code, out = self._run([str(self.jd), "--json"])
        payload = json.loads(out)
        self.assertEqual(code, 0)
        self.assertIn("Python", payload["keywords"])
        self.assertGreater(payload["total"], 0)

    def test_empty_jd_exits_one(self):
        empty = self.dir / "empty.txt"
        empty.write_text("the and you", encoding="utf-8")
        code, out = self._run([str(empty)])
        self.assertEqual(code, 1)
        self.assertIn("没抽到关键词", out)

    def test_missing_file_exits_two(self):
        code, out = self._run([str(self.dir / "nope.txt")])
        self.assertEqual(code, 2)
        self.assertIn("JD 文件不存在", out)


class TestLintIntegration(unittest.TestCase):
    """lint_resume.py --jd 必须能把 JD 抽出来的词喂给 R6。"""

    def test_jd_flag_produces_coverage_line(self):
        import lint_resume

        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "jd.txt").write_text("熟悉 Python 与 SQL。", encoding="utf-8")
            (d / "r.md").write_text("- 用 Python 搭建管线；\n", encoding="utf-8")
            buf = io.StringIO()
            code = 0
            with redirect_stdout(buf):
                try:
                    lint_resume.main([str(d / "r.md"), "--jd", str(d / "jd.txt")])
                except SystemExit as e:
                    code = e.code
            out = buf.getvalue()
            self.assertEqual(code, 0)
            self.assertIn("R6 关键词覆盖 1/2", out)


if __name__ == "__main__":
    unittest.main(verbosity=2)
