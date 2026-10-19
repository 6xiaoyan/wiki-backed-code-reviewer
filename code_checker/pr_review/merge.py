"""合并与去重（确定性，PR 模式不调用模型做合并）。

PR 模式的合并只做可解释的确定性操作：
  * 同 (file, line, rule_id) 视为同一条，保留严重度最高者并合并来源；
  * 确定性检查结果优先保留（其证据来自 Python 正则，不依赖模型）；
  * 按严重度、文件、行号排序。
"""

from __future__ import annotations

from code_checker.pr_review.models import Finding, SEVERITY_ORDER


def merge_findings(*groups: list[Finding]) -> list[Finding]:
    merged: dict[tuple[str, int, str], Finding] = {}
    for group in groups:
        for f in group:
            key = (f.file, f.line, f.rule_id)
            existing = merged.get(key)
            if existing is None:
                merged[key] = f
                continue
            # 严重度更高者胜出；相同则保留确定性来源
            new_rank = SEVERITY_ORDER.get(f.severity, 99)
            old_rank = SEVERITY_ORDER.get(existing.severity, 99)
            winner, loser = (f, existing) if new_rank < old_rank else (existing, f)
            if existing.source != f.source:
                sources = sorted({s for s in existing.source.split("|") + f.source.split("|") if s})
                winner.source = "|".join(sources)
            if len(loser.message) > len(winner.message):
                winner.message = loser.message
            if not winner.suggestion and loser.suggestion:
                winner.suggestion = loser.suggestion
            merged[key] = winner
    return sorted(
        merged.values(),
        key=lambda f: (SEVERITY_ORDER.get(f.severity, 99), f.file, f.line, f.rule_id),
    )


def severity_counts(findings: list[Finding]) -> dict[str, int]:
    counts = {"critical": 0, "warning": 0, "suggestion": 0, "info": 0}
    for f in findings:
        counts[f.severity] = counts.get(f.severity, 0) + 1
    return counts
