"""
unit test: _write_review_cache / _read_review_cache / get_violation_detail
验证本地审查缓存的读写和按需加载。
"""

import os
import sys
import json
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from code_checker.tools import (
    _write_review_cache,
    _read_review_cache,
    set_state,
    get_violation_detail,
    _CACHE_DIR,
)

FAKE_STATE = {
    "merged_violations": [
        {
            "file": "/src/main.cpp",
            "line": 42,
            "rule": "禁止 Tab 缩进",
            "severity": "critical",
            "current": "\tint x = 0;",
            "expected": "    int x = 0;",
            "reason": "使用了 Tab 缩进",
            "surrounding": " 41: {\n→42: \tint x = 0;\n 43: }",
        },
        {
            "file": "/src/utils.cpp",
            "line": 15,
            "rule": "行宽 ≤ 100",
            "severity": "warning",
            "current": "std::cout << \"very long line...\"",
            "expected": "拆成多行",
            "reason": "行宽 105 字符",
            "surrounding": " 14: \n→15: std::cout << \"...\"\n 16: ",
        },
    ],
    "fix_plans": [
        {"fix_before": "\tint x = 0;", "fix_after": "    int x = 0;", "reason": "Tab → 空格"},
        {"fix_before": "std::cout << \"very long line...\"", "fix_after": "std::cout\n    << \"...\"", "reason": "拆行"},
    ],
}


def _cache_path(index: int) -> str:
    return os.path.join(_CACHE_DIR, f"{index}.json")


class TestReviewCache(unittest.TestCase):

    def setUp(self):
        set_state(FAKE_STATE)
        for i in range(10):
            p = _cache_path(i)
            if os.path.exists(p):
                os.remove(p)

    def tearDown(self):
        for i in range(10):
            p = _cache_path(i)
            if os.path.exists(p):
                os.remove(p)

    # ── 写 ──

    def test_first_write_creates_file(self):
        _write_review_cache(0, FAKE_STATE["fix_plans"][0],
                            score=3, passed=False,
                            feedback="tab 没完全替换", suggestion="检查第 3 行",
                            rule_snippet="禁止 Tab 缩进",
                            scoring_criteria="1. 全文无 tab")

        self.assertTrue(os.path.exists(_cache_path(0)))

        data = _read_review_cache(0)
        self.assertIsNotNone(data)
        self.assertEqual(data["file"], "/src/main.cpp")
        self.assertEqual(data["line"], 42)
        self.assertEqual(data["rule_name"], "禁止 Tab 缩进")
        self.assertEqual(len(data["attempts"]), 1)
        self.assertEqual(data["attempts"][0]["score"], 3)
        self.assertEqual(data["attempts"][0]["passed"], False)
        self.assertEqual(data["attempts"][0]["suggestion"], "检查第 3 行")
        self.assertEqual(data["scoring_criteria"], "1. 全文无 tab")
        self.assertEqual(data["rule_snippet"], "禁止 Tab 缩进")

    def test_second_write_appends(self):
        plan = FAKE_STATE["fix_plans"][0]
        _write_review_cache(0, plan, score=3, passed=False,
                            feedback="失败", suggestion="改一下",
                            rule_snippet="r", scoring_criteria="c")
        _write_review_cache(0, plan, score=8, passed=True,
                            feedback="修好", suggestion="",
                            rule_snippet="r", scoring_criteria="")

        self.assertIsNone(_read_review_cache(0), "通过后不应返回缓存")

    def test_passed_not_returned(self):
        _write_review_cache(0, FAKE_STATE["fix_plans"][0],
                            score=10, passed=True,
                            feedback="完美", suggestion="",
                            rule_snippet="r", scoring_criteria="c")

        self.assertIsNone(_read_review_cache(0))

    def test_nonexistent_returns_none(self):
        self.assertIsNone(_read_review_cache(999))

    def test_two_violations_independent(self):
        _write_review_cache(0, FAKE_STATE["fix_plans"][0],
                            score=3, passed=False,
                            feedback="f0", suggestion="s0",
                            rule_snippet="r0", scoring_criteria="c0")
        _write_review_cache(1, FAKE_STATE["fix_plans"][1],
                            score=7, passed=True,
                            feedback="f1", suggestion="",
                            rule_snippet="r1", scoring_criteria="c1")

        self.assertTrue(os.path.exists(_cache_path(0)))
        self.assertTrue(os.path.exists(_cache_path(1)))
        self.assertIsNotNone(_read_review_cache(0))  # 未通过
        self.assertIsNone(_read_review_cache(1))      # 已通过

    def test_write_missing_violation(self):
        _write_review_cache(99, {"fix_before": "old", "fix_after": "new", "reason": "t"},
                            score=5, passed=False,
                            feedback="test", suggestion="",
                            rule_snippet="", scoring_criteria="")

        data = _read_review_cache(99)
        self.assertIsNotNone(data)
        self.assertEqual(data["file"], "")
        self.assertEqual(data["line"], 0)

    # ── get_violation_detail 集成 ──

    def test_get_detail_without_cache(self):
        detail = get_violation_detail.func(0)
        self.assertEqual(detail["file"], "/src/main.cpp")
        self.assertEqual(detail["line"], 42)
        self.assertNotIn("history", detail)
        self.assertNotIn("scoring_criteria", detail)

    def test_get_detail_with_cache(self):
        _write_review_cache(0, FAKE_STATE["fix_plans"][0],
                            score=3, passed=False,
                            feedback="没修好", suggestion="第 42 行改成 4 空格",
                            rule_snippet="禁止 Tab",
                            scoring_criteria="1. 无 tab 2. 缩进 4 空格")

        detail = get_violation_detail.func(0)
        self.assertEqual(len(detail.get("history", [])), 1)
        self.assertEqual(detail["history"][0]["score"], 3)
        self.assertEqual(detail["latest_suggestion"], "第 42 行改成 4 空格")
        self.assertEqual(detail["scoring_criteria"], "1. 无 tab 2. 缩进 4 空格")
        self.assertEqual(detail["rule_snippet"], "禁止 Tab")

    def test_get_detail_multiple_attempts(self):
        plan = FAKE_STATE["fix_plans"][0]
        _write_review_cache(0, plan, score=2, passed=False,
                            feedback="方向错", suggestion="步骤一",
                            rule_snippet="r", scoring_criteria="c")
        _write_review_cache(0, plan, score=3, passed=False,
                            feedback="还不对", suggestion="步骤二",
                            rule_snippet="r", scoring_criteria="")
        _write_review_cache(0, plan, score=5, passed=False,
                            feedback="接近", suggestion="步骤三",
                            rule_snippet="r", scoring_criteria="")

        detail = get_violation_detail.func(0)
        self.assertEqual(len(detail["history"]), 3)
        self.assertEqual(detail["history"][0]["score"], 2)
        self.assertEqual(detail["history"][2]["score"], 5)
        self.assertEqual(detail["latest_suggestion"], "步骤三")

    def test_scoring_criteria_anchored(self):
        plan = FAKE_STATE["fix_plans"][0]
        _write_review_cache(0, plan, score=3, passed=False,
                            feedback="f1", suggestion="s1",
                            rule_snippet="r1", scoring_criteria="【首次标准】1. xxx 2. yyy")
        _write_review_cache(0, plan, score=4, passed=False,
                            feedback="f2", suggestion="s2",
                            rule_snippet="r2", scoring_criteria="【不应覆盖】")

        detail = get_violation_detail.func(0)
        self.assertEqual(detail["scoring_criteria"], "【首次标准】1. xxx 2. yyy")

    # ── 边界条件 ──

    def test_write_with_empty_fix(self):
        _write_review_cache(0, {"fix_before": "", "fix_after": "", "reason": ""},
                            score=0, passed=False, feedback="", suggestion="",
                            rule_snippet="", scoring_criteria="")
        data = _read_review_cache(0)
        self.assertIsNotNone(data)
        self.assertEqual(len(data["attempts"]), 1)

    def test_corrupted_json_returns_none(self):
        path = _cache_path(100)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write("this is not json{{{")

        self.assertIsNone(_read_review_cache(100))

    def test_get_detail_out_of_range(self):
        detail = get_violation_detail.func(999)
        self.assertIn("error", detail)


if __name__ == "__main__":
    unittest.main(verbosity=2)
