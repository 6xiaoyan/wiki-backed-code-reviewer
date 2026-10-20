"""可信规则正文：领域拆分、注入上限与引用核验（问题 1）。"""

from code_checker.pr_review.rules import (
    build_domain_rules,
    page_for_rule,
    quote_in_injected,
    quote_supported,
    rule_clause,
    rule_source,
)

CPP_INDENTATION_SENTENCE = "所有 C++ 源代码文件必须使用"
QT_SENTENCE = "Qt 代码"


def test_cpp_corpus_contains_rule_body_text():
    corpus = build_domain_rules("cpp")
    assert corpus.included
    assert "cpp/indentation" in corpus.included
    assert "### cpp/indentation — 缩进规范" in corpus.text
    assert CPP_INDENTATION_SENTENCE in corpus.text
    assert corpus.used_bytes <= corpus.limit_bytes
    assert corpus.used_bytes > 0
    # 默认预算能容纳 C++ 主规则与本仓库配置的副规则
    assert not corpus.truncated
    # 只有实际注入的规则会进入可引用集合
    assert set(corpus.injected_text) == set(corpus.included)
    assert CPP_INDENTATION_SENTENCE in corpus.injected_text["cpp/indentation"]


def test_domains_do_not_mix_rule_bodies():
    cpp = build_domain_rules("cpp")
    qt = build_domain_rules("qt")
    sqlite = build_domain_rules("sqlite")

    assert all(slug.startswith(("cpp/", "tencent/")) for slug in cpp.included)
    assert all(slug.startswith("qt/") for slug in qt.included)
    assert all(slug.startswith("sqlite/") for slug in sqlite.included)

    assert "### qt/" not in cpp.text
    assert "### cpp/" not in qt.text
    assert "### tencent/" not in qt.text
    assert "### sqlite/" not in qt.text
    assert "### cpp/" not in sqlite.text
    assert CPP_INDENTATION_SENTENCE not in qt.text
    assert "cpp/indentation" not in qt.included
    assert "qt/no-tabs" not in cpp.included


def test_rule_budget_excludes_and_reports_instead_of_silent_drop():
    corpus = build_domain_rules("cpp", limit_bytes=2500)
    assert corpus.truncated
    assert corpus.excluded
    assert corpus.included
    assert corpus.used_bytes <= 2500
    assert corpus.text
    reported = {item["rule_id"] for item in corpus.excluded}
    assert any(slug not in corpus.text for slug in reported)
    assert all(item.get("reason") for item in corpus.excluded)
    summary = corpus.to_dict()
    assert summary["rules_not_injected"] == len(corpus.excluded)
    assert summary["rules_injected"] == len(corpus.included)
    # 被预算排除的规则不能出现在本轮可引用集合中
    assert set(corpus.injected_text) == set(corpus.included)
    for item in corpus.excluded:
        assert item["rule_id"] not in corpus.injected_text


def test_page_level_limit_marks_page_uncovered():
    corpus = build_domain_rules("cpp", max_page_bytes=64, limit_bytes=64 * 1024)
    assert corpus.empty
    assert corpus.excluded
    assert all("单页" in item["reason"] for item in corpus.excluded)


def test_rule_clause_and_source_come_from_trusted_wiki():
    clause = rule_clause("cpp/indentation")
    assert "4 个空格" in clause
    assert "C++代码规范.md" in rule_source("cpp/indentation")
    page = page_for_rule("cpp/indentation")
    assert page is not None
    assert page.domain == "cpp"
    assert page.clause


def test_quote_verification_against_rule_body():
    supported, _ = quote_supported(
        "cpp/indentation", "所有 C++ 源代码文件必须使用**4 个空格**进行缩进",
    )
    assert supported

    supported, reason = quote_supported(
        "cpp/indentation", "这条规则允许使用制表符缩进",
    )
    assert not supported
    assert "未出现" in reason

    supported, reason = quote_supported("cpp/indentation", "4 个")
    assert not supported
    assert "过短" in reason

    supported, reason = quote_supported("cpp/does-not-exist", "任意引用内容")
    assert not supported
    assert "不存在" in reason


def test_quote_in_injected_restricts_to_actual_injected_text():
    corpus = build_domain_rules("cpp")
    injected = corpus.injected_text
    quote = "所有 C++ 源代码文件必须使用**4 个空格**进行缩进"
    supported, _ = quote_in_injected("cpp/indentation", quote, injected)
    assert supported

    # 页面中存在、但不在本轮注入的条款中的文字不能被确认
    other_page_text = "将 Tab 键设置为插入 4 个空格"
    assert quote_supported("cpp/indentation", other_page_text)[0]
    supported, reason = quote_in_injected(
        "cpp/indentation", other_page_text, injected,
    )
    assert not supported
    assert "不在本轮注入" in reason

    # 未注入的规则一律拒绝
    supported, reason = quote_in_injected("qt/no-tabs", "任意规则正文", injected)
    assert not supported
    assert "未在本轮注入" in reason
