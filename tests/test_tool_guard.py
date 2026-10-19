"""PR 模式工具权限与图结构测试（PRD §5、§13 的“诱导执行”场景）。"""

import inspect

import pytest

from code_checker import tools


@pytest.fixture(autouse=True)
def reset_pr_mode():
    tools.set_pr_mode(False)
    yield
    tools.set_pr_mode(False)


def test_run_git_log_is_rejected_in_pr_mode():
    tools.set_pr_mode(True)
    out = tools.run_git_log.invoke({"repo_path": ".", "count": 5})
    assert "PR 模式工具约束" in out
    assert "run_git_log" in out


def test_fix_tools_are_rejected_in_pr_mode():
    tools.set_pr_mode(True)
    assert "PR 模式工具约束" in tools.propose_fix.invoke({
        "idx": 0, "file": "src/a.cpp", "line": 1,
        "fix_before": "a", "fix_after": "b", "reason": "x",
    })
    assert "PR 模式工具约束" in tools.submit_review.invoke({
        "idx": 0, "score": 9, "passed": True, "feedback": "x",
        "suggestion": "y", "rule_snippet": "z",
    })


def test_allowed_tool_surface_has_no_shell_or_publish_tools():
    allowed = tools.PR_MODE_ALLOWED_TOOLS
    for forbidden in ("shell", "run_command", "exec", "run_git_log",
                      "propose_fix", "propose_patchset", "submit_review",
                      "create_comment", "update_comment", "publish"):
        assert forbidden not in allowed
    assert allowed.isdisjoint(tools._PR_FORBIDDEN_TOOLS)


def test_read_file_only_sees_fixed_snapshot():
    tools.set_agent_name("cpp_agent")
    tools.set_state({
        "file_contents": {"src/a.cpp": "int allowed = 1;\n"},
        "file_list": ["src/a.cpp"],
    })
    assert tools.read_file.invoke({"file_path": "src/a.cpp"}) == "int allowed = 1;\n"
    missing = tools.read_file.invoke({"file_path": "/etc/passwd"})
    assert missing.startswith("文件未找到")
    assert tools.list_files.invoke({}) == ["src/a.cpp"]


def test_pr_graph_has_no_fix_review_or_wiki_write_nodes():
    from code_checker.pr_review.graph_pr import build_pr_graph

    app = build_pr_graph()
    node_names = set(app.nodes)
    assert {"prepare", "deterministic", "agents", "verify", "merge", "export"} <= node_names
    for forbidden in ("fix_agent", "review_agent", "format_fixer",
                      "wiki_arbitration", "skill_generator"):
        assert forbidden not in node_names


def test_pr_reviewer_module_has_no_process_or_network_calls():
    from code_checker.pr_review import agents

    source = inspect.getsource(agents)
    for token in ("subprocess", "urllib", "requests", "socket", "os.system"):
        assert token not in source
