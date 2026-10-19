"""
AgentState — LangGraph 全局状态定义。

字段按处理阶段分为三类：
  1. 输入 / 扫描阶段
  2. 各检查器产出
  3. 合并 → 修复 → 审查 → 报告 流水线
"""

from typing import TypedDict, Optional, Annotated
from langgraph.graph.message import add_messages
from langchain_core.messages import BaseMessage


def _merge_degradation_log(left: list[dict] | None, right: list[dict] | None) -> list[dict]:
    """合并并行分支的降级日志。每个分支返回自己的增量事件，reducer 汇总。"""
    return (left or []) + (right or [])


class AgentState(TypedDict):
    # ── 输入 ──────────────────────────────────────────────
    repo_path: str
    """待扫描的 Git 仓库路径（由调用方提供）"""

    # ── repo_scanner 产出 ─────────────────────────────────
    file_list: Optional[list[str]]
    """扫描到的源代码文件列表（绝对路径）"""

    file_contents: Optional[dict[str, str]]
    """文件路径 → 文件全文的映射"""

    # ── 确定性检查器产出（系统强制执行，不经 LLM，不丢不漏）──
    deterministic_violations: Optional[list[dict]]
    """
    确定性正则规则发现的违规。每条包含:
      file, line, rule, severity, current, expected, reason,
      surrounding, source_kind="deterministic", must_keep=True,
      check_id (对应的检查标识)
    """

    coverage_ledger: Optional[dict]
    """
    覆盖率账本。结构:
      {
        "run_id": str,
        "required_checks": [{"file": str, "check": str}, ...],
        "completed_checks": [{"file": str, "check": str}, ...],
        "missing_checks": [{"file": str, "check": str}, ...],
        "coverage_complete": bool,
      }
    """

    # ── 四路检查器产出 ────────────────────────────────────
    cpp_violations: Optional[list[dict]]
    """
    C++ 规范违规列表。每条包含:
      file, line, rule, severity, current, expected, reason,
      surrounding (违规行前后 3 行真实代码上下文，带行号，违规行 → 标注)
    """

    qt_violations: Optional[list[dict]]
    """Qt 规范违规列表（字段同上）"""

    git_violations: Optional[list[dict]]
    """Git 提交规范违规列表"""

    sqlite_violations: Optional[list[dict]]
    """SQLite 安全违规列表（字段同 cpp_violations）"""

    # ── 事实核验门禁驳回的幻觉违规 ──
    refuted_violations: Optional[list[dict]]
    """
    合并前事实核验阶段驳回的违规（声称的代码在源文件中不存在）。
    这些违规不进入 fix/review 流程，但保留在报告中供人工审核。
    每条额外包含: _fact_check_reason（驳回原因）。
    """

    # ── 合并 & 修复流水线 ─────────────────────────────────
    merged_violations: Optional[list[dict]]
    """去重合并后的全部违规项"""

    fix_plans: Optional[list[dict]]
    """
    修复方案列表。每条包含:
      file, line, fix_before, fix_after, reason,
      fix_status ("pending"|"proposed"|"passed"|"failed"|"refuted"|"unresolved"|"infra"),
      score (0-10), feedback,
      suggestion (self_critique 修改建议), rule_snippet (相关规范原文摘录)
      changes: list[dict] (跨文件 PatchSet，替代单个 fix_before/fix_after)
    """

    fix_iteration: int
    """当前自我审查迭代次数（上限见 config.MAX_FIX_ITERATIONS）"""

    format_fix_log: Optional[list[dict]]
    """format_fixer 自动修复记录（留痕）。每条包含 idx, file, line, rule, fix_before, fix_after, tool"""

    final_report: Optional[str]
    """最终生成的 Markdown 报告全文"""

    final_fix_guide: Optional[str]
    """给 Claude 的修复指南 Markdown 全文"""

    # ── 消息通道（LangGraph 内置，用于 Human-in-the-loop 等扩展）──
    messages: Annotated[list[BaseMessage], add_messages]

    # ── 可观测性 ──
    run_id: Optional[str]
    """当前 pipeline 执行 ID，关联所有 trace 事件"""

    # ── 管道完整性标记 ──
    pipeline_errors: Optional[list[str]]
    """管道运行中检测到的非致命错误（coverage incomplete 等），写入报告供人工审查"""

    # ── 运行完整性标记 ──
    run_incomplete: Optional[bool]
    """
    True 表示运行不完整（存在 unreviewed/proposed/null 方案），
    报告可信度自动降级，wiki 仲裁跳过。
    """

    # ── 降级状态 ──
    degradation_log: Annotated[list[dict], _merge_degradation_log]
    """
    逐阶段降级事件列表。每条包含:
      stage: str           # 阶段名
      status: str          # "ok" | "degraded" | "skipped" | "failed"
      reason: str          # 降级原因
      impact: str          # 对报告质量的影响

    使用 Annotated 合并函数：并行扇出节点各自返回增量事件，
    LangGraph 在 step 结束时汇总——避免 LastValue 冲突。
    """

    offline_mode: Optional[bool]
    """是否为离线模式（零 API 调用）。由 DEGRADATION_MODE=offline 或 --offline 设置。"""

    # ── PR 模式字段（第一阶段新增）────────────────────────────
    pr_mode: Optional[bool]
    """是否为 PR diff 审查模式。PR 模式不调用全仓 scanner、fix/review 循环与 Wiki 写入。"""

    review_request: Optional[dict]
    """
    PR 模式的固定输入（repo、PR 号、base/head/merge_base SHA、
    审查程序提交、规则/提示词/配置摘要、模型标识、run id/attempt、预算）。
    """

    diff_scope: Optional[dict]
    """
    PR 模式的 diff 范围：
      {changed_files: [...], included_files: [...], excluded_files: [...],
       not_covered: [...], merge_base_sha, head_sha}
    """

    review_status: Optional[str]
    """PR 结果状态：completed / skipped / incomplete / failed / superseded。"""

    review_budget: Optional[dict]
    """PR 模式的预算与用量（模型请求、上下文字节、阶段耗时、token 用量）。"""

    review_coverage: Optional[dict]
    """PR 模式的覆盖说明（已审查文件、未覆盖范围、额外上下文读取记录）。"""
