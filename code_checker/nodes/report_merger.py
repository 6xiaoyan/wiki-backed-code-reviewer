"""
report_merger_agent — 违规合并去重 Agent。

将四路检查器（C++ / Qt / Git / SQLite）的产出合并，
通过 LLM 判断语义重复（不仅同文件同行号，还识别同一问题被不同表述报告的情况），
使用 deepseek-v4-flash 快速分类去重。
"""

import os

from langchain_core.messages import HumanMessage
from langchain_core.tools import tool
from langgraph.prebuilt import create_react_agent

from code_checker.state import AgentState
from code_checker.config import llm_flash, SEVERITY_ORDER
from code_checker.context_compaction import create_compaction_hook
from code_checker.tools import (
    set_state, read_file, get_rules_text,
)

# ── merger 专用共享缓冲区 ──
_merged_buffer: list[dict] = []

# ── 事实核验后的违规列表覆盖（防止 LLM 绕过核验从 state 读取原始违规）──
_fact_checked_violations: list[dict] | None = None
"""事实核验后存储的通过核验的违规列表。get_all_violations 工具优先返回此列表。"""


def _get_all_violations() -> list[dict]:
    """获取全部违规：确定性违规（must_keep）+ 四路 LLM checker 违规。

    优先返回事实核验后的列表（_fact_checked_violations），
    防止 LLM 合并 agent 绕过事实核验门禁从 state 直接读取未过滤的违规。

    确定性违规优先，带 source_kind="deterministic" 和 must_keep=True，
    LLM 合并阶段不允许删除这些违规。
    """
    # ── 事实核验后使用过滤列表 ──
    global _fact_checked_violations
    if _fact_checked_violations is not None:
        return list(_fact_checked_violations)

    from code_checker.tools import _state_ref
    state = _state_ref
    if state is None:
        return []

    # ── 先收集确定性违规（must_keep=True）──
    all_v = []
    idx = 0
    det_violations = state.get("deterministic_violations") or []
    for v in det_violations:
        item = dict(v)
        item.setdefault("source_kind", "deterministic")
        item.setdefault("must_keep", True)
        item["idx"] = idx
        all_v.append(item)
        idx += 1

    # ── 再收集 LLM checker 违规 ──
    sources = [
        ("cpp", "cpp_violations"),
        ("qt", "qt_violations"),
        ("git", "git_violations"),
        ("sqlite", "sqlite_violations"),
    ]
    for src_name, state_key in sources:
        violations = state.get(state_key) or []
        for v in violations:
            item = dict(v)
            item["source"] = src_name
            item["idx"] = idx
            all_v.append(item)
            idx += 1
    return all_v


@tool
def get_all_violations() -> list[dict]:
    """获取四路检查器的全部违规列表。每条包含 idx/file/line/rule/severity/current/expected/reason/source。"""
    return _get_all_violations()


@tool
def submit_merged_violations(violations: list[dict]) -> str:
    """提交合并去重后的最终违规列表。这是你审查去重后的最终输出。

    每条违规保留字段: file, line, rule, severity, current, expected, reason, source,
    violation_id, source_kind, must_keep, check_id, rule_section, rule_excerpt, rule_page, rule_clause。
    violation_id 是系统分配给每条违规的唯一追踪标识，必须原样保留，不可修改或丢弃。
    source 字段如果一条违规来自多个检查器，用 | 分隔，如 "cpp|qt"。
    """
    global _merged_buffer
    _merged_buffer = list(violations)
    return f"已提交 {len(violations)} 条合并违规"


def get_merged_buffer() -> list[dict]:
    """节点函数在 agent 运行后取出合并结果。"""
    return list(_merged_buffer)


def _fact_check_violations(
    violations: list[dict],
    file_contents: dict[str, str],
) -> tuple[list[dict], list[dict]]:
    """合并前事实核验门禁：验证每条 LLM 违规的 claimed code 是否真实存在。

    对每条 violation 执行三项检查：
      1. 文件存在性：file 路径是否在 file_contents 中
      2. 行号有效性：line 是否指向有效代码行（非空行、不超过文件行数）
      3. 代码匹配：violation.current 是否与源文件中对应行的代码匹配
         （归一化比较：去除首尾空白后，检查前者是否是后者的子串）

    确定性违规（must_keep=True）和来源为 "git" 的违规（不基于源码行）跳过核验。

    Returns:
        (passed_violations, refuted_violations):
          - passed_violations: 核验通过的违规 + 跳过核验的违规（进入合并流程）
          - refuted_violations: 被驳回的幻觉违规（不进入合并，存入 state 供报告展示）
    """
    passed = []
    refuted = []

    for v in violations:
        # ── 跳过确定性违规和 Git 违规 ──
        if v.get("must_keep") or v.get("source_kind") == "deterministic":
            v["_fact_check_status"] = "skipped"  # 确定性检查，无需 LLM 事实核验
            passed.append(v)
            continue
        if v.get("source") == "git":
            v["_fact_check_status"] = "skipped"  # Git 违规不基于源码行，不适用行号核验
            passed.append(v)
            continue

        file_path = v.get("file", "")
        line_num = v.get("line", 0)
        claimed_current = v.get("current", "").strip()
        rule = v.get("rule", "")
        severity = v.get("severity", "")

        # ── 检查 1 & 2：文件存在 + 行号有效 ──
        content = _resolve_file_content(file_path, file_contents)
        if content is None:
            # 文件不存在 → 可能是 checker agent 虚构的文件路径
            v["_fact_check_status"] = "refuted"
            _log_refuted(v, f"文件不存在: {file_path}")
            refuted.append(v)
            continue

        lines = content.split("\n")
        if line_num < 1 or line_num > len(lines):
            # 行号超出范围
            v["_fact_check_status"] = "refuted"
            _log_refuted(v, f"行号 {line_num} 超出文件范围 (1-{len(lines)})")
            refuted.append(v)
            continue

        actual_line = lines[line_num - 1].strip()

        # ── 检查 3：代码匹配 ──
        if not claimed_current:
            # current 为空 → 无法核验代码匹配，但仍标记为未核实
            # 可能是 rule-only 违规（如 "缺少 PRAGMA key"）或 checker 未摘录代码
            v["_fact_check_unverified"] = True
            v["_fact_check_status"] = "unverified"
            passed.append(v)
            continue

        if _codes_match(claimed_current, actual_line):
            v["_fact_check_status"] = "verified"
            passed.append(v)
        else:
            # ── 模糊匹配：尝试邻近行 ──
            matched = False
            for offset in (-2, -1, 1, 2):
                neighbor = line_num + offset
                if 1 <= neighbor <= len(lines):
                    if _codes_match(claimed_current, lines[neighbor - 1].strip()):
                        # 行号偏差（checker 报的行号与实际差 1-2 行），修正行号后通过
                        v["line"] = neighbor
                        v["_line_corrected"] = True
                        v["_fact_check_status"] = "verified"
                        passed.append(v)
                        matched = True
                        break
            if not matched:
                v["_fact_check_status"] = "refuted"
                _log_refuted(
                    v,
                    f"代码不匹配 — 声称行 {line_num}: "
                    f"'{claimed_current[:120]}' vs "
                    f"实际: '{actual_line[:120]}'",
                )
                refuted.append(v)

    return passed, refuted


def _resolve_file_content(file_path: str, file_contents: dict[str, str]) -> str | None:
    """解析文件路径到内容。支持绝对路径和文件名匹配。"""
    if not file_path:
        return None  # 空路径不匹配任何文件
    if file_path in file_contents:
        return file_contents[file_path]
    # 尝试文件名匹配
    import os as _os
    for fp, content in file_contents.items():
        if _os.path.basename(fp) == file_path:
            return content
        # file_path in fp 只在 file_path 足够长时才做子串匹配
        # 防止短路径（如 "a"）命中无关文件
        if len(file_path) >= 4 and file_path in fp:
            return content
    return None


def _codes_match(claimed: str, actual: str) -> bool:
    """比较 claimed 代码和 actual 代码是否匹配。

    归一化：去除首尾空白，限制长度。
    如果任一为空，不匹配。

    子串匹配有最小长度门禁：防止 claimed="invented();}" 与 actual="}"
    这类短代码包含关系误匹配。claimed 和 actual 都必须 ≥ 10 字符才允许
    子串匹配；否则只允许精确匹配或去空白精确匹配。
    """
    c = claimed.strip()[:300]
    a = actual.strip()[:300]
    if not c or not a:
        return False
    # 精确匹配
    if c == a:
        return True
    # 子串匹配：双方都必须足够长，防止 "}" in "invented();}" 类误匹配
    MIN_SUBSTR_LEN = 10
    if len(c) >= MIN_SUBSTR_LEN and len(a) >= MIN_SUBSTR_LEN:
        if c in a or a in c:
            return True
    # 去除所有空白后比较
    c_norm = "".join(c.split())
    a_norm = "".join(a.split())
    if c_norm and a_norm:
        if c_norm == a_norm:
            return True
        if len(c_norm) >= MIN_SUBSTR_LEN and len(a_norm) >= MIN_SUBSTR_LEN:
            if c_norm in a_norm or a_norm in c_norm:
                return True
    return False


def _log_refuted(violation: dict, reason: str) -> None:
    """记录被驳回的幻觉违规。修改原始字典，标记为事实核验不通过。"""
    violation["_fact_check_failed"] = True
    violation["_fact_check_reason"] = reason
    # 摘要日志
    rule = violation.get("rule", "?")
    file_name = os.path.basename(violation.get("file", "?"))
    line = violation.get("line", 0)
    print(f"  [事实核验] 🚨 驳回: {rule} @ {file_name}:{line} — {reason[:150]}")


MERGER_SYSTEM_PROMPT = """你是代码规范审查结果的合并去重专家。四路检查器各自独立运行，可能对同一问题产生重复报告。

=== 重要：must_keep 违规 ===
部分违规带有 must_keep=true 和 source_kind="deterministic" 标记。
这些是系统确定性检查的结果，**绝对不可删除**。你可以：
  - 将其与 LLM 发现的语义重复违规合并（保留 must_keep 那条）
  - 补充更详细的原因说明
  - 调整严重度（只能升不能降：suggestion→warning→critical）
但**最终输出必须包含所有 must_keep=true 的违规**。

=== 工作流程 ===
1. 用 get_all_violations 获取全部违规（确定性 + LLM 语义）
2. 逐条审阅，判断哪些是重复报告：
   a. 同文件同行号且同规则 → 肯定是重复（不同 checker 重复报告同一问题）
   b. 同文件同行号但规则不同 → **不重复**（同一行可能同时违反
      命名、安全等多条规则），保留两条
   c. 同文件相邻行（±3 行）且指向同一问题 → 很可能是重复
   d. 同一规则、不同检查器用不同措辞报告 → 语义重复
   e. 不同域的检查器各报告各的 → 不重复（保留两条，source 标记各自来源）
3. 重复项处理：保留严重度最高的一条，source 合并为 "cpp|qt" 格式
   如果其中一条是 must_keep=true，保留 must_keep 那条
4. 全部审完后用 submit_merged_violations 提交
   **再次确认**：提交的列表中必须包含所有 must_keep=true 的违规

=== 去重原则 ===
- 同文件同行号同规则 → 合并（不同 checker 重复报告），保留严重度最高的一条
- 同文件同行号不同规则 → **不合并**（同一行违反多条独立规则）
- 严重度: critical > warning > suggestion（同位置保留最高的）
- 来源标记: 如果 cpp 和 qt 都报了同一条，source 写成 "cpp|qt"
- 宁可多报不漏报：不确定是否重复的，保留不合并
- 不同文件绝不合并
- must_keep=true 绝不删除"""

MERGER_AGENT_TOOLS = [
    read_file, get_rules_text, get_all_violations, submit_merged_violations,
]


def report_merger(state: AgentState) -> dict:
    """违规合并去重 agent 节点。

    让 LLM 判断四路检查器的违规是否重复，
    输出语义去重后的 merged_violations。

    关键不变量：must_keep=True 的违规（确定性检查结果）
    绝不能被 LLM 合并删除。即使 LLM 遗漏，系统也会自动补回。

    新增：合并前执行事实核验门禁。
    对每条 LLM 发现的违规，验证其声称的代码是否真实存在于源文件中。
    幻觉违规（声称的代码不存在）在此阶段被驳回，不进入合并和修复。
    """
    print("[合并 agent ] 启动...")

    # ── 清理上一次运行的进程级全局缓存，防止跨运行数据污染 ──
    global _fact_checked_violations, _merged_buffer
    _fact_checked_violations = None
    _merged_buffer = []
    # 同时清理所有 checker domain 的违规缓冲区
    from code_checker.tools import _violations_buffers, _buffer_lock as _tools_lock
    with _tools_lock:
        _violations_buffers.clear()

    set_state(state)

    # ── 收集所有违规 ──
    all_violations = _get_all_violations()
    total = len(all_violations)

    # ── 阶段 0：事实核验门禁（合并前拦截幻觉）──
    all_violations, refuted_violations = _fact_check_violations(
        all_violations, state.get("file_contents", {}),
    )
    refuted_count = len(refuted_violations)
    if refuted_count > 0:
        print(f"  [合并 agent ] 🚨 事实核验驳回 {refuted_count} 条幻觉违规"
              f"（声称的代码在源文件中不存在）")
        total = len(all_violations)

    # 将驳回的违规存入 state，供报告展示
    state["refuted_violations"] = refuted_violations

    # ── 覆盖全局变量：get_all_violations 工具优先返回核验后的列表 ──
    # global 已在函数顶部声明，此处直接赋值
    _fact_checked_violations = all_violations

    # ── 识别 must_keep 违规（用于后置校验）──
    must_keep_violations = [v for v in all_violations if v.get("must_keep")]
    must_keep_fingerprints: set[tuple[str, int, str]] = set()
    for v in must_keep_violations:
        fp = (v.get("file", ""), v.get("line", 0), v.get("rule", ""))
        must_keep_fingerprints.add(fp)
    det_count = len(must_keep_violations)

    if total == 0:
        if refuted_count > 0:
            print(f"  [合并 agent ] 全部 {refuted_count} 条违规被事实核验驳回，无违规进入合并")
        else:
            print("  [合并 agent ] 无违规，跳过")
        return {"merged_violations": [], "refuted_violations": refuted_violations}

    try:
        agent = create_react_agent(
            model=llm_flash,
            tools=MERGER_AGENT_TOOLS,
            prompt=MERGER_SYSTEM_PROMPT,
            pre_model_hook=create_compaction_hook(
                "report_merger",
                critical_tool_names={"get_all_violations", "get_rules_text", "submit_merged_violations"},
            ),
        )

        from code_checker.utils import invoke_with_retry
        result = invoke_with_retry(
            agent,
            f"开始合并去重。共 {total} 条违规（其中 {det_count} 条为确定性检查结果，"
            f"标记 must_keep=true，绝不可从最终输出中删除）。"
            f"请用 get_all_violations 获取全部违规，逐条审阅去重，"
            f"最后用 submit_merged_violations 提交结果。",
            "report_merger",
            config={"recursion_limit": 50},
        )

        merged = get_merged_buffer()
        msg_count = len(result.get("messages", []))
    except Exception as e:
        print(f"  [合并 agent ] LLM 调用异常: {e}，fallback 到按 (file,line) 去重")
        merged = []
        msg_count = 0
        # 记录降级
        log = list(state.get("degradation_log") or [])
        log.append({
            "stage": "report_merger",
            "status": "degraded",
            "reason": f"LLM 调用失败: {e}，使用确定性 (file,line) 去重",
            "impact": "去重粒度降低（仅按文件+行号，不做语义去重），可能保留少量重复违规",
        })
        state["degradation_log"] = log

    # ── 如果 agent 没有提交（空返回或异常），fallback 到简单去重 ──
    if not merged:
        if msg_count > 0:
            print("  [合并 agent ] LLM 未产出，fallback 到按 (file,line) 去重")
        merged = _fallback_dedup(all_violations)

    # ── 后置不变量保护：确保 must_keep 违规不被 LLM 遗漏 ──
    merged = _restore_missing_must_keep(merged, must_keep_violations)

    # ── 可观测性：回填 violation_id（LLM 可能遗漏此字段）──
    merged = _reattach_violation_ids(merged, all_violations)

    # 清理内部字段
    for v in merged:
        v.pop("idx", None)

    print(f"  [合并 agent ] {total} → {len(merged)} 条"
          f"（确定性 {det_count}, LLM 语义 {len(merged) - det_count}）, "
          f"{msg_count} 轮消息"
          f"{f', 事实核验驳回 {refuted_count}' if refuted_count else ''}")
    return {
        "merged_violations": merged,
        "refuted_violations": refuted_violations,
    }


def _fallback_dedup(all_violations: list[dict]) -> list[dict]:
    """确定性去重回退策略（LLM 合并失败时使用）。

    使用 (file, line, rule) 三要素作为去重键：
    - 同一文件同一行但不同规则 → 不合并（可能同时违反命名+安全规则）
    - 同一文件同一行同一规则 → 合并 source（多个 checker 重复报告）
    - 合并时保留严重度最高的一条，source 用 | 连接
    """
    from code_checker.config import SEVERITY_ORDER
    seen: dict[tuple, dict] = {}
    for v in all_violations:
        # ── 三要素去重键：file + line + rule ──
        # 同一行可能违反多条规则（如命名+安全），不能按 (file,line) 盲目合并
        key = (v.get("file"), v.get("line"), v.get("rule"))
        if key in seen:
            existing = seen[key]
            v_sev = SEVERITY_ORDER.get(v.get("severity"), 99)
            e_sev = SEVERITY_ORDER.get(existing.get("severity"), 99)
            # 合并 source：保留严重度高的，source 标记两个 checker
            if v_sev < e_sev:
                v["source"] = (existing.get("source", "") + "|" +
                               v.get("source", ""))
                seen[key] = v
            else:
                existing["source"] = (existing.get("source", "") + "|" +
                                     v.get("source", ""))
        else:
            seen[key] = v
    return sorted(
        seen.values(),
        key=lambda v: (SEVERITY_ORDER.get(v.get("severity"), 99),
                       v.get("file", ""), v.get("line", 0)),
    )


def _restore_missing_must_keep(
    merged: list[dict],
    must_keep_violations: list[dict],
) -> list[dict]:
    """后置不变量检查：确保所有 must_keep 违规都在合并结果中。

    如果 LLM 合并时遗漏了任何 must_keep 违规，自动补回并记录警告。
    """
    if not must_keep_violations:
        return merged

    # ── 构建合并结果的文件-行号-规则指纹集 ──
    merged_fingerprints: set[tuple[str, int, str]] = set()
    for v in merged:
        fp = (v.get("file", ""), v.get("line", 0), v.get("rule", ""))
        merged_fingerprints.add(fp)

    restored = 0
    for v in must_keep_violations:
        fp = (v.get("file", ""), v.get("line", 0), v.get("rule", ""))
        if fp not in merged_fingerprints:
            # LLM 遗漏了这条 must_keep 违规 → 自动补回
            merged.append(dict(v))
            merged_fingerprints.add(fp)
            restored += 1

    if restored > 0:
        print(f"  [合并 agent ] ⚠️ 保护性恢复 {restored} 条被 LLM 遗漏的 must_keep 违规")

    return merged


def _reattach_violation_ids(
    merged: list[dict],
    all_violations: list[dict],
) -> list[dict]:
    """回填 violation_id：用 (file, line, rule) 指纹匹配原始违规。

    LLM 合并时可能遗漏 violation_id 等追踪字段。此函数确定性回填，
    确保下游 fix_agent / review_agent 能通过 violation_id 串联事件。
    """
    # 构建原始违规的指纹 → 完整字段映射
    source_by_fp: dict[tuple, dict] = {}
    for v in all_violations:
        fp = (v.get("file", ""), v.get("line", 0), v.get("rule", ""))
        # 只在第一个匹配时设置（避免覆盖）
        if fp not in source_by_fp:
            source_by_fp[fp] = v

    reattached = 0
    for v in merged:
        # 跳过已有有效 violation_id 的条目
        if v.get("violation_id"):
            continue
        fp = (v.get("file", ""), v.get("line", 0), v.get("rule", ""))
        src = source_by_fp.get(fp)
        if src:
            vid = src.get("violation_id", "")
            if vid:
                v["violation_id"] = vid
                # 同时回填其他可能被 LLM 丢弃的追踪字段
                for field in ("source_kind", "must_keep", "check_id",
                              "rule_section", "rule_excerpt", "rule_page", "rule_clause"):
                    if field in src and field not in v:
                        v[field] = src[field]
                reattached += 1

    if reattached > 0:
        print(f"  [合并 agent ] 回填 {reattached} 条 violation_id（LLM 合并时被丢弃）")

    return merged
