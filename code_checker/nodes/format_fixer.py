"""
format_fixer — 确定性格式修复节点。

位于 report_merger 与 fix_agent 之间，拦截纯格式类违规并用正则/规则引擎直接修复。
修复结果直接写入 fix_plans（status=1, score=10, fix_method="format_fixer"），
不经 review_agent 循环（确定性修复无需 LLM 审查）。

仅将语义类违规传给下游 fix_agent → review_agent 循环。
"""

import re
import os
from collections.abc import Callable
from code_checker.state import AgentState

# ── 格式规则：rule_name → (severity, fix_function) ──
# 每个 fix_function 签名为 (file_path: str, line: int, current: str) → (fix_before, fix_after, tool_name) | None
# 返回 None 表示无法自动修复，降级给 LLM


def _fix_tab_to_spaces(file_path: str, line: int, current: str) -> "tuple[str, str, str] | None":
    """Tab 字符 → 4 空格。"""
    if "\t" not in current:
        return None
    fixed = current.replace("\t", "    ")
    # 提取包含 tab 的具体行
    before = current.split("\n")[0] if "\n" in current else current
    after = before.replace("\t", "    ")
    return (before, after, "tab→spaces")


def _fix_include_order(file_path: str, line: int, current: str) -> "tuple[str, str, str] | None":
    """修复 include 排序：系统头文件 → 第三方库 → 项目头文件。

    仅当 current 包含多个 #include 行时生效。
    """
    lines = current.strip().split("\n")
    includes = [l for l in lines if l.strip().startswith("#include")]
    if len(includes) < 2:
        return None

    def _include_key(line: str) -> int:
        stripped = line.strip()
        if stripped.startswith("#include <") and not stripped.startswith("#include <Q"):
            return 0  # 系统头文件
        elif stripped.startswith("#include <Q"):
            return 1  # Qt 第三方库
        else:
            return 2  # 项目头文件 ("...")

    # 检查是否已有序
    keys = [_include_key(l) for l in includes]
    if keys == sorted(keys):
        return None  # 已经有序

    sorted_includes = sorted(includes, key=_include_key)
    before = "\n".join(includes)
    after = "\n".join(sorted_includes)
    return (before, after, "include-sort")


def _fix_header_guard(file_path: str, line: int, current: str) -> "tuple[str, str, str] | None":
    """修复头文件保护宏命名不一致。

    常见问题：末尾多余下划线 / #ifndef 与 #define 不匹配。
    """
    if not file_path.endswith((".h", ".hpp")):
        return None

    # 尝试从 #ifndef 行提取正确的宏名
    current_stripped = current.strip()
    if not current_stripped.startswith("#define "):
        return None

    # 尝试读取文件获取 #ifndef 行
    try:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
    except Exception:
        return None

    # 找到 #ifndef 行
    ifndef_match = re.search(r"#ifndef\s+(\w+)", content)
    define_match = re.search(r"#define\s+(\w+)", content)

    if not ifndef_match or not define_match:
        return None

    ifndef_name = ifndef_match.group(1)
    define_name = define_match.group(1)

    if ifndef_name == define_name:
        return None  # 已匹配

    before = current_stripped
    after = f"#define {ifndef_name}"
    return (before, after, "header-guard-fix")


def _fix_brace_allman(file_path: str, line: int, current: str) -> "tuple[str, str, str] | None":
    """修复大括号 Allman 风格：控制语句的左大括号独占一行。

    仅处理明确可修复的模式：if/for/while (...) { → if/for/while (...)\n{
    """
    lines = current.strip().split("\n")
    if len(lines) != 1:
        return None

    line_text = lines[0].strip()

    # 匹配: if/for/while (...) { ... }
    m = re.match(
        r"(if|for|while|else\s*if)\s*(\([^{]*\))\s*\{\s*(.*?)\s*\}?\s*$",
        line_text,
    )
    if m:
        keyword = m.group(1)
        condition = m.group(2)
        body = m.group(3).rstrip(" }")
        before = line_text
        after = f"{keyword} {condition}\n{{\n    {body}\n}}"
        return (before, after, "brace-allman")

    return None


# ── 格式规则注册表 ──
FORMAT_RULES: dict[str, Callable] = {
    "缩进规则": _fix_tab_to_spaces,
    "2.1 缩进规则": _fix_tab_to_spaces,
    "头文件规范 — include 顺序": _fix_include_order,
    "1.2 头文件规范 - include顺序": _fix_include_order,
    "头文件规范 - include顺序": _fix_include_order,
    "1.2 头文件规范 - 保护宏格式": _fix_header_guard,
    "头文件保护宏格式": _fix_header_guard,
    "2.4 大括号使用规范": _fix_brace_allman,
    "1.3 代码格式 - 大括号Allman风格": _fix_brace_allman,
}

# 也支持模糊匹配的规则名（包含关键词即命中）
FORMAT_KEYWORDS: dict[str, Callable] = {
    "include顺序": _fix_include_order,
    "include 顺序": _fix_include_order,
    "保护宏格式": _fix_header_guard,
    "大括号": _fix_brace_allman,
    "缩进": _fix_tab_to_spaces,
    "tab": _fix_tab_to_spaces,
    "Tab": _fix_tab_to_spaces,
}


def _match_format_rule(rule_name: str) -> "Callable | None":
    """根据规则名匹配格式修复函数。先精确匹配，再关键词模糊匹配。"""
    if rule_name in FORMAT_RULES:
        return FORMAT_RULES[rule_name]
    for keyword, func in FORMAT_KEYWORDS.items():
        if keyword in rule_name:
            return func
    return None


def format_fixer(state: AgentState) -> dict:
    """格式修复节点。

    遍历 merged_violations，对格式类违规：
      1. 应用确定性修复（正则替换）
      2. 直接将修复方案写入 fix_plans（status=1, score=10）
      3. 记录到 format_fix_log（留痕）

    语义类违规不处理，留给下游 fix_agent。
    """
    violations = state.get("merged_violations") or []
    existing_plans = state.get("fix_plans") or []
    format_fix_log: list[dict] = []

    if not violations:
        print("[format_fixer] 无违规，跳过")
        return {}

    # ── 初始化 fix_plans ──
    if not existing_plans:
        all_plans: list = [None] * len(violations)
    else:
        all_plans = list(existing_plans)

    auto_fixed = 0
    semantic_count = 0

    for idx, v in enumerate(violations):
        rule_name = v.get("rule", "")
        fix_func = _match_format_rule(rule_name)

        if fix_func is None:
            semantic_count += 1
            continue  # 语义违规，留给 fix_agent

        file_path = v.get("file", "")
        line_num = v.get("line", 0)
        current = v.get("current", "")

        if not file_path or not os.path.isfile(file_path):
            continue

        try:
            result = fix_func(file_path, line_num, current)
        except Exception as e:
            print(f"  [format_fixer] #{idx} {rule_name} 修复异常: {e}")
            semantic_count += 1
            continue

        if result is None:
            # 修复函数判为无法自动修复，降级给 LLM
            semantic_count += 1
            continue

        fix_before, fix_after, tool_name = result

        # ── 记录到 fix_plans ──
        all_plans[idx] = {
            "idx": idx,
            "file": file_path,
            "line": line_num,
            "fix_before": fix_before,
            "fix_after": fix_after,
            "reason": f"[format_fixer:{tool_name}] 确定性格式修复",
            "status": 1,      # 直接通过
            "score": 10,       # 满分
            "feedback": f"自动修复（{tool_name}），无需 LLM 审查",
            "suggestion": "",
            "rule_snippet": v.get("rule", ""),
            "fix_method": "format_fixer",
            "tool": tool_name,
            "violation_id": v.get("violation_id", ""),
        }

        # ── 留痕 ──
        format_fix_log.append({
            "idx": idx,
            "file": file_path,
            "line": line_num,
            "rule": rule_name,
            "severity": v.get("severity", ""),
            "fix_before": fix_before,
            "fix_after": fix_after,
            "tool": tool_name,
        })
        auto_fixed += 1

    print(
        f"[format_fixer] 自动修复 {auto_fixed} 条, "
        f"剩余 {semantic_count} 条交 LLM 处理"
    )

    return {
        "fix_plans": all_plans,
        "format_fix_log": format_fix_log,
    }
