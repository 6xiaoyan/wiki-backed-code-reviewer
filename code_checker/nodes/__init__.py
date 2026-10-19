"""
检查器 & 处理节点模块（双层架构：确定性 + LLM 语义）。

每个节点是一个纯函数，签名为 (AgentState) -> dict，由 LangGraph StateGraph 调度。

双层检查架构：
  - deterministic_checker: 确定性正则检查（Python 强制执行，不经 LLM，不丢不漏）
  - cpp_agent / qt_agent / git_agent / sqlite_agent: LLM 语义审查

流水线节点:
  - report_merger: 合并去重 agent（must_keep 保护）
  - fix_agent / review_agent: fix-review loop agents
  - format_fixer: 确定性格式修复
  - repo_scanner / report_exporter: 入口/出口
"""

# 确定性检查器（第一层：系统强制执行）
from code_checker.nodes.deterministic_checker import deterministic_checker

# Agent 节点（第二层：LLM 语义审查）
from code_checker.nodes.agent_cpp import cpp_agent
from code_checker.nodes.agent_qt import qt_agent
from code_checker.nodes.agent_git import git_agent
from code_checker.nodes.agent_sqlite import sqlite_agent
from code_checker.nodes.agent_fix import fix_agent
from code_checker.nodes.agent_review import review_agent

# 基础节点
from code_checker.nodes.repo_scanner import repo_scanner
from code_checker.nodes.github_scanner import github_scanner
from code_checker.nodes.report_merger import report_merger
from code_checker.nodes.format_fixer import format_fixer
from code_checker.nodes.report_exporter import report_exporter

__all__ = [
    # 确定性检查器
    "deterministic_checker",
    # Agent 节点
    "cpp_agent",
    "qt_agent",
    "git_agent",
    "sqlite_agent",
    "fix_agent",
    "review_agent",
    # 基础节点
    "repo_scanner",
    "github_scanner",
    "report_merger",
    "format_fixer",
    "report_exporter",
]
