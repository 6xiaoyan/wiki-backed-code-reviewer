"""PR 审查测试的公共夹具（不依赖网络或模型凭据）。"""

from __future__ import annotations

import os
import subprocess
from dataclasses import dataclass

import pytest

from code_checker.pr_review.config import PRConfig
from code_checker.pr_review.models import BudgetConfig, ReviewRequest
from code_checker.pr_review.snapshot import Snapshot, TextBlob


def git(repo: str, *args: str) -> str:
    proc = subprocess.run(
        [
            "git", "-C", repo,
            "-c", "core.autocrlf=false",
            "-c", "commit.gpgsign=false",
            "-c", "user.email=tests@example.com",
            "-c", "user.name=Tests",
            *args,
        ],
        capture_output=True, text=True, check=False,
    )
    if proc.returncode != 0:
        raise AssertionError(f"git {' '.join(args)} 失败: {proc.stderr}")
    return proc.stdout.strip()


def write_text(repo: str, path: str, text: str) -> None:
    full = os.path.join(repo, path.replace("/", os.sep))
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(text)


@dataclass
class RepoFixture:
    path: str
    base_sha: str
    head_sha: str
    merge_base: str
    pr_branch: str = "pr"


@pytest.fixture
def make_repo(tmp_path):
    """创建 base(main) → pr 分支的临时 Git 仓库。"""

    def _make(base: dict[str, str], head: dict[str, str] | None = None, *,
              base_msg: str = "feat: base version",
              head_msg: str = "feat: change version",
              deleted: list[str] | None = None,
              renames: dict[str, str] | None = None) -> RepoFixture:
        repo = str(tmp_path / "repo")
        os.makedirs(repo, exist_ok=True)
        git(repo, "init", "-b", "main")
        git(repo, "config", "core.autocrlf", "false")
        for path, text in base.items():
            write_text(repo, path, text)
        git(repo, "add", "-A")
        git(repo, "commit", "-m", base_msg)
        base_sha = git(repo, "rev-parse", "HEAD")

        git(repo, "checkout", "-b", "pr")
        for path, text in (head or {}).items():
            write_text(repo, path, text)
        for path in deleted or []:
            full = os.path.join(repo, path)
            if os.path.exists(full):
                os.remove(full)
                git(repo, "rm", "--cached", path, "--quiet")
        for old, new in (renames or {}).items():
            git(repo, "mv", old, new)
        git(repo, "add", "-A")
        git(repo, "commit", "-m", head_msg)
        head_sha = git(repo, "rev-parse", "HEAD")
        merge_base = git(repo, "merge-base", "main", "pr")
        return RepoFixture(repo, base_sha, head_sha, merge_base, "pr")

    return _make


@pytest.fixture
def request_for():
    def _make(repo: RepoFixture, **overrides) -> ReviewRequest:
        data = dict(
            repo="owner/repo",
            pr_number=7,
            base_sha=repo.base_sha,
            head_sha=repo.head_sha,
            merge_base_sha=repo.merge_base,
            program_sha="a" * 40,
            run_id="12345",
            run_attempt=1,
            run_url="https://github.example/owner/repo/actions/runs/12345",
            trigger="pull_request_target",
            model_id="deepseek-v4-flash",
        )
        data.update(overrides)
        return ReviewRequest(**data)

    return _make


@pytest.fixture
def offline_config():
    def _make(**budget) -> PRConfig:
        return PRConfig(
            budget=BudgetConfig(**budget) if budget else BudgetConfig(),
            offline=True,
        )

    return _make


class FakeSnapshot(Snapshot):
    """内存快照：按 (path, sha) 返回内容，用于范围/证据单元测试。"""

    def __init__(self, head: dict[str, str], base: dict[str, str] | None = None):
        self.head = dict(head)
        self.base = dict(base or {})

    def _contents(self, sha: str) -> dict[str, str]:
        return self.head if sha.endswith("head") else self.base

    def file_info(self, path: str, sha: str):
        text = self._contents(sha).get(path)
        if text is None:
            return None
        return {"sha": f"blob-{path}", "size": len(text.encode("utf-8")), "mode": "100644"}

    def read_text(self, path: str, sha: str, *, max_bytes: int = 1024 * 1024) -> TextBlob:
        text = self._contents(sha)[path]
        return TextBlob(path, sha, text, "utf-8", len(text.encode("utf-8")))

    def read_bytes(self, path: str, sha: str, *, max_bytes: int = 1024 * 1024) -> bytes:
        return self._contents(sha)[path].encode("utf-8")


class FakeLLM:
    """可控的模型替身：返回固定 JSON，并记录调用次数与提示词。"""

    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0
        self.prompts: list[str] = []

    def invoke(self, prompt):
        self.calls += 1
        self.prompts.append(prompt)
        text = self.responses.pop(0) if len(self.responses) > 1 else self.responses[0]

        class _Resp:
            content = text
            usage_metadata = {"input_tokens": 10, "output_tokens": 5}
            response_metadata = {}

        return _Resp()


@pytest.fixture
def fake_snapshot():
    return FakeSnapshot


@pytest.fixture
def fake_llm():
    return FakeLLM


@pytest.fixture
def git_fn():
    return git


@pytest.fixture
def write_fn():
    return write_text
