"""
全局配置：LLM 客户端、文件扩展名、正则模式、规则文件路径。

所有模块从此处引用配置，避免散落各处的魔法常量。
"""

import os
import re
from langchain_openai import ChatOpenAI

# ---------------------------------------------------------------------------
# LLM 模型 — 默认全部使用 deepseek-v4-flash
#
# 凭据只从环境变量读取，绝不出现在源码、文档或日志中：
#   DEEPSEEK_API_KEY（首选）或 OPENAI_API_KEY（兼容）
# 缺少凭据时仍可导入本模块（离线模式、PR 模式的结构化输出均可运行），
# 但真实模型调用会失败。PR 入口会在运行前显式检查并报告配置缺失。
# ---------------------------------------------------------------------------
_LLM_MODEL = os.environ.get("CODE_REVIEW_MODEL", "deepseek-v4-flash")
_LLM_BASE_URL = os.environ.get("CODE_REVIEW_LLM_BASE_URL", "https://api.deepseek.com")
_LLM_PROVIDER = "deepseek"

LLM_API_KEY_ENV = "DEEPSEEK_API_KEY"
LLM_API_KEY = (
    os.environ.get("DEEPSEEK_API_KEY")
    or os.environ.get("OPENAI_API_KEY")
    or ""
)
LLM_CREDENTIALS_CONFIGURED = bool(LLM_API_KEY)


def has_llm_credentials() -> bool:
    """是否配置了模型凭据。凭据值本身不会返回或记录。"""
    return bool(os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("OPENAI_API_KEY"))


def describe_llm_config() -> dict:
    """返回非敏感的模型配置摘要（用于 ReviewRequest 版本记录）。"""
    return {
        "provider": _LLM_PROVIDER,
        "model": _LLM_MODEL,
        "base_url": _LLM_BASE_URL,
        "temperature": 0,
        "credentials_configured": has_llm_credentials(),
    }


if not has_llm_credentials():
    print("[配置] 未检测到 DEEPSEEK_API_KEY/OPENAI_API_KEY；离线模式可用，在线审查需配置凭据")

# ---------------------------------------------------------------------------
# 降级模式
# ---------------------------------------------------------------------------
# DEGRADATION_MODE=strict  — 不降级，API 故障即 crash（CI 门禁）
# DEGRADATION_MODE=normal  — LLM 阶段降级但继续，始终产出报告（默认）
# DEGRADATION_MODE=offline — 零 API 调用，只跑确定性检查 + format_fixer
# ---------------------------------------------------------------------------
_DEGRADATION_MODE = os.environ.get("DEGRADATION_MODE", "normal").lower()
if _DEGRADATION_MODE not in ("strict", "normal", "offline"):
    print(f"[配置] 未知 DEGRADATION_MODE={_DEGRADATION_MODE}，回退为 normal")
    _DEGRADATION_MODE = "normal"
IS_OFFLINE = _DEGRADATION_MODE == "offline"
IS_STRICT = _DEGRADATION_MODE == "strict"
print(f"[配置] 降级模式: {_DEGRADATION_MODE.upper()}")


def get_degradation_mode() -> str:
    """获取当前降级模式。运行时可通过 set_degradation_mode() 覆盖。"""
    return _DEGRADATION_MODE


def set_degradation_mode(mode: str) -> None:
    """运行时覆盖降级模式（用于 CLI --offline/--strict 标志）。"""
    global _DEGRADATION_MODE, IS_OFFLINE, IS_STRICT
    mode = mode.lower()
    if mode not in ("strict", "normal", "offline"):
        raise ValueError(f"未知降级模式: {mode}")
    _DEGRADATION_MODE = mode
    IS_OFFLINE = mode == "offline"
    IS_STRICT = mode == "strict"

# ---------------------------------------------------------------------------
# LLM 客户端
# ---------------------------------------------------------------------------

# 审查/修复方案评分/语义审查 — flash 模型，temperature=0 确保确定性
# timeout=120: flash 模型响应快
# max_retries=0: SDK 级重试已关闭，由 invoke_with_retry 统一管理重试策略。
#   避免 SDK 重试 × agent 重试的乘法放大效应。
llm = ChatOpenAI(
    model=_LLM_MODEL,
    base_url=_LLM_BASE_URL,
    api_key=LLM_API_KEY or "missing-api-key",
    temperature=0,
    max_tokens=131072,
    max_retries=0,
    timeout=120,
)

# 辅助模型：修复生成、去重合并，始终用 flash
# max_retries=0: SDK 级重试已关闭（同上）
# timeout=120: flash 模型响应更快，超时更短
llm_flash = ChatOpenAI(
    model=_LLM_MODEL,
    base_url=_LLM_BASE_URL,
    api_key=LLM_API_KEY or "missing-api-key",
    temperature=0.3,
    max_tokens=131072,
    max_retries=0,
    timeout=120,
)

# ---------------------------------------------------------------------------
# 文件扫描
# ---------------------------------------------------------------------------
SOURCE_EXTENSIONS: set[str] = {".cpp", ".h", ".hpp", ".cc", ".pro", ".ui"}

CXX_EXTENSIONS: set[str] = {".cpp", ".h", ".hpp", ".cc"}
QT_SPECIAL_EXTENSIONS: set[str] = {".pro", ".ui"}

# ---------------------------------------------------------------------------
# 规则文件路径
#
# 优先使用环境变量 CODE_REVIEW_RULES_DIR；否则使用项目根目录下的 rules/；
# 若都不存在则回退到 code_checker/rules/（便于独立发布目录不依赖上级目录）。
# 机器相关的绝对路径不得硬编码。
# ---------------------------------------------------------------------------
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_PACKAGE_ROOT = os.path.dirname(os.path.abspath(__file__))


def _resolve_rules_dir() -> str:
    env_dir = os.environ.get("CODE_REVIEW_RULES_DIR", "").strip()
    if env_dir:
        return os.path.abspath(env_dir)
    root_dir = os.path.join(PROJECT_ROOT, "rules")
    if os.path.isdir(root_dir):
        return root_dir
    return os.path.join(_PACKAGE_ROOT, "rules")


RULES_DIR = _resolve_rules_dir()
CPP_RULES_FILE = os.path.join(RULES_DIR, "C++代码规范.md")
QT_RULES_FILE = os.path.join(RULES_DIR, "QT代码开发规范.md")
SQLITE_RULES_FILE = os.path.join(RULES_DIR, "SQLite加密.md")

# ---------------------------------------------------------------------------
# Qt 标记正则 — 用于判断文件是否包含 Qt 代码
# ---------------------------------------------------------------------------
QT_MARKERS = re.compile(
    r"Q_OBJECT|#include\s*<Q\w+>|:\s*(public|private|protected)\s+Q\w+|"
    r"\bsignals\s*:|\b(public|private|protected)\s+slots\s*:"
)

# ---------------------------------------------------------------------------
# SQLite 标记正则 — 用于判断文件是否涉及 SQLite
# ---------------------------------------------------------------------------
SQLITE_MARKERS = re.compile(
    r'#include\s*<sqlite3\.h>|sqlite3_|PRAGMA\s+\w|'
    r"INSERT\s+INTO|DELETE\s+FROM|UPDATE\s+\w+\s+SET|SELECT\s+.*\s+FROM|"
    r'\.db"|\.sqlite"|QSqlDatabase|QSqlQuery'
)

# ---------------------------------------------------------------------------
# Git conventional commit 相关
# ---------------------------------------------------------------------------
VALID_COMMIT_TYPES: set[str] = {
    "feat", "fix", "docs", "style", "refactor", "perf",
    "test", "chore", "build", "ci", "revert",
}

COMMIT_MESSAGE_RE = re.compile(r"^(\w+)(?:\(([^)]*)\))?: (.+)$")

# ---------------------------------------------------------------------------
# 严重度排序权重（越小越严重）
# ---------------------------------------------------------------------------
SEVERITY_ORDER: dict[str, int] = {"critical": 0, "warning": 1, "suggestion": 2}

# ---------------------------------------------------------------------------
# 自我审查迭代上限
# ---------------------------------------------------------------------------
MAX_FIX_ITERATIONS: int = 3

# ---------------------------------------------------------------------------
# 知识缓存 — 审查标准 & 修复知识持久化
# ---------------------------------------------------------------------------
CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".cache")
MAX_CACHE_ATTEMPTS: int = 5   # 每条违规缓存最多保留的 fix→critique 尝试记录数
# fix_agent: 每条违规独立处理，全部并行（无 chunk，无复杂度分拣）
# 取消 chunk 的原因：flash 模型在 chunk 内会将第一条违规的修复方案作为"锚点"，
# 导致后续违规复用同一模板（跨 idx 复用），修复正确率急剧下降。
# 一条违规一次调用 = 零交叉污染 + 全并行 = 端到端时延 = max(单条耗时)。
MAX_CONCURRENCY: int = 20  # 全局 LLM 并发上限（过高会触发 DeepSeek 503）


def is_complex_fix_plan(plan: dict) -> bool:
    """判断修复方案是否为复杂跨文件 PatchSet。"""
    if plan is None:
        return False
    changes = plan.get("changes")
    if changes and isinstance(changes, list) and len(changes) > 0:
        # 涉及多个文件或多次修改
        files = set(ch.get("file", "") for ch in changes if ch.get("file"))
        if len(files) > 1 or len(changes) > 1:
            return True
    return False


# ---------------------------------------------------------------------------
# 基础设施类违规 — 需人工处理，fix agent 不参与
# ---------------------------------------------------------------------------
# 这些规则的修复需要环境变更（安装软件、配置 PATH、系统设置等），
# 不是代码编辑工具能解决的。匹配时直接标记为"需人工处理"跳过。
INFRA_RULES: set[str] = {
    "Git 环境可用性",
    # 以下为 git agent 可能产出的规则名，均在 fix_agent 入口被 severity="info" 兜底
    "Git 环境检查",
    "Git 提交格式",
    "Git 提交类型",
    "Git 标题长度",
}

# ---------------------------------------------------------------------------
# 规则加载系统 — 阶段裁剪（L1）
# ---------------------------------------------------------------------------
# 键: domain, 值: {phase: [要排除的章节标题前缀]}
# 章节标题以 "## N." 或 "## N、" 或 "# " 开头
RULES_SECTION_FILTERS: dict[str, dict[str, list[str]]] = {
    "cpp": {
        "checker_exclude": [
            "## 9.",
            "## 11.",
            "## 12.",
        ],
    },
    "qt": {
        "checker_exclude": [
            "## 六、",
        ],
    },
    "sqlite": {
        "checker_exclude": [
            "# 验证方案",
        ],
    },
}


def filter_rules_by_phase(rules_text: str, domain: str, phase: str) -> str:
    """按阶段裁剪规范文本，去掉非相关章节。

    按 ## 或 # 标题切分章节，排除匹配 CHECKER_EXCLUDE 的章节。
    phase="fix" / "review" 不在此层处理——它们走 L2 精确注入路径。

    Args:
        rules_text: 规范文件全文。
        domain: cpp / qt / sqlite。
        phase: checker / fix / review。

    Returns:
        裁剪后的规范文本。
    """
    import re

    if phase not in ("checker",):
        # fix / review 走 L2 精确注入，L1 不裁剪，但正常不应被调用
        return rules_text

    filters = RULES_SECTION_FILTERS.get(domain, {})
    exclude_prefixes = filters.get("checker_exclude", [])
    if not exclude_prefixes:
        return rules_text

    # ── 按章节标题切分 ──
    # 匹配 "## N." / "## N、" / "## 一、" / "# 文本" 开头的行作为章节边界
    # 支持阿拉伯数字（1, 2, 10）和中文数字（一, 二, ..., 十）
    # 也支持无编号的 # 标题（如 "# 验证方案"）— 此时用整行作为 header
    section_pattern = re.compile(
        r"^(#{1,2}\s+(?:\d+(?:[\.\、]\d+)*[\.\、]?"
        r"|[一二三四五六七八九十]+[、\.])"
        r"|#\s+\S.*)",
        re.MULTILINE,
    )
    splits = list(section_pattern.finditer(rules_text))

    if not splits:
        # 无编号章节标题（如 SQLite 规范）→ 简单字符串匹配去除
        for prefix in exclude_prefixes:
            import re as _re
            # 从匹配位置截断到文件末尾
            idx = rules_text.find(prefix)
            if idx >= 0:
                rules_text = rules_text[:idx].rstrip()
                print(f"  [规则加载] {domain}/{phase}: 去除章节 '{prefix}'")
                break
        return rules_text

    # 构建章节列表: [(start, end, header_text)]
    sections = []
    for i, m in enumerate(splits):
        start = m.start()
        end = splits[i + 1].start() if i + 1 < len(splits) else len(rules_text)
        header = m.group(1).strip()
        sections.append((start, end, header))

    # 如果标题前有前言，也保留
    if splits[0].start() > 0:
        preamble = rules_text[:splits[0].start()].strip()
    else:
        preamble = ""

    # ── 过滤：排除匹配 exclude_prefixes 的章节 ──
    kept: list[str] = []
    if preamble:
        kept.append(preamble)

    removed: list[str] = []
    for start, end, header in sections:
        excluded = False
        for prefix in exclude_prefixes:
            if header.startswith(prefix) or prefix in header:
                excluded = True
                break
        if excluded:
            removed.append(header)
            continue
        kept.append(rules_text[start:end])

    if removed:
        print(f"  [规则加载] {domain}/{phase}: 去除 {len(removed)} 个章节: {removed}")

    return "\n\n".join(kept)


# ---------------------------------------------------------------------------
# GitHub MCP 集成
# ---------------------------------------------------------------------------
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN") or os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN", "")

# GitHub URL 解析 — 区分本地路径和远程仓库
GITHUB_URL_RE = re.compile(
    r"(?:https?://)?github\.com/([^/]+)/([^/]+?)(?:\.git)?(?:/tree/([^/]+))?/?$"
)


def is_github_url(path: str) -> bool:
    """判断传入的路径是否为 GitHub URL（而非本地目录）。

    支持:
      - https://github.com/owner/repo
      - github.com/owner/repo
      - owner/repo（简写，当本地不存在该路径时视为 GitHub 仓库）
    """
    if not path:
        return False
    # 完整 URL
    if GITHUB_URL_RE.match(path.strip().rstrip("/")):
        return True
    # 简写 owner/repo（仅当本地不存在时）
    # 排除相对路径（以 . 开头）和 Windows 盘符路径
    stripped = path.strip()
    if re.match(r"^[^/]+/[^/]+$", stripped) and not stripped.startswith("."):
        return not os.path.exists(path) and not os.path.isdir(path)
    return False

# ---------------------------------------------------------------------------
# 追踪输出目录
# ---------------------------------------------------------------------------
TRACES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "traces")

# ---------------------------------------------------------------------------
# 输出报告路径
# ---------------------------------------------------------------------------
OUTPUT_REPORT_FILENAME: str = "compliance_report.md"
