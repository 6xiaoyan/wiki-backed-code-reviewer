"""
knowledge_cache — 每条违规的审查标准与修复知识本地持久化。

设计原则:
  - 每条违规一个 JSON 文件（按 merged_violations 索引命名: 0.json, 1.json, ...）
  - 文件内容: 原始代码、规则原文摘录、怎么算通过、每次 fix→critique 尝试历史
  - 通过后不再加载（通过就不加载，没通过就加载）

目录结构:
  code_checker/.cache/violations/
  ├── 0.json
  ├── 1.json
  └── ...

每条 JSON 结构:
  {
    "index": 0,
    "file": "...",
    "line": 42,
    "rule_name": "...",
    "severity": "...",
    "current_code": "...",       // 违规行原始代码
    "expected": "...",           // 期望的修复方向
    "reason": "...",             // 违规原因
    "rule_snippet": "...",       // 规范原文摘录（首次由 LLM 提炼，后续沿用）
    "scoring_criteria": "...",   // 评分标准（首次由 LLM 提炼，后续锚定）
    "attempts": [
      {
        "iter": 1,
        "fix_before": "...",
        "fix_after": "...",
        "score": 5,
        "passed": false,
        "feedback": "...",
        "suggestion": "..."
      }
    ],
    "passed": false,
    "updated_at": "2026-07-20T..."
  }
"""

import json
import os
import threading
from datetime import datetime, timezone
from typing import Optional

from code_checker.config import CACHE_DIR, MAX_CACHE_ATTEMPTS

_lock = threading.Lock()


def _violations_dir() -> str:
    return os.path.join(CACHE_DIR, "violations")


def _ensure_dir() -> None:
    os.makedirs(_violations_dir(), exist_ok=True)


def _cache_path(index: int) -> str:
    return os.path.join(_violations_dir(), f"{index}.json")


# ============================================================================
# 核心 API
# ============================================================================


def load(index: int) -> Optional[dict]:
    """加载某条违规的缓存。

    Args:
        index: merged_violations 中的索引。

    Returns:
        dict 或 None（文件不存在或已通过时返回 None）。
    """
    path = _cache_path(index)
    with _lock:
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except (json.JSONDecodeError, OSError):
            return None

    # 已通过的不加载
    if data.get("passed"):
        return None
    return data


def save(index: int, data: dict) -> None:
    """保存某条违规的缓存。"""
    _ensure_dir()
    data["updated_at"] = datetime.now(timezone.utc).isoformat()
    path = _cache_path(index)
    with _lock:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)


def init_from_violation(index: int, violation: dict) -> dict:
    """从违规项初始化缓存条目（首次创建）。

    Args:
        index: 违规索引。
        violation: merged_violations 中的条目。

    Returns:
        初始化后的缓存 dict。
    """
    return {
        "index": index,
        "file": violation.get("file", ""),
        "line": violation.get("line", 0),
        "rule_name": violation.get("rule", ""),
        "severity": violation.get("severity", ""),
        "current_code": violation.get("current", ""),
        "expected": violation.get("expected", ""),
        "reason": violation.get("reason", ""),
        "rule_snippet": "",
        "scoring_criteria": "",
        "attempts": [],
        "passed": False,
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }


def record_attempt(
    index: int,
    plan: dict,
    result: dict,
    rule_snippet: str = "",
) -> None:
    """记录一次 fix→critique 尝试。

    每次 self_critique 审查后调用。

    Args:
        index: 违规索引。
        plan: fix_plans 条目 {fix_before, fix_after, ...}。
        result: LLM 审查结果 {score, passed, feedback, suggestion, rule_snippet}。
        rule_snippet: LLM 返回的规范摘录。
    """
    existing = load(index)
    if existing is None:
        # 可能已被标记为 passed，不再更新
        # 或者首次调用前没有 init，尝试直接加载已通过的文件
        path = _cache_path(index)
        if os.path.exists(path):
            with _lock:
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        existing = json.load(f)
                except (json.JSONDecodeError, OSError):
                    return
            if existing and existing.get("passed"):
                return  # 已通过，不更新
        if existing is None:
            return  # 没有初始化过，跳过

    passed = result.get("passed", False) if result else False

    # ── 首次提炼规则摘录和评分标准 ──
    if not existing.get("rule_snippet") and rule_snippet:
        existing["rule_snippet"] = rule_snippet

    # ── scoring_criteria 优先用 LLM 显式返回的 ──
    explicit_criteria = (result or {}).get("scoring_criteria", "")
    if explicit_criteria and len(explicit_criteria) > 10:
        # LLM 显式返回了 scoring_criteria，直接使用（无论是否首次）
        existing["scoring_criteria"] = explicit_criteria
    elif not existing.get("scoring_criteria"):
        # fallback: LLM 没有返回 scoring_criteria 且缓存中没有，从 feedback 拼凑
        fb = (result or {}).get("feedback", "")
        score = (result or {}).get("score", 0)
        if fb:
            existing["scoring_criteria"] = (
                f"评分维度: 正确性/完整性/无副作用/风格一致, 阈值≥6分。"
                f"本次评分{score}分。审查意见: {fb[:300]}"
            )

    # ── 追加尝试记录 ──
    attempt = {
        "iter": len(existing["attempts"]) + 1,
        "fix_before": plan.get("fix_before", "")[:500],
        "fix_after": plan.get("fix_after", "")[:500],
        "score": result.get("score", 5) if result else 5,
        "passed": passed,
        "feedback": (result or {}).get("feedback", "")[:300],
        "suggestion": (result or {}).get("suggestion", "")[:300],
    }
    existing["attempts"].append(attempt)

    # ── 限制尝试记录数 ──
    if len(existing["attempts"]) > MAX_CACHE_ATTEMPTS:
        existing["attempts"] = existing["attempts"][-MAX_CACHE_ATTEMPTS:]

    # ── 标记是否通过 ──
    existing["passed"] = passed

    save(index, existing)


def build_prompt_injection(index: int) -> str:
    """为 self_critique 构建历史标准锚定块。

    加载该违规的历史缓存，注入 rule_snippet + scoring_criteria + 历史案例。
    检测到多轮重复失败时升级严厉程度。
    """
    data = load(index)
    if not data:
        return ""

    parts = [f"=== 违规 #{index} 历史审查记录（标准必须保持一致）==="]
    parts.append(f"规则: {data.get('rule_name', '')}")

    if data.get("rule_snippet"):
        parts.append(f"\n规范原文摘录（沿用）:\n{data['rule_snippet'][:500]}")

    if data.get("scoring_criteria"):
        parts.append(f"\n评分标准（沿用）:\n{data['scoring_criteria'][:400]}")

    attempts = data.get("attempts", [])
    n = len(attempts)

    if attempts:
        parts.append(f"\n历史修改尝试（共{n}次）:")
        for a in attempts:
            status = "✓" if a["passed"] else "✗"
            same = " [未改动]" if a.get("fix_before") == a.get("fix_after") else ""
            parts.append(
                f"  {a['iter']}. [{status}] score={a['score']}{same}"
                f" | {a['fix_before'][:120]} → {a['fix_after'][:120]}"
            )
            if a.get("feedback"):
                parts.append(f"     审查: {a['feedback'][:200]}")
            if not a["passed"] and a.get("suggestion"):
                parts.append(f"     建议: {a['suggestion'][:200]}")

    parts.append(
        "\n请严格遵循上述规范和评分标准。"
        "如果历史有通过案例，参考其修改模式；如果历史有失败案例，务必避免重复同样错误。"
    )
    return "\n".join(parts)


def build_fix_planner_injection(index: int) -> str:
    """为 fix_planner 构建历史感知的注入块。

    加载该违规的历史缓存，展示完整的修改历史 + 最新建议 + 审查标准。
    """
    data = load(index)
    if not data:
        return ""

    attempts = data.get("attempts", [])
    n = len(attempts)
    parts = [f"=== 违规 #{index} 历史修复记录 ==="]

    # ── 历史 ──
    for a in attempts:
        status = "✓" if a["passed"] else "✗"
        same = " [未改动]" if a.get("fix_before") == a.get("fix_after") else ""
        parts.append(
            f"  {a['iter']}. [{status}] score={a['score']}{same}"
            f" | {a['fix_before'][:100]} → {a['fix_after'][:100]}"
        )
        if a.get("feedback"):
            parts.append(f"     审查: {a['feedback'][:200]}")
        if not a["passed"] and a.get("suggestion"):
            parts.append(f"     建议: {a['suggestion'][:300]}")

    # ── 最新建议（最优先）──
    last = attempts[-1]
    if last.get("suggestion"):
        parts.append(f"\n最新修改建议: {last['suggestion'][:400]}")

    # ── 审查标准 ──
    if data.get("scoring_criteria"):
        parts.append(f"\n审查标准: {data['scoring_criteria'][:300]}")

    return "\n".join(parts)


def is_passed(index: int) -> bool:
    """检查某条违规是否已通过（不加载完整数据，只检查 passed 标记）。"""
    path = _cache_path(index)
    with _lock:
        if not os.path.exists(path):
            return False
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            return data.get("passed", False)
        except (json.JSONDecodeError, OSError):
            return False
