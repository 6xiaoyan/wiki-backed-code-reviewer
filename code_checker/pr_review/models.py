"""PR 审查的数据模型与状态机常量。

设计原则：
  * 纯标准库，可在没有模型凭据、没有 LangGraph 的环境中导入与测试。
  * 所有版本标识、预算与状态字段都显式建模，便于写入 ReviewRequest/结果 JSON。
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Optional

# ---------------------------------------------------------------------------
# 状态机（PRD §9.1）
# ---------------------------------------------------------------------------
STATUS_COMPLETED = "completed"
STATUS_SKIPPED = "skipped"
STATUS_INCOMPLETE = "incomplete"
STATUS_FAILED = "failed"
STATUS_SUPERSEDED = "superseded"

ALL_STATUSES = (
    STATUS_COMPLETED,
    STATUS_SKIPPED,
    STATUS_INCOMPLETE,
    STATUS_FAILED,
    STATUS_SUPERSEDED,
)

#: analyze 进程的退出码。incomplete 必须以非零状态结束（PRD §9.1）。
STATUS_EXIT_CODES = {
    STATUS_COMPLETED: 0,
    STATUS_SKIPPED: 0,
    STATUS_INCOMPLETE: 2,
    STATUS_FAILED: 1,
    STATUS_SUPERSEDED: 0,
}

SEVERITIES = ("critical", "warning", "suggestion", "info")
SEVERITY_ORDER = {"critical": 0, "warning": 1, "suggestion": 2, "info": 3}

#: 会被发送给模型/纳入审查的文件类型（与现有全仓模式保持一致）。
SOURCE_EXTENSIONS = {".cpp", ".h", ".hpp", ".cc", ".pro", ".ui"}
CXX_EXTENSIONS = {".cpp", ".h", ".hpp", ".cc"}
QT_SPECIAL_EXTENSIONS = {".pro", ".ui"}

#: 二进制/生成/第三方目录，记录为排除项，不发送给模型（PRD §6.1-5）。
EXCLUDED_DIR_NAMES = {
    ".git", ".github", "build", "dist", "out", "node_modules",
    "third_party", "thirdparty", "3rdparty", "vendor", "external",
    "external_sources", "moc", "obj", ".cache", "__pycache__",
}
GENERATED_FILE_PATTERNS = (
    r"(^|/)moc_.*\.(cpp|h)$",
    r"(^|/)ui_.*\.h$",
    r".*_generated\.(cpp|h|cc)$",
    r".*\.pb\.(cc|h)$",
    r".*_autogen/.*",
    r".*\.min\.(js|css)$",
)


# ---------------------------------------------------------------------------
# Diff 结构
# ---------------------------------------------------------------------------
@dataclass
class DiffLine:
    """统一 diff 中的一行。"""

    kind: str  # " " | "+" | "-" | "\\"（no newline 标记）
    text: str
    old_lineno: Optional[int] = None
    new_lineno: Optional[int] = None

    def to_dict(self) -> dict:
        return {
            "kind": self.kind,
            "text": self.text,
            "old_lineno": self.old_lineno,
            "new_lineno": self.new_lineno,
        }


@dataclass
class Hunk:
    """一个 @@ 段落。行号均为 1-based；计数为 0 时起始行号按 Git 语义处理。"""

    old_start: int
    old_count: int
    new_start: int
    new_count: int
    header: str = ""
    lines: list[DiffLine] = field(default_factory=list)

    @property
    def added_new_linenos(self) -> set[int]:
        return {ln.new_lineno for ln in self.lines
                if ln.kind == "+" and ln.new_lineno is not None}

    @property
    def removed_old_linenos(self) -> set[int]:
        return {ln.old_lineno for ln in self.lines
                if ln.kind == "-" and ln.old_lineno is not None}

    @property
    def context_new_linenos(self) -> set[int]:
        return {ln.new_lineno for ln in self.lines
                if ln.kind == " " and ln.new_lineno is not None}

    @property
    def changed_line_count(self) -> int:
        return sum(1 for ln in self.lines if ln.kind in ("+", "-"))

    def to_dict(self) -> dict:
        return {
            "old_start": self.old_start,
            "old_count": self.old_count,
            "new_start": self.new_start,
            "new_count": self.new_count,
            "header": self.header,
            "lines": [ln.to_dict() for ln in self.lines],
        }


@dataclass
class ChangedFile:
    """diff 中的一个文件条目（含改名/删除/新增/二进制）。"""

    path: str  # head 侧路径；删除文件时为旧路径
    old_path: Optional[str] = None
    status: str = "modified"  # added|modified|deleted|renamed|copied|binary
    additions: int = 0
    deletions: int = 0
    is_binary: bool = False
    hunks: list[Hunk] = field(default_factory=list)

    @property
    def display_path(self) -> str:
        if self.status == "renamed" and self.old_path and self.old_path != self.path:
            return f"{self.old_path} → {self.path}"
        return self.path

    @property
    def added_linenos(self) -> set[int]:
        out: set[int] = set()
        for h in self.hunks:
            out |= h.added_new_linenos
        return out

    @property
    def removed_linenos(self) -> set[int]:
        out: set[int] = set()
        for h in self.hunks:
            out |= h.removed_old_linenos
        return out

    @property
    def changed_linenos(self) -> set[int]:
        """head 侧“本次改动涉及”的行：新增行 + 改动块内的上下文行。"""
        out: set[int] = set()
        for h in self.hunks:
            out |= h.added_new_linenos
            out |= h.context_new_linenos
        return out

    @property
    def context_new_linenos(self) -> set[int]:
        """改动块内的上下文行（未修改，但位于 hunk 范围内）。"""
        out: set[int] = set()
        for h in self.hunks:
            out |= h.context_new_linenos
        return out

    @property
    def changed_line_count(self) -> int:
        return sum(h.changed_line_count for h in self.hunks)

    def to_dict(self) -> dict:
        return {
            "path": self.path,
            "old_path": self.old_path,
            "status": self.status,
            "additions": self.additions,
            "deletions": self.deletions,
            "is_binary": self.is_binary,
            "hunks": [h.to_dict() for h in self.hunks],
        }


# ---------------------------------------------------------------------------
# 预算（PRD §10）
# ---------------------------------------------------------------------------
@dataclass
class BudgetConfig:
    """可信预算配置。PR 作者无法通过修改 PR 内的文件提高额度。"""

    max_files: int = 50
    max_changed_lines: int = 3000
    max_file_bytes: int = 256 * 1024
    max_extra_context_bytes: int = 2 * 1024 * 1024
    max_model_requests: int = 40
    review_timeout_seconds: int = 15 * 60
    model_retries_per_call: int = 2
    artifact_retention_days: int = 14
    max_rule_context_bytes: int = 64 * 1024
    max_rule_page_bytes: int = 4 * 1024

    @classmethod
    def from_dict(cls, data: Optional[dict]) -> "BudgetConfig":
        if not data:
            return cls()
        known = {f for f in cls.__dataclass_fields__}
        return cls(**{k: int(v) for k, v in data.items() if k in known and v is not None})

    def to_dict(self) -> dict:
        return {
            "max_files": self.max_files,
            "max_changed_lines": self.max_changed_lines,
            "max_file_bytes": self.max_file_bytes,
            "max_extra_context_bytes": self.max_extra_context_bytes,
            "max_model_requests": self.max_model_requests,
            "review_timeout_seconds": self.review_timeout_seconds,
            "model_retries_per_call": self.model_retries_per_call,
            "artifact_retention_days": self.artifact_retention_days,
            "max_rule_context_bytes": self.max_rule_context_bytes,
            "max_rule_page_bytes": self.max_rule_page_bytes,
        }


# ---------------------------------------------------------------------------
# 审查请求 / 结果
# ---------------------------------------------------------------------------
@dataclass
class ReviewRequest:
    """一次审查的固定输入。三个 SHA 必须来自同一次读取（PRD §6、§8）。"""

    repo: str  # "owner/repo"
    pr_number: int
    base_sha: str
    head_sha: str
    merge_base_sha: str
    program_sha: str = ""
    run_id: str = ""
    run_attempt: int = 1
    run_url: str = ""
    trigger: str = ""
    rules_digest: str = ""
    prompts_digest: str = ""
    config_digest: str = ""
    model_provider: str = "deepseek"
    model_id: str = ""
    budget: BudgetConfig = field(default_factory=BudgetConfig)
    draft: bool = False
    pr_state: str = "open"

    def to_dict(self) -> dict:
        return {
            "repo": self.repo,
            "pr_number": self.pr_number,
            "base_sha": self.base_sha,
            "head_sha": self.head_sha,
            "merge_base_sha": self.merge_base_sha,
            "program_sha": self.program_sha,
            "run_id": self.run_id,
            "run_attempt": self.run_attempt,
            "run_url": self.run_url,
            "trigger": self.trigger,
            "rules_digest": self.rules_digest,
            "prompts_digest": self.prompts_digest,
            "config_digest": self.config_digest,
            "model_provider": self.model_provider,
            "model_id": self.model_id,
            "budget": self.budget.to_dict(),
            "draft": self.draft,
            "pr_state": self.pr_state,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ReviewRequest":
        known = set(cls.__dataclass_fields__)
        kwargs = {k: v for k, v in data.items() if k in known and k != "budget"}
        kwargs["budget"] = BudgetConfig.from_dict(data.get("budget"))
        return cls(**kwargs)


@dataclass
class Finding:
    """一条已确认问题。所有字段都由可信代码生成或经证据核验。"""

    id: str
    severity: str
    file: str
    line: int
    rule_id: str
    rule_title: str
    message: str
    code_evidence: str
    change_relation: str  # added|modified|deleted
    source: str
    rule_page: str = ""
    rule_quote: str = ""
    """模型从可信 Wiki 正文中逐字摘录、并已被证据核验的一句话依据。"""
    rule_basis: str = ""
    """从可信 Wiki 页面确定性提取的规则条款原文（报告展示用）。"""
    rule_source: str = ""
    """规则来源（source_file / source_section），来自页面 frontmatter。"""
    suggestion: str = ""
    end_line: Optional[int] = None

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "severity": self.severity,
            "file": self.file,
            "line": self.line,
            "end_line": self.end_line,
            "rule_id": self.rule_id,
            "rule_title": self.rule_title,
            "rule_page": self.rule_page,
            "rule_quote": self.rule_quote,
            "rule_basis": self.rule_basis,
            "rule_source": self.rule_source,
            "message": self.message,
            "code_evidence": self.code_evidence,
            "change_relation": self.change_relation,
            "suggestion": self.suggestion,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Finding":
        return cls(
            id=str(data.get("id", "")),
            severity=str(data.get("severity", "warning")),
            file=str(data.get("file", "")),
            line=int(data.get("line") or 0),
            end_line=(int(data["end_line"]) if data.get("end_line") else None),
            rule_id=str(data.get("rule_id", "")),
            rule_title=str(data.get("rule_title", "")),
            rule_page=str(data.get("rule_page", "")),
            rule_quote=str(data.get("rule_quote", "")),
            rule_basis=str(data.get("rule_basis", "")),
            rule_source=str(data.get("rule_source", "")),
            message=str(data.get("message", "")),
            code_evidence=str(data.get("code_evidence", "")),
            change_relation=str(data.get("change_relation", "added")),
            suggestion=str(data.get("suggestion", "")),
            source=str(data.get("source", "")),
        )


@dataclass
class ReviewResult:
    """完整审查结果。写入 result.json，并派生 Markdown 报告与 PR 汇总评论。"""

    schema_version: int
    status: str
    status_reason: str
    review_key: str
    generated_at: str
    request: ReviewRequest
    summary: dict = field(default_factory=dict)
    findings: list[Finding] = field(default_factory=list)
    uncertain_findings: list[dict] = field(default_factory=list)
    filtered_findings: list[dict] = field(default_factory=list)
    excluded_files: list[dict] = field(default_factory=list)
    reviewed_files: list[dict] = field(default_factory=list)
    not_covered: list[dict] = field(default_factory=list)
    degradation: list[dict] = field(default_factory=list)
    budget_usage: dict = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    artifacts: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "status": self.status,
            "status_reason": self.status_reason,
            "review_key": self.review_key,
            "generated_at": self.generated_at,
            "request": self.request.to_dict(),
            "summary": self.summary,
            "findings": [f.to_dict() for f in self.findings],
            "uncertain_findings": self.uncertain_findings,
            "filtered_findings": self.filtered_findings,
            "excluded_files": self.excluded_files,
            "reviewed_files": self.reviewed_files,
            "not_covered": self.not_covered,
            "degradation": self.degradation,
            "budget_usage": self.budget_usage,
            "errors": self.errors,
            "artifacts": self.artifacts,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ReviewResult":
        return cls(
            schema_version=int(data.get("schema_version", 1)),
            status=str(data.get("status", STATUS_FAILED)),
            status_reason=str(data.get("status_reason", "")),
            review_key=str(data.get("review_key", "")),
            generated_at=str(data.get("generated_at", "")),
            request=ReviewRequest.from_dict(data.get("request") or {}),
            summary=dict(data.get("summary") or {}),
            findings=[Finding.from_dict(f) for f in (data.get("findings") or [])],
            uncertain_findings=list(data.get("uncertain_findings") or []),
            filtered_findings=list(data.get("filtered_findings") or []),
            excluded_files=list(data.get("excluded_files") or []),
            reviewed_files=list(data.get("reviewed_files") or []),
            not_covered=list(data.get("not_covered") or []),
            degradation=list(data.get("degradation") or []),
            budget_usage=dict(data.get("budget_usage") or {}),
            errors=[str(e) for e in (data.get("errors") or [])],
            artifacts=dict(data.get("artifacts") or {}),
        )


def make_review_key(request: ReviewRequest) -> str:
    """用仓库、PR、三个 SHA 与审查配置计算稳定标识（PRD §8）。

    只包含可公开、非敏感的值；API Key 永不参与。
    """
    payload = {
        "repo": request.repo,
        "pr_number": request.pr_number,
        "base_sha": request.base_sha,
        "head_sha": request.head_sha,
        "merge_base_sha": request.merge_base_sha,
        "program_sha": request.program_sha,
        "rules_digest": request.rules_digest,
        "prompts_digest": request.prompts_digest,
        "config_digest": request.config_digest,
        "model_provider": request.model_provider,
        "model_id": request.model_id,
        "budget": request.budget.to_dict(),
    }
    raw = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def digest_text(text: str) -> str:
    """对文件内容做短摘要（用于规则/skill/提示词版本）。"""
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()[:16]


def digest_files(paths: list[str]) -> str:
    """对一组文件的内容做确定性摘要；缺失文件记为 MISSING。"""
    h = hashlib.sha256()
    for p in sorted(paths):
        h.update(p.encode("utf-8", errors="replace"))
        h.update(b"\0")
        try:
            with open(p, "rb") as fh:
                h.update(fh.read())
        except OSError:
            h.update(b"MISSING")
        h.update(b"\0")
    return h.hexdigest()[:16]


def stable_finding_id(file: str, line: int, rule_id: str, index: int) -> str:
    """生成稳定且可读的 finding id（同一输入重跑得到同一 id）。"""
    seed = f"{file}:{line}:{rule_id}".encode("utf-8", errors="replace")
    return f"F{index:03d}-{hashlib.sha256(seed).hexdigest()[:6]}"


def json_dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=False)
