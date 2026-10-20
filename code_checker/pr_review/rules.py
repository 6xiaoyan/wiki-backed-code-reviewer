"""可信 Wiki 规则正文的注入与引用核验（PRD §7 领域 Agent 依据）。

设计目标：
  * 每个领域只看到**本领域**的规则正文（C++ 含腾讯安全副规则），不混入其他领域；
  * 注入有明确上限：单页上限与领域总量上限都来自可信配置；
  * 超限的规则不会被静默丢弃，而是记录到 ``RuleCorpus.excluded``，
    由流水线标为 ``incomplete`` 并写入运行记录；
  * 报告中的“规则正文”来自 Wiki 页面原文，模型引用（rule_quote）会被
    确定性核验是否真的出现在页面正文中。

全部读取本地 ``code_checker/rules-wiki``，不访问网络、不读取 PR 分支内容。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache

#: 主领域之外允许注入的副规则域（腾讯安全规则属于 C++ 安全审查范围）。
DOMAIN_EXTRA_DOMAINS: dict[str, tuple[str, ...]] = {
    "cpp": ("tencent",),
}

_DOMAIN_TITLES = {
    "cpp": "C++ 代码规范",
    "qt": "Qt 开发规范",
    "sqlite": "SQLite 加密规范",
}

_FRONTMATTER_RE = re.compile(r"^---\s*\n.*?\n---\s*\n", re.DOTALL)
_SECTION_RE = re.compile(r"^##\s+(?P<name>[^\n#]+?)\s*$", re.MULTILINE)
_WS_RE = re.compile(r"\s+")


@dataclass(frozen=True)
class RulePage:
    slug: str
    domain: str
    title: str
    content: str
    clause: str
    source_file: str = ""
    source_section: str = ""
    priority: str = "main"

    @property
    def source(self) -> str:
        parts = [p for p in (self.source_file, self.source_section) if p]
        return " ".join(parts)


@dataclass
class RuleCorpus:
    """一次运行中注入给某个领域 Agent 的规则正文集合。"""

    domain: str
    text: str
    included: list[str] = field(default_factory=list)
    excluded: list[dict] = field(default_factory=list)
    used_bytes: int = 0
    limit_bytes: int = 0
    total_pages: int = 0
    injected_text: dict[str, str] = field(default_factory=dict)
    """rule_id → 本轮实际注入的正文块（引用核验只能在这个范围内进行）。"""

    @property
    def truncated(self) -> bool:
        return bool(self.excluded)

    @property
    def empty(self) -> bool:
        return not self.included

    def to_dict(self) -> dict:
        """运行记录用摘要（不重复保存完整正文）。"""
        return {
            "domain": self.domain,
            "rules_injected": len(self.included),
            "rules_not_injected": len(self.excluded),
            "pages": self.total_pages,
            "used_bytes": self.used_bytes,
            "limit_bytes": self.limit_bytes,
            "included": list(self.included),
            "excluded": [dict(e) for e in self.excluded],
        }


def _extract_section(text: str, name: str) -> str:
    """提取 ``## name`` 到下一个二级标题之间的正文。"""
    matches = list(_SECTION_RE.finditer(text))
    for i, match in enumerate(matches):
        if match.group("name").strip() != name:
            continue
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        return text[start:end].strip()
    return ""


def _strip_frontmatter(text: str) -> str:
    return _FRONTMATTER_RE.sub("", text, count=1).strip()


def _clean_meta(value) -> str:
    return str(value or "").strip().strip('"').strip("'").strip()


def _normalize(text: str) -> str:
    """归一化用于引用核验：忽略空白与 Markdown 强调符号。"""
    text = (text or "").replace("**", "").replace("`", "").replace("*", "")
    return _WS_RE.sub("", text)


@lru_cache(maxsize=1)
def rule_pages() -> dict[str, RulePage]:
    """读取可信 Wiki 索引，构建 rule_id → RulePage。失败时返回空表。"""
    try:
        from code_checker.wiki_search import _init_index, _parse_frontmatter

        index = _init_index()
    except Exception:
        return {}

    pages: dict[str, RulePage] = {}
    for slug, raw in index.items():
        content = str(raw.get("content") or "")
        meta = _parse_frontmatter(content)
        clause = _extract_section(content, "规则条款")
        pages[slug] = RulePage(
            slug=slug,
            domain=str(raw.get("domain") or ""),
            title=str(raw.get("title") or slug),
            content=content,
            clause=clause,
            source_file=_clean_meta(meta.get("source_file")),
            source_section=_clean_meta(meta.get("source_section")),
            priority=str(raw.get("priority") or "main"),
        )
    return pages


def page_for_rule(rule_id: str) -> RulePage | None:
    return rule_pages().get(rule_id)


def pages_for_domain(domain: str,
                     extra_domains: tuple[str, ...] | None = None) -> list[RulePage]:
    """返回该领域（含配置的副规则域）的页面，按 slug 稳定排序。"""
    domains = (domain,)
    if extra_domains is None:
        extra_domains = DOMAIN_EXTRA_DOMAINS.get(domain, ())
    domains += tuple(extra_domains)
    pages = [p for p in rule_pages().values() if p.domain in domains]
    return sorted(pages, key=lambda p: p.slug)


def build_domain_rules(
    domain: str,
    *,
    limit_bytes: int = 64 * 1024,
    max_page_bytes: int = 4 * 1024,
    extra_domains: tuple[str, ...] | None = None,
) -> RuleCorpus:
    """构建领域规则正文。

    超过单页或领域总量的规则不会被截断后继续使用，而是排除并记录；
    调用方必须据此把结果标为 ``incomplete``。
    """
    pages = pages_for_domain(domain, extra_domains)
    corpus = RuleCorpus(
        domain=domain, text="", limit_bytes=int(limit_bytes),
        total_pages=len(pages),
    )
    blocks: list[str] = []
    for page in pages:
        clause = page.clause or _strip_frontmatter(page.content)[:max_page_bytes]
        if not clause.strip():
            corpus.excluded.append({
                "rule_id": page.slug,
                "reason": "可信 Wiki 页面没有可注入的规则正文",
            })
            continue
        source = f"来源: {page.source}\n" if page.source else ""
        block = f"### {page.slug} — {page.title}\n{source}{clause}\n"
        nbytes = len(block.encode("utf-8"))
        if nbytes > max_page_bytes:
            corpus.excluded.append({
                "rule_id": page.slug,
                "reason": (
                    f"单页规则正文 {nbytes} 字节超过上限 {max_page_bytes} 字节"
                ),
                "bytes": nbytes,
            })
            continue
        if corpus.used_bytes + nbytes > limit_bytes:
            corpus.excluded.append({
                "rule_id": page.slug,
                "reason": (
                    f"超出领域规则正文注入预算：已用 {corpus.used_bytes} 字节，"
                    f"上限 {limit_bytes} 字节"
                ),
                "bytes": nbytes,
            })
            continue
        blocks.append(block)
        corpus.included.append(page.slug)
        corpus.injected_text[page.slug] = block
        corpus.used_bytes += nbytes
    corpus.text = "\n".join(blocks)
    return corpus


def rule_clause(rule_id: str, *, max_chars: int = 800) -> str:
    """返回用于报告展示的规则条款原文（确定性提取）。"""
    page = page_for_rule(rule_id)
    if page is None:
        return ""
    text = page.clause or _strip_frontmatter(page.content)
    text = text.strip()
    if len(text) > max_chars:
        text = text[:max_chars].rstrip() + "…"
    return text


def rule_source(rule_id: str) -> str:
    page = page_for_rule(rule_id)
    return page.source if page else ""


def quote_supported(rule_id: str, quote: str) -> tuple[bool, str]:
    """核验模型引用的规则正文是否真的出现在可信 Wiki 页面中。

    仅用于一般性检查；PR 审查必须使用 ``quote_in_injected``，把范围限制在
    本轮实际注入给该领域 Agent 的正文。

    Returns:
        (是否支持, 不支持原因)
    """
    page = page_for_rule(rule_id)
    if page is None:
        return False, "规则页面不存在"
    normalized = _normalize(quote)
    if len(normalized) < 8:
        return False, "引用的规则正文过短，无法核验"
    if normalized in _normalize(page.content):
        return True, ""
    if normalized in _normalize(page.clause):
        return True, ""
    return False, "引用的规则正文未出现在可信 Wiki 页面中"


def quote_in_injected(
    rule_id: str,
    quote: str,
    injected_text: dict[str, str],
) -> tuple[bool, str]:
    """核验引用是否来自该领域本轮**实际注入**的规则正文。

    ``injected_text`` 是 ``RuleCorpus.injected_text``（rule_id → 注入块）。
    """
    block = injected_text.get(rule_id)
    if block is None:
        return False, "该规则未在本轮注入给当前领域 Agent（其他领域或被预算排除）"
    normalized = _normalize(quote)
    if len(normalized) < 8:
        return False, "引用的规则正文过短，无法核验"
    if normalized not in _normalize(block):
        return False, "引用的规则正文不在本轮注入的正文范围内"
    return True, ""


def domain_title(domain: str) -> str:
    return _DOMAIN_TITLES.get(domain, domain)
