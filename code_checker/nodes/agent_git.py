"""
agent_git — Git 提交规范审查 Agent。

LLM agent 运行 git log，逐条检查提交信息格式，
通过 run_git_log/report_violation 工具完成审查。

当 LLM 不可用时（offline 模式或 API 故障），自动降级为纯 Python
正则检查，不依赖 LLM。Git 的 4 条规则全部是正则可检查的。
"""

import os
import re
import subprocess

from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent

from code_checker.state import AgentState
from code_checker.config import llm_flash, VALID_COMMIT_TYPES, get_degradation_mode
from code_checker.context_compaction import create_compaction_hook
from code_checker.utils import invoke_with_retry, serialize_messages
from code_checker.skill_loader import load_live_skills
from code_checker.tracer import get_current_tracer
from code_checker.tools import (
    set_state, get_violations_buffer,
    read_file, report_violation, run_git_log,
    set_agent_name, get_wiki_page,
)

GIT_SYSTEM_PROMPT = f"""你是 Git 提交规范审查专家。检查最近 50 条 commit 是否符合规范。

=== Git 提交规范（4 条全量，内嵌系统提示词）===
来源: LLM Wiki git 域。以下为完整的规则条款，无需额外查阅。

1. **git/commit-format** — 提交格式: <type>: <description> | regex
   条款: 提交信息必须遵循 <type>: <description> 格式。type 后可跟可选的 (scope)。冒号后一个空格。

2. **git/commit-type-enum** — 类型枚举限定 | regex
   条款: type 只能为以下之一: {', '.join(sorted(VALID_COMMIT_TYPES))}。其他类型均视为违规。

3. **git/commit-desc-length** — 描述长度 ≤ 50 字符 | regex
   条款: 描述（冒号后的部分）长度不得超过 50 个字符。超长描述影响 git log --oneline 可读性。

4. **git/commit-desc-style** — 描述首字母小写，无句号 | regex
   条款: 描述不以句号结尾。描述首字母不大写（中文描述除外）。

=== 工作流程 ===
1. 用 run_git_log 获取最近 50 条 commit（格式: <hash>|||<subject>）
2. 对照上方规则逐条解析 commit，检查：
   a. 格式是否匹配 <type>: <description>
   b. type 是否在允许列表中
   c. 描述是否 ≤ 50 字符
   d. 描述是否不以句号结尾
   e. 描述首字母是否不大写（中文跳过）
3. 每发现一个违规，用 report_violation 记录：
   - file: 仓库路径
   - line: 0（commit 无行号）
   - rule: Git 提交格式 / Git 提交类型 / Git 标题长度 / 等
   - severity: info（Git 违规无法自动修复，仅用于报告展示）
   - rule_page: 对应的 wiki 页面路径，如 "git/commit-format"
   - current: 违规的 commit subject
   - expected: 期望的正确格式
   - reason: 明确说明为什么违反规范
4. 检查完所有 commit 后，说明"检查完成"

=== 重要 ===
- severity 必须填 "info"（Git 违规属于流程问题，fix agent 无法自动修 commit message）
- 如果 git 未安装或无提交记录，报告一个 git-not-found 或 git-empty 违规
- 一次报告一条违规"""

GIT_AGENT_TOOLS = [
    run_git_log, read_file, report_violation,
    get_wiki_page,
]


def _git_local_check(repo_path: str) -> list[dict]:
    """纯 Python 正则检查 Git 提交规范（LLM 不可用时的降级方案）。

    不依赖 LLM，直接运行 git log 并用正则检查每条 commit 的：
      1. 格式: <type>: <description>
      2. type 枚举
      3. 描述长度 ≤ 50
      4. 描述首字母不大写，无句号
    """
    violations: list[dict] = []

    # ── 运行 git log ──
    try:
        output = subprocess.check_output(
            ["git", "-C", repo_path, "log", "--oneline", "-50",
             "--format=%H|||%s"],
            stderr=subprocess.STDOUT,
            text=True,
            timeout=10,
        )
    except (subprocess.CalledProcessError, FileNotFoundError,
            subprocess.TimeoutExpired, OSError) as e:
        print(f"  [git_agent ] git log 执行失败: {e}")
        violations.append({
            "file": repo_path,
            "line": 0,
            "rule": "Git 环境检查",
            "severity": "info",
            "current": "git 未安装或未找到",
            "expected": "git 已安装且可用",
            "reason": "系统中未安装 git 或 git 不在 PATH 中，无法执行 git log 获取提交记录，导致无法进行 Git 提交规范审查。",
            "source": "git",
        })
        return violations

    commits = [line.strip() for line in output.strip().split("\n") if line.strip()]
    if not commits:
        return violations

    # ── 逐条检查 ──
    commit_re = re.compile(r"^(\w+)(?:\(([^)]*)\))?: (.+)$")

    for commit_line in commits:
        # 解析: <hash>|||<subject>
        parts = commit_line.split("|||", 1)
        if len(parts) != 2:
            continue
        subject = parts[1].strip()

        m = commit_re.match(subject)
        if not m:
            violations.append({
                "file": repo_path,
                "line": 0,
                "rule": "Git 提交格式",
                "severity": "info",
                "current": subject[:80],
                "expected": "<type>: <description>（如 feat: 添加用户登录）",
                "reason": f"提交信息 '{subject[:60]}' 不符合 <type>: <description> 格式",
                "source": "git",
            })
            continue

        commit_type = m.group(1)
        description = m.group(3)

        # 检查 type 枚举
        if commit_type not in VALID_COMMIT_TYPES:
            violations.append({
                "file": repo_path,
                "line": 0,
                "rule": "Git 提交类型",
                "severity": "info",
                "current": subject[:80],
                "expected": f"type 应为以下之一: {', '.join(sorted(VALID_COMMIT_TYPES))}",
                "reason": f"'{commit_type}' 不在允许的提交类型列表中",
                "source": "git",
            })

        # 检查描述长度
        if len(description) > 50:
            violations.append({
                "file": repo_path,
                "line": 0,
                "rule": "Git 标题长度",
                "severity": "info",
                "current": subject[:80],
                "expected": "描述 ≤ 50 字符",
                "reason": f"描述 '{description[:40]}...' 长度 {len(description)} 超过 50 字符限制",
                "source": "git",
            })

        # 检查描述风格（首字母不大写，无句号）
        style_issues = []
        if description and description[0].isupper() and not _is_cjk(description[0]):
            style_issues.append("首字母应不大写")
        if description.endswith("."):
            style_issues.append("不应以句号结尾")
        if style_issues:
            violations.append({
                "file": repo_path,
                "line": 0,
                "rule": "Git 描述风格",
                "severity": "info",
                "current": subject[:80],
                "expected": "描述首字母不大写（中文除外），不以句号结尾",
                "reason": f"描述 '{description[:50]}': {', '.join(style_issues)}",
                "source": "git",
            })

    return violations


def _is_cjk(ch: str) -> bool:
    """判断字符是否为 CJK（中日韩）字符。"""
    cp = ord(ch)
    return (0x4E00 <= cp <= 0x9FFF or 0x3400 <= cp <= 0x4DBF
            or 0x3040 <= cp <= 0x309F or 0x30A0 <= cp <= 0x30FF
            or 0xAC00 <= cp <= 0xD7AF)


def git_agent(state: AgentState) -> dict:
    """Git 提交规范审查 agent 节点。

    正常情况下用 LLM agent 全面审查。LLM 不可用时
    （offline 模式或 API 故障）自动降级为纯正则本地检查。
    """
    print("  [git_agent ] 启动...")

    set_agent_name("git_agent")
    set_state(state)
    repo_path = state.get("repo_path", "")

    # ── offline 模式：直接走本地检查 ──
    if get_degradation_mode() == "offline":
        print("  [git_agent ] offline 模式，使用本地正则检查")
        violations = _git_local_check(repo_path)
        _log_git_degradation(state, "offline 模式，使用本地正则检查")
        print(f"  [git_agent ] 完成（本地模式）: {len(violations)} 条违规")
        return {"git_violations": violations}

    # ── 正常模式：LLM agent ──
    try:
        skills_text = load_live_skills("git")
        prompt = GIT_SYSTEM_PROMPT
        if skills_text:
            prompt = GIT_SYSTEM_PROMPT + "\n\n" + skills_text
        agent = create_react_agent(
            model=llm_flash,
            tools=GIT_AGENT_TOOLS,
            prompt=prompt,
            pre_model_hook=create_compaction_hook(
                "git_agent",
                critical_tool_names={"run_git_log", "get_rules_text"},
            ),
        )

        result = invoke_with_retry(
            agent,
            f"开始审查 Git 提交规范。仓库路径: {repo_path}。请先 run_git_log 获取提交记录。",
            "git_agent",
            config={"recursion_limit": 50},
        )

        tracer = get_current_tracer()
        if tracer is not None:
            tracer.record_agent_trace("git", serialize_messages(result.get("messages", [])))

        violations = get_violations_buffer()
        msg_count = len(result.get("messages", []))
        print(f"  [git_agent ] 完成: {len(violations)} 条违规, {msg_count} 轮消息")

    except Exception as e:
        print(f"  [git_agent ] LLM 调用失败: {e}，降级到本地正则检查")
        violations = _git_local_check(repo_path)
        _log_git_degradation(state, f"API 调用失败: {e}，降级到本地正则检查")
        print(f"  [git_agent ] 完成（降级模式）: {len(violations)} 条违规")

    for v in violations:
        v["source"] = "git"
        if v.get("severity") != "info":
            v["severity"] = "info"

    return {"git_violations": violations}


def _log_git_degradation(state: AgentState, reason: str) -> None:
    """记录 git_agent 降级事件。"""
    log = list(state.get("degradation_log") or [])
    log.append({
        "stage": "git_agent",
        "status": "degraded",
        "reason": reason,
        "impact": "Git 提交规范检查使用本地正则（功能完整，但无 LLM 语义增强）",
    })
    state["degradation_log"] = log
