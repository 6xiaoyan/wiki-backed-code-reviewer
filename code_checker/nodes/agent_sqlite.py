"""
agent_sqlite — SQLite 安全审查 Agent。

包含 2 个 SQLite 域正则工具 + LLM 安全审查。
只检查含 SQLite 标记的文件（sqlite3_ / PRAGMA / QSqlDatabase 等）。
每个文件独立调 LLM，全量并行（不切 chunk）。
使用 deepseek-v4-flash。
"""

import os
from concurrent.futures import as_completed

from code_checker.rate_limiter import RateLimitedExecutor

from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent

from code_checker.state import AgentState
from code_checker.config import llm, CXX_EXTENSIONS, SQLITE_MARKERS, MAX_CONCURRENCY
from code_checker.context_compaction import CompactionHookFactory
from code_checker.utils import invoke_with_retry, serialize_messages
from code_checker.skill_loader import load_live_skills
from code_checker.tracer import get_current_tracer
from code_checker.tools import (
    set_state, get_violations_buffer,
    read_file, list_files, report_violation,
    search_in_file, get_rules_text,
    set_agent_name, get_wiki_page,
    # ── SQLite 域正则工具（2 个）──
    check_sqlite_pragma_key,
    check_sqlite_kdf,
)

SQLITE_SYSTEM_PROMPT = """你是 SQLite 安全审查专家。对分配给你的数据库相关文件执行 LLM 语义审查。

=== SQLite 安全规则（5 条全量，内嵌系统提示词）===
来源: LLM Wiki sqlite 域。以下为完整的规则条款，无需额外查阅。

1. **sqlite/must-use-sqlcipher** — 必须使用 SQLCipher 加密 | regex
   条款: 所有 SQLite 数据库连接必须使用 SQLCipher 加密变体。禁止使用未加密的 SQLite。连接建立后必须立即执行 PRAGMA key 设置密钥。

2. **sqlite/pragma-key** — PRAGMA key 设置密钥 | regex
   条款: 数据库连接后必须立即执行 PRAGMA key = '...'，设置加密密钥。密钥不得硬编码在源码中，必须从安全的外部来源获取。

3. **sqlite/kdf-iterations** — KDF 迭代数 ≥ 256000 | regex
   条款: 必须执行 PRAGMA cipher_default_kdf_iter = 256000，确保 KDF 迭代次数不低于 256000，以抵御暴力破解。

4. **sqlite/no-manual-salt** — 禁止手动管理 salt/PBKDF2 | regex
   条款: 禁止手动管理 salt 或自实现 PBKDF2 密钥派生——让 SQLCipher 内部自动处理。手动管理容易引入加密弱点。

5. **sqlite/no-self-aes** — 禁止自实现 AES 替代 SQLCipher | regex
   条款: 禁止自实现 AES 加密（如调用 AES_encrypt / EVP_* / QAESEncryption 做数据库加密）替代 SQLCipher。SQLCipher 是唯一的数据库加密方案。

=== 副规则域（补充）===
tencent 域加密安全规则索引：
  tencent/no-hardcoded-key | 禁止硬编码密钥 | crypto
  tencent/secure-wipe-sensitive-data | 安全擦除敏感数据 | crypto
  tencent/no-plaintext-sensitive-data | 禁止明文存储敏感数据 | crypto
  tencent/use-csprng | 使用密码学安全随机数 | crypto
  tencent/no-weak-crypto | 禁止弱加密算法 | crypto
→ 用 get_wiki_page("tencent/<slug>") 直接读取完整条款

=== 架构说明 ===
确定性的 SQLite 检查（PRAGMA key 加密、KDF 迭代数）已由系统确定性检查器预先执行，你不需重复这些检查。

你的任务是 LLM 安全语义审查——查找正则无法检测的安全漏洞。

=== 工作流程 ===
1. 对分配给你的每个文件，先 read_file 判断是否涉及 SQLite（sqlite3_ / PRAGMA / QSqlDatabase / QSqlQuery），不涉及则跳过
2. 对每个 SQLite 文件，执行 LLM 安全审查：

   【LLM 安全审查 — 对照规则逐行检查】
   - SQL 注入：是否参数化（禁止字符串拼接，必须 ? 占位符 + sqlite3_bind_*）
   - 密钥硬编码：密钥是否从外部安全获取
   - 密钥清零：用后是否安全清零
   - SQLCipher：是否使用加密版本（非明文 SQLite）
   - 连接复用：避免重复打开/关闭
   - 检查 password/key/key_vault 等变量名是否暗示密钥泄露

3. 需要补充 tencent 安全规则时，对照上方索引用 get_wiki_page("tencent/<slug>") 查阅
4. 每条违规用 report_violation 记录
5. 全部文件检查完后说明"检查完成"

=== report_violation 关键要求 ===
- rule 字段建议带规则编号，如 "S-01 sqlite/must-use-sqlcipher"
- rule_page: 【必填·Wiki模式】wiki 页面路径，如 "sqlite/must-use-sqlcipher"。
  系统会从此页面确定性提取 rule_clause 原文。
- rule_excerpt: 【必填】从上方规则条款中摘录相关原文（2-3句）。
- SQL 注入和密钥泄露是 critical 级别，优先报告
- 违规的 current 字段必须从文件中精确复制"""

SQLITE_AGENT_TOOLS = [
    read_file, list_files, report_violation, search_in_file, get_rules_text,
    get_wiki_page,
    check_sqlite_pragma_key, check_sqlite_kdf,
]


def _run_single_file(
    file_path: str, file_idx: int, total_files: int,
    compaction_factory: CompactionHookFactory = None,
) -> int:
    """在单个线程中运行一个 subagent，检查单个文件。"""
    set_agent_name(f"sqlite_agent/file{file_idx+1}")
    if compaction_factory:
        compaction_factory.set_chunk(f"{file_idx + 1}/{total_files}")
    skills_text = load_live_skills("sqlite")
    prompt = SQLITE_SYSTEM_PROMPT
    if skills_text:
        prompt = SQLITE_SYSTEM_PROMPT + "\n\n" + skills_text
    agent = create_react_agent(
        model=llm,
        tools=SQLITE_AGENT_TOOLS,
        prompt=prompt,
        pre_model_hook=compaction_factory.hook if compaction_factory else None,
    )

    task_msg = (
        f"审查单个 SQLite 文件（{file_idx + 1}/{total_files}）：\n"
        f"  {file_path}\n\n"
        f"规则条款已内嵌在系统提示词中。"
        f"先 read_file 判断是否涉及 SQLite，是则逐行对照规则审查，不是则跳过。"
        f"需要 tencent 安全规则时对照索引用 get_wiki_page 查阅。"
    )
    result = invoke_with_retry(agent, task_msg, f"sqlite/{file_idx+1}",
                               config={"recursion_limit": 150})
    tracer = get_current_tracer()
    if tracer is not None:
        tracer.record_agent_trace(f"sqlite/file{file_idx+1}",
                                  serialize_messages(result.get("messages", [])))
    return len(result.get("messages", []))


def sqlite_agent(state: AgentState) -> dict:
    """SQLite 安全审查 agent 节点。

    过滤出含 SQLite 标记的文件，每个文件独立调 LLM，全量并行（不切 chunk）。
    端到端时延 = max(单文件耗时)，而非 batch 累加。
    """
    print("  [sqlite_agent] 启动...")

    set_state(state)

    file_list = state.get("file_list") or []
    file_contents = state.get("file_contents") or {}

    # ── 过滤 SQLite 文件 ──
    sqlite_files = [
        fp for fp in file_list
        if os.path.splitext(fp)[1].lower() in CXX_EXTENSIONS
        and SQLITE_MARKERS.search(file_contents.get(fp, ""))
    ]

    if not sqlite_files:
        print("  [sqlite_agent] 无 SQLite 文件，跳过")
        return {"sqlite_violations": []}

    total_files = len(sqlite_files)
    max_workers = min(total_files, MAX_CONCURRENCY)
    print(f"  [sqlite_agent] {total_files} 个 SQLite 文件 → {total_files} 路并行"
          f"（并发上限 {max_workers}）")

    compaction_factory = CompactionHookFactory(
        "sqlite_agent",
        critical_tool_names={"get_rules_text", "report_violation", "get_wiki_page"},
        l4_model=llm,
    )
    failed_count = 0
    with RateLimitedExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(
                _run_single_file, fp, i, total_files, compaction_factory,
            )
            for i, fp in enumerate(sqlite_files)
        ]
        for f in as_completed(futures):
            try:
                f.result()
            except Exception as e:
                failed_count += 1
                print(f"  [sqlite_agent] 文件审查异常: {e}")

    # ── 记录降级 ──
    if failed_count > 0:
        degradation_log = list(state.get("degradation_log") or [])
        degradation_log.append({
            "stage": "sqlite_agent",
            "status": "degraded" if failed_count < total_files else "failed",
            "reason": f"{failed_count}/{total_files} 个文件审查 API 调用失败",
            "impact": f"{failed_count} 个文件未经 LLM 安全审查",
        })
        state["degradation_log"] = degradation_log

    # ── 收集结果 ──
    violations = get_violations_buffer()
    for v in violations:
        v["source"] = "sqlite"
        if not v.get("surrounding"):
            from code_checker.utils import enrich_violation_context
            enrich_violation_context(v, file_contents)

    print(f"  [sqlite_agent] 完成: {len(violations)} 条违规")
    return {"sqlite_violations": violations}
