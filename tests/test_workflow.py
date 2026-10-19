"""工作流安全边界测试（PRD §5、§13）。"""

from pathlib import Path

import pytest
import yaml

def _find_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "code_checker").is_dir() and (parent / ".github").is_dir():
            return parent
    return here.parents[3]


ROOT = _find_root()
WORKFLOW = ROOT / ".github" / "workflows" / "pr-review.yml"


@pytest.fixture(scope="module")
def workflow():
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def on_block(workflow):
    # PyYAML 按 YAML 1.1 会把裸 on 解析为布尔 True
    return workflow.get("on") or workflow.get(True)


def _iter_steps(job):
    for step in job.get("steps", []):
        yield step


def _all_uses(workflow):
    for job in workflow["jobs"].values():
        for step in _iter_steps(job):
            if "uses" in step:
                yield step["uses"]


def _all_run_blocks(job):
    return "\n".join(step.get("run", "") for step in _iter_steps(job))


def test_triggers(on_block):
    assert "pull_request_target" in on_block
    assert on_block["pull_request_target"]["types"] == [
        "opened", "synchronize", "reopened", "ready_for_review",
    ]
    assert "workflow_dispatch" in on_block
    assert on_block["workflow_dispatch"]["inputs"]["pr_number"]["required"] is True
    # 不使用会在 PR 分支上下文运行的 pull_request 触发器
    assert "pull_request" not in on_block


def test_default_permissions_are_read_only(workflow):
    assert workflow["permissions"] == {"contents": "read"}


def test_job_permissions_are_separated(workflow):
    analyze = workflow["jobs"]["analyze"]["permissions"]
    publish = workflow["jobs"]["publish"]["permissions"]
    assert analyze.get("pull-requests") == "read"
    assert "write" not in str(analyze)
    assert publish.get("pull-requests") == "write"
    assert publish.get("contents") == "read"


def test_concurrency_cancels_same_pr(workflow):
    concurrency = workflow["concurrency"]
    assert concurrency["cancel-in-progress"] is True
    group = concurrency["group"]
    assert "github.event.pull_request.number" in group
    assert "inputs.pr_number" in group


def test_publish_runs_after_analyze_and_validates_result(workflow):
    publish = workflow["jobs"]["publish"]
    assert publish["needs"] == "analyze"
    condition = str(publish["if"])
    assert "always()" in condition
    assert "has_result" in condition
    runs = _all_run_blocks(publish)
    assert "pr_review publish" in runs
    assert "--expected-head-sha" in runs
    assert "--expected-run-id" in runs
    uses = [s.get("uses", "") for s in publish["steps"]]
    assert any(u.startswith("actions/download-artifact@") for u in uses)


def test_analyze_has_model_secret_publish_does_not(workflow):
    analyze = workflow["jobs"]["analyze"]
    publish = workflow["jobs"]["publish"]
    assert "DEEPSEEK_API_KEY" in yaml.safe_dump(analyze, allow_unicode=True)
    publish_dump = yaml.safe_dump(publish, allow_unicode=True)
    assert "DEEPSEEK_API_KEY" not in publish_dump
    assert "secrets.GITHUB_TOKEN" in publish_dump


def test_publish_installs_no_dependencies(workflow):
    publish_dump = yaml.safe_dump(workflow["jobs"]["publish"], allow_unicode=True)
    assert "pip install" not in publish_dump
    assert "requirements.txt" not in publish_dump


def test_only_first_party_actions(workflow):
    uses = list(_all_uses(workflow))
    assert uses, "工作流没有引用任何 action"
    for value in uses:
        assert value.startswith("actions/"), f"非第一方 action: {value}"


def test_pr_head_is_fetched_as_data_not_checked_out(workflow):
    analyze = workflow["jobs"]["analyze"]
    for step in analyze["steps"]:
        run = step.get("run", "")
        assert "git checkout" not in run
        assert "git switch" not in run
        assert "worktree" not in run
    fetch = next(s for s in analyze["steps"] if "Fetch PR head" in s.get("name", ""))
    assert "refs/pull/${PR_NUMBER}/head" in fetch["run"]
    assert "refs/remotes/pr/head" in fetch["run"]


def test_artifact_retention_and_timeouts(workflow):
    analyze = workflow["jobs"]["analyze"]
    upload = next(s for s in analyze["steps"] if s.get("uses", "").startswith("actions/upload-artifact"))
    assert int(upload["with"]["retention-days"]) == 14
    assert analyze["timeout-minutes"] == 20
    assert workflow["jobs"]["publish"]["timeout-minutes"] == 10


def test_review_step_uses_trusted_workspace_and_exit_codes(workflow):
    analyze = workflow["jobs"]["analyze"]
    step = next(s for s in analyze["steps"] if s.get("name") == "Run PR review")
    assert "code_checker.pr_review analyze" in step["run"]
    assert '--repo-path "${GITHUB_WORKSPACE}"' in step["run"]
    env = step["env"]
    assert env["DEEPSEEK_API_KEY"] == "${{ secrets.DEEPSEEK_API_KEY }}"
    assert env["GITHUB_TOKEN"] == "${{ secrets.GITHUB_TOKEN }}"
