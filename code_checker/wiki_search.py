"""
Wiki 检索引擎 —— 为 Agent 提供规则 Wiki 的搜索和页面读取能力。

支持：
  - 按域（domain）过滤：cpp / qt / sqlite / git / tencent / qt-wiki / google
  - 按关键词搜索标题和正文
  - 按 rule_id 精确获取单个页面
  - 读取相关页面（通过 related_pages wikilink）

所有查询记录到结构化日志，便于追溯 LLM 的查阅行为。
"""

import os
import re
import json
import time
import threading
from typing import Optional
from dataclasses import dataclass, field, asdict

# ---------------------------------------------------------------------------
# 路径
# ---------------------------------------------------------------------------
_WIKI_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rules-wiki", "wiki")
_FIX_PATTERNS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "rules-wiki", "fix-patterns")
_FIX_PATTERNS_RAW_DIR = os.path.join(_FIX_PATTERNS_DIR, "raw")

# ---------------------------------------------------------------------------
# 日志
# ---------------------------------------------------------------------------
@dataclass
class WikiAccessLog:
    """单次 wiki 访问的记录。"""
    timestamp: str = ""
    agent: str = ""              # cpp_agent / qt_agent / fix_agent / ...
    action: str = ""             # search / get_page / get_related
    query: str = ""              # 搜索关键词或 rule_id
    domain_filter: str = ""      # 域过滤（如有）
    results: list[str] = field(default_factory=list)  # 返回的页面 slug 列表
    result_count: int = 0
    elapsed_ms: float = 0.0

_wiki_log: list[WikiAccessLog] = []
_wiki_log_lock = threading.Lock()

# 日志文件路径
_WIKI_LOG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "wiki_access.log")

def _log_access(entry: WikiAccessLog) -> None:
    """线程安全地记录一次 wiki 访问，同时写结构化日志文件和追加行。"""
    with _wiki_log_lock:
        _wiki_log.append(entry)

    # 追加到日志文件
    try:
        with open(_WIKI_LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(asdict(entry), ensure_ascii=False) + "\n")
    except Exception:
        pass

def get_wiki_log() -> list[dict]:
    """获取当前会话的完整 wiki 访问日志。"""
    with _wiki_log_lock:
        return [asdict(e) for e in _wiki_log]

def clear_wiki_log() -> None:
    """清空日志（每次 pipeline 启动时调用）。"""
    global _wiki_log
    with _wiki_log_lock:
        _wiki_log = []

# ---------------------------------------------------------------------------
# 页面索引
# ---------------------------------------------------------------------------
# 全局缓存：{slug: {domain, rule_id, title, path, related_pages, content}}
_page_index: Optional[dict[str, dict]] = None
_index_lock = threading.Lock()

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)
WIKILINK_RE = re.compile(r"\[\[([^]]+)\]\]")

def _parse_frontmatter(text: str) -> dict:
    """解析 YAML frontmatter（简化版，不依赖 PyYAML）。"""
    m = FRONTMATTER_RE.match(text)
    if not m:
        return {}
    fm_text = m.group(1)
    meta = {}
    for line in fm_text.split("\n"):
        line = line.strip()
        if ":" not in line:
            continue
        key, _, value = line.partition(":")
        key = key.strip()
        value = value.strip()
        # 简单列表解析
        if value.startswith("[") and value.endswith("]"):
            items = [v.strip().strip("'\"") for v in value[1:-1].split(",") if v.strip()]
            meta[key] = items
        elif value == "true":
            meta[key] = True
        elif value == "false":
            meta[key] = False
        else:
            meta[key] = value
    return meta

def _extract_related(text: str) -> list[str]:
    """从正文中提取 wikilink 指向的页面。"""
    links = []
    for m in WIKILINK_RE.finditer(text):
        link = m.group(1)
        # 跳过跨页锚点
        if "#" in link:
            link = link.split("#")[0]
        links.append(link)
    return links

def _build_index() -> dict[str, dict]:
    """构建完整 wiki 页面索引（首次调用时执行，后续走缓存）。

    索引范围:
      - rules-wiki/wiki/     → 规则库（domain=cpp/qt/sqlite/git/tencent/qt-wiki/google）
      - rules-wiki/fix-patterns/ → 修复模式库（domain=fix-patterns），排除 raw/ 草稿
    """
    global _page_index
    with _index_lock:
        if _page_index is not None:
            return _page_index

        idx = {}

        # ── 1. 规则 wiki ──
        for domain in os.listdir(_WIKI_DIR):
            domain_dir = os.path.join(_WIKI_DIR, domain)
            if not os.path.isdir(domain_dir):
                continue
            for fname in os.listdir(domain_dir):
                if not fname.endswith(".md"):
                    continue
                fpath = os.path.join(domain_dir, fname)
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        text = f.read()
                except Exception:
                    continue

                meta = _parse_frontmatter(text)
                slug = f"{domain}/{fname[:-3]}"  # e.g. "cpp/naming-classes"
                title = meta.get("title", fname[:-3])
                rule_id = meta.get("rule_id", slug)

                # 合并 frontmatter related_pages + 正文 wikilink
                related = list(meta.get("related_pages", []))
                body_links = _extract_related(text)
                for link in body_links:
                    if link not in related:
                        related.append(link)

                idx[slug] = {
                    "slug": slug,
                    "domain": domain,
                    "rule_id": rule_id,
                    "title": title,
                    "path": fpath,
                    "priority": meta.get("priority", "main"),
                    "check_method": meta.get("check_method", ""),
                    "checkability": meta.get("checkability", ""),
                    "conflicts_with": meta.get("conflicts_with", []),
                    "overrides": meta.get("overrides", []),
                    "related_pages": related,
                    "content": text,
                }

        # ── 2. Fix Patterns（排除 raw/ 草稿目录）──
        if os.path.isdir(_FIX_PATTERNS_DIR):
            for fname in os.listdir(_FIX_PATTERNS_DIR):
                if not fname.endswith(".md"):
                    continue
                fpath = os.path.join(_FIX_PATTERNS_DIR, fname)
                if not os.path.isfile(fpath):
                    continue
                # 排除 raw/ 下的草稿（已在目录级别排除，此处双保险）
                if _FIX_PATTERNS_RAW_DIR in fpath:
                    continue
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        text = f.read()
                except Exception:
                    continue

                meta = _parse_frontmatter(text)
                slug = f"fix-patterns/{fname[:-3]}"
                title = meta.get("title", fname[:-3])
                rule_id = meta.get("rule_id", slug)

                related = list(meta.get("related_pages", []))
                body_links = _extract_related(text)
                for link in body_links:
                    if link not in related:
                        related.append(link)

                idx[slug] = {
                    "slug": slug,
                    "domain": "fix-patterns",
                    "rule_id": rule_id,
                    "title": title,
                    "path": fpath,
                    "priority": meta.get("priority", "pattern"),
                    "check_method": meta.get("check_method", ""),
                    "checkability": meta.get("checkability", ""),
                    "conflicts_with": meta.get("conflicts_with", []),
                    "overrides": meta.get("overrides", []),
                    "related_pages": related,
                    "content": text,
                }

        _page_index = idx
        return idx

def _init_index() -> dict[str, dict]:
    """获取索引（自动初始化）。"""
    if _page_index is None:
        return _build_index()
    return _page_index

# ---------------------------------------------------------------------------
# 搜索
# ---------------------------------------------------------------------------

def search_wiki_pages(
    query: str,
    domain: str = "",
    max_results: int = 10,
    agent_name: str = "unknown",
) -> dict:
    """搜索 wiki 页面。

    Args:
        query: 搜索关键词（空格分隔多词，匹配标题和正文）
        domain: 限制域（cpp/qt/sqlite/git/tencent/qt-wiki/google），空=全部
        max_results: 最多返回条数
        agent_name: 调用者名称（用于日志）

    Returns:
        {"matches": [...], "total": int, "query": str}
        每条 match: {slug, domain, title, rule_id, priority, snippet, score}
    """
    t0 = time.perf_counter()
    idx = _init_index()

    keywords = query.lower().split()
    scored = []

    for slug, page in idx.items():
        if domain and page["domain"] != domain:
            continue

        title_lower = page["title"].lower()
        content_lower = page["content"].lower()

        # 计算相关度分数
        score = 0
        for kw in keywords:
            # 标题命中权重高
            score += title_lower.count(kw) * 10
            # 正文命中权重低
            score += content_lower.count(kw) * 0.5
            # rule_id 精确匹配
            if kw == page["rule_id"].lower():
                score += 20

        if score > 0:
            # 生成摘录（匹配关键词周围文本）
            snippet = _make_snippet(page["content"], keywords, max_len=300)
            scored.append({
                "slug": slug,
                "domain": page["domain"],
                "title": page["title"],
                "rule_id": page["rule_id"],
                "priority": page["priority"],
                "check_method": page["check_method"],
                "snippet": snippet,
                "score": round(score, 1),
            })

    # 按分数降序
    scored.sort(key=lambda x: x["score"], reverse=True)
    total = len(scored)
    matches = scored[:max_results]

    # 日志
    result_slugs = [m["slug"] for m in matches]
    _log_access(WikiAccessLog(
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%S"),
        agent=agent_name,
        action="search",
        query=query,
        domain_filter=domain,
        results=result_slugs,
        result_count=len(matches),
        elapsed_ms=round((time.perf_counter() - t0) * 1000, 1),
    ))

    return {
        "matches": matches,
        "total": total,
        "query": query,
        "domain": domain or "all",
    }

def _make_snippet(text: str, keywords: list[str], max_len: int = 300) -> str:
    """在正文中匹配关键词附近生成摘录。"""
    text_lower = text.lower()
    best_pos = -1
    best_score = 0

    for kw in keywords:
        pos = text_lower.find(kw)
        while pos >= 0:
            # 评分：附近关键词密度
            window_start = max(0, pos - 100)
            window_end = min(len(text_lower), pos + 100)
            window = text_lower[window_start:window_end]
            density = sum(window.count(k) for k in keywords)
            if density > best_score:
                best_score = density
                best_pos = pos
            pos = text_lower.find(kw, pos + 1)

    if best_pos < 0:
        return text[:max_len].strip()

    start = max(0, best_pos - 80)
    end = min(len(text), best_pos + 200)
    snippet = text[start:end].strip()
    if start > 0:
        snippet = "…" + snippet
    if end < len(text):
        snippet = snippet + "…"
    return snippet[:max_len]

# ---------------------------------------------------------------------------
# 获取单页
# ---------------------------------------------------------------------------

def get_wiki_page(slug: str, agent_name: str = "unknown") -> dict | None:
    """获取指定 wiki 页面的完整内容。

    Args:
        slug: 页面标识，如 "cpp/naming-classes" 或 "naming-classes"
        agent_name: 调用者名称（用于日志）

    Returns:
        {slug, domain, title, rule_id, content, related_pages, ...} 或 None
    """
    t0 = time.perf_counter()
    idx = _init_index()

    # 支持短名（不带域前缀）
    if slug in idx:
        page = idx[slug]
    else:
        # 尝试模糊匹配
        found = None
        for s, p in idx.items():
            if s.endswith(slug) or p["rule_id"] == slug:
                found = p
                break
        if found is None:
            _log_access(WikiAccessLog(
                timestamp=time.strftime("%Y-%m-%dT%H:%M:%S"),
                agent=agent_name, action="get_page", query=slug,
                results=[], result_count=0,
                elapsed_ms=round((time.perf_counter() - t0) * 1000, 1),
            ))
            return None
        page = found

    _log_access(WikiAccessLog(
        timestamp=time.strftime("%Y-%m-%dT%H:%M:%S"),
        agent=agent_name, action="get_page", query=slug,
        results=[page["slug"]], result_count=1,
        elapsed_ms=round((time.perf_counter() - t0) * 1000, 1),
    ))

    return {
        "slug": page["slug"],
        "domain": page["domain"],
        "title": page["title"],
        "rule_id": page["rule_id"],
        "priority": page["priority"],
        "check_method": page["check_method"],
        "conflicts_with": page["conflicts_with"],
        "overrides": page["overrides"],
        "related_pages": page["related_pages"],
        "content": page["content"],
    }

# ---------------------------------------------------------------------------
# 获取相关页面
# ---------------------------------------------------------------------------

def get_related_pages(slug: str, agent_name: str = "unknown") -> list[dict]:
    """获取与指定页面相关的其他 wiki 页面内容。

    返回相关页面的简要信息（slug, title, domain）+ 摘要。
    """
    page = get_wiki_page(slug, agent_name)
    if not page:
        return []

    related = []
    for link in page.get("related_pages", []):
        p = get_wiki_page(link, agent_name)
        if p:
            related.append({
                "slug": p["slug"],
                "title": p["title"],
                "domain": p["domain"],
                "priority": p["priority"],
                "snippet": p["content"][:500],
            })
    return related

# ---------------------------------------------------------------------------
# 列出域中所有页面
# ---------------------------------------------------------------------------

def list_domain_pages(domain: str) -> list[dict]:
    """列出指定域中的所有 wiki 页面（仅标题和摘要，不含全文）。"""
    idx = _init_index()
    pages = []
    for slug, page in idx.items():
        if page["domain"] == domain:
            pages.append({
                "slug": slug,
                "title": page["title"],
                "rule_id": page["rule_id"],
                "priority": page["priority"],
                "check_method": page["check_method"],
                "conflicts_with": page["conflicts_with"],
            })
    pages.sort(key=lambda x: x["slug"])
    return pages

# ---------------------------------------------------------------------------
# 统计
# ---------------------------------------------------------------------------

def get_wiki_stats() -> dict:
    """返回 wiki 统计信息。"""
    idx = _init_index()
    domains = {}
    for slug, page in idx.items():
        d = page["domain"]
        domains[d] = domains.get(d, 0) + 1
    return {
        "total_pages": len(idx),
        "domains": domains,
        "wiki_dir": _WIKI_DIR,
    }
