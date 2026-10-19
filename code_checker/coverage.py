"""
coverage — 覆盖率账本：证明每个文件必须执行的检查都已实际完成。

审查系统的第一性要求是"覆盖率可证明"（不能静默跳过文件/规则）。
此模块独立于 LLM/ReAct/L4，是纯 Python 确定性逻辑。

与消息历史的区别：
  - 消息历史：LLM 的 ReAct 对话记录，可压缩/摘要/丢弃
  - 覆盖率账本：系统事实，不可压缩，不可由 LLM 摘要替代

用法：
  ledger = build_coverage_ledger(file_list, file_contents)
  # ... checker 执行期间 ...
  mark_check_completed(ledger, "passworddialog.h", "check_header_guard")
  # ... 检查完成 ...
  missing = assert_coverage_complete(ledger)
"""

import os
import uuid
from datetime import datetime


def build_coverage_ledger(
    file_list: list[str],
    file_contents: dict[str, str],
) -> dict:
    """为文件列表构建覆盖率账本。

    对每个文件，根据扩展名和内容确定必须执行的检查列表。

    Args:
        file_list: 源文件绝对路径列表
        file_contents: 文件路径 → 文件全文

    Returns:
        覆盖率账本 dict:
        {
            "run_id": str,
            "required_checks": [{"file": str, "check": str, "category": str}, ...],
            "completed_checks": [{"file": str, "check": str}, ...],
            "coverage_complete": False,
        }
    """
    from code_checker.config import (
        CXX_EXTENSIONS, QT_SPECIAL_EXTENSIONS, QT_MARKERS, SQLITE_MARKERS,
    )

    required: list[dict] = []

    for fp in file_list:
        ext = os.path.splitext(fp)[1].lower()
        content = file_contents.get(fp, "")
        basename = os.path.basename(fp)

        # ── 所有 C++ 文件通用检查 ──
        if ext in CXX_EXTENSIONS:
            required.append({"file": fp, "check": "check_tab_indentation", "category": "cpp"})
            required.append({"file": fp, "check": "check_line_width", "category": "cpp"})
            required.append({"file": fp, "check": "check_define_macro", "category": "cpp"})
            required.append({"file": fp, "check": "check_c_style_array", "category": "cpp"})
            required.append({"file": fp, "check": "check_throw_spec", "category": "cpp"})
            required.append({"file": fp, "check": "check_default_lambda_capture", "category": "cpp"})
            required.append({"file": fp, "check": "check_reinterpret_cast", "category": "cpp"})
            required.append({"file": fp, "check": "check_virtual_override", "category": "cpp"})
            required.append({"file": fp, "check": "check_c_variadic", "category": "cpp"})

        # ── 头文件专项检查 ──
        if ext in (".h", ".hpp"):
            required.append({"file": fp, "check": "check_header_guard", "category": "cpp"})
            required.append({"file": fp, "check": "check_using_namespace_in_header", "category": "cpp"})

        # ── Qt 文件检查 ──
        is_qt = False
        if ext in QT_SPECIAL_EXTENSIONS:
            is_qt = True
        elif ext in CXX_EXTENSIONS and QT_MARKERS.search(content):
            is_qt = True

        if is_qt:
            required.append({"file": fp, "check": "check_qt_include_dot_h", "category": "qt"})
            required.append({"file": fp, "check": "check_qt_signal_name", "category": "qt"})
            required.append({"file": fp, "check": "check_qt_slot_name", "category": "qt"})

        # ── SQLite 文件检查 ──
        if ext in CXX_EXTENSIONS and SQLITE_MARKERS.search(content):
            required.append({"file": fp, "check": "check_sqlite_pragma_key", "category": "sqlite"})
            required.append({"file": fp, "check": "check_sqlite_kdf", "category": "sqlite"})

    ledger = {
        "run_id": uuid.uuid4().hex[:12],
        "generated_at": datetime.now().isoformat(),
        "required_checks": required,
        "completed_checks": [],
        "coverage_complete": False,
    }

    return ledger


def mark_check_completed(ledger: dict, file: str, check: str) -> None:
    """标记一条检查已完成。幂等：重复标记不报错。

    Args:
        ledger: coverage ledger dict
        file: 文件绝对路径
        check: 检查函数名（如 "check_header_guard"）
    """
    entry = {"file": file, "check": check}
    if entry not in ledger["completed_checks"]:
        ledger["completed_checks"].append(entry)


def mark_all_completed_for_file(ledger: dict, file: str) -> None:
    """将某个文件的所有 required checks 标记为已完成。"""
    for rc in ledger["required_checks"]:
        if rc["file"] == file:
            mark_check_completed(ledger, file, rc["check"])


def assert_coverage_complete(ledger: dict) -> list[dict]:
    """检查覆盖率是否完整。返回缺失的检查列表；空列表 = 全部完成。

    同时更新 ledger["coverage_complete"] 和 ledger["missing_checks"]。

    Returns:
        缺失的检查列表，每条为 {"file": str, "check": str, "category": str}
    """
    completed_set: set[tuple[str, str]] = set()
    for cc in ledger["completed_checks"]:
        completed_set.add((cc["file"], cc["check"]))

    missing: list[dict] = []
    for rc in ledger["required_checks"]:
        key = (rc["file"], rc["check"])
        if key not in completed_set:
            missing.append(rc)

    ledger["missing_checks"] = missing
    ledger["coverage_complete"] = (len(missing) == 0)

    return missing


def format_coverage_report(ledger: dict) -> str:
    """生成人类可读的覆盖率报告。"""
    total = len(ledger["required_checks"])
    completed = len(ledger["completed_checks"])
    missing = ledger.get("missing_checks", [])

    lines = [
        f"覆盖率达标检查",
        f"  run_id: {ledger['run_id']}",
        f"  总检查数: {total}",
        f"  已完成: {completed}",
        f"  缺失: {len(missing)}",
        f"  覆盖率: {completed}/{total} ({_pct(completed, total)})",
        f"  通过: {'✅' if ledger['coverage_complete'] else '❌ 未达标'}",
    ]

    if missing:
        # 按 category 分组
        by_cat: dict[str, list] = {}
        for m in missing:
            cat = m.get("category", "unknown")
            by_cat.setdefault(cat, []).append(m)

        lines.append("")
        lines.append("  缺失检查:")
        for cat in sorted(by_cat):
            lines.append(f"    [{cat}] {len(by_cat[cat])} 条")
            for m in by_cat[cat][:5]:  # 每种最多展示 5 条
                fname = os.path.basename(m["file"])
                lines.append(f"      - {fname}: {m['check']}")
            if len(by_cat[cat]) > 5:
                lines.append(f"      ... 还有 {len(by_cat[cat]) - 5} 条")

    return "\n".join(lines)


def _pct(n: int, total: int) -> str:
    if total == 0:
        return "0%"
    return f"{n / total * 100:.0f}%"
