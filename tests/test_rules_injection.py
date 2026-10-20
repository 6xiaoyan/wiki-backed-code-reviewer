"""领域提示词注入规则正文、超限报告与无规则时不调用模型（问题 1）。"""

import json

from code_checker.pr_review import rules
from code_checker.pr_review.config import PRConfig
from code_checker.pr_review.models import BudgetConfig
from code_checker.pr_review.pipeline import run_analysis
from code_checker.pr_review.snapshot import LocalGitSnapshot

CPP_CLAUSE = "所有 C++ 源代码文件必须使用"
CPP_QUOTE = "函数和方法必须使用camelCase（首字母小写，后续每个单词的首字母大写）"

MAIN_CLEAN = """#include <iostream>

int main() {
    return 0;
}
"""

MAIN_TAB = """#include <iostream>

int helper() {
\treturn 1;
}

int main() {
    return 0;
}
"""

WIDGET_QT = """#include <QWidget>

class Widget : public QWidget {
    Q_OBJECT

public:
    explicit Widget(QWidget* parent = nullptr);
};
"""


def _run(repo, request, config, llm):
    return run_analysis(
        LocalGitSnapshot(repo.path), request, config=config, llm=llm, offline=False,
    )


def test_cpp_prompt_contains_cpp_rule_bodies_only(make_repo, request_for, fake_llm):
    repo = make_repo({"src/main.cpp": MAIN_CLEAN}, {"src/main.cpp": MAIN_TAB},
                     head_msg="feat: add helper")
    llm = fake_llm(["[]"])
    result = _run(repo, request_for(repo), PRConfig(), llm)

    assert result.status == "completed"
    assert llm.calls == 1
    prompt = llm.prompts[0]
    assert "### cpp/indentation — 缩进规范" in prompt
    assert CPP_CLAUSE in prompt
    assert '"rule_quote"' in prompt
    assert "### qt/" not in prompt
    assert "### sqlite/" not in prompt

    # 确定性问题的报告依据也来自可信 Wiki 正文
    tab = [f for f in result.findings if f.rule_id.endswith("check_tab_indentation")][0]
    assert tab.rule_page == "cpp/indentation"
    assert "4 个空格" in tab.rule_basis
    assert tab.rule_quote
    assert "C++代码规范.md" in tab.rule_source


def test_qt_prompt_contains_qt_rules_not_cpp(make_repo, request_for, fake_llm):
    repo = make_repo({"src/main.cpp": MAIN_CLEAN}, {"src/widget.cpp": WIDGET_QT},
                     head_msg="feat: add widget")
    llm = fake_llm(["[]"])
    result = _run(repo, request_for(repo), PRConfig(), llm)

    assert result.status == "completed"
    prompt = llm.prompts[0]
    assert "### qt/" in prompt
    assert "### cpp/" not in prompt
    assert "### tencent/" not in prompt
    assert CPP_CLAUSE not in prompt
    assert "Qt 开发规范" in prompt


def test_rule_budget_overflow_marks_incomplete_and_reports_uncovered(
    make_repo, request_for, fake_llm,
):
    repo = make_repo({"src/main.cpp": MAIN_CLEAN}, {"src/main.cpp": MAIN_TAB},
                     head_msg="feat: add helper")
    llm = fake_llm(["[]"])
    result = _run(
        repo, request_for(repo),
        PRConfig(budget=BudgetConfig(max_rule_context_bytes=2500)), llm,
    )

    assert result.status == "incomplete"
    assert "规则正文" in result.status_reason
    coverage = result.artifacts["rule_coverage"]
    assert coverage and coverage[0]["rules_not_injected"] > 0
    assert coverage[0]["rules_injected"] > 0
    assert result.summary["rules_not_injected"] > 0

    prompt = llm.prompts[0]
    missing_slug = coverage[0]["excluded"][0]["rule_id"]
    assert f"### {missing_slug}" not in prompt
    assert "规则正文因输入预算未注入" in prompt

    from code_checker.pr_review.report import render_report

    report = render_report(result)
    assert "规则正文注入范围" in report
    assert missing_slug in report


def test_no_rule_body_means_no_model_call(make_repo, request_for, fake_llm):
    repo = make_repo({"src/main.cpp": MAIN_CLEAN}, {"src/main.cpp": MAIN_TAB},
                     head_msg="feat: add helper")
    llm = fake_llm(["[]"])
    result = _run(
        repo, request_for(repo),
        PRConfig(budget=BudgetConfig(max_rule_page_bytes=32)), llm,
    )

    assert llm.calls == 0
    assert result.status == "incomplete"
    assert "没有可注入的可信规则正文" in result.status_reason
    assert result.artifacts["rule_coverage"][0]["rules_injected"] == 0


# ---------------------------------------------------------------------------
# 规则作用域：只能确认该领域本轮实际注入的规则与正文
# ---------------------------------------------------------------------------
def _finding_json(rule_id: str, quote: str, *, line: int = 4,
                  code: str = "\treturn 1;", extra: dict | None = None) -> str:
    finding = {
        "file": "src/main.cpp",
        "line": line,
        "rule_id": rule_id,
        "severity": "critical",
        "message": "测试问题",
        "rule_quote": quote,
        "code": code,
        "suggestion": "修复（建议，未执行验证）",
    }
    if extra:
        finding.update(extra)
    return json.dumps([finding], ensure_ascii=False)


def _page_quote(rule_id: str, size: int = 120) -> str:
    page = rules.page_for_rule(rule_id)
    assert page is not None and page.clause
    return page.clause[:size]


def test_other_domain_rule_cannot_be_confirmed(make_repo, request_for, fake_llm):
    repo = make_repo({"src/main.cpp": MAIN_CLEAN}, {"src/main.cpp": MAIN_TAB},
                     head_msg="feat: add helper")
    # 即使模型伪造 _agent_domain=qt，服务端也会按实际 Agent 领域覆盖
    llm = fake_llm([_finding_json(
        "qt/no-tabs", _page_quote("qt/no-tabs"),
        extra={"_agent_domain": "qt"},
    )])
    result = _run(repo, request_for(repo), PRConfig(), llm)

    assert not [f for f in result.findings if f.rule_id == "qt/no-tabs"]
    assert result.uncertain_findings
    reasons = " ".join(item["reason"] for item in result.uncertain_findings)
    assert "未注入给 cpp 领域 Agent" in reasons


def test_budget_excluded_rule_cannot_be_confirmed(make_repo, request_for, fake_llm):
    repo = make_repo({"src/main.cpp": MAIN_CLEAN}, {"src/main.cpp": MAIN_TAB},
                     head_msg="feat: add helper")
    budget = BudgetConfig(max_rule_context_bytes=2500)
    # 先确定哪些规则会被预算排除，再让模型引用它
    corpus = rules.build_domain_rules(
        "cpp", limit_bytes=budget.max_rule_context_bytes,
        max_page_bytes=budget.max_rule_page_bytes,
    )
    assert corpus.excluded
    excluded_slug = corpus.excluded[0]["rule_id"]

    llm = fake_llm([_finding_json(excluded_slug, _page_quote(excluded_slug))])
    result = _run(repo, request_for(repo), PRConfig(budget=budget), llm)

    assert not [f for f in result.findings if f.rule_id == excluded_slug]
    reasons = " ".join(item["reason"] for item in result.uncertain_findings)
    assert "未注入给 cpp 领域 Agent" in reasons
    assert "预算" in reasons


def test_quote_outside_injected_text_cannot_be_confirmed(
    make_repo, request_for, fake_llm,
):
    repo = make_repo({"src/main.cpp": MAIN_CLEAN}, {"src/main.cpp": MAIN_TAB},
                     head_msg="feat: add helper")
    quote = "将 Tab 键设置为插入 4 个空格"
    supported, _ = rules.quote_supported("cpp/indentation", quote)
    assert supported  # 整页正文中存在
    injected = rules.build_domain_rules("cpp").injected_text
    assert quote not in injected["cpp/indentation"]  # 但不在本轮注入的条款中

    llm = fake_llm([_finding_json("cpp/indentation", quote)])
    result = _run(repo, request_for(repo), PRConfig(), llm)

    assert not [f for f in result.findings if f.rule_id == "cpp/indentation"]
    reasons = " ".join(item["reason"] for item in result.uncertain_findings)
    assert "不在本轮注入的正文范围内" in reasons


def test_injected_rule_and_quote_can_be_confirmed(make_repo, request_for, fake_llm):
    repo = make_repo({"src/main.cpp": MAIN_CLEAN}, {"src/main.cpp": MAIN_TAB},
                     head_msg="feat: add helper")
    quote = "所有 C++ 源代码文件必须使用**4 个空格**进行缩进"
    llm = fake_llm([_finding_json("cpp/indentation", quote)])
    result = _run(repo, request_for(repo), PRConfig(), llm)

    # 确定性的 Tab 问题与模型引用同一规则，合并后仍可见规则正文
    model_findings = [f for f in result.findings if f.rule_id == "cpp/indentation"]
    assert len(model_findings) == 1
    model_finding = model_findings[0]
    assert model_finding.rule_quote == quote
    assert "4 个空格" in model_finding.rule_basis
