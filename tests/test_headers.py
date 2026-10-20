"""关联头文件从固定 head_sha 的仓库树中查找（问题 4）。"""

from code_checker.pr_review.config import PRConfig
from code_checker.pr_review.models import BudgetConfig
from code_checker.pr_review.pipeline import run_analysis
from code_checker.pr_review.snapshot import LocalGitSnapshot

FOO_H = """#ifndef DEMO_FOO_H_
#define DEMO_FOO_H_

int helperFromHeader(int value);

#endif  // DEMO_FOO_H_
"""

FOO_CPP_BASE = """#include "foo.h"

int foo() {
    return helperFromHeader(1);
}
"""

FOO_CPP_HEAD = FOO_CPP_BASE + """
int bar() {
    return 2;
}
"""

OTHER_CPP = """#include <iostream>

int main() {
    return 0;
}
"""


def _run(repo, request, llm, budget=None):
    return run_analysis(
        LocalGitSnapshot(repo.path), request,
        config=PRConfig(budget=budget or BudgetConfig()),
        llm=llm, offline=False,
    )


def test_unchanged_header_is_read_from_head_tree(make_repo, request_for, fake_llm):
    repo = make_repo(
        {"src/foo.cpp": FOO_CPP_BASE, "src/foo.h": FOO_H},
        {"src/foo.cpp": FOO_CPP_HEAD},
        head_msg="feat: add bar",
    )
    llm = fake_llm(["[]"])
    result = _run(repo, request_for(repo), llm)

    assert result.status == "completed"
    prompt = llm.prompts[0]
    assert "直接相关头文件 src/foo.h" in prompt
    assert "int helperFromHeader(int value);" in prompt

    reads = result.artifacts["context_reads"]
    header_reads = [r for r in reads if r["path"] == "src/foo.h"]
    assert len(header_reads) == 1
    read = header_reads[0]
    assert read["sha"] == repo.head_sha
    assert read["start"] == 1
    assert read["purpose"].startswith("被 src/foo.cpp include")
    # 头文件没有在本次 diff 中修改，不能被算作已审查文件
    assert [f["path"] for f in result.reviewed_files] == ["src/foo.cpp"]


def test_header_read_failure_marks_incomplete(make_repo, request_for, fake_llm):
    repo = make_repo(
        {"src/foo.cpp": FOO_CPP_BASE, "src/foo.h": FOO_H},
        {"src/foo.cpp": FOO_CPP_HEAD},
        head_msg="feat: add bar",
    )
    llm = fake_llm(["[]"])
    result = _run(repo, request_for(repo), llm,
                  budget=BudgetConfig(max_extra_context_bytes=0))

    assert llm.calls == 1  # 上下文失败不阻断模型调用，但结果不可宣称完成
    assert result.status == "incomplete"
    assert "读取关联头文件失败" in result.status_reason
    assert any(e["stage"] == "context" and e["status"] == "failed"
               for e in result.degradation)
    assert "直接相关头文件" not in llm.prompts[0]


def test_missing_quoted_project_header_marks_incomplete(make_repo, request_for, fake_llm):
    repo = make_repo(
        {"src/foo.cpp": FOO_CPP_BASE},
        {"src/foo.cpp": FOO_CPP_HEAD},
        head_msg="feat: add bar",
    )
    llm = fake_llm(["[]"])
    result = _run(repo, request_for(repo), llm)

    assert result.status == "incomplete"
    assert "引用的项目头文件不在固定版本树中" in result.status_reason
    assert result.artifacts["header_context_missing"]
    assert any(e["stage"] == "context" and e["status"] == "failed"
               for e in result.degradation)


def test_missing_angle_header_is_recorded_but_not_blocking(
    make_repo, request_for, fake_llm,
):
    cpp = """#include <foo.h>

int foo() {
    return 0;
}
"""
    repo = make_repo(
        {"src/foo.cpp": cpp},
        {"src/foo.cpp": cpp + """
int baz() {
    return 3;
}
"""},
        head_msg="feat: add baz",
    )
    llm = fake_llm(["[]"])
    result = _run(repo, request_for(repo), llm)

    assert result.status == "completed"
    missing = result.artifacts["header_context_missing"]
    assert missing and missing[0]["quoted"] is False
    assert any(e["stage"] == "context" and e["status"] == "degraded"
               for e in result.degradation)


def test_header_not_referenced_by_cpp_is_not_read(make_repo, request_for, fake_llm):
    repo = make_repo(
        {"src/foo.cpp": OTHER_CPP, "src/foo.h": FOO_H},
        {"src/foo.cpp": OTHER_CPP + """
int baz() {
    return 3;
}
"""},
        head_msg="feat: add baz",
    )
    llm = fake_llm(["[]"])
    result = _run(repo, request_for(repo), llm)

    assert result.status == "completed"
    assert not [r for r in result.artifacts["context_reads"]
                if r["path"] == "src/foo.h"]
    assert "直接相关头文件" not in llm.prompts[0]
