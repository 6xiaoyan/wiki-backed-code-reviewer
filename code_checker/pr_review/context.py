"""审查上下文构建：变更片段 + 所在函数/类 + 必要时读取关联文件。

遵循 PRD §6.1：模型优先看到 diff 片段与所在符号，不预先递归读取全仓源码。
所有额外读取都经过预算计量并记录 (路径, 版本, 范围, 用途)。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from code_checker.pr_review.budget import ReviewBudget
from code_checker.pr_review.models import ChangedFile
from code_checker.pr_review.snapshot import Snapshot, SnapshotError

_FUNC_RE = re.compile(
    r"^\s*(?:template\s*<[^>]*>\s*)?"
    r"(?:[\w:<>,*&\s]+?\s+)?[\w:~<>]+\s*\([^;{}]*\)\s*"
    r"(?:const\s*)?(?:noexcept\s*)?(?:override\s*)?(?:final\s*)?\{?\s*$"
)
_CLASS_RE = re.compile(r"^\s*(class|struct)\s+([\w:]+)[^;{]*\{?\s*$")
_NAMESPACE_RE = re.compile(r"^\s*namespace\s+([\w:]+)\s*\{?\s*$")
_COMMENT_OR_STRING_RE = re.compile(r"^\s*(//|/\*|\*)")


@dataclass
class Symbol:
    kind: str
    name: str
    start_line: int
    end_line: int

    def to_dict(self) -> dict:
        return {
            "kind": self.kind, "name": self.name,
            "start_line": self.start_line, "end_line": self.end_line,
        }


@dataclass
class ContextRead:
    path: str
    sha: str
    start: int
    end: int
    purpose: str
    bytes: int

    def to_dict(self) -> dict:
        return {
            "path": self.path, "sha": self.sha, "start": self.start,
            "end": self.end, "purpose": self.purpose, "bytes": self.bytes,
        }


@dataclass
class ContextBuilder:
    snapshot: Snapshot
    budget: ReviewBudget
    reads: list[ContextRead] = field(default_factory=list)

    def read_range(self, path: str, sha: str, start: int, end: int,
                   purpose: str) -> str:
        blob = self.snapshot.read_text(path, sha)
        lines = blob.text.split("\n")
        start = max(1, start)
        end = min(len(lines), end)
        if end < start:
            return ""
        text = "\n".join(lines[start - 1:end])
        self.budget.add_context(path, sha, start, end, len(text.encode("utf-8")))
        self.reads.append(ContextRead(path, sha, start, end, purpose,
                                      len(text.encode("utf-8"))))
        return text

    def reads_dict(self) -> list[dict]:
        return [r.to_dict() for r in self.reads]


def find_enclosing_symbol(text: str, line: int) -> Symbol | None:
    """启发式定位包含指定行的函数/类/命名空间。

    只做静态文本扫描，不解析 C++ 语法；找不到时返回 None（不影响审查，
    只是模型上下文少一段）。
    """
    if not text or line < 1:
        return None
    lines = text.split("\n")
    line = min(line, len(lines))
    best: Symbol | None = None

    for idx in range(line - 1, max(-1, line - 400), -1):
        raw = lines[idx]
        if _COMMENT_OR_STRING_RE.match(raw):
            continue
        m_class = _CLASS_RE.match(raw)
        if m_class:
            end = _find_block_end(lines, idx)
            if end >= line:
                best = Symbol(m_class.group(1), m_class.group(2).strip(), idx + 1, end)
                break
        m_ns = _NAMESPACE_RE.match(raw)
        if m_ns:
            end = _find_block_end(lines, idx)
            if end >= line:
                best = Symbol("namespace", m_ns.group(1), idx + 1, end)
                break
        if _FUNC_RE.match(raw) and not raw.strip().startswith(("if", "for", "while", "switch")):
            end = _find_block_end(lines, idx)
            if end >= line:
                best = Symbol("function", _guess_name(raw), idx + 1, end)
                break
    return best


def _guess_name(declaration: str) -> str:
    m = re.search(r"([~\w:]+)\s*\([^;{}]*\)", declaration)
    return m.group(1) if m else declaration.strip()[:80]


def _find_block_end(lines: list[str], start_idx: int) -> int:
    """从声明行开始找匹配的右花括号所在行（1-based）；找不到返回文件末尾。"""
    depth = 0
    opened = False
    for idx in range(start_idx, min(len(lines), start_idx + 800)):
        for ch in lines[idx]:
            if ch == "{":
                depth += 1
                opened = True
            elif ch == "}":
                depth -= 1
                if opened and depth <= 0:
                    return idx + 1
    return len(lines)


def format_hunks(cf: ChangedFile, *, max_lines: int = 120) -> str:
    """把改动块格式化为带行号的紧凑文本。"""
    out: list[str] = []
    used = 0
    for h in cf.hunks:
        header = (
            f"@@ -{h.old_start},{h.old_count} +{h.new_start},{h.new_count} @@ {h.header}"
        ).strip()
        out.append(header)
        for line in h.lines:
            if line.kind == "\\":
                continue
            if used >= max_lines:
                out.append(f"...（改动片段已截断，剩余 {len(h.lines)} 行未显示）")
                return "\n".join(out)
            lineno = line.new_lineno if line.new_lineno is not None else line.old_lineno
            out.append(f"{line.kind}{lineno:>5} | {line.text}")
            used += 1
    return "\n".join(out)


def build_file_context(
    cf: ChangedFile,
    text: str,
    *,
    max_hunk_lines: int = 120,
    max_context_chars: int = 14000,
) -> str:
    """为单个文件生成模型输入片段（不含全文）。"""
    parts = [f"文件: {cf.path}（{cf.status}，+{cf.additions}/-{cf.deletions}）"]
    hunks = format_hunks(cf, max_lines=max_hunk_lines)
    if hunks:
        parts.append("改动片段：\n" + hunks)

    if text:
        first_added = min(cf.added_linenos) if cf.added_linenos else None
        if first_added:
            symbol = find_enclosing_symbol(text, first_added)
            if symbol:
                body = "\n".join(text.split("\n")[symbol.start_line - 1:symbol.end_line])
                if len(body) > 4000:
                    body = body[:4000] + "\n...（符号内容已截断）"
                parts.append(
                    f"所在{symbol.kind}: {symbol.name} "
                    f"(行 {symbol.start_line}-{symbol.end_line})\n{body}"
                )
    context = "\n\n".join(parts)
    if len(context) > max_context_chars:
        context = context[:max_context_chars] + "\n...（上下文已截断）"
    return context
