"""
agent_qt — Qt 代码规范审查 Agent。

包含 3 个 Qt 域正则工具 + LLM 语义审查。
只检查含 Qt 标记的文件（Q_OBJECT / signals / slots 等）。
每个文件独立调 LLM，全量并行（不切 chunk）。
使用 deepseek-v4-flash。
"""

import os
from concurrent.futures import as_completed

from code_checker.rate_limiter import RateLimitedExecutor

from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent

from code_checker.state import AgentState
from code_checker.config import llm, CXX_EXTENSIONS, QT_SPECIAL_EXTENSIONS, QT_MARKERS, MAX_CONCURRENCY
from code_checker.context_compaction import CompactionHookFactory
from code_checker.utils import invoke_with_retry, serialize_messages
from code_checker.skill_loader import load_live_skills
from code_checker.tracer import get_current_tracer
from code_checker.tools import (
    set_state, get_violations_buffer,
    read_file, list_files, report_violation,
    search_in_file, get_rules_text,
    set_agent_name, get_wiki_page,
    # ── Qt 域正则工具（3 个）──
    check_line_width,
    check_qt_include_dot_h,
    check_qt_signal_name,
    check_qt_slot_name,
)

QT_SYSTEM_PROMPT = """你是 Qt 代码规范审查专家。对分配给你的 Qt 文件执行 LLM 语义审查。

=== 核心硬规则（始终生效，不可违反）===
来源: rules/QT代码开发规范.md §2.1 §3.3.2 §3.3.3 §3.4.1 §3.2 §4.3

1. 禁止 Tab 缩进 — 4 个空格
2. Qt 头文件禁止 .h 后缀 — #include <QWidget> 非 <qpushbutton.h>
3. 信号名禁止含 "signal" — dataReady() 非 dataReadySignal()
4. 槽名禁止含 "slot" — onSave() 非 onSaveSlot()
5. UI 控件成员前缀: QLabel→m_lbl, QPushButton→m_btn, QLineEdit→m_edt,
   QGroupBox→m_grb, QSpinBox→m_spn, QCheckBox→m_chb, QComboBox→m_cmb,
   QStackedWidget→m_stk, QTableWidget→m_tblWgt, QListWidget→m_lstWgt,
   QTreeWidget→m_treeWgt, QTextBrowser→m_txb, QScrollArea→m_scrArea,
   QDialog→m_dlg, QToolButton→m_tbtn, QDoubleSpinBox→m_dspn
6. 类名禁止以单个 Q 开头（非 Qt 官方类的自定义类）

=== 架构说明 ===
确定性的 Qt 正则检查（include .h 后缀、信号/槽命名）已由系统确定性检查器预先执行。你不需要重复这些检查。

你的任务是 LLM 语义审查——查找正则无法检测的深层 Qt 问题。

=== Qt 规则索引（共 51 条，来自 LLM Wiki）===
逐行审查代码时，对照此索引判断每段代码涉及哪几条规则。
匹配到规则后调用 get_wiki_page(slug) 获取完整条款（示例+检查方法+修复指南）。
若从索引中无法确定对应规则，尝试用 slug 名直接 get_wiki_page。

## §2.1 缩进
  [Q-01a] qt/indent-4-spaces | 4空格缩进 | regex
  [Q-01b] qt/no-tabs | 禁止TAB | regex

## §2.2 变量声明
  [Q-02] qt/one-var-per-line | 每行一个变量 | regex
  [Q-03] qt/no-short-names | 避免短变量名 | llm
  [Q-04] qt/late-declaration | 变量延迟定义 | llm
  [Q-05a] qt/variable-camelcase | 驼峰命名 | regex
  [Q-05b] qt/no-abbreviations | 避免缩写 | llm
  [Q-06] qt/class-naming-pascal | 类名PascalCase | regex

## §2.3 空白字符
  [Q-07] qt/blank-line-grouping | 空行分组，禁止连续多空行 | regex
  [Q-08] qt/keyword-spacing | 关键字后空格 | regex
  [Q-09] qt/pointer-ref-spacing | 指针/引用紧跟类型 | regex
  [Q-10] qt/binary-op-spacing | 二元操作符空格 | regex
  [Q-11a] qt/no-space-after-cast | 转换后不加空格 | regex
  [Q-11b] qt/no-cstyle-cast | 避免C风格转换 | regex

## §2.4 大括号
  [Q-12] qt/braces-knr | 控制流K&R风格 ⚠️与C++ Allman冲突 | regex
  [Q-13] qt/braces-function-class | 函数/类定义Allman | regex
  [Q-14] qt/braces-single-line | 单行else可省略大括号 | regex
  [Q-15] qt/braces-multiline-parent | 父语句跨行必须大括号 | regex
  [Q-16] qt/braces-ifelse-symmetry | if-else对称大括号 | regex
  [Q-17] qt/braces-empty-body | 空体用{} | regex

## §2.5 ~ §2.9 杂项
  [Q-18] qt/parentheses-precedence | 圆括号明确优先级 | llm
  [Q-19] qt/switch-case-alignment | case与switch对齐 | regex
  [Q-20] qt/switch-break | case需break/return或注释 | regex
  [Q-21] qt/line-width | 行宽≤120字符 ⚠️被C++100覆盖 | regex
  [Q-22] qt/line-break-style | 逗号行尾，操作符行首 | regex
  [Q-23] qt/no-virtual-on-override | override不写virtual | regex
  [Q-24a] qt/readability-over-rules | 可读性优先 | advisory
  [Q-24b] qt/no-closing-brace-own-line | 右括号不单独换行 | regex
  [Q-24c] qt/minimal-blank-lines | 空行简洁原则 | advisory

## §3.1 ~ §3.4 命名
  [Q-25] qt/file-naming | 文件名=类名全小写 | regex
  [Q-26] qt/class-semantic-noun | 类名为名词短语 | llm
  [Q-27] qt/ui-class-parent-suffix | 界面类体现父类 | regex
  [Q-28] qt/no-single-q-prefix | 禁止单Q前缀 | regex
  [Q-29a] qt/method-verb-phrase | 方法名为动词短语 | llm
  [Q-29b] qt/getter-no-get | getter不加get前缀 | regex
  [Q-30] qt/method-no-classname | 方法名不含类名 | regex
  [Q-31] qt/signal-no-signal-word | 信号名不含signal | regex
  [Q-32] qt/slot-no-slot-word | 槽名不含slot | regex
  [Q-33] qt/on-obj-slot-internal | on_obj_signal仅内部使用 | llm
  [Q-34] qt/var-qclass-lowercase | 下划线变量 ⚠️被C++覆盖 | advisory
  [Q-35] qt/var-last-word-type | 末词为类型 | llm
  [Q-36] qt/ui-control-prefix | UI控件缩写前缀 | regex

## §4.1 ~ §4.4 代码组织
  [Q-37] qt/class-max-lines | 超1000行评估拆分 | advisory
  [Q-38] qt/function-max-lines | 函数2000行必须拆分 | regex
  [Q-39] qt/include-order | include顺序（Qt变体）| regex
  [Q-40] qt/member-declaration-order | 成员声明顺序 | regex
  [Q-40a] qt/cpp-function-order | .cpp与.h顺序一致 | advisory
  [Q-41] qt/include-no-dot-h | Qt头文件无.h后缀 | regex
  [Q-42] qt/parent-child-memory | 父类管理子类内存 | llm
  [Q-43] qt/who-new-who-delete | 谁new谁delete | llm
  [Q-44] qt/no-boost-smart-ptr | 不建议boost智能指针 | advisory

=== Qt Wiki 对照（8条 | domain=qt-wiki，冲突以公司规则为准）===
  qt-wiki/variable-declaration | ✅一致 | qt-wiki/braces | ⚠️单行括号冲突
  qt-wiki/parentheses | ✅一致 | qt-wiki/switch-style | ✅一致
  qt-wiki/no-else-after-jump | 补充条款 | qt-wiki/whitespace | ⚠️行宽冲突
  qt-wiki/template-spacing | 补充条款 | qt-wiki/general-exceptions | 仅供参考
→ 用 get_wiki_page("qt-wiki/<slug>") 查阅对照细节

=== 工作流程（Wiki-First）===
1. 对分配给你的每个文件，先 read_file 判断是否含 Qt 代码（Q_OBJECT / signals / slots / QWidget 等），非 Qt 文件跳过
2. 对每个 Qt 文件，逐行审查：
   a. 对照上方规则索引，判断代码涉及哪几条规则
   b. 调用 get_wiki_page(slug) 获取完整条款（含正确/错误示例、检查方法）
   c. 对照 wiki 页面原文判断是否为违规
   d. 若索引中无法确定，尝试用 slug 名直接 get_wiki_page
3. 每条违规用 report_violation 记录
4. 全部文件检查完后说明"检查完成"

【Wikilink 导航约束】
- related 类型链接最多跟随 1 层 | see_also 禁止在检查阶段跟随
- 同一文件累计读取 wiki 页面 ≤ 5 页

【LLM 语义审查重点】
- 文件命名规范（类名小写转文件名，无下划线）
- 类名命名（禁用单个Q开头）
- 控件成员前缀（m_lbl, m_btn, m_edt 等）
- include 顺序（系统→第三方→项目）
- 信号/槽声明风格
- Qt 特定安全模式

=== report_violation 关键要求 ===
- rule: 建议带 § 章节号，如 "§3.4.1 UI 控件类名缩写表"
- rule_page: 【必填·Wiki模式】wiki 页面路径，如 "qt/braces-knr"、"qt/ui-control-prefix"
  系统会从此页面确定性提取 rule_clause 原文，消除 LLM 摘录偏差。
- rule_section: wiki 页面中的锚点，如 "## 规则条款"
- rule_excerpt: 【必填】从 wiki 页面中摘录条款原文（2-5句，含正确/错误示例）。
  不要自己总结——直接从 get_wiki_page 返回内容中复制粘贴。

=== 重要 ===
- 违规的 current 字段必须从文件中精确复制
- 一次只处理一个文件
- 需要确认模式时仍可调用正则工具辅助判断"""

QT_AGENT_TOOLS = [
    read_file, list_files, report_violation, search_in_file, get_rules_text,
    get_wiki_page,
    check_line_width, check_qt_include_dot_h,
    check_qt_signal_name, check_qt_slot_name,
]


def _run_single_file(
    file_path: str, file_idx: int, total_files: int,
    compaction_factory: CompactionHookFactory = None,
) -> int:
    """在单个线程中运行一个 subagent，检查单个文件。"""
    set_agent_name(f"qt_agent/file{file_idx+1}")
    if compaction_factory:
        compaction_factory.set_chunk(f"{file_idx + 1}/{total_files}")
    skills_text = load_live_skills("qt")
    prompt = QT_SYSTEM_PROMPT
    if skills_text:
        prompt = QT_SYSTEM_PROMPT + "\n\n" + skills_text
    agent = create_react_agent(
        model=llm,
        tools=QT_AGENT_TOOLS,
        prompt=prompt,
        pre_model_hook=compaction_factory.hook if compaction_factory else None,
    )

    task_msg = (
        f"审查单个 Qt 文件（{file_idx + 1}/{total_files}）：\n"
        f"  {file_path}\n\n"
        f"先 read_file 判断是否含 Qt 代码，非 Qt 文件跳过。"
        f"是 Qt 文件则对照系统提示词中的 Wiki 规则索引逐行审查。"
        f"发现可疑代码时调用 get_wiki_page(\"qt/<slug>\") 获取完整规则条款。"
    )
    result = invoke_with_retry(agent, task_msg, f"qt/{file_idx+1}",
                               config={"recursion_limit": 150})
    tracer = get_current_tracer()
    if tracer is not None:
        tracer.record_agent_trace(f"qt/file{file_idx+1}",
                                  serialize_messages(result.get("messages", [])))
    return len(result.get("messages", []))


def qt_agent(state: AgentState) -> dict:
    """Qt 规范审查 agent 节点。

    过滤出含 Qt 标记的文件，每个文件独立调 LLM，全量并行（不切 chunk）。
    端到端时延 = max(单文件耗时)，而非 batch 累加。
    """
    print("  [qt_agent  ] 启动...")

    set_state(state)

    file_list = state.get("file_list") or []
    file_contents = state.get("file_contents") or {}

    # ── 过滤 Qt 文件 ──
    qt_files = []
    for fp in file_list:
        ext = os.path.splitext(fp)[1].lower()
        if ext in QT_SPECIAL_EXTENSIONS:
            qt_files.append(fp)
        elif ext in CXX_EXTENSIONS:
            content = file_contents.get(fp, "")
            if QT_MARKERS.search(content):
                qt_files.append(fp)

    if not qt_files:
        print("  [qt_agent  ] 无 Qt 文件，跳过")
        return {"qt_violations": []}

    total_files = len(qt_files)
    max_workers = min(total_files, MAX_CONCURRENCY)
    print(f"  [qt_agent  ] {total_files} 个 Qt 文件 → {total_files} 路并行"
          f"（并发上限 {max_workers}）")

    compaction_factory = CompactionHookFactory(
        "qt_agent",
        critical_tool_names={"get_rules_text", "report_violation", "get_wiki_page"},
        l4_model=llm,
    )
    failed_count = 0
    with RateLimitedExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(
                _run_single_file, fp, i, total_files, compaction_factory,
            )
            for i, fp in enumerate(qt_files)
        ]
        for f in as_completed(futures):
            try:
                f.result()
            except Exception as e:
                failed_count += 1
                print(f"  [qt_agent  ] 文件审查异常: {e}")

    # ── 记录降级 ──
    if failed_count > 0:
        degradation_log = list(state.get("degradation_log") or [])
        degradation_log.append({
            "stage": "qt_agent",
            "status": "degraded" if failed_count < total_files else "failed",
            "reason": f"{failed_count}/{total_files} 个文件审查 API 调用失败",
            "impact": f"{failed_count} 个文件未经 LLM 语义审查",
        })
        state["degradation_log"] = degradation_log

    # ── 收集结果 ──
    violations = get_violations_buffer()
    for v in violations:
        v["source"] = "qt"
        if not v.get("surrounding"):
            from code_checker.utils import enrich_violation_context
            enrich_violation_context(v, file_contents)

    print(f"  [qt_agent  ] 完成: {len(violations)} 条违规")
    return {"qt_violations": violations}
