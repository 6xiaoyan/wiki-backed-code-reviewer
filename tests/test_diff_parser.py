"""diff 解析与行号映射测试。"""

import pytest

from code_checker.pr_review.diff_parser import (
    DiffParseError,
    parse_diff,
    parse_github_pull_files,
    unquote_git_path,
)
from code_checker.pr_review.snapshot import LocalGitSnapshot


SAMPLE_DIFF = """diff --git a/src/main.cpp b/src/main.cpp
index 1111111..2222222 100644
--- a/src/main.cpp
+++ b/src/main.cpp
@@ -1,5 +1,7 @@
 #include <iostream>
 
-int main() {
+int main(int argc, char** argv) {
+    (void)argc;
+    (void)argv;
     return 0;
 }
diff --git a/src/new.cpp b/src/new.cpp
new file mode 100644
index 0000000..3333333
--- /dev/null
+++ b/src/new.cpp
@@ -0,0 +1,3 @@
+void added() {
+    return;
+}
diff --git a/src/old.cpp b/src/old.cpp
deleted file mode 100644
index 4444444..0000000
--- a/src/old.cpp
+++ /dev/null
@@ -1,2 +0,0 @@
-void removed() {
-}
diff --git a/src/a.cpp b/src/b.cpp
similarity index 90%
rename from src/a.cpp
rename to src/b.cpp
index 5555555..6666666 100644
--- a/src/a.cpp
+++ b/src/b.cpp
@@ -1,2 +1,2 @@
 int value = 1;
-int doubled = value * 1;
+int doubled = value * 2;
diff --git a/assets/logo.png b/assets/logo.png
new file mode 100644
index 0000000..7777777
Binary files /dev/null and b/assets/logo.png differ
diff --git "a/src/with space.cpp" "b/src/with space.cpp"
index 8888888..9999999 100644
--- "a/src/with space.cpp"
+++ "b/src/with space.cpp"
@@ -1 +1 @@
-old line
+new line
"""


def test_parse_all_change_kinds():
    files = {f.path: f for f in parse_diff(SAMPLE_DIFF)}
    assert set(files) == {
        "src/main.cpp", "src/new.cpp", "src/old.cpp", "src/b.cpp",
        "assets/logo.png", "src/with space.cpp",
    }

    main = files["src/main.cpp"]
    assert main.status == "modified"
    assert main.additions == 3 and main.deletions == 1
    assert main.added_linenos == {3, 4, 5}
    # 第二行是改动块中的上下文行（未修改）
    assert 2 in main.context_new_linenos
    assert 7 in main.context_new_linenos

    new = files["src/new.cpp"]
    assert new.status == "added"
    assert new.added_linenos == {1, 2, 3}

    old = files["src/old.cpp"]
    assert old.status == "deleted"
    assert old.path == "src/old.cpp"
    assert old.removed_linenos == {1, 2}

    renamed = files["src/b.cpp"]
    assert renamed.status == "renamed"
    assert renamed.old_path == "src/a.cpp"
    assert renamed.added_linenos == {2}
    assert renamed.removed_linenos == {2}

    binary = files["assets/logo.png"]
    assert binary.is_binary and binary.status == "binary"

    spaced = files["src/with space.cpp"]
    assert spaced.added_linenos == {1}


def test_hunk_line_numbers_are_1_based_and_contiguous():
    files = {f.path: f for f in parse_diff(SAMPLE_DIFF)}
    main = files["src/main.cpp"]
    hunk = main.hunks[0]
    assert (hunk.old_start, hunk.old_count) == (1, 5)
    assert (hunk.new_start, hunk.new_count) == (1, 7)
    added = [ln.new_lineno for ln in hunk.lines if ln.kind == "+"]
    assert added == [3, 4, 5]
    removed = [ln.old_lineno for ln in hunk.lines if ln.kind == "-"]
    assert removed == [3]


def test_multiple_hunks():
    diff = """diff --git a/x.cpp b/x.cpp
--- a/x.cpp
+++ b/x.cpp
@@ -1,2 +1,2 @@
-a
+b
 c
@@ -10,2 +10,3 @@
 d
+e
 f
"""
    f = parse_diff(diff)[0]
    assert len(f.hunks) == 2
    assert f.hunks[0].added_new_linenos == {1}
    assert f.hunks[1].added_new_linenos == {11}
    assert f.hunks[1].old_start == 10


def test_github_pull_files_payload():
    payload = [{
        "filename": "src/main.cpp",
        "status": "modified",
        "additions": 1,
        "deletions": 1,
        "patch": "@@ -1,3 +1,3 @@\n context\n-old line\n+new line\n tail",
    }, {
        "filename": "src/moved.cpp",
        "previous_filename": "src/old.cpp",
        "status": "renamed",
        "additions": 0,
        "deletions": 0,
    }]
    files = parse_github_pull_files(payload)
    assert files[0].path == "src/main.cpp"
    assert files[0].hunks[0].added_new_linenos == {2}
    assert files[1].status == "renamed"
    assert files[1].old_path == "src/old.cpp"


def test_unquote_paths():
    assert unquote_git_path('"src/a b.cpp"') == "src/a b.cpp"
    assert unquote_git_path('"src/tab\\tchar.cpp"') == "src/tab\tchar.cpp"


def test_malformed_diff_raises():
    with pytest.raises(DiffParseError):
        parse_diff("@@ -1 +1 @@\n-a\n+b\n")


def test_real_git_diff_rename_and_delete(make_repo):
    repo = make_repo(
        base={
            "src/keep.cpp": "int keep = 1;\n",
            "src/old.cpp": "int value = 1;\nint doubled = value * 1;\n",
            "src/removed.cpp": "void removed() {\n}\n",
        },
        head={
            "src/keep.cpp": "int keep = 2;\n",
            "src/new.cpp": "void added() {\n}\n",
        },
        deleted=["src/removed.cpp"],
        renames={"src/old.cpp": "src/renamed.cpp"},
        head_msg="feat: rename and delete files",
    )
    snapshot = LocalGitSnapshot(repo.path)
    diff = snapshot.diff(repo.merge_base, repo.head_sha)
    files = {f.path: f for f in parse_diff(diff)}

    assert files["src/keep.cpp"].status == "modified"
    assert files["src/new.cpp"].status == "added"
    assert files["src/removed.cpp"].status == "deleted"
    assert files["src/renamed.cpp"].status == "renamed"
    assert files["src/renamed.cpp"].old_path == "src/old.cpp"


def test_deleted_file_uses_old_path_as_path(make_repo):
    repo = make_repo(
        base={"src/gone.cpp": "int gone = 1;\n"},
        head={"src/other.cpp": "int other = 1;\n"},
        deleted=["src/gone.cpp"],
        head_msg="refactor: remove gone",
    )
    snapshot = LocalGitSnapshot(repo.path)
    files = {f.path: f for f in parse_diff(snapshot.diff(repo.merge_base, repo.head_sha))}
    assert files["src/gone.cpp"].status == "deleted"
    assert files["src/gone.cpp"].removed_linenos == {1}
