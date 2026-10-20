"""PR 模式的确定性检查与改动关联性过滤（PRD §6.1、§6.2）。

复用 ``code_checker.nodes.deterministic_checker`` 中已有的正则规则（不在 PR
入口重写规则），但只对本次变更文件执行，并把每条候选与 diff 对应起来：

  * added     —— 新增行上的问题，可作为本次发现；
  * deleted   —— 删除行导致的问题（只在删除行上报告）；
  * modified  —— 改动行上原本不存在、改动后出现的问题；
  * uncertain —— 上下文行/规则级检查，证据不足以判定为新引入；
  * filtered  —— 历史问题或在未改动行上，记录原因但不计入确认问题。
"""

from __future__ import annotations

import os

from code_checker.pr_review import rules as rules_module
from code_checker.pr_review.models import (
    ChangedFile,
    Finding,
    SEVERITY_ORDER,
    stable_finding_id,
)

#: check_id → wiki 页面（页面存在时才写入 rule_page）。
CHECK_TO_WIKI: dict[str, str] = {
    "check_tab_indentation": "cpp/indentation",
    "check_line_width": "cpp/line-width",
    "check_define_macro": "cpp/no-macro-constants",
    "check_c_style_array": "cpp/no-cstyle-strings-arrays",
    "check_throw_spec": "cpp/no-throw-spec",
    "check_default_lambda_capture": "cpp/lambda-explicit-capture",
    "check_reinterpret_cast": "cpp/no-reinterpret-c-cast",
    "check_c_variadic": "cpp/no-varargs",
    "check_header_guard": "cpp/header-guards",
    "check_using_namespace_in_header": "cpp/no-using-namespace-in-header",
    "check_qt_include_dot_h": "qt/include-no-dot-h",
    "check_qt_signal_name": "qt/signal-no-signal-word",
    "check_qt_slot_name": "qt/slot-no-slot-word",
    "check_sqlite_pragma_key": "sqlite/must-use-sqlcipher",
    "check_sqlite_kdf": "sqlite/kdf-iterations",
}

#: 规则级检查：报告的 current 不是具体代码行，而是“缺失项”描述。
FILE_LEVEL_CHECKS = {"check_sqlite_pragma_key", "check_sqlite_kdf"}


def _wiki_page_exists(slug: str) -> bool:
    from code_checker.wiki_search import _WIKI_DIR  # noqa: PLC0415 - 延迟导入避免循环

    if not slug:
        return False
    return os.path.isfile(os.path.join(_WIKI_DIR, slug.replace("/", os.sep) + ".md"))


def run_deterministic_checks(
    files: list[ChangedFile],
    contents: dict[str, str],
) -> list[dict]:
    """对变更文件执行现有确定性规则。零 LLM 调用。"""
    from code_checker.nodes.deterministic_checker import _run_deterministic_checks

    paths = [f.path for f in files]
    return _run_deterministic_checks(paths, contents, ledger=None)


def _new_to_old_map(cf: ChangedFile) -> dict[int, int]:
    mapping: dict[int, int] = {}
    for hunk in cf.hunks:
        for line in hunk.lines:
            if line.new_lineno is not None and line.old_lineno is not None:
                mapping[line.new_lineno] = line.old_lineno
    return mapping


def _head_line(contents: dict[str, str], path: str, line: int) -> str:
    text = contents.get(path)
    if text is None:
        return ""
    lines = text.split("\n")
    if 1 <= line <= len(lines):
        return lines[line - 1].strip()
    return ""


def _base_line(base_contents: dict[str, str], path: str, line: int) -> str:
    return _head_line(base_contents, path, line)


def _evidence_matches(claimed: str, actual: str) -> bool:
    c = (claimed or "").strip()
    a = (actual or "").strip()
    if not c or not a:
        return False
    return c == a or c in a or a in c or "".join(c.split()) == "".join(a.split())


def _is_file_level(check_id: str) -> bool:
    return check_id in FILE_LEVEL_CHECKS


def filter_deterministic_violations(
    violations: list[dict],
    files: list[ChangedFile],
    head_contents: dict[str, str],
    base_contents: dict[str, str],
    *,
    rule_page_resolver=_wiki_page_exists,
) -> dict:
    """把确定性违规分成 confirmed / uncertain / filtered 三类。

    Returns:
        {"confirmed": [Finding], "uncertain": [dict], "filtered": [dict]}
    """
    by_path = {f.path: f for f in files}
    confirmed: list[Finding] = []
    uncertain: list[dict] = []
    filtered: list[dict] = []
    index = 0

    for v in violations:
        path = str(v.get("file") or "")
        line = int(v.get("line") or 0)
        rule = str(v.get("rule") or "")
        check_id = str(v.get("check_id") or "")
        severity = str(v.get("severity") or "warning")
        current = str(v.get("current") or "")
        cf = by_path.get(path)
        if cf is None:
            filtered.append({
                "file": path, "line": line, "rule": rule, "source": "deterministic",
                "reason": "文件不在本次审查范围",
            })
            continue

        relation = ""
        reason = ""
        evidence = current

        if cf.status == "deleted":
            if line in cf.removed_linenos:
                relation = "deleted"
                evidence = f"- {current}"
            else:
                reason = "删除文件中未被删除的行，属于历史问题"
        elif line in cf.added_linenos:
            relation = "added"
            evidence = f"+ {current}"
        elif line in cf.context_new_linenos:
            old_line = _new_to_old_map(cf).get(line)
            base_text = _base_line(base_contents, path, old_line) if old_line else ""
            if base_text and _evidence_matches(current, base_text):
                reason = "同一问题在改动前的版本中已存在（历史问题，不计为本次新增）"
            else:
                reason = "位于改动块上下文行，无法证明由本次改动引入"
        else:
            if _is_file_level(check_id) and cf.status == "added":
                relation = "added"
                evidence = current or "（新增文件缺少规则要求的配置）"
            elif _is_file_level(check_id):
                reason = (
                    "规则级检查（如缺少加密配置）在改动前已存在，"
                    "本次改动未新增该缺失，证据不足"
                )
            else:
                reason = "该行不在本次 diff 改动范围内（历史问题）"

        if relation:
            if not _is_file_level(check_id) and not _evidence_matches(
                current, _head_line(head_contents, path, line)
            ):
                reason = "声称的代码与固定版本中的实际行不匹配"
                relation = ""

        if relation:
            index += 1
            page = CHECK_TO_WIKI.get(check_id, "") if rule_page_resolver(
                CHECK_TO_WIKI.get(check_id, "")) else ""
            basis = rules_module.rule_clause(page) if page else ""
            confirmed.append(Finding(
                id=stable_finding_id(path, line, check_id or rule, index),
                severity=severity if severity in SEVERITY_ORDER else "warning",
                file=path,
                line=line,
                rule_id=f"deterministic/{check_id}" if check_id else "deterministic",
                rule_title=rule,
                rule_page=page,
                rule_quote=basis[:800],
                rule_basis=basis,
                rule_source=rules_module.rule_source(page) if page else "",
                message=str(v.get("reason") or rule),
                code_evidence=evidence[:500],
                change_relation=relation,
                suggestion=f"将 `{current}` 改为 `{v.get('expected', '')}`（建议，未执行验证）",
                source="deterministic",
            ))
            continue

        entry = {
            "file": path,
            "line": line,
            "rule": rule,
            "rule_id": f"deterministic/{check_id}" if check_id else "deterministic",
            "severity": severity,
            "source": "deterministic",
            "reason": reason,
        }
        if "证据不足" in reason or "无法证明" in reason:
            uncertain.append(entry)
        else:
            filtered.append(entry)

    return {"confirmed": confirmed, "uncertain": uncertain, "filtered": filtered}
