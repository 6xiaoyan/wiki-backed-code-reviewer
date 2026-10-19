"""
Code Checker — 基于 LangGraph 的代码规范自动审查系统。

对 C++/Qt 项目进行多维度合规检查（代码规范、Git 提交、SQLite 安全），
自动生成修复方案，通过自我审查迭代优化，最终输出 Markdown 报告。

Usage:
    from code_checker.graph import app
    result = app.invoke({"repo_path": "./your-repo", ...})

注意：包导入本身保持轻量（不加载 LangGraph 全图），这样 PR 发布任务
只需要标准库即可运行校验与评论发布代码。`app` 与 `AgentState` 通过
模块级 ``__getattr__`` 惰性导入，兼容原有 ``from code_checker import app``。
"""

from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover - 仅类型检查
    from code_checker.graph import app
    from code_checker.state import AgentState

__all__ = ["app", "AgentState"]


def __getattr__(name: str):
    if name == "app":
        from code_checker.graph import app as _app

        return _app
    if name == "AgentState":
        from code_checker.state import AgentState as _state

        return _state
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
