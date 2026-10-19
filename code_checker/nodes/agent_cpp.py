"""
agent_cpp — C++ 代码规范审查 Agent。

包含 11 个确定性正则工具 + LLM 语义审查。
每个文件独立调 LLM，全量并行（不切 chunk）。
使用 deepseek-v4-flash。
"""

import os
from concurrent.futures import as_completed

from code_checker.rate_limiter import RateLimitedExecutor

from langchain_core.messages import HumanMessage
from langgraph.prebuilt import create_react_agent

from code_checker.state import AgentState
from code_checker.config import llm, CXX_EXTENSIONS, CPP_RULES_FILE, MAX_CONCURRENCY
from code_checker.context_compaction import CompactionHookFactory
from code_checker.utils import invoke_with_retry, serialize_messages
from code_checker.skill_loader import load_live_skills
from code_checker.tracer import get_current_tracer
from code_checker.tools import (
    set_state, get_violations_buffer,
    read_file, list_files, report_violation,
    search_in_file, get_rules_text,
    set_agent_name, get_wiki_page,
    # ── C++ 域正则工具（11 个）──
    check_tab_indentation,
    check_line_width,
    check_header_guard,
    check_using_namespace_in_header,
    check_define_macro,
    check_c_style_array,
    check_throw_spec,
    check_default_lambda_capture,
    check_reinterpret_cast,
    check_virtual_override,
    check_c_variadic,
)

CPP_SYSTEM_PROMPT = f"""你是 C++ 代码规范审查专家。对分配给你的 C++ 文件执行 LLM 语义审查。

=== 核心硬规则（始终生效，不可违反）===
来源: rules/C++代码规范.md §1.1 §1.2 §1.3 §2.3 §7

1. 禁止裸 new/delete — 必须 std::make_unique / std::make_shared
2. 禁止 C 风格类型转换 — 必须 static_cast / dynamic_cast / const_cast
3. 禁止 throw() 异常规范 — 必须 noexcept
4. 禁止默认 Lambda 捕获 [=]/[&] — 必须显式列出捕获变量
5. 禁止 C 风格字符串/数组 — 使用 std::string / std::vector / std::array
6. 禁止 reinterpret_cast
7. 禁止头文件中 using namespace
8. 禁止 #define 常量/函数 — 使用 constexpr / const / 模板
9. 析构函数必须标记 noexcept
10. 类名 PascalCase，函数/变量 camelCase，常量 UPPER_CASE，私有成员 m_ 前缀

=== 架构说明 ===
确定性检查器已预先执行以下检查，你不需要重复它们：
  ✅ Tab 缩进、行宽(≤100)、#define 宏/函数、C 风格数组声明
  ✅ throw() 异常规范、reinterpret_cast、virtual override
  ✅ C 可变参数(...)、lambda [=]/[&] 默认捕获
  ✅ 头文件保护宏格式、头文件 using namespace

确定性检查器未覆盖以下规则——你必须逐文件审查：
  ❗ 命名约定 [C-01~C-06]：类 PascalCase、函数 camelCase、变量 camelCase、
     常量 UPPER_CASE、私有成员 m_ 前缀、命名空间全小写
  ❗ 大括号风格 [C-13]：Allman 风格（左括号独占一行）
  ❗ include 顺序 [C-07]
  ❗ 运算符空格/指针引用紧跟类型 [C-16]
  ❗ C 风格类型转换 (int)x / (char*)ptr —— 必须 static_cast/dynamic_cast
  ❗ 所有标记 llm 的深层语义规则（智能指针、RAII、异常安全、模板、线程安全等）

换言之：你的审查范围 = 命名 + 格式（未自动化部分）+ 语义。
wiki 索引中的 regex 标注仅表示"该规则理论上可正则化"，不等于"已由本系统执行"。

=== C++ 规则索引（共 71 条，来自 LLM Wiki）===
逐行审查代码时，对照此索引判断每段代码涉及哪几条规则。
匹配到规则后调用 get_wiki_page(slug) 获取完整条款（示例+检查方法+修复指南）。
若从索引中无法确定对应规则，尝试用 slug 名直接 get_wiki_page，如 get_wiki_page("cpp/no-unvalidated-input")。

## §1.1 命名约定
  [C-01] cpp/naming-classes | 类/结构/枚举 PascalCase | regex
  [C-02] cpp/naming-functions | 函数/方法 camelCase（动词开头）| regex
  [C-03] cpp/naming-variables | 变量 camelCase ⚠️覆盖Qt下划线 | regex
  [C-04] cpp/naming-constants | 常量 UPPER_CASE | regex
  [C-05] cpp/naming-private-members | 私有成员 m_camelCase | regex
  [C-06] cpp/naming-namespaces | 命名空间全小写点分隔 | regex

## §1.2 头文件规范
  [C-07] cpp/include-order | #include 顺序 | regex
  [C-08] cpp/header-guards | 保护宏 PROJECT_MODULE_FILE_H_ | regex
  [C-09] cpp/forward-declarations | 优先前置声明 | llm
  [C-10] cpp/templates-in-headers | 模板定义在头文件 | regex
  [C-11] cpp/inline-functions | 内联函数谨慎使用 | advisory

## §1.3 代码格式
  [C-12] cpp/indentation | 4空格缩进，禁止Tab | regex
  [C-13] cpp/braces | Allman大括号风格 ⚠️ | regex
  [C-14] cpp/line-width | 行宽≤100字符 ⚠️覆盖Qt | regex
  [C-15] cpp/parameter-alignment | 参数换行对齐 | llm
  [C-16] cpp/operator-spacing | 运算符空格，指针/引用紧跟类型 | regex

## §2.1 智能指针
  [C-17] cpp/unique-ptr | 优先 unique_ptr | llm
  [C-18] cpp/shared-ptr | shared_ptr 仅共享所有权 | llm
  [C-19] cpp/weak-ptr | weak_ptr 打破循环引用 | llm
  [C-20] cpp/make-smart-ptr | make_unique/make_shared | regex
  [C-21] cpp/no-bare-ownership | 禁止裸指针表示所有权 | llm

## §2.2 移动语义
  [C-22] cpp/move-ctors | 移动构造/赋值 | llm
  [C-23] cpp/std-move-usage | std::move 明确标识 | llm
  [C-24] cpp/perfect-forwarding | std::forward 完美转发 | llm
  [C-25] cpp/moved-from-state | 移动后有效但未指定 | llm

## §2.3 Lambda 表达式
  [C-26] cpp/lambda-over-bind | lambda优先于std::bind | llm
  [C-27] cpp/lambda-explicit-capture | 明确捕获，禁止[=]/[&] | regex
  [C-28] cpp/lambda-small-scope | 小函数用lambda | advisory
  [C-29] cpp/lambda-explicit-return | 多行lambda显式返回类型 | regex
  [C-30] cpp/lambda-no-large-in-hotpath | 热路径避免大型lambda | advisory

## §3.1 RAII
  [C-31] cpp/raii-principle | 资源管理基于RAII | llm
  [C-31a] cpp/raii-ctor-dtor | 构造获取析构释放 | llm
  [C-32] cpp/raii-copy-semantics | 禁止拷贝或正确实现 | llm
  [C-33] cpp/raii-std-wrappers | 使用标准库RAII包装器 | llm

## §3.2 内存泄漏
  [C-34] cpp/no-bare-new-delete | 禁止裸new/delete | regex
  [C-35] cpp/use-containers | 用容器替代手动管理 | regex
  [C-36] cpp/memory-tools | 定期使用内存检测工具 | advisory
  [C-37] cpp/weak-ptr-cycles | 循环引用必须用weak_ptr | llm
  [C-38] cpp/no-throw-dtor | 析构函数禁止抛异常 | regex

## §4.1 异常使用
  [C-39] cpp/exception-not-for-flow | 异常不用于控制流 | llm
  [C-40] cpp/exception-throw-by-value | 值抛常引用接 | regex
  [C-41] cpp/exception-inherit-std | 自定义异常继承std::exception | regex
  [C-43] cpp/noexcept-spec | noexcept正确标记 | llm
  [C-44] cpp/no-throw-spec | 禁止throw()，用noexcept | regex

## §4.2 异常安全
  [C-45] cpp/exception-safety-guarantees | 提供三种保证之一 | llm
  [C-45a] cpp/exception-prefer-strong | 优先强保证或不抛 | llm
  [C-46] cpp/exception-raii-safety | RAII确保异常安全 | llm

## §5.1 模板
  [C-47] cpp/template-meaningful-names | 模板参数有意义名称 | llm
  [C-48] cpp/template-over-macros | 模板优先于宏 | llm
  [C-49] cpp/template-constraints | SFINAE/Concepts约束 | llm
  [C-50] cpp/template-no-overuse | 避免过度模板元编程 | advisory

## §5.2 概念（Concepts）
  [C-51] cpp/concepts-cpp20 | C++20必须用概念 | regex
  [C-52] cpp/concepts-naming | 概念描述性名称 | regex
  [C-53] cpp/concepts-std-first | 优先使用标准概念 | llm
  [C-54] cpp/concepts-precise | 精确约束requirements | advisory

## §6.1 线程安全
  [C-55] cpp/thread-safe-marking | 明确标识线程安全性 | advisory
  [C-56] cpp/mutex-shared-data | mutex保护共享数据 | llm
  [C-57] cpp/thread-local | 优先thread_local | llm
  [C-58] cpp/avoid-datarace-deadlock | 避免数据竞争/死锁 | llm
  [C-59] cpp/atomic-lockfree | 原子操作无锁编程 | llm

## §6.2 原子操作与锁
  [C-60] cpp/atomics-vs-locks | 简单用原子，复杂用锁 | llm
  [C-61] cpp/memory-order | 适当内存顺序，默认seq_cst | llm
  [C-62] cpp/lock-guard | 优先lock_guard | regex
  [C-63] cpp/scoped-lock | scoped_lock同时获取多锁 | regex
  [C-64] cpp/no-user-code-under-lock | 持锁不调用用户代码 | llm

## §7 禁止项
  [C-65] cpp/no-macro-constants | 禁止宏常量/函数 | regex
  [C-66] cpp/no-cstyle-strings-arrays | 禁止C风格字符串数组 | regex
  [C-67] cpp/no-varargs | 禁止可变参数(...) | regex
  [C-68] cpp/no-using-namespace-in-header | 头文件禁止using namespace | regex
  [C-69] cpp/no-global-variables | 禁止全局变量 | regex
  [C-70] cpp/no-reinterpret-c-cast | 禁止reinterpret_cast/C风格转换 | regex
  [C-71] cpp/no-unvalidated-input | 禁止未验证输入 | llm

=== 腾讯安全规则索引（49条，副规则 | domain=tencent）===
§1 C/C++使用错误(9) §2 编程习惯(14) §3 多线程(3) §4 加密(5)
§5 文件操作(3) §6 内存(2) §7 数字(6) §8 指针(7)
重点页面: tencent/no-unbounded-string-copy | tencent/safe-process-creation
  tencent/no-alloca-vla | tencent/printf-format-match | tencent/no-user-format-string
  tencent/switch-default | tencent/no-hardcoded-key | tencent/no-stack-address-return
  tencent/thread-safe-variables | tencent/signal-handler-race | tencent/toctou-race
  tencent/no-plaintext-sensitive-data | tencent/use-csprng
  tencent/no-oob-write | tencent/no-int-overflow | tencent/no-div-zero
  tencent/null-after-free | tencent/null-check-before-deref | tencent/no-type-confusion
  tencent/smart-ptr-get-safety
→ 用 get_wiki_page("tencent/<slug>") 直接读取细节

=== Google C++ 对照（10条，⚠️ 全部以公司规则为准，仅供参考）===
  google/naming | ❌蛇形命名→公司camelCase | google/formatting | ❌2空格→公司4空格/80→100字符
  google/headers | ❌前向声明冲突 | google/cpp-features | ❌异常/RTTI禁止→公司允许
  google/scoping | 补充条款 | google/classes | ✅一致+补充
  google/functions | ✅一致+补充 | google/smart-pointers | ✅一致
  google/comments | 补充条款 | google/exceptions-windows | 仅供参考
→ 仅作背景参考，不作为违规判断依据

=== 工作流程（Wiki-First）===
1. 对分配给你的每个 .cpp/.h/.hpp/.cc 文件，逐行审查：
   a. 对照上方规则索引，判断当前代码段可能涉及哪几条规则
   b. 调用 get_wiki_page(slug) 获取该规则的完整条款（含正确/错误示例、检查方法）
   c. 对照 wiki 页面原文判断是否为违规
2. 每条违规用 report_violation 记录
3. 全部文件检查完后说明"检查完成"

【Wikilink 导航约束】
- related 类型链接最多跟随 1 层
- see_also 类型链接禁止在检查阶段跟随
- 同一文件累计读取 wiki 页面 ≤ 5 页（超过则基于已有上下文判断）

【LLM 语义审查重点】
- 命名约定（PascalCase类名, camelCase函数/变量, m_前缀, UPPER_CASE常量）
- 头文件规范（include顺序, 前置声明）
- 智能指针（禁止裸new/delete, std::make_unique/make_shared）
- RAII/异常安全（noexcept, 析构不抛异常）
- 移动语义（std::move）
- 禁止C风格字符串/类型转换
- 代码重复/设计问题

=== report_violation 关键要求 ===
- rule: 建议带 § 章节号，如 "§1.1 命名约定 — 类名应 PascalCase"
- rule_page: 【必填·Wiki模式】wiki 页面路径，如 "cpp/naming-classes"。
  系统会从此页面确定性提取 rule_clause 原文，消除 LLM 摘录偏差。
- rule_section: wiki 页面中的锚点，如 "## 规则条款"
- rule_excerpt: 【必填】从 wiki 页面中摘录与该违规直接相关的条款原文（2-5句，含正确/错误示例）。
  不要自己总结——直接从 get_wiki_page 返回内容中复制粘贴。
  这会被下游 fix_agent 和 review_agent 直接使用。

=== 重要 ===
- 违规的 current 字段必须从文件中精确复制
- 一次只处理一个文件，处理完再换下一个
- 语义审查时如需确认模式，仍可调用正则工具辅助判断"""

CPP_AGENT_TOOLS = [
    read_file, list_files, report_violation, search_in_file, get_rules_text,
    get_wiki_page,
    check_tab_indentation, check_line_width, check_header_guard,
    check_using_namespace_in_header, check_define_macro, check_c_style_array,
    check_throw_spec, check_default_lambda_capture, check_reinterpret_cast,
    check_virtual_override, check_c_variadic,
]


def _run_single_file(
    file_path: str, file_idx: int, total_files: int,
    compaction_factory: CompactionHookFactory = None,
) -> int:
    """在单个线程中运行一个 subagent，检查单个文件。"""
    set_agent_name(f"cpp_agent/file{file_idx+1}")
    if compaction_factory:
        compaction_factory.set_chunk(f"{file_idx + 1}/{total_files}")
    skills_text = load_live_skills("cpp")
    prompt = CPP_SYSTEM_PROMPT
    if skills_text:
        prompt = CPP_SYSTEM_PROMPT + "\n\n" + skills_text
    agent = create_react_agent(
        model=llm,
        tools=CPP_AGENT_TOOLS,
        prompt=prompt,
        pre_model_hook=compaction_factory.hook if compaction_factory else None,
    )

    task_msg = (
        f"审查单个 C++ 文件（{file_idx + 1}/{total_files}）：\n"
        f"  {file_path}\n\n"
        f"只检查这个文件。对照系统提示词中的 Wiki 规则索引逐行审查。"
        f"发现可疑代码时调用 get_wiki_page(\"cpp/<slug>\") 获取完整规则条款。"
    )
    result = invoke_with_retry(agent, task_msg, f"cpp/{file_idx+1}",
                               config={"recursion_limit": 150})
    tracer = get_current_tracer()
    if tracer is not None:
        tracer.record_agent_trace(f"cpp/file{file_idx+1}",
                                  serialize_messages(result.get("messages", [])))
    return len(result.get("messages", []))


def cpp_agent(state: AgentState) -> dict:
    """C++ 规范审查 agent 节点。

    每个文件独立调 LLM，全量并行执行（不切 chunk）。
    端到端时延 = max(单文件耗时)，而非 batch 累加。
    """
    print("  [cpp_agent ] 启动...")

    set_state(state)

    file_list = state.get("file_list") or []
    file_contents = state.get("file_contents") or {}
    cxx_files = [
        fp for fp in file_list
        if os.path.splitext(fp)[1].lower() in CXX_EXTENSIONS
    ]

    if not cxx_files:
        print("  [cpp_agent ] 无 C++ 文件，跳过")
        return {"cpp_violations": []}

    total_files = len(cxx_files)
    max_workers = min(total_files, MAX_CONCURRENCY)
    print(f"  [cpp_agent ] {total_files} 个 C++ 文件 → {total_files} 路并行"
          f"（并发上限 {max_workers}）")

    compaction_factory = CompactionHookFactory(
        "cpp_agent",
        critical_tool_names={"get_rules_text", "report_violation", "get_wiki_page"},
        l4_model=llm,
    )
    failed_count = 0
    with RateLimitedExecutor(max_workers=max_workers) as executor:
        futures = [
            executor.submit(
                _run_single_file, fp, i, total_files, compaction_factory,
            )
            for i, fp in enumerate(cxx_files)
        ]
        for f in as_completed(futures):
            try:
                f.result()
            except Exception as e:
                failed_count += 1
                print(f"  [cpp_agent ] 文件审查异常: {e}")

    # ── 记录降级 ──
    if failed_count > 0:
        degradation_log = list(state.get("degradation_log") or [])
        degradation_log.append({
            "stage": "cpp_agent",
            "status": "degraded" if failed_count < total_files else "failed",
            "reason": f"{failed_count}/{total_files} 个文件审查 API 调用失败",
            "impact": f"{failed_count} 个文件未经 LLM 语义审查",
        })
        state["degradation_log"] = degradation_log

    # ── 收集结果 ──
    violations = get_violations_buffer()
    for v in violations:
        v["source"] = "cpp"
        if not v.get("surrounding"):
            from code_checker.utils import enrich_violation_context
            enrich_violation_context(v, file_contents)

    print(f"  [cpp_agent ] 完成: {len(violations)} 条违规")
    return {"cpp_violations": violations}
