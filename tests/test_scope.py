"""审查范围、排除项与预算测试（PRD §6.1、§10）。"""

from code_checker.pr_review.models import (
    BudgetConfig,
    ChangedFile,
    DiffLine,
    Hunk,
    ReviewRequest,
)
from code_checker.pr_review.scope import (
    EXCLUDE_BINARY,
    EXCLUDE_DIR,
    EXCLUDE_GENERATED,
    EXCLUDE_REVIEW_CONFIG,
    EXCLUDE_TOO_LARGE,
    EXCLUDE_UNSUPPORTED,
    build_scope,
)


def _changed(path, *, status="modified", added=(3,), context=(1, 2, 4),
             additions=1, deletions=0, old_path=None):
    hunk = Hunk(1, 0, 1, 0)
    for line in sorted(set(added) | set(context)):
        kind = "+" if line in added else " "
        hunk.lines.append(DiffLine(kind, "line", line if kind == " " else None, line))
    hunk.new_count = len(hunk.lines)
    hunk.old_count = len(context)
    return ChangedFile(
        path=path, old_path=old_path, status=status,
        additions=additions, deletions=deletions, hunks=[hunk],
    )


def _request(**kw):
    data = dict(
        repo="owner/repo", pr_number=1, base_sha="base", head_sha="head",
        merge_base_sha="base",
    )
    data.update(kw)
    return ReviewRequest(**data)


def test_excludes_binary_unsupported_dirs_and_generated(fake_snapshot):

    files = [
        _changed("assets/logo.png", status="binary"),
        _changed("README.md"),
        _changed("CMakeLists.txt"),
        _changed("third_party/lib.cpp"),
        _changed("build/moc_widget.cpp"),
        _changed("src/moc_widget.cpp"),
        _changed("src/ui_main.h"),
        _changed("src/main.cpp"),
        _changed("code_checker/nodes/agent_cpp.py"),
    ]
    snapshot = fake_snapshot({"src/main.cpp": "int main() {}\n"}, {})
    decision, contents = build_scope(files, snapshot, _request(), BudgetConfig())

    excluded = {e["path"]: e["category"] for e in decision.excluded}
    assert excluded["assets/logo.png"] == EXCLUDE_BINARY
    assert excluded["README.md"] == EXCLUDE_REVIEW_CONFIG
    assert excluded["CMakeLists.txt"] == EXCLUDE_UNSUPPORTED
    assert excluded["third_party/lib.cpp"] == EXCLUDE_DIR
    assert excluded["build/moc_widget.cpp"] == EXCLUDE_DIR
    assert excluded["src/moc_widget.cpp"] == EXCLUDE_GENERATED
    assert excluded["src/ui_main.h"] == EXCLUDE_GENERATED
    assert excluded["code_checker/nodes/agent_cpp.py"] == EXCLUDE_REVIEW_CONFIG
    assert [f.path for f in decision.included] == ["src/main.cpp"]
    assert set(contents) == {"src/main.cpp"}


def test_no_text_change_excluded(fake_snapshot):

    files = [_changed("src/renamed.cpp", status="renamed", old_path="src/old.cpp",
                      added=(), context=(), additions=0, deletions=0)]
    files[0].hunks = []
    decision, _ = build_scope(files, fake_snapshot({"src/renamed.cpp": ""}, {}),
                              _request(), BudgetConfig())
    assert decision.excluded[0]["category"] == "no_text_change"
    assert decision.status_override == "skipped"


def test_review_config_only_pr_is_skipped(fake_snapshot):

    files = [_changed(".github/workflows/pr-review.yml", status="modified",
                      additions=2, deletions=1)]
    decision, _ = build_scope(
        files, fake_snapshot({".github/workflows/pr-review.yml": "name: x\n"}, {}),
        _request(), BudgetConfig(),
    )
    assert decision.status_override == "skipped"
    assert "配置候选" in " ".join(decision.reasons)
    assert not decision.included


def test_file_too_large_alone_is_incomplete(fake_snapshot):
    big = "x" * 2000
    files = [_changed("src/big.cpp")]
    decision, contents = build_scope(
        files, fake_snapshot({"src/big.cpp": big}, {}),
        _request(), BudgetConfig(max_file_bytes=1000),
    )
    assert not decision.excluded  # 不是普通排除项，而是未覆盖项
    assert decision.not_covered[0]["path"] == "src/big.cpp"
    assert decision.not_covered[0]["category"] == EXCLUDE_TOO_LARGE
    assert decision.status_override == "incomplete"
    assert "未被实际审查" in " ".join(decision.reasons)
    assert not decision.included
    assert contents == {}


def test_file_too_large_with_normal_file_is_incomplete(fake_snapshot):
    files = [_changed("src/big.cpp"), _changed("src/small.cpp")]
    decision, contents = build_scope(
        files, fake_snapshot({"src/big.cpp": "x" * 2000,
                              "src/small.cpp": "int value = 0;\n"}, {}),
        _request(), BudgetConfig(max_file_bytes=1000),
    )
    assert [f.path for f in decision.included] == ["src/small.cpp"]
    assert [item["path"] for item in decision.not_covered] == ["src/big.cpp"]
    assert decision.status_override == "incomplete"
    assert set(contents) == {"src/small.cpp"}


def test_file_exactly_at_limit_is_included(fake_snapshot):
    text = "y" * 1000
    files = [_changed("src/edge.cpp")]
    decision, contents = build_scope(
        files, fake_snapshot({"src/edge.cpp": text}, {}),
        _request(), BudgetConfig(max_file_bytes=1000),
    )
    assert [f.path for f in decision.included] == ["src/edge.cpp"]
    assert not decision.not_covered
    assert decision.status_override is None
    assert contents["src/edge.cpp"] == text


def test_file_count_budget_marks_incomplete_without_silent_drop(fake_snapshot):

    files = [_changed(f"src/file{i:02d}.cpp") for i in range(51)]
    head = {f.path: "int value = 0;\n" for f in files}
    decision, contents = build_scope(
        files, fake_snapshot(head, {}), _request(), BudgetConfig(max_files=50),
    )
    assert len(decision.included) == 50
    assert len(decision.not_covered) == 1
    assert decision.status_override == "incomplete"
    assert "50" in " ".join(decision.reasons)
    assert len(contents) == 50


def test_changed_line_budget_marks_incomplete(fake_snapshot):

    files = [
        _changed("src/a.cpp", additions=2000),
        _changed("src/b.cpp", additions=2000),
    ]
    head = {"src/a.cpp": "int a = 0;\n", "src/b.cpp": "int b = 0;\n"}
    decision, _ = build_scope(
        files, fake_snapshot(head, {}), _request(),
        BudgetConfig(max_changed_lines=3000),
    )
    assert [f.path for f in decision.included] == ["src/a.cpp"]
    assert decision.not_covered[0]["path"] == "src/b.cpp"
    assert decision.status_override == "incomplete"
    assert decision.applicable_changed_lines == 2000


def test_deleted_file_read_from_base_version(fake_snapshot):

    deleted = _changed("src/gone.cpp", status="deleted", added=(), context=(),
                       additions=0, deletions=3)
    deleted.hunks[0].lines = [DiffLine("-", "int gone;", 1, None)]
    decision, contents = build_scope(
        [deleted], fake_snapshot({}, {"src/gone.cpp": "int gone;\n"}),
        _request(), BudgetConfig(),
    )
    assert decision.included[0].status == "deleted"
    assert contents["src/gone.cpp"] == "int gone;\n"


def test_nothing_applicable_is_skipped(fake_snapshot):

    decision, _ = build_scope(
        [_changed("assets/logo.png", status="binary")],
        fake_snapshot({}, {}), _request(), BudgetConfig(),
    )
    assert decision.status_override == "skipped"
    assert "没有适用的代码改动" in " ".join(decision.reasons)


def test_pipeline_single_oversized_file_is_incomplete_not_skipped(
    make_repo, request_for, fake_llm,
):
    from code_checker.pr_review.config import PRConfig
    from code_checker.pr_review.pipeline import run_analysis
    from code_checker.pr_review.snapshot import LocalGitSnapshot

    repo = make_repo(
        {"src/big.cpp": "x" * 2000},
        {"src/big.cpp": "y" * 2000},
        head_msg="feat: rewrite big file",
    )
    llm = fake_llm(["[]"])
    result = run_analysis(
        LocalGitSnapshot(repo.path), request_for(repo),
        config=PRConfig(budget=BudgetConfig(max_file_bytes=1000)),
        llm=llm, offline=False,
    )
    assert result.status == "incomplete"
    assert result.status != "skipped"
    assert llm.calls == 0  # 没有实际审查任何代码文件
    assert result.not_covered
    assert "超过单文件上限" in result.status_reason
