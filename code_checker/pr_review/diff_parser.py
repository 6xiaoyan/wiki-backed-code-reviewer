"""统一 diff 解析。

只解析 Git 生成的 diff 文本（``git diff --unified`` 或 GitHub compare API 的
``patch`` 字段），不执行任何被审查代码。解析结果携带每行的旧/新行号，
供后续“改动关联性”核验使用。
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from code_checker.pr_review.models import ChangedFile, DiffLine, Hunk


class DiffParseError(ValueError):
    """diff 结构无法解析（数据不完整时不应把失败当成没有改动）。"""


_DIFF_GIT_RE = re.compile(
    r'^diff --git ("(?:[^"\\]|\\.)*"|\S+) ("(?:[^"\\]|\\.)*"|\S+)\s*$'
)
_HUNK_RE = re.compile(
    r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@ ?(.*)$"
)
_QUOTED_RE = re.compile(r'^"(.*)"$')

_ESCAPES = {
    "a": "\a", "b": "\b", "f": "\f", "n": "\n", "r": "\r",
    "t": "\t", "v": "\v", "\\": "\\", '"': '"',
}


def unquote_git_path(value: str) -> str:
    """还原 Git 用 C 风格引号/八进制转义表示的路径。"""
    value = value.strip()
    m = _QUOTED_RE.match(value)
    if not m:
        return value
    body = m.group(1)
    out: list[str] = []
    i = 0
    while i < len(body):
        ch = body[i]
        if ch != "\\" or i + 1 >= len(body):
            out.append(ch)
            i += 1
            continue
        nxt = body[i + 1]
        if nxt in _ESCAPES:
            out.append(_ESCAPES[nxt])
            i += 2
        elif nxt.isdigit():
            # Git 使用三位八进制表示非 ASCII 字节
            octal = body[i + 1:i + 4]
            if len(octal) == 3 and all(c in "01234567" for c in octal):
                out.append(chr(int(octal, 8)))
                i += 4
            else:
                out.append(nxt)
                i += 2
        else:
            out.append(nxt)
            i += 2
    return "".join(out)


def _strip_prefix(path: str) -> str:
    path = unquote_git_path(path)
    if path.startswith("a/") or path.startswith("b/"):
        return path[2:]
    return path


def _parse_file_header_line(line: str) -> str:
    """解析 ``--- a/path`` / ``+++ b/path`` 中的路径。"""
    rest = line[4:]
    path = rest.split("\t", 1)[0]
    return _strip_prefix(path)


def parse_diff(diff_text: str) -> list[ChangedFile]:
    """解析 diff 文本为 ChangedFile 列表。

    Raises:
        DiffParseError: 遇到 hunk 头但缺少文件头等结构错误。
    """
    files: list[ChangedFile] = []
    current: ChangedFile | None = None
    hunk: Hunk | None = None
    old_left = new_left = 0
    old_lineno = new_lineno = 0
    seen_hunk_header = False

    for raw_line in diff_text.splitlines():
        line = raw_line.rstrip("\r")

        # ── 新文件条目 ──
        if line.startswith("diff --git "):
            m = _DIFF_GIT_RE.match(line)
            current = ChangedFile(path="", old_path=None)
            if m:
                current.old_path = _strip_prefix(m.group(1))
                current.path = _strip_prefix(m.group(2))
            files.append(current)
            hunk = None
            old_left = new_left = 0
            seen_hunk_header = False
            continue

        # 允许 diff 直接从 ---/+++ 开始（部分 API 只返回 patch 片段）
        if current is None:
            if line.startswith("--- ") or line.startswith("+++ "):
                current = ChangedFile(path="")
                files.append(current)
                seen_hunk_header = False
            elif line.strip() == "":
                continue
            else:
                raise DiffParseError(f"diff 在文件头之前出现意外内容: {line[:120]!r}")

        if hunk is not None and (old_left > 0 or new_left > 0):
            # ── hunk 正文 ──
            if line.startswith("\\"):
                hunk.lines.append(DiffLine(kind="\\", text=line[1:]))
                continue
            if line.startswith("+"):
                hunk.lines.append(DiffLine("+", line[1:], None, new_lineno))
                new_lineno += 1
                new_left -= 1
                current.additions += 1
                continue
            if line.startswith("-"):
                hunk.lines.append(DiffLine("-", line[1:], old_lineno, None))
                old_lineno += 1
                old_left -= 1
                current.deletions += 1
                continue
            # 上下文行（包括空行：diff 中上下文空行表现为单个空格）
            hunk.lines.append(DiffLine(" ", line[1:] if line.startswith(" ") else line,
                                       old_lineno, new_lineno))
            old_lineno += 1
            new_lineno += 1
            old_left -= 1
            new_left -= 1
            continue

        # ── 文件级元数据 ──
        if line.startswith("new file mode"):
            current.status = "added"
            continue
        if line.startswith("deleted file mode"):
            current.status = "deleted"
            continue
        if line.startswith("rename from "):
            current.old_path = _strip_prefix(line[len("rename from "):].strip())
            current.status = "renamed"
            continue
        if line.startswith("rename to "):
            current.path = _strip_prefix(line[len("rename to "):].strip())
            current.status = "renamed"
            continue
        if line.startswith("copy from "):
            current.old_path = _strip_prefix(line[len("copy from "):].strip())
            current.status = "copied"
            continue
        if line.startswith("copy to "):
            current.path = _strip_prefix(line[len("copy to "):].strip())
            current.status = "copied"
            continue
        if line.startswith("--- "):
            path = _parse_file_header_line(line)
            if path == "/dev/null":
                current.status = "added"
            else:
                current.old_path = path
            continue
        if line.startswith("+++ "):
            path = _parse_file_header_line(line)
            if path == "/dev/null":
                current.status = "deleted"
            else:
                current.path = path
            continue
        if line.startswith("Binary files ") or line.startswith("GIT binary patch"):
            current.is_binary = True
            current.status = "binary"
            continue
        if line.startswith("index ") or line.startswith("old mode") \
                or line.startswith("new mode") or line.startswith("similarity index") \
                or line.startswith("dissimilarity index"):
            continue

        m = _HUNK_RE.match(line)
        if m:
            if not current.path and not current.old_path:
                raise DiffParseError(f"hunk 缺少文件路径: {line[:120]!r}")
            if current.status not in ("added", "deleted", "renamed", "copied", "binary"):
                current.status = "modified"
            old_start = int(m.group(1))
            old_count = int(m.group(2)) if m.group(2) is not None else 1
            new_start = int(m.group(3))
            new_count = int(m.group(4)) if m.group(4) is not None else 1
            hunk = Hunk(old_start, old_count, new_start, new_count, (m.group(5) or "").strip())
            current.hunks.append(hunk)
            old_lineno, new_lineno = old_start, new_start
            old_left, new_left = old_count, new_count
            seen_hunk_header = True
            continue

        # 其他元数据行（mode/index 等兼容）
        if line.startswith("\\ No newline"):
            if hunk is not None:
                hunk.lines.append(DiffLine("\\", ""))
            continue

        if seen_hunk_header:
            # hunk 计数已耗尽后出现的非 diff 结构内容：忽略空行，其余报错
            if line.strip() == "":
                continue
            raise DiffParseError(f"无法识别的 diff 行: {line[:120]!r}")
        # 文件头之前的其他元数据（如 "diff --cc" 未支持）忽略
        if not current.path:
            continue

    # ── 规范化 ──
    for f in files:
        if f.status == "binary":
            f.is_binary = True
        if f.old_path and f.path and f.old_path != f.path and f.status == "modified":
            # git 未输出 rename 信息（相似度低）时仍保留旧路径用于证据
            f.status = "renamed"
        if f.status == "deleted" and f.old_path:
            f.path = f.old_path
        if not f.path and f.old_path:
            f.path = f.old_path
    return [f for f in files if f.path or f.old_path]


def parse_github_pull_files(files_payload: list[dict]) -> list[ChangedFile]:
    """把 GitHub ``GET /pulls/{n}/files`` 的条目转换为 ChangedFile。

    该接口的 patch 不含完整文件内容，行号语义与统一 diff 一致。
    """
    out: list[ChangedFile] = []
    for item in files_payload or []:
        status = str(item.get("status") or "modified")
        cf = ChangedFile(
            path=str(item.get("filename") or ""),
            old_path=str(item.get("previous_filename") or "") or None,
            status=status,
            additions=int(item.get("additions") or 0),
            deletions=int(item.get("deletions") or 0),
        )
        patch = item.get("patch")
        if patch:
            try:
                parsed = parse_diff(f"diff --git a/{cf.path} b/{cf.path}\n{patch}")
                if parsed:
                    cf.hunks = parsed[0].hunks
            except DiffParseError:
                cf.hunks = []
        out.append(cf)
    return out


def total_changed_lines(files: list[ChangedFile]) -> int:
    return sum(f.additions + f.deletions for f in files)
