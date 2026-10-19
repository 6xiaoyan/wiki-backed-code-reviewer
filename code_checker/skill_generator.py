"""
skill_generator — trace2skill 生成器（定位 → 归因 → 成稿）。

这是 skill 自进化闭环的发动机：输入「一条轨迹 + 一个漏检」，输出「一条候选 skill」。
拆成三段，每段输入输出强类型（见 SKILL_SELF_EVOLUTION.md 阶段 4）：

  ① 定位 locate        missed_id + -agent.jsonl → 一次 agent 轨迹（确定性，不会错）
  ② 归因 attribute     一次轨迹 → 归因卡（强模型起稿 + 人确认，唯一的语义判断）
  ③ 成稿 draft         归因卡 + 真实代码 → 四段式 skill 正文（强模型）

group_misses_by_rule（归组去重，防爆炸）跑在三段之前，一次归因覆盖同 rule 的多个 miss。

安全边界（写死，不可绕）：
  - 只处理 source_kind == "llm" 的违规；deterministic 的漏检是 checker 代码 bug，
    归工程师改代码，不是 skill 的活（见 SKILL_SELF_EVOLUTION.md 一、定位与边界）。
  - 归因是「模型起稿 + 人确认」，本模块只产出草稿，落库须人过目。
"""

import os
import json

from code_checker.config import PROJECT_ROOT, llm_flash
from code_checker.utils import read_file_content, extract_surrounding_lines


# ── 归因卡 schema（定死，第一版人从下拉里选，攒多了再自动化）───────────────
FAILURE_MODES = [
    "漏读文件",          # 压根没 read_file 到目标文件
    "控制流未串联",      # 读了但把「失败检查」和「后续使用」分段孤立地看
    "同规则多实例漏报",  # 报了相邻同类，漏了另一处同类实例
    "规则边界判断错",    # 读了 wiki，但把「是否违规」的边界判反了
    "读错 wiki 页",      # 翻了错误的 wiki 页，导致判断依据错
]

ATTRIBUTION_SCHEMA = {
    "failure_mode": "有限枚举：" + " / ".join(FAILURE_MODES),
    "evidence": [
        {"tool": "read_file", "args": "mainwindow.cpp", "note": "读了目标文件"},
        {"tool": "get_wiki_page", "args": "cpp/exception-safety-guarantees",
         "note": "读了正确 wiki"},
        {"tool": "report_violation", "args": "...line 23", "note": "报了相邻行，漏了目标行"},
    ],
    "root_cause": "一句话：它读了 X、做了 Y，但因为 Z 没识别出这条违规",
    "conclusion": "一句话：把『失败检查』和『后续使用』当成同一控制流来审查",
}


# ── 归组去重 ─────────────────────────────────────────────────
def group_misses_by_rule(missed: list) -> list[dict]:
    """把漏检违规按 rule 聚类，一类一条 skill；排除 deterministic。

    Args:
        missed: GroundTruthViolation 列表（评测判出的漏检）。

    Returns:
        [{"rule", "agent", "misses": [GroundTruthViolation, ...]}, ...]
        deterministic 违规被排除（它们的漏检是 checker 代码 bug，不归 skill）。
    """
    groups: dict[str, dict] = {}
    for v in missed:
        if getattr(v, "source_kind", "") != "llm":
            continue  # deterministic 不进 skill 系统
        rule = (getattr(v, "rule", None) or "未知规则")
        key = rule
        if key not in groups:
            groups[key] = {
                "rule": rule,
                "agent": _rule_to_agent(v),
                "misses": [],
            }
        groups[key]["misses"].append(v)
    return list(groups.values())


def _rule_to_agent(v) -> str:
    """把一条违规映射到它归属的 agent 域（定向隔离的依据）。

    优先用 benchmark_id 前缀（C/Q/S/G）；无 benchmark_id 时按 rule 关键词回退，
    兜底 cpp（大多数规则是 C++ 域）。
    """
    bid = getattr(v, "benchmark_id", None) or ""
    prefix = bid.split("-")[0].upper() if bid else ""
    if prefix == "C":
        return "cpp"
    if prefix == "Q":
        return "qt"
    if prefix == "S":
        return "sqlite"
    if prefix == "G":
        return "git"

    rule = getattr(v, "rule", None) or ""
    sqlite_kw = ("SQL", "PRAGMA", "密钥", "加密", "查询", "参数化", "Base64", "KDF")
    if any(k in rule for k in sqlite_kw):
        return "sqlite"
    qt_kw = ("Qt", "槽", "信号", "控件", "界面类", "QWidget", "include 顺序", "包含顺序")
    if any(k in rule for k in qt_kw):
        return "qt"
    return "cpp"


# ── ① 定位：从漏检 id 反查轨迹（机械）─────────────────────────
def locate_trace(missed, agent_traces_path: str) -> list[dict]:
    """从 -agent.jsonl 里捞出「审查过 missed.file 的 agent 轨迹」。

    匹配依据：轨迹 messages 里出现过 read_file(参数含 missed.file) 的工具调用。
    返回命中的消息列表（可能 0 条——说明 agent 压根没读这个文件，
    归因结论就是「漏读文件」）。

    Args:
        missed: GroundTruthViolation（用它拿 file 字段）。
        agent_traces_path: tracer 落盘的 -agent.jsonl 绝对路径。
    """
    target = getattr(missed, "file", "").replace("\\", "/")
    hits: list[dict] = []
    if not os.path.exists(agent_traces_path):
        return hits
    with open(agent_traces_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
            except json.JSONDecodeError:
                continue
            if ev.get("event") != "agent_trace":
                continue
            if _trace_touched(ev, target):
                hits.append(ev.get("messages", []))
    return hits


def _trace_touched(event: dict, target: str) -> bool:
    """判断一条 agent 轨迹是否 read_file 过目标文件。

    serialize_messages 把 tool_calls.args 存成了 JSON 字符串（可能被截断），
    所以用子串匹配而非重新解析——相对路径和绝对路径都能命中。
    """
    for m in event.get("messages", []):
        for tc in m.get("tool_calls", []):
            if tc.get("name") != "read_file":
                continue
            args = tc.get("args", "")
            if target in str(args):
                return True
    return False


def find_latest_agent_traces(traces_dir: str = None) -> str | None:
    """返回 TRACES_DIR 下最新的 -agent.jsonl 路径（归因时喂给 locate_trace）。"""
    if traces_dir is None:
        from code_checker.config import TRACES_DIR
        traces_dir = TRACES_DIR
    if not os.path.isdir(traces_dir):
        return None
    candidates = [
        os.path.join(traces_dir, fn)
        for fn in os.listdir(traces_dir)
        if fn.endswith("-agent.jsonl")
    ]
    if not candidates:
        return None
    return max(candidates, key=os.path.getmtime)


# ── ② 归因：强模型读轨迹出「归因卡」，人确认 ────────────────────
def _trace_to_readable(trace_messages: list[dict]) -> str:
    """把序列化后的轨迹消息转成可读文本，供归因模型阅读。"""
    lines: list[str] = []
    for m in trace_messages:
        role = m.get("role", "?")
        if role == "human":
            lines.append(f"[human] {m.get('text', '')}")
        elif role == "ai":
            text = m.get("text", "")
            if text:
                lines.append(f"[ai] {text}")
            for tc in m.get("tool_calls", []):
                lines.append(f"  -> 调用工具 {tc.get('name', '?')}({tc.get('args', '')})")
        elif role == "tool":
            lines.append(f"  <- 工具返回[{m.get('name', '?')}]: {m.get('preview', '')}")
        else:
            lines.append(f"[{role}] {m.get('text', '')}")
    return "\n".join(lines)


def propose_attribution(missed, trace_messages: list[dict], model=None) -> dict:
    """强模型读一次 agent 轨迹，输出归因卡草稿。人确认后才是真归因。

    Args:
        missed: GroundTruthViolation。
        trace_messages: locate_trace 捞出的一次轨迹（已序列化的消息列表）。
        model: 归因用模型，默认 llm_flash。

    Returns:
        归因卡 dict（failure_mode / evidence / root_cause / conclusion）。
        模型输出解析失败时返回空 dict，调用方应提示人工归因。
    """
    from langchain_core.messages import HumanMessage

    if model is None:
        model = llm_flash
    trace_text = _trace_to_readable(trace_messages)
    if not trace_text.strip():
        trace_text = "（无轨迹：agent 未产生任何 read_file 调用，疑似漏读该文件）"

    prompt = f"""你是审查 agent 的判错归因助手。下面是一次代码审查 agent 的完整轨迹，
以及它漏检的一条违规。读轨迹，回答「它为什么没报这条」。

漏检违规：{getattr(missed, 'file', '?')}:{getattr(missed, 'line', '?')}，
规则「{getattr(missed, 'rule', '?')}」

=== agent 轨迹 ===
{trace_text}

=== 输出（严格 JSON，不要多余字段）===
{{
  "failure_mode": "从 [{', '.join(FAILURE_MODES)}] 中选一个",
  "evidence": [{{"tool": "...", "args": "...", "note": "..."}}],
  "root_cause": "它读了X做了Y，因为Z没识别出",
  "conclusion": "经验一句话，将来给 agent 看的那句"
}}"""
    try:
        resp = model.invoke([HumanMessage(content=prompt)])
        content = str(resp.content).strip()
        # 容忍 ```json 包裹
        if content.startswith("```"):
            content = content.strip("`")
            if content.startswith("json"):
                content = content[4:].strip()
        card = json.loads(content)
        return card if isinstance(card, dict) else {}
    except Exception as e:  # noqa: BLE001
        print(f"  [skill-gen] 归因草稿生成失败: {e}")
        return {}


# ── ③ 成稿：归因卡 → 四段 skill（阶段 2 的格式）────────────────
def _miss_to_dict(missed, repo_path: str) -> dict:
    """把一条漏检违规转成 dict，补上真实代码 current 字段（反例从真实代码取）。"""
    file = getattr(missed, "file", "")
    line = getattr(missed, "line", None)
    abs_path = os.path.join(repo_path, file.replace("/", os.sep))
    content = read_file_content(abs_path) or ""
    current = ""
    if content and line:
        current = extract_surrounding_lines(content, int(line), context_lines=2)
    return {"file": file, "line": line, "current": current}


def propose_skill(agent_name: str, rule: str, misses: list, attribution_card: dict,
                  model=None) -> str:
    """把「人已确认的归因卡」落成四段式 skill 正文。

    Args:
        agent_name: 目标域（cpp/qt/git/sqlite）。
        rule: 关联规则名。
        misses: 漏检违规 dict 列表（每项含 file/line/current，见 _miss_to_dict）。
        attribution_card: 人已确认的归因卡。
        model: 成稿模型，默认 llm_flash。

    Returns:
        四段式 markdown skill 正文（不含代码块包裹）。
    """
    from langchain_core.messages import HumanMessage

    if model is None:
        model = llm_flash
    misses_text = "\n".join(
        f"- {m.get('file', '?')}:{m.get('line', '?')}\n  `{str(m.get('current', ''))[:300]}`"
        for m in misses
    )

    prompt = f"""你是代码规范审查经验撰写助手。把下面的归因卡写成一条 Agent Skill。

严格约束：
1. 只输出 skill 正文（四段：# 语义经验 / ## 触发 / ## 判断 / ## 反例）。
2. 不写规则原文、不抄 wiki 条款——规则以 wiki 为准，只补「怎么识别这个场景」。
3. 「判断」段必须落实归因卡的 conclusion；「触发」段落实 failure_mode + root_cause。
4. 反例只用下面提供的真实代码，禁止虚构。
5. 一条 skill 只讲一个语义场景，禁止夹带第二条。

=== 归因卡（人已确认，直接采用）===
失败模式: {attribution_card.get('failure_mode', '')}
根因: {attribution_card.get('root_cause', '')}
结论: {attribution_card.get('conclusion', '')}
关联规则: {rule}
目标 agent: {agent_name}

=== 真实代码 ===
{misses_text}

=== 输出 ===
（四段 markdown，不要代码块包裹）"""
    try:
        resp = model.invoke([HumanMessage(content=prompt)])
        return str(resp.content).strip()
    except Exception as e:  # noqa: BLE001
        print(f"  [skill-gen] skill 成稿失败: {e}")
        return ""


# ── 便捷入口：给定标准答案 + 漏检 id + 轨迹，产出归因卡草稿 ──────
def draft_attribution_cards(missed_violations: list, agent_traces_path: str,
                            model=None) -> list[dict]:
    """对一组漏检违规，逐条定位轨迹 + 起草归因卡（人确认前的半成品）。

    Returns:
        [{"missed": GroundTruthViolation, "traces": [...], "card": {...}}, ...]
        card 为空 dict 表示定位到 0 条轨迹或模型解析失败，需人工归因。
    """
    results: list[dict] = []
    for v in missed_violations:
        traces = locate_trace(v, agent_traces_path)
        card = propose_attribution(v, traces[0] if traces else [], model) if traces else {}
        results.append({"missed": v, "traces": traces, "card": card})
    return results
