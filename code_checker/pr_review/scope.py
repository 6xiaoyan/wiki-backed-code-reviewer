"""审查范围：从全仓扫描改为以 PR diff 为入口（PRD §6.1）。

职责：
  * 判断哪些变更文件“适用”审查；
  * 记录每个排除项及原因（二进制/生成/第三方/不支持类型/超大）；
  * 执行文件数与变更行数预算，超出部分明确记为 not_covered，
    不静默只审查前若干文件；
  * 识别“只修改了审查程序/规则/工作流”的 PR，按 PRD 标为 skipped。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from code_checker.pr_review.models import (
    CXX_EXTENSIONS,
    EXCLUDED_DIR_NAMES,
    GENERATED_FILE_PATTERNS,
    QT_SPECIAL_EXTENSIONS,
    SOURCE_EXTENSIONS,
    BudgetConfig,
    ChangedFile,
)
from code_checker.pr_review.snapshot import FileTooLarge, Snapshot, SnapshotError

EXCLUDE_BINARY = "binary"
EXCLUDE_UNSUPPORTED = "unsupported_type"
EXCLUDE_DIR = "excluded_directory"
EXCLUDE_GENERATED = "generated_file"
EXCLUDE_NO_TEXT_CHANGE = "no_text_change"
EXCLUDE_TOO_LARGE = "file_too_large"
EXCLUDE_REVIEW_CONFIG = "review_config_change"

#: 审查程序/规则/skill/工作流自身的改动。它们不改变本轮审查标准。
REVIEW_CONFIG_PREFIXES = (
    "code_checker/",
    "rules-wiki/",
    "rules/",
    "agent-skills/",
    "docs/",
    ".github/",
    "tests/",
)
REVIEW_CONFIG_FILENAMES = {
    "pyproject.toml", "requirements.txt", "requirements-dev.txt",
    "README.md", "AGENTS.md", ".env.example", ".gitignore",
}

_GENERATED_RES = [re.compile(p) for p in GENERATED_FILE_PATTERNS]


@dataclass
class ScopeDecision:
    included: list[ChangedFile] = field(default_factory=list)
    excluded: list[dict] = field(default_factory=list)
    not_covered: list[dict] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)
    applicable_changed_lines: int = 0
    status_override: str | None = None

    @property
    def has_applicable_changes(self) -> bool:
        return bool(self.included)

    def to_dict(self) -> dict:
        return {
            "included_files": [f.path for f in self.included],
            "excluded_files": self.excluded,
            "not_covered": self.not_covered,
            "reasons": self.reasons,
            "applicable_changed_lines": self.applicable_changed_lines,
            "status_override": self.status_override,
        }


def is_review_config_path(path: str) -> bool:
    norm = path.replace("\\", "/")
    if norm in REVIEW_CONFIG_FILENAMES:
        return True
    if norm.rsplit("/", 1)[-1] in REVIEW_CONFIG_FILENAMES and "/" not in norm:
        return True
    return any(norm.startswith(p) or f"/{p}" in f"/{norm}" for p in REVIEW_CONFIG_PREFIXES)


def _has_excluded_dir(path: str) -> bool:
    parts = [p.lower() for p in path.replace("\\", "/").split("/")[:-1]]
    return any(p in EXCLUDED_DIR_NAMES for p in parts)


def _is_generated(path: str) -> bool:
    norm = path.replace("\\", "/")
    return any(rx.search(norm) for rx in _GENERATED_RES)


def classify_path(path: str, changed: ChangedFile) -> tuple[bool, str, str]:
    """判断单个文件是否适用。

    Returns:
        (included, reason, category)
    """
    if changed.is_binary or changed.status == "binary":
        return False, "二进制文件，不发送给模型", EXCLUDE_BINARY
    if is_review_config_path(path):
        return False, (
            "审查程序/规则/skill/工作流配置改动；本阶段不改变本次审查标准，"
            "仅作为配置候选记录"
        ), EXCLUDE_REVIEW_CONFIG
    ext = ("." + path.rsplit(".", 1)[-1].lower()) if "." in path else ""
    if ext not in SOURCE_EXTENSIONS:
        return False, f"不支持的文件类型（{ext or '无扩展名'}）", EXCLUDE_UNSUPPORTED
    if _has_excluded_dir(path):
        return False, "第三方/构建/缓存目录", EXCLUDE_DIR
    if _is_generated(path):
        return False, "生成文件（moc/ui/自动生成）", EXCLUDE_GENERATED
    if changed.status != "deleted" and not changed.hunks:
        return False, "仅改名或模式变更，无文本改动", EXCLUDE_NO_TEXT_CHANGE
    return True, "", ""


def domain_of(path: str, content: str) -> str:
    """按文件路径与内容判断主要审查域（cpp/qt/sqlite）。"""
    from code_checker.config import QT_MARKERS, SQLITE_MARKERS

    ext = ("." + path.rsplit(".", 1)[-1].lower()) if "." in path else ""
    if ext in QT_SPECIAL_EXTENSIONS:
        return "qt"
    if ext in CXX_EXTENSIONS:
        if SQLITE_MARKERS.search(content or ""):
            return "sqlite"
        if QT_MARKERS.search(content or ""):
            return "qt"
        return "cpp"
    return "cpp"


def build_scope(
    changed_files: list[ChangedFile],
    snapshot: Snapshot,
    request,
    budget_config: BudgetConfig,
) -> tuple[ScopeDecision, dict[str, str]]:
    """根据 diff 与预算构建审查范围。

    Returns:
        (decision, head_contents)：head_contents 仅包含“本次审查需要”的文件内容，
        不会递归读取全仓源码。
    """
    decision = ScopeDecision()
    head_contents: dict[str, str] = {}
    all_config_only = bool(changed_files)

    candidates: list[tuple[ChangedFile, str]] = []
    for cf in changed_files:
        if not is_review_config_path(cf.path):
            all_config_only = False
        included, reason, category = classify_path(cf.path, cf)
        if not included:
            decision.excluded.append({
                "path": cf.path,
                "old_path": cf.old_path,
                "status": cf.status,
                "category": category,
                "reason": reason,
            })
            continue

        sha = request.base_sha if cf.status == "deleted" else request.head_sha
        try:
            info = snapshot.file_info(cf.path, sha)
        except SnapshotError as exc:
            decision.not_covered.append({
                "path": cf.path, "reason": f"读取文件信息失败: {exc}",
            })
            decision.status_override = "incomplete"
            decision.reasons.append(f"{cf.path}: 读取文件信息失败")
            continue

        size = int((info or {}).get("size") or 0)
        if size > budget_config.max_file_bytes:
            # 超过单文件上限属于“未覆盖”，不是普通的排除项：
            # 有适用代码改动但没有读取，不能静默跳过，也不能宣称审查完成。
            reason = (
                f"文件 {size} 字节超过单文件上限 "
                f"{budget_config.max_file_bytes} 字节，未读取"
            )
            decision.not_covered.append({
                "path": cf.path,
                "old_path": cf.old_path,
                "status": cf.status,
                "category": EXCLUDE_TOO_LARGE,
                "reason": reason,
            })
            decision.status_override = "incomplete"
            decision.reasons.append(f"{cf.path}: {reason}")
            continue

        try:
            blob = snapshot.read_text(cf.path, sha, max_bytes=budget_config.max_file_bytes)
        except FileTooLarge as exc:
            decision.not_covered.append({
                "path": cf.path, "old_path": cf.old_path, "status": cf.status,
                "category": EXCLUDE_TOO_LARGE, "reason": str(exc),
            })
            decision.status_override = "incomplete"
            decision.reasons.append(f"{cf.path}: {exc}")
            continue
        except SnapshotError as exc:
            decision.not_covered.append({
                "path": cf.path, "reason": f"读取文件失败: {exc}",
            })
            decision.status_override = "incomplete"
            decision.reasons.append(f"{cf.path}: 读取失败")
            continue

        if blob.replacement_chars:
            decision.reasons.append(f"{cf.path}: 文本编码无法完整解码，已用替换字符")
        head_contents[cf.path] = blob.text
        candidates.append((cf, blob.text))

    # ── 文件数预算 ──
    approved = candidates
    if len(candidates) > budget_config.max_files:
        approved = candidates[:budget_config.max_files]
        for cf, _ in candidates[budget_config.max_files:]:
            decision.not_covered.append({
                "path": cf.path,
                "reason": (
                    f"超过单 PR 适用文件预算（{budget_config.max_files} 个），"
                    f"本次未审查"
                ),
            })
        decision.status_override = "incomplete"
        decision.reasons.append(
            f"适用文件 {len(candidates)} 个，超过预算 {budget_config.max_files} 个；"
            f"已审查前 {budget_config.max_files} 个，其余明确未完成"
        )

    # ── 变更行预算 ──
    selected: list[ChangedFile] = []
    used_lines = 0
    line_budget_exceeded = False
    for cf, text in approved:
        cost = cf.additions + cf.deletions
        if used_lines + cost > budget_config.max_changed_lines:
            decision.not_covered.append({
                "path": cf.path,
                "reason": (
                    f"超过单 PR 变更行预算（{budget_config.max_changed_lines} 行），"
                    f"本次未审查"
                ),
            })
            decision.status_override = "incomplete"
            line_budget_exceeded = True
            continue
        used_lines += cost
        selected.append(cf)
    if line_budget_exceeded:
        decision.reasons.append(
            f"变更行预算 {budget_config.max_changed_lines} 行；"
            f"实际纳入 {used_lines} 行，未覆盖文件已列出"
        )

    # 未纳入的 head 内容不应暴露给模型
    kept_paths = {cf.path for cf in selected}
    head_contents = {p: t for p, t in head_contents.items() if p in kept_paths}

    decision.included = selected
    decision.applicable_changed_lines = used_lines

    if not decision.included:
        if decision.not_covered:
            # 存在适用代码改动，但都因预算/读取失败未审查：
            # 这必须是 incomplete，不能降级成普通 skipped。
            decision.status_override = "incomplete"
            decision.reasons.append(
                f"存在 {len(decision.not_covered)} 个适用代码文件未被实际审查"
                f"（超预算或读取失败），审查未完成"
            )
        elif all_config_only and changed_files:
            decision.status_override = "skipped"
            decision.reasons.append(
                "本 PR 只修改了审查程序/规则/skill/工作流；"
                "这些改动不改变本次审查标准，作为配置候选记录，"
                "本阶段不执行 Wiki 评测或自动发布"
            )
        elif changed_files:
            decision.status_override = "skipped"
            decision.reasons.append("没有适用的代码改动（所有变更文件均被排除）")
        else:
            decision.status_override = "skipped"
            decision.reasons.append("PR 没有文件改动")

    return decision, head_contents
