"""只读快照：固定版本读取、路径校验、截断报错。"""

import base64

import pytest

from code_checker.pr_review.diff_parser import parse_diff
from code_checker.pr_review.snapshot import (
    FileTooLarge,
    GitHubApiSnapshot,
    LocalGitSnapshot,
    SnapshotError,
    SnapshotUnsupported,
)


def test_reads_fixed_sha_not_working_tree(make_repo):
    repo = make_repo(
        {"src/main.cpp": "int value = 0;\n"},
        {"src/main.cpp": "int value = 1;\n"},
        head_msg="feat: bump value",
    )
    snapshot = LocalGitSnapshot(repo.path)
    # 工作树当前在 pr（head）；读取 base 版本必须返回 base 内容
    assert snapshot.read_text("src/main.cpp", repo.base_sha).text == "int value = 0;\n"
    assert snapshot.read_text("src/main.cpp", repo.head_sha).text == "int value = 1;\n"


def test_diff_and_merge_base(make_repo):
    repo = make_repo(
        {"src/main.cpp": "int value = 0;\n"},
        {"src/main.cpp": "int value = 1;\n"},
        head_msg="feat: bump value",
    )
    snapshot = LocalGitSnapshot(repo.path)
    assert snapshot.resolve_merge_base(repo.base_sha, repo.head_sha) == repo.merge_base
    diff = snapshot.diff(repo.merge_base, repo.head_sha)
    files = parse_diff(diff)
    assert files[0].path == "src/main.cpp"
    assert files[0].added_linenos == {1}


def test_path_traversal_is_rejected(make_repo):
    repo = make_repo({"src/main.cpp": "int x = 0;\n"}, {"src/main.cpp": "int x = 1;\n"})
    snapshot = LocalGitSnapshot(repo.path)
    for bad in ("../outside.txt", "/etc/passwd", "C:/Windows/system.ini", "a/../../b"):
        with pytest.raises(SnapshotError):
            snapshot.read_text(bad, repo.head_sha)


def test_missing_commit_and_file_raise(make_repo):
    repo = make_repo({"src/main.cpp": "int x = 0;\n"}, {"src/main.cpp": "int x = 1;\n"})
    snapshot = LocalGitSnapshot(repo.path)
    with pytest.raises(SnapshotError):
        snapshot.verify_commit("deadbeefdeadbeefdeadbeefdeadbeefdeadbeef")
    with pytest.raises(SnapshotError):
        snapshot.read_text("src/missing.cpp", repo.head_sha)


def test_file_size_limit(make_repo):
    big = "x" * 5000
    repo = make_repo({"src/big.cpp": big}, {"src/big.cpp": big + "y"})
    snapshot = LocalGitSnapshot(repo.path)
    with pytest.raises(FileTooLarge):
        snapshot.read_text("src/big.cpp", repo.head_sha, max_bytes=1024)


def test_commit_subjects_cover_only_pr_range(make_repo, git_fn, write_fn):
    repo = make_repo(
        {"src/main.cpp": "int x = 0;\n"},
        {"src/main.cpp": "int x = 1;\n"},
        base_msg="feat: before pr",
        head_msg="feat: first pr commit",
    )
    write_fn(repo.path, "src/main.cpp", "int x = 2;\n")
    git_fn(repo.path, "add", "-A")
    git_fn(repo.path, "commit", "-m", "feat: second pr commit")
    snapshot = LocalGitSnapshot(repo.path)
    subjects = [c["subject"] for c in snapshot.commit_subjects(repo.merge_base, "HEAD")]
    assert subjects == ["feat: first pr commit", "feat: second pr commit"]


class FakeGitHubClient:
    def __init__(self, *, files=None, truncated=False, blobs=None):
        self.files = files or []
        self.truncated = truncated
        self.blobs = blobs or {}
        self.calls = []

    def compare(self, repo, base, head):
        self.calls.append(("compare", base, head))
        return {
            "merge_base_commit": {"sha": "m" * 40},
            "commits": [{"sha": "c" * 40, "commit": {"message": "feat: x\n\nbody"}}],
            "files": self.files,
        }

    def get_tree(self, repo, sha):
        return {
            "truncated": self.truncated,
            "tree": [
                {"path": "src/a.cpp", "type": "blob", "sha": "blob1",
                 "size": 12, "mode": "100644"},
                {"path": "src", "type": "tree", "sha": "tree1"},
            ],
        }

    def get_blob(self, repo, sha):
        return {"content": base64.b64encode(self.blobs[sha]).decode()}


def test_github_snapshot_compare_truncation_is_explicit():
    files = [{"filename": "src/f0.cpp", "status": "modified",
              "patch": "@@ -1 +1 @@\n-a\n+b"}] * 300
    client = FakeGitHubClient(files=files)
    snapshot = GitHubApiSnapshot(client, "owner/repo")
    with pytest.raises(SnapshotUnsupported):
        snapshot.diff("a" * 40, "b" * 40)


def test_github_snapshot_tree_truncation_is_explicit():
    client = FakeGitHubClient(truncated=True)
    snapshot = GitHubApiSnapshot(client, "owner/repo")
    with pytest.raises(SnapshotUnsupported):
        snapshot.list_tree("a" * 40)


def test_github_snapshot_reads_blob_and_diff():
    client = FakeGitHubClient(
        files=[{
            "filename": "src/a.cpp", "status": "modified",
            "patch": "@@ -1,2 +1,2 @@\n int x = 0;\n-int y = 1;\n+int y = 2;",
        }],
        blobs={"blob1": b"int x = 0;\n"},
    )
    snapshot = GitHubApiSnapshot(client, "owner/repo")
    diff = snapshot.diff("a" * 40, "b" * 40)
    files = parse_diff(diff)
    assert files[0].path == "src/a.cpp"
    assert files[0].added_linenos == {2}
    assert snapshot.read_text("src/a.cpp", "a" * 40).text == "int x = 0;\n"
    assert snapshot.resolve_merge_base("a" * 40, "b" * 40) == "m" * 40


def test_github_snapshot_binary_and_rename_headers():
    client = FakeGitHubClient(files=[
        {"filename": "src/new.cpp", "status": "added",
         "patch": "@@ -0,0 +1,1 @@\n+int x = 1;"},
        {"filename": "src/renamed.cpp", "previous_filename": "src/old.cpp",
         "status": "renamed", "patch": "@@ -1,1 +1,1 @@\n-int x = 1;\n+int x = 2;"},
        {"filename": "assets/logo.png", "status": "added"},
    ])
    snapshot = GitHubApiSnapshot(client, "owner/repo")
    files = {f.path: f for f in parse_diff(snapshot.diff("a" * 40, "b" * 40))}
    assert files["src/new.cpp"].status == "added"
    assert files["src/renamed.cpp"].status == "renamed"
    assert files["src/renamed.cpp"].old_path == "src/old.cpp"
    assert files["assets/logo.png"].is_binary
