"""端到端：真实 Git 仓库上的离线审查、多提交与产物（PRD §6、§13）。"""

import json
import os

import pytest

from code_checker.pr_review.config import PRConfig
from code_checker.pr_review.models import BudgetConfig
from code_checker.pr_review.pipeline import run_analysis
from code_checker.pr_review.report import SUMMARY_MARKER, render_comment
from code_checker.pr_review.snapshot import LocalGitSnapshot

MAIN_CLEAN = """#include <iostream>

int main() {
    return 0;
}
"""

MAIN_WITH_TAB = """#include <iostream>

int helper() {
\treturn 1;
}

int main() {
    return 0;
}
"""

LEGACY_WITH_TAB = """// 历史文件
#include <string>

std::string legacyName() {
\treturn "legacy";
}
"""

LEGACY_MODIFIED = LEGACY_WITH_TAB + """
std::string legacyOther() {
    return "other";
}
"""

GONE_WITH_TAB = """#include <cstdio>

void gone() {
\tstd::printf("gone");
}
"""

DB_MISSING_PRAGMA = """#include <sqlite3.h>

int openDatabase() {
    return sqlite3_open("storage", nullptr);
}
"""


@pytest.fixture
def rich_repo(make_repo):
    return make_repo(
        base={
            "src/main.cpp": MAIN_CLEAN,
            "src/legacy.cpp": LEGACY_WITH_TAB,
            "src/gone.cpp": GONE_WITH_TAB,
        },
        head={
            "src/main.cpp": MAIN_WITH_TAB,
            "src/legacy.cpp": LEGACY_MODIFIED,
            "src/db.cpp": DB_MISSING_PRAGMA,
        },
        deleted=["src/gone.cpp"],
        base_msg="feat: base",
        head_msg="feat: add helper and db",
    )


def _request_body(result):
    return result


def test_offline_end_to_end_filters_history_and_reports_deleted(rich_repo, request_for, tmp_path):
    out = tmp_path / "artifacts"
    result = run_analysis(
        LocalGitSnapshot(rich_repo.path), request_for(rich_repo),
        config=PRConfig(offline=True), offline=True, artifact_dir=str(out),
    )

    assert result.status == "incomplete"
    assert "离线模式" in result.status_reason

    keys = {(f.file, f.line, f.rule_id) for f in result.findings}
    assert ("src/main.cpp", 4, "deterministic/check_tab_indentation") in keys
    assert ("src/db.cpp", 1, "deterministic/check_sqlite_pragma_key") in keys
    assert ("src/db.cpp", 1, "deterministic/check_sqlite_kdf") in keys
    assert ("src/gone.cpp", 4, "deterministic/check_tab_indentation") in keys
    # 历史问题不能作为本次新增
    assert not any(f.file == "src/legacy.cpp" for f in result.findings)
    assert any(f["file"] == "src/legacy.cpp" for f in result.filtered_findings)

    # 删除文件的问题必须带删除关系
    deleted = [f for f in result.findings if f.file == "src/gone.cpp"][0]
    assert deleted.change_relation == "deleted"

    # 产物齐全且可追查
    for name in ("review-result.json", "review-report.md", "pr-comment.md"):
        assert os.path.isfile(out / name)
    payload = json.loads((out / "review-result.json").read_text(encoding="utf-8"))
    assert payload["request"]["head_sha"] == rich_repo.head_sha
    assert payload["request"]["merge_base_sha"] == rich_repo.merge_base
    report = (out / "review-report.md").read_text(encoding="utf-8")
    assert "已过滤候选" in report
    assert "确定由本次改动引入" not in report  # 不出现虚假的因果断言
    comment = (out / "pr-comment.md").read_text(encoding="utf-8")
    assert comment.startswith(SUMMARY_MARKER)
    assert rich_repo.head_sha[:7] in comment
    assert "最新代码已通过" not in comment


def test_langgraph_and_sequential_paths_agree(rich_repo, request_for, tmp_path):
    from code_checker.pr_review.graph_pr import run_analysis_graph

    sequential = run_analysis(
        LocalGitSnapshot(rich_repo.path), request_for(rich_repo),
        config=PRConfig(offline=True), offline=True,
        artifact_dir=str(tmp_path / "seq"),
    )
    graph = run_analysis_graph(
        LocalGitSnapshot(rich_repo.path), request_for(rich_repo),
        config=PRConfig(offline=True), offline=True,
        artifact_dir=str(tmp_path / "graph"),
    )
    key = lambda r: [(f.file, f.line, f.rule_id) for f in r.findings]
    assert key(sequential) == key(graph)
    assert sequential.status == graph.status == "incomplete"


def test_second_push_reviews_whole_pr_range(rich_repo, request_for, git_fn, write_fn):
    snapshot = LocalGitSnapshot(rich_repo.path)
    first = run_analysis(
        snapshot, request_for(rich_repo), config=PRConfig(offline=True), offline=True,
    )
    first_tabs = [f for f in first.findings
                  if f.file == "src/main.cpp"
                  and f.rule_id.endswith("check_tab_indentation")]

    # 在同一 PR 上再提交一次（追加另一个 Tab 缩进函数）
    write_fn(rich_repo.path, "src/main.cpp", MAIN_WITH_TAB + """
int another() {
\treturn 2;
}
""")
    git_fn(rich_repo.path, "add", "-A")
    git_fn(rich_repo.path, "commit", "-m", "feat: add another helper")
    new_head = git_fn(rich_repo.path, "rev-parse", "HEAD")

    second = run_analysis(
        LocalGitSnapshot(rich_repo.path),
        request_for(rich_repo, head_sha=new_head),
        config=PRConfig(offline=True), offline=True,
    )
    tab_lines = sorted(f.line for f in second.findings
                       if f.file == "src/main.cpp" and f.rule_id.endswith("check_tab_indentation"))
    # 第一次提交引入的 Tab 仍然属于整个 PR 的改动范围
    assert 4 in tab_lines
    assert 12 in tab_lines
    assert len(tab_lines) == len(first_tabs) + 1


def test_cli_local_offline_writes_status(rich_repo, tmp_path, monkeypatch):
    from code_checker.pr_review.cli import main

    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    out = tmp_path / "cli-out"
    code = main([
        "local", "--repo-path", rich_repo.path,
        "--base", rich_repo.base_sha, "--head", rich_repo.head_sha,
        "--offline", "--output-dir", str(out),
    ])
    assert code == 2
    status = json.loads((out / "review-status.json").read_text(encoding="utf-8"))
    assert status["status"] == "incomplete"
    assert status["has_result"] is True
    assert (out / "pr-comment.md").is_file()


def test_cli_missing_credentials_fails(rich_repo, tmp_path, monkeypatch):
    from code_checker.pr_review.cli import main

    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    out = tmp_path / "cli-fail"
    code = main([
        "local", "--repo-path", rich_repo.path,
        "--base", rich_repo.base_sha, "--head", rich_repo.head_sha,
        "--output-dir", str(out),
    ])
    assert code == 1
    result = json.loads((out / "review-result.json").read_text(encoding="utf-8"))
    assert result["status"] == "failed"
    assert "缺少模型凭据" in result["status_reason"]


def test_analyze_accepts_structured_request_file(rich_repo, request_for, tmp_path,
                                                 monkeypatch):
    from code_checker.pr_review.cli import main

    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    request = request_for(rich_repo, pr_number=7)
    request_path = tmp_path / "request.json"
    request_path.write_text(json.dumps(request.to_dict(), ensure_ascii=False),
                            encoding="utf-8")
    out = tmp_path / "request-out"
    code = main([
        "analyze", "--request-file", str(request_path),
        "--repo-path", rich_repo.path, "--offline", "--output-dir", str(out),
    ])
    assert code == 2
    payload = json.loads((out / "review-result.json").read_text(encoding="utf-8"))
    assert payload["request"]["head_sha"] == rich_repo.head_sha
    assert payload["request"]["pr_number"] == 7
    assert payload["request"]["repo"] == "owner/repo"
    assert payload["status"] == "incomplete"


def test_comment_does_not_claim_all_code_safe(rich_repo, request_for):
    result = run_analysis(
        LocalGitSnapshot(rich_repo.path), request_for(rich_repo),
        config=PRConfig(offline=True), offline=True,
    )
    comment = render_comment(result)
    assert "所有代码安全" not in comment
    assert "未执行验证" in comment
