"""只读代码快照。

PR 模式下所有文件内容都来自固定提交的只读快照：
  * LocalGitSnapshot   —— 通过 ``git cat-file`` / ``git ls-tree`` / ``git diff``
    读取 Git 对象数据库，从不创建 PR head 的工作树，也不运行 PR 中的任何脚本。
  * GitHubApiSnapshot  —— 通过 Git Trees/Blobs API 读取固定 SHA，API 返回
    ``truncated`` 或触及 300 文件上限时显式报错。

两者接口一致，PR 审查图不感知数据来源。
"""

from __future__ import annotations

import base64
import os
import re
import subprocess
from dataclasses import dataclass
from typing import Optional

MAX_READ_BYTES = 1024 * 1024  # 单次读取硬上限，超过即判定不可审查
BINARY_SNIFF_BYTES = 8192


class SnapshotError(RuntimeError):
    """快照读取失败。调用方必须把它当作“失败/未完成”，不能当作“没有改动”。"""


class SnapshotUnsupported(SnapshotError):
    """数据被截断或接口不支持，需显式报告缺失。"""


class FileTooLarge(SnapshotError):
    pass


@dataclass
class TextBlob:
    path: str
    sha: str
    text: str
    encoding: str
    size: int
    replacement_chars: bool = False


def looks_binary(data: bytes) -> bool:
    chunk = data[:BINARY_SNIFF_BYTES]
    return b"\x00" in chunk


def decode_text(data: bytes) -> tuple[str, str, bool]:
    """解码文本，返回 (text, encoding, 是否使用了替换字符)。"""
    for enc in ("utf-8", "gbk"):
        try:
            return data.decode(enc), enc, False
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace"), "utf-8-replace", True


def _validate_relpath(path: str) -> str:
    if not path or path.startswith("/") or re.match(r"^[A-Za-z]:", path):
        raise SnapshotError(f"非法仓库路径: {path!r}")
    norm = path.replace("\\", "/")
    parts = [p for p in norm.split("/") if p]
    if any(p in ("..", ".") for p in parts):
        raise SnapshotError(f"路径包含上跳目录: {path!r}")
    if "\x00" in norm:
        raise SnapshotError("路径包含 NUL 字符")
    return "/".join(parts)


class Snapshot:
    """只读快照接口。"""

    def verify_commit(self, sha: str) -> None:
        raise NotImplementedError

    def resolve_ref(self, ref: str) -> str:
        raise NotImplementedError

    def resolve_merge_base(self, base_sha: str, head_sha: str) -> str:
        raise NotImplementedError

    def diff(self, merge_base_sha: str, head_sha: str) -> str:
        raise NotImplementedError

    def commit_subjects(self, base_sha: str, head_sha: str) -> list[dict]:
        raise NotImplementedError

    def list_tree(self, sha: str) -> dict[str, dict]:
        raise NotImplementedError

    def file_info(self, path: str, sha: str) -> Optional[dict]:
        raise NotImplementedError

    def read_bytes(self, path: str, sha: str, *,
                   max_bytes: int = MAX_READ_BYTES) -> bytes:
        raise NotImplementedError

    def read_text(self, path: str, sha: str, *,
                  max_bytes: int = MAX_READ_BYTES) -> TextBlob:
        raise NotImplementedError


# ---------------------------------------------------------------------------
# 本地 Git 对象快照
# ---------------------------------------------------------------------------
class LocalGitSnapshot(Snapshot):
    """基于本地 Git 对象数据库的只读快照。

    只调用 cat-file / ls-tree / diff / log / merge-base 等只读命令；
    从不调用 checkout / worktree / apply / hook，因此 PR 分支的代码不会被执行。
    """

    def __init__(self, repo_path: str, *, timeout: float = 120.0):
        self.repo_path = os.path.abspath(repo_path)
        self.timeout = timeout
        if not os.path.isdir(self.repo_path):
            raise SnapshotError(f"仓库目录不存在: {self.repo_path}")
        try:
            self._git(["rev-parse", "--git-dir"], timeout=30)
        except SnapshotError as exc:
            raise SnapshotError(f"不是可用的 Git 仓库: {self.repo_path}") from exc
        self._tree_cache: dict[str, dict[str, dict]] = {}
        self._compare_cache: dict[tuple[str, str], list[dict]] = {}

    def __repr__(self) -> str:
        return f"LocalGitSnapshot({self.repo_path!r})"

    # ── 进程调用 ──
    def _git(self, args: list[str], *, timeout: Optional[float] = None,
             check: bool = True) -> bytes:
        env = dict(os.environ)
        env["GIT_TERMINAL_PROMPT"] = "0"
        env["GIT_OPTIONAL_LOCKS"] = "0"
        cmd = [
            "git", "-C", self.repo_path,
            "-c", "core.fsmonitor=false",
            "-c", "core.quotepath=false",
            "--no-pager", *args,
        ]
        try:
            proc = subprocess.run(
                cmd, capture_output=True, timeout=timeout or self.timeout,
                env=env, check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise SnapshotError(f"git 命令执行失败: {exc}") from exc
        if check and proc.returncode != 0:
            stderr = proc.stderr.decode("utf-8", errors="replace")[:400]
            raise SnapshotError(f"git {' '.join(args[:3])} 失败: {stderr}")
        return proc.stdout

    # ── 版本解析 ──
    def verify_commit(self, sha: str) -> None:
        if not re.match(r"^[0-9a-fA-F]{4,64}$", sha or ""):
            raise SnapshotError(f"SHA 格式无效: {sha!r}")
        try:
            self._git(["cat-file", "-e", f"{sha}^{{commit}}"])
        except SnapshotError as exc:
            raise SnapshotError(f"提交对象不存在: {sha}（请先 fetch 该提交）") from exc

    def resolve_ref(self, ref: str) -> str:
        out = self._git(["rev-parse", "--verify", f"{ref}^{{commit}}"])
        return out.decode().strip()

    def resolve_merge_base(self, base_sha: str, head_sha: str) -> str:
        self.verify_commit(base_sha)
        self.verify_commit(head_sha)
        try:
            out = self._git(["merge-base", base_sha, head_sha])
        except SnapshotError as exc:
            raise SnapshotError(
                f"找不到 {base_sha[:8]} 与 {head_sha[:8]} 的共同祖先"
            ) from exc
        sha = out.decode().strip()
        if not sha:
            raise SnapshotError("merge-base 返回空值")
        return sha

    # ── diff 与提交 ──
    def diff(self, merge_base_sha: str, head_sha: str) -> str:
        out = self._git([
            "diff", "--unified=3", "--no-color", "--no-ext-diff", "--no-textconv",
            "--find-renames", "--find-copies=40%", "--src-prefix=a/", "--dst-prefix=b/",
            merge_base_sha, head_sha,
        ])
        return out.decode("utf-8", errors="replace")

    def commit_subjects(self, base_sha: str, head_sha: str) -> list[dict]:
        key = (base_sha, head_sha)
        if key in self._compare_cache:
            return self._compare_cache[key]
        out = self._git([
            "log", "--reverse", "--no-merges",
            "--format=%H%x1f%s%x1f%b%x1e", f"{base_sha}..{head_sha}",
        ])
        commits = []
        for chunk in out.decode("utf-8", errors="replace").split("\x1e"):
            chunk = chunk.strip("\n")
            if not chunk:
                continue
            parts = chunk.split("\x1f")
            if len(parts) < 2:
                continue
            commits.append({
                "sha": parts[0].strip(),
                "subject": parts[1].strip(),
                "body": (parts[2].strip() if len(parts) > 2 else ""),
            })
        self._compare_cache[key] = commits
        return commits

    # ── 文件内容 ──
    def list_tree(self, sha: str) -> dict[str, dict]:
        if sha in self._tree_cache:
            return self._tree_cache[sha]
        out = self._git(["ls-tree", "-r", "-l", "-z", sha])
        entries: dict[str, dict] = {}
        for item in out.split(b"\x00"):
            if not item:
                continue
            try:
                meta, path = item.split(b"\t", 1)
            except ValueError:
                continue
            fields = meta.decode("utf-8", errors="replace").split()
            if len(fields) < 4:
                continue
            mode, obj_type, obj_sha, size = fields[0], fields[1], fields[2], fields[3]
            if obj_type != "blob":
                continue
            try:
                size_int = int(size)
            except ValueError:
                size_int = -1
            entries[path.decode("utf-8", errors="replace")] = {
                "sha": obj_sha, "size": size_int, "mode": mode,
            }
        self._tree_cache[sha] = entries
        return entries

    def file_info(self, path: str, sha: str) -> Optional[dict]:
        path = _validate_relpath(path)
        return self.list_tree(sha).get(path)

    def read_bytes(self, path: str, sha: str, *, max_bytes: int = MAX_READ_BYTES) -> bytes:
        path = _validate_relpath(path)
        info = self.file_info(path, sha)
        if info is None:
            raise SnapshotError(f"提交 {sha[:8]} 中不存在文件: {path}")
        if info["size"] > max_bytes:
            raise FileTooLarge(
                f"文件 {path} 大小 {info['size']} 字节，超过上限 {max_bytes} 字节"
            )
        out = self._git(["cat-file", "blob", f"{sha}:{path}"])
        if len(out) > max_bytes:
            raise FileTooLarge(f"文件 {path} 读取结果超过上限 {max_bytes} 字节")
        return out

    def read_text(self, path: str, sha: str, *,
                  max_bytes: int = MAX_READ_BYTES) -> TextBlob:
        data = self.read_bytes(path, sha, max_bytes=max_bytes)
        if looks_binary(data):
            raise SnapshotError(f"文件 {path} 是二进制文件")
        text, encoding, replaced = decode_text(data)
        return TextBlob(path, sha, text, encoding, len(data), replaced)


# ---------------------------------------------------------------------------
# GitHub API 快照
# ---------------------------------------------------------------------------
class GitHubApiSnapshot(Snapshot):
    """通过 GitHub API 固定 SHA 读取的只读快照。"""

    MAX_COMPARE_FILES = 300

    def __init__(self, client, repo: str):
        self.client = client
        self.repo = repo
        self._compare_cache: dict[tuple[str, str], dict] = {}
        self._tree_cache: dict[str, dict[str, dict]] = {}
        self._blob_cache: dict[str, bytes] = {}

    def __repr__(self) -> str:
        return f"GitHubApiSnapshot({self.repo!r})"

    def verify_commit(self, sha: str) -> None:
        if not re.match(r"^[0-9a-fA-F]{7,64}$", sha or ""):
            raise SnapshotError(f"SHA 格式无效: {sha!r}")
        try:
            self.client.get_commit(self.repo, sha)
        except Exception as exc:
            raise SnapshotError(f"无法读取提交 {sha}: {exc}") from exc

    def resolve_ref(self, ref: str) -> str:
        data = self.client.get_commit(self.repo, ref)
        sha = str(data.get("sha") or "")
        if not sha:
            raise SnapshotError(f"无法解析 ref: {ref}")
        return sha

    @staticmethod
    def _compare_key(base: str, head: str) -> tuple[str, str]:
        return (base, head)

    def _compare(self, base_sha: str, head_sha: str) -> dict:
        key = self._compare_key(base_sha, head_sha)
        if key in self._compare_cache:
            return self._compare_cache[key]
        data = self.client.compare(self.repo, base_sha, head_sha)
        files = data.get("files") or []
        if len(files) >= self.MAX_COMPARE_FILES:
            raise SnapshotUnsupported(
                f"compare API 返回 {len(files)} 个文件，可能已被截断"
                f"（GitHub 上限 {self.MAX_COMPARE_FILES}）"
            )
        if not data.get("merge_base_commit"):
            raise SnapshotError("compare 结果缺少 merge_base_commit")
        self._compare_cache[key] = data
        return data

    def resolve_merge_base(self, base_sha: str, head_sha: str) -> str:
        data = self._compare(base_sha, head_sha)
        sha = str((data.get("merge_base_commit") or {}).get("sha") or "")
        if not sha:
            raise SnapshotError("compare 结果缺少共同祖先 SHA")
        return sha

    def diff(self, merge_base_sha: str, head_sha: str) -> str:
        data = self._compare(merge_base_sha, head_sha)
        return _compare_to_unified_diff(data.get("files") or [])

    def commit_subjects(self, base_sha: str, head_sha: str) -> list[dict]:
        data = self._compare(base_sha, head_sha)
        out = []
        for item in data.get("commits") or []:
            commit = item.get("commit") or {}
            message = str(commit.get("message") or "")
            out.append({
                "sha": str(item.get("sha") or ""),
                "subject": message.split("\n", 1)[0].strip(),
                "body": message,
            })
        return out

    def list_tree(self, sha: str) -> dict[str, dict]:
        if sha in self._tree_cache:
            return self._tree_cache[sha]
        data = self.client.get_tree(self.repo, sha)
        if data.get("truncated"):
            raise SnapshotUnsupported(
                "GitHub Trees API 返回 truncated=true，文件树不完整"
            )
        entries: dict[str, dict] = {}
        for item in data.get("tree") or []:
            if item.get("type") != "blob":
                continue
            entries[str(item.get("path"))] = {
                "sha": str(item.get("sha") or ""),
                "size": int(item.get("size") or 0),
                "mode": str(item.get("mode") or ""),
            }
        self._tree_cache[sha] = entries
        return entries

    def file_info(self, path: str, sha: str) -> Optional[dict]:
        path = _validate_relpath(path)
        return self.list_tree(sha).get(path)

    def read_bytes(self, path: str, sha: str, *, max_bytes: int = MAX_READ_BYTES) -> bytes:
        path = _validate_relpath(path)
        info = self.file_info(path, sha)
        if info is None:
            raise SnapshotError(f"提交 {sha[:8]} 中不存在文件: {path}")
        if info["size"] > max_bytes:
            raise FileTooLarge(
                f"文件 {path} 大小 {info['size']} 字节，超过上限 {max_bytes} 字节"
            )
        blob_sha = info["sha"]
        if blob_sha in self._blob_cache:
            return self._blob_cache[blob_sha]
        data = self.client.get_blob(self.repo, blob_sha)
        content = data.get("content") or ""
        try:
            raw = base64.b64decode(content)
        except Exception as exc:
            raise SnapshotError(f"blob {blob_sha[:8]} base64 解码失败") from exc
        if len(raw) > max_bytes:
            raise FileTooLarge(f"blob {blob_sha[:8]} 超过大小上限")
        self._blob_cache[blob_sha] = raw
        return raw

    def read_text(self, path: str, sha: str, *,
                  max_bytes: int = MAX_READ_BYTES) -> TextBlob:
        data = self.read_bytes(path, sha, max_bytes=max_bytes)
        if looks_binary(data):
            raise SnapshotError(f"文件 {path} 是二进制文件")
        text, encoding, replaced = decode_text(data)
        return TextBlob(path, sha, text, encoding, len(data), replaced)


def _compare_to_unified_diff(files: list[dict]) -> str:
    """把 compare API 的 files 列表重建为统一 diff 文本。"""
    chunks: list[str] = []
    for item in files:
        filename = str(item.get("filename") or "")
        prev = str(item.get("previous_filename") or "")
        status = str(item.get("status") or "modified")
        left = prev or filename
        chunks.append(f"diff --git a/{left} b/{filename}")
        chunks.append(f"index 0000000..0000000 100644")
        if status == "added":
            chunks.append("new file mode 100644")
            chunks.append("--- /dev/null")
            chunks.append(f"+++ b/{filename}")
        elif status == "removed":
            chunks.append("deleted file mode 100644")
            chunks.append(f"--- a/{left}")
            chunks.append("+++ /dev/null")
        elif status == "renamed":
            chunks.append(f"rename from {left}")
            chunks.append(f"rename to {filename}")
            chunks.append(f"--- a/{left}")
            chunks.append(f"+++ b/{filename}")
        else:
            chunks.append(f"--- a/{left}")
            chunks.append(f"+++ b/{filename}")
        patch = item.get("patch")
        if patch:
            chunks.append(str(patch).rstrip("\n"))
        else:
            chunks.append(f"Binary files a/{left} and b/{filename} differ")
        chunks.append("")
    return "\n".join(chunks)
