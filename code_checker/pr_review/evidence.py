"""证据核验：模型发现必须在固定版本中可核对，且与本次改动相关。

每条候选都要通过：
  1. 文件属于本次审查范围；
  2. 行号在固定版本文件范围内；
  3. 引用的代码与固定版本对应行一致（归一化比较）；
  4. 规则依据来自可信 Wiki/确定性检查（rule_id 可解析）；
  5. 与改动关联：新增行 / 删除行；上下文行上的问题视为历史问题。
证据不足的候选进入 ``uncertain_findings``，不计入已确认问题，也不作为合并阻断。
"""

from __future__ import annotations

import re
from typing import Iterable

from code_checker.pr_review.models import (
    ChangedFile,
    Finding,
    SEVERITY_ORDER,
    stable_finding_id,
)

_WS_RE = re.compile(r"\s+")


def default_rule_registry() -> dict[str, dict]:
    """从可信 Wiki 索引构建 rule_id → {title, domain} 注册表。

    只读取本地 ``code_checker/rules-wiki``，不访问网络，也不读取 PR 分支内容。
    """
    try:
        from code_checker.wiki_search import _init_index

        index = _init_index()
    except Exception:
        return {}
    return {
        slug: {
            "title": str(page.get("title") or slug),
            "domain": str(page.get("domain") or ""),
        }
        for slug, page in index.items()
    }


def _norm(text: str) -> str:
    return _WS_RE.sub("", (text or "").strip())


def codes_match(claimed: str, actual: str) -> bool:
    c, a = _norm(claimed), _norm(actual)
    if not c or not a:
        return False
    if c == a:
        return True
    if len(c) >= 10 and len(a) >= 10 and (c in a or a in c):
        return True
    return False


def _line_at(contents: dict[str, str], path: str, line: int) -> str:
    text = contents.get(path)
    if text is None:
        return ""
    lines = text.split("\n")
    if 1 <= line <= len(lines):
        return lines[line - 1].strip()
    return ""


def _new_to_old_map(cf: ChangedFile) -> dict[int, int]:
    mapping: dict[int, int] = {}
    for hunk in cf.hunks:
        for line in hunk.lines:
            if line.new_lineno is not None and line.old_lineno is not None:
                mapping[line.new_lineno] = line.old_lineno
    return mapping


def relation_for(cf: ChangedFile, line: int) -> tuple[str, str]:
    """返回 (relation, reason)。relation 为空表示不能作为确认问题。"""
    if cf.status == "deleted":
        if line in cf.removed_linenos:
            return "deleted", ""
        return "", "该行不在删除范围内（历史问题）"
    if line in cf.added_linenos:
        return "added", ""
    if line in cf.context_new_linenos:
        return "", "位于未改动的上下文行，无法证明由本次改动引入（历史问题）"
    return "", "该行不在本次 diff 改动范围内（历史问题）"


def verify_findings(
    raw_findings: Iterable[dict],
    *,
    files: list[ChangedFile],
    head_contents: dict[str, str],
    base_contents: dict[str, str],
    registry: dict[str, dict],
    default_source: str,
    max_findings: int = 200,
) -> dict:
    """核验模型输出。

    Returns:
        {"confirmed": [Finding], "uncertain": [dict], "filtered": [dict]}
    """
    by_path = {f.path: f for f in files}
    confirmed: list[Finding] = []
    uncertain: list[dict] = []
    filtered: list[dict] = []
    seen: set[tuple[str, int, str]] = set()
    index = 0

    for raw in raw_findings or []:
        if not isinstance(raw, dict):
            continue
        path = str(raw.get("file") or "").replace("\\", "/").lstrip("./")
        try:
            line = int(raw.get("line") or 0)
        except (TypeError, ValueError):
            line = 0
        rule_id = str(raw.get("rule_id") or raw.get("rule_page") or "").strip()
        severity = str(raw.get("severity") or "warning").strip().lower()
        message = str(raw.get("message") or raw.get("reason") or "").strip()
        code = str(raw.get("code") or raw.get("current") or "").strip()
        suggestion = str(raw.get("suggestion") or "").strip()
        source = str(raw.get("source") or default_source)

        if severity not in SEVERITY_ORDER:
            severity = "warning"

        cf = by_path.get(path)
        if cf is None:
            uncertain.append(_entry(path, line, rule_id, severity, source,
                                    "文件不在本次审查范围", raw))
            continue
        if line < 1:
            uncertain.append(_entry(path, line, rule_id, severity, source,
                                    "缺少有效行号", raw))
            continue
        content = head_contents.get(path, "")
        if content and line > len(content.split("\n")):
            uncertain.append(_entry(path, line, rule_id, severity, source,
                                    "行号超出固定版本文件范围", raw))
            continue

        actual = _line_at(head_contents, path, line)
        if code and not codes_match(code, actual):
            # 允许行号 ±2 的偏差，但必须能在附近找到引用代码
            corrected = None
            for delta in (-2, -1, 1, 2):
                cand = _line_at(head_contents, path, line + delta)
                if cand and codes_match(code, cand):
                    corrected = line + delta
                    break
            if corrected is None:
                uncertain.append(_entry(
                    path, line, rule_id, severity, source,
                    "引用的代码在固定版本对应位置不存在（疑似幻觉）", raw,
                ))
                continue
            line = corrected

        if not rule_id or (registry and rule_id not in registry):
            uncertain.append(_entry(
                path, line, rule_id, severity, source,
                "规则依据无法在可信 Wiki/确定性检查中解析", raw,
            ))
            continue

        relation, reason = relation_for(cf, line)
        if not relation:
            if "上下文行" in reason:
                base_line = _new_to_old_map(cf).get(line)
                if base_line and codes_match(code or actual,
                                             _line_at(base_contents, path, base_line)):
                    reason = "同一问题在改动前的版本中已存在（历史问题）"
            filtered.append(_entry(path, line, rule_id, severity, source, reason, raw))
            continue

        key = (path, line, rule_id)
        if key in seen:
            continue
        seen.add(key)
        index += 1
        confirmed.append(Finding(
            id=stable_finding_id(path, line, rule_id, index),
            severity=severity,
            file=path,
            line=line,
            rule_id=rule_id,
            rule_title=str((registry.get(rule_id) or {}).get("title") or rule_id),
            rule_page=rule_id if rule_id in registry else "",
            message=message[:2000] or "（模型未给出说明）",
            code_evidence=(code or actual)[:500],
            change_relation=relation,
            suggestion=(suggestion[:1500] + "（建议，未执行验证）"
                        if suggestion and "未执行验证" not in suggestion else suggestion),
            source=source,
        ))
        if len(confirmed) >= max_findings:
            break

    return {"confirmed": confirmed, "uncertain": uncertain, "filtered": filtered}


def _entry(path: str, line: int, rule_id: str, severity: str, source: str,
           reason: str, raw: dict | None = None) -> dict:
    entry = {
        "file": path,
        "line": line,
        "rule_id": rule_id,
        "severity": severity,
        "source": source,
        "reason": reason,
    }
    if raw and raw.get("message"):
        entry["message"] = str(raw.get("message"))[:500]
    return entry
