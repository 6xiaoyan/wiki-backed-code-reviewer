"""PR 模式可信配置。

配置来源必须可信：默认值写在本文件（随审查程序提交），可被维护者在
workflow/env 中覆盖；PR 分支中的任何文件都不能改变这些值。
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from functools import lru_cache

from code_checker.pr_review.models import BudgetConfig, digest_files, digest_text


@dataclass
class PRConfig:
    budget: BudgetConfig = field(default_factory=BudgetConfig)
    bot_login: str = "github-actions[bot]"
    offline: bool = False
    model_id: str = "deepseek-v4-flash"
    model_provider: str = "deepseek"
    artifact_retention_days: int = 14

    @classmethod
    def from_env(cls, env: dict | None = None) -> "PRConfig":
        env = dict(os.environ if env is None else env)
        raw_budget = env.get("CODE_REVIEW_BUDGET", "").strip()
        budget = BudgetConfig()
        if raw_budget:
            try:
                budget = BudgetConfig.from_dict(json.loads(raw_budget))
            except (json.JSONDecodeError, TypeError, ValueError):
                # 配置损坏时使用默认预算，不静默放宽
                budget = BudgetConfig()
        offline = env.get("CODE_REVIEW_OFFLINE", "").strip().lower() in ("1", "true", "yes")
        return cls(
            budget=budget,
            bot_login=env.get("REVIEW_BOT_LOGIN", "").strip() or "github-actions[bot]",
            offline=offline,
            model_id=env.get("CODE_REVIEW_MODEL", "deepseek-v4-flash").strip()
            or "deepseek-v4-flash",
            model_provider="deepseek",
            artifact_retention_days=budget.artifact_retention_days,
        )

    def to_dict(self) -> dict:
        return {
            "budget": self.budget.to_dict(),
            "bot_login": self.bot_login,
            "offline": self.offline,
            "model_id": self.model_id,
            "model_provider": self.model_provider,
            "artifact_retention_days": self.artifact_retention_days,
        }


def compute_config_digest(config: PRConfig) -> str:
    """非敏感配置摘要（不含任何凭据）。"""
    return digest_text(json.dumps(config.to_dict(), sort_keys=True, ensure_ascii=False))


@lru_cache(maxsize=4)
def compute_rules_digest() -> str:
    """规则 Wiki 与 live skill 的内容摘要（可信版本标识）。"""
    import glob

    package_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    paths = sorted(glob.glob(os.path.join(package_root, "rules-wiki", "wiki", "**", "*.md"),
                             recursive=True))
    paths += sorted(glob.glob(os.path.join(package_root, "agent-skills", "live", "**", "*.md"),
                              recursive=True))
    return digest_files(paths)


@lru_cache(maxsize=4)
def compute_prompts_digest() -> str:
    """提示词摘要：对领域审查系统提示词取摘要。"""
    from code_checker.pr_review.agents import _BASE_PROMPT

    return digest_text(_BASE_PROMPT)
