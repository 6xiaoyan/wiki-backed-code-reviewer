---
title: LLM Wiki 索引
description: C++/Qt 代码检查规范 Wiki（全局导航页，含副规则对照）
generated: 2026-07-27
updated: 2026-07-27
total_pages: 199
domains:
  cpp: 72
  qt: 51
  sqlite: 5
  git: 4
  tencent: 49
  qt-wiki: 8
  google: 10
---

# LLM Wiki（代码检查规则知识库）

本 Wiki 将 `rules/` 目录下的 **7 份规范文件**编译为 **199 条独立可检查的规则页面**，每条规则包含条款原文、正确错误示例、检查方法和修复指南，可供人类审查和 LLM Agent 消费。

## 域导入

| 域 | 页面数 | 来源 | 优先级 |
|----|--------|------|--------|
| [C++](#一c-域） | 72 | C++代码规范.md | 主规则 |
| [Qt](#二qt-域） | 51 | QT代码开发规范.md | 主规则 |
| [SQLite](#三sqlite-域） | 5 | SQLite加密.md | 主规则 |
| [Git](#四git-域） | 4 | git规范.md | 主规则 |
| [腾讯安全](#五腾讯安全域） | 49 | Tencent_C++_Security_Guide.md | 副规则 |
| [Qt Wiki](#六qt-wiki-对照） | 8 | Qt_Coding_Style.md | 副规则 |
| [Google C++](#七google-c-对照） | 10 | Google_C++_Style_Guide.md | 副规则 |
| **合计** | **199** | | |

> **冲突裁决原则：** 副规则与主规则冲突时，**以公司主规则为准**。副规则的对照页面中均标注了冲突项和裁决结果。

---

## 一、C++ 域
### §1.1 命名约定

| ID | 页面 | 检查方法|
|----|------|---------|
| C-01 | [[cpp/naming-classes]] | 类/结构/枚举 PascalCase | regex |
| C-02 | [[cpp/naming-functions]] | 函数/方法 camelCase（动词开头） | regex |
| C-03 | [[cpp/naming-variables]] | 变量 camelCase（名称形容词） ⚠️ 覆盖 Qt 下划线| regex |
| C-04 | [[cpp/naming-constants]] | 常量 UPPER_CASE | regex |
| C-05 | [[cpp/naming-private-members]] | 私有成员 m_camelCase | camelCase_ | regex |
| C-06 | [[cpp/naming-namespaces]] | 命名空间全小写点分隔 | regex |

### §1.2 头文件规范
| ID | 页面 | 检查方法|
|----|------|---------|
| C-07 | [[cpp/include-order]] | #include 顺序 | regex |
| C-08 | [[cpp/header-guards]] | 保护宏PROJECT_MODULE_FILE_H_ | regex |
| C-09 | [[cpp/forward-declarations]] | 优先前置声明 | llm |
| C-10 | [[cpp/templates-in-headers]] | 模板定义在头文件。| regex |
| C-11 | [[cpp/inline-functions]] | 内联函数谨慎使用 | advisory |

### §1.3 代码格式

| ID | 页面 | 检查方法|
|----|------|---------|
| C-12 | [[cpp/indentation]]：4 空格缩进，禁止Tab | regex |
| C-13 | [[cpp/braces]] | Allman 大括号风格⚠️ | regex |
| C-14 | [[cpp/line-width]] | 行宽 ≤ 100 字符 ⚠️ 覆盖 Qt 行宽 | regex |
| C-15 | [[cpp/parameter-alignment]] | 参数换行对齐 | llm |
| C-16 | [[cpp/operator-spacing]] | 运算符空格，指针/引用紧跟类型 | regex |

### §2.1 智能指针

| ID | 页面 | 检查方法|
|----|------|---------|
| C-17 | [[cpp/unique-ptr]] | 优先 unique_ptr | llm |
| C-18 | [[cpp/shared-ptr]] | shared_ptr 仅共享所有权 | llm |
| C-19 | [[cpp/weak-ptr]] | weak_ptr 打破循环引用 | llm |
| C-20 | [[cpp/make-smart-ptr]] | make_unique / make_shared | regex |
| C-21 | [[cpp/no-bare-ownership]] | 禁止裸指针表示所有权 | llm |

### §2.2 移动语义

| ID | 页面 | 检查方法|
|----|------|---------|
| C-22 | [[cpp/move-ctors]] | 移动构造赋值| llm |
| C-23 | [[cpp/std-move-usage]] | std::move 明确标识 | llm |
| C-24 | [[cpp/perfect-forwarding]] | std::forward 完美转发 | llm |
| C-25 | [[cpp/moved-from-state]] | 移动后有效但未指南| llm |

### §2.3 Lambda 表达式
| ID | 页面 | 检查方法|
|----|------|---------|
| C-26 | [[cpp/lambda-over-bind]] | lambda 优先于std::bind | llm |
| C-27 | [[cpp/lambda-explicit-capture]] | 明确捕获方式，禁止[=]/[&] | regex |
| C-28 | [[cpp/lambda-small-scope]] | 小函数用 lambda | advisory |
| C-29 | [[cpp/lambda-explicit-return]] | 多行 lambda 显式返回类型 | regex |
| C-30 | [[cpp/lambda-no-large-in-hotpath]] | 热路径避免大型lambda | advisory |

### §3.1 RAII

| ID | 页面 | 检查方法|
|----|------|---------|
| C-31 | [[cpp/raii-principle]] | 资源管理基于 RAII | llm |
| C-31a | [[cpp/raii-ctor-dtor]] | 构造获取析构释放 | llm |
| C-32 | [[cpp/raii-copy-semantics]] | 禁止拷贝或正确实参| llm |
| C-33 | [[cpp/raii-std-wrappers]] | 使用标准库RAII 包装器 | llm |

### §3.2 内存泄漏

| ID | 页面 | 检查方法|
|----|------|---------|
| C-34 | [[cpp/no-bare-new-delete]] | 禁止裸new/delete | regex |
| C-35 | [[cpp/use-containers]] | 用容器替代手动数据| regex |
| C-36 | [[cpp/memory-tools]] | 定期使用内存检测工作| advisory |
| C-37 | [[cpp/weak-ptr-cycles]] | 循环引用必须用weak_ptr | llm |
| C-38 | [[cpp/no-throw-dtor]] | 析构函数禁止抛异常| regex |

### §4.1 异常使用

| ID | 页面 | 检查方法|
|----|------|---------|
| C-39 | [[cpp/exception-not-for-flow]] | 异常不用于控制流 | llm |
| C-40 | [[cpp/exception-throw-by-value]] | 值抛常引用| regex |
| C-41 | [[cpp/exception-inherit-std]] | 自定义异常继承std::exception | regex |
| C-43 | [[cpp/noexcept-spec]] | noexcept 正确标记 | llm |
| C-44 | [[cpp/no-throw-spec]] | 禁止 throw()，用 noexcept | regex |

### §4.2 异常安全

| ID | 页面 | 检查方法|
|----|------|---------|
| C-45 | [[cpp/exception-safety-guarantees]] ：提供三种保证之一 | llm |
| C-45a | [[cpp/exception-prefer-strong]] | 优先强保证或不抛 | llm |
| C-46 | [[cpp/exception-raii-safety]] | RAII 确保异常安全 | llm |

### §5.1 模板

| ID | 页面 | 检查方法|
|----|------|---------|
| C-47 | [[cpp/template-meaningful-names]] | 模板参数有意义名称| llm |
| C-48 | [[cpp/template-over-macros]] | 模板优先于宏 | llm |
| C-49 | [[cpp/template-constraints]] | SFINAE/Concepts 约束 | llm |
| C-50 | [[cpp/template-no-overuse]] | 避免过度模板元编译| advisory |

### §5.2 概念（Concepts）
| ID | 页面 | 检查方法|
|----|------|---------|
| C-51 | [[cpp/concepts-cpp20]] | C++20 必须用概念约定| regex |
| C-52 | [[cpp/concepts-naming]] | 概念描述性名称| regex |
| C-53 | [[cpp/concepts-std-first]] | 优先使用标准概念 | llm |
| C-54 | [[cpp/concepts-precise]] | 精确约束 requirements | advisory |

### §6.1 线程安全

| ID | 页面 | 检查方法|
|----|------|---------|
| C-55 | [[cpp/thread-safe-marking]] | 明确标识线程安全 | advisory |
| C-56 | [[cpp/mutex-shared-data]] | mutex 保护共享数据 | llm |
| C-57 | [[cpp/thread-local]] | 优先 thread_local | llm |
| C-58 | [[cpp/avoid-datarace-deadlock]] | 避免数据竞争/死锁 | llm |
| C-59 | [[cpp/atomic-lockfree]] | 原子操作无锁编程 | llm |

### §6.2 原子操作与锁

| ID | 页面 | 检查方法|
|----|------|---------|
| C-60 | [[cpp/atomics-vs-locks]] | 简单用原子，复杂用锁| llm |
| C-61 | [[cpp/memory-order]] | 适当内存顺序，默认seq_cst | llm |
| C-62 | [[cpp/lock-guard]] | 优先 lock_guard，延迟用 unique_lock | regex |
| C-63 | [[cpp/scoped-lock]] | scoped_lock 同时获取多锁 | regex |
| C-64 | [[cpp/no-user-code-under-lock]] | 持锁不调用用户代码 | llm |

### §7 禁止项
| ID | 页面 | 检查方法|
|----|------|---------|
| C-65 | [[cpp/no-macro-constants]] | 禁止宏常量函数 | regex |
| C-66 | [[cpp/no-cstyle-strings-arrays]] | 禁止 C 风格字符串和数组 | regex |
| C-67 | [[cpp/no-varargs]] | 禁止可变参数（...）| regex |
| C-68 | [[cpp/no-using-namespace-in-header]] | 头文件禁止using namespace | regex |
| C-69 | [[cpp/no-global-variables]] | 禁止全局变量 | regex |
| C-70 | [[cpp/no-reinterpret-c-cast]] | 禁止 reinterpret_cast / C 风格转换 | regex |
| C-71 | [[cpp/no-unvalidated-input]] | 禁止未验证输入| llm |

---

## 二、Qt 域
### §2.1 缩进

| ID | 页面 | 检查方法|
|----|------|---------|
| Q-01a | [[qt/indent-4-spaces]]：4 空格缩进 | regex |
| Q-01b | [[qt/no-tabs]] | 禁止 TAB | regex |

### §2.2 变量声明

| ID | 页面 | 检查方法|
|----|------|---------|
| Q-02 | [[qt/one-var-per-line]] | 每行一个变量| regex |
| Q-03 | [[qt/no-short-names]] | 避免短变量名 | llm |
| Q-04 | [[qt/late-declaration]] | 变量延迟定义 | llm |
| Q-05a | [[qt/variable-camelcase]] | 驼峰命名 | regex |
| Q-05b | [[qt/no-abbreviations]] | 避免缩写 | llm |
| Q-06 | [[qt/class-naming-pascal]] | 类名 PascalCase | regex |

### §2.3 空白字符

| ID | 页面 | 检查方法|
|----|------|---------|
| Q-07 | [[qt/blank-line-grouping]] | 空行分组，禁止连续多态| regex |
| Q-08 | [[qt/keyword-spacing]] | 关键字后空格 | regex |
| Q-09 | [[qt/pointer-ref-spacing]] | 指针/引用紧跟类型 | regex |
| Q-10 | [[qt/binary-op-spacing]] | 二元操作符空格| regex |
| Q-11a | [[qt/no-space-after-cast]] | 转换后不加空格| regex |
| Q-11b | [[qt/no-cstyle-cast]] | 避免 C 风格转换 | regex |

### §2.4 大括号
| ID | 页面 | 检查方法|
|----|------|---------|
| Q-12 | [[qt/braces-knr]] | 控制流K&R 风格 ⚠️ | regex |
| Q-13 | [[qt/braces-function-class]] | 函数/类定义Allman | regex |
| Q-14 | [[qt/braces-single-line]] | 单行为else 可省略大括号 | regex |
| Q-15 | [[qt/braces-multiline-parent]] | 父语句跨行必须大括号 | regex |
| Q-16 | [[qt/braces-ifelse-symmetry]] | if-else 对称大括号| regex |
| Q-17 | [[qt/braces-empty-body]] | 空体用{} | regex |

### §2.5 ~ §2.9

| ID | 页面 | 检查方法|
|----|------|---------|
| Q-18 | [[qt/parentheses-precedence]] | 圆括号明确优先级 | llm |
| Q-19 | [[qt/switch-case-alignment]] | case 与 switch 对齐 | regex |
| Q-20 | [[qt/switch-break]] | case 需 break/return 或注册| regex |
| Q-21 | [[qt/line-width]] | 行宽 ≤ 120 字符 ⚠️ 被C-14 覆盖 | regex |
| Q-22 | [[qt/line-break-style]] | 逗号行尾，操作符行首 | regex |
| Q-23 | [[qt/no-virtual-on-override]] | override 不写 virtual | regex |
| Q-24a | [[qt/readability-over-rules]] | 可读性优先| advisory |
| Q-24b | [[qt/no-closing-brace-own-line]] | 右括号不单独换行 | regex |
| Q-24c | [[qt/minimal-blank-lines]] | 空行简洁原则| advisory |

### §3.1 ~ §3.4 命名

| ID | 页面 | 检查方法|
|----|------|---------|
| Q-25 | [[qt/file-naming]] | 文件名 = 类名全小写| regex |
| Q-26 | [[qt/class-semantic-noun]] | 类名为名词短语| llm |
| Q-27 | [[qt/ui-class-parent-suffix]] | 界面类体现父类| regex |
| Q-28 | [[qt/no-single-q-prefix]] | 禁止单Q 前缀 | regex |
| Q-29a | [[qt/method-verb-phrase]] | 方法名为动词短语 | llm |
| Q-29b | [[qt/getter-no-get]] | getter 不加 get 前缀 | regex |
| Q-30 | [[qt/method-no-classname]] | 方法名不含类型| regex |
| Q-31 | [[qt/signal-no-signal-word]] | 信号名不变signal | regex |
| Q-32 | [[qt/slot-no-slot-word]] | 槽名不含 slot | regex |
| Q-33 | [[qt/on-obj-slot-internal]] | on_obj_signal 仅内存| llm |
| Q-34 | [[qt/var-qclass-lowercase]] | 下划线变量⚠️ 被C-03 覆盖 | advisory |
| Q-35 | [[qt/var-last-word-type]] | 末词为类型| llm |
| Q-36 | [[qt/ui-control-prefix]] | UI 控件缩写前缀 | regex |

### §4.1 ~ §4.4 代码组织

| ID | 页面 | 检查方法|
|----|------|---------|
| Q-37 | [[qt/class-max-lines]] | 超 1000 行评估拆分| advisory |
| Q-38 | [[qt/function-max-lines]] | 函数 2000 行必须拆分| regex |
| Q-39 | [[qt/include-order]] | include 顺序（Qt 变体）| regex |
| Q-40 | [[qt/member-declaration-order]] | 成员声明顺序 | regex |
| Q-40a | [[qt/cpp-function-order]] | .cpp 与 .h 顺序一致 | advisory |
| Q-41 | [[qt/include-no-dot-h]] | Qt 头文件无 .h 后缀 | regex |
| Q-42 | [[qt/parent-child-memory]] | 父类管理子类内存 | llm |
| Q-43 | [[qt/who-new-who-delete]] | 谁new谁delete | llm |
| Q-44 | [[qt/no-boost-smart-ptr]] | 不建议boost 智能指针 | advisory |

---

## 三、SQLite 域
| ID | 页面 | 检查方法|
|----|------|---------|
| S-01 | [[sqlite/must-use-sqlcipher]] | 必须使用 SQLCipher | regex |
| S-02 | [[sqlite/pragma-key]] | PRAGMA key 设置密钥 | regex |
| S-03 | [[sqlite/kdf-iterations]] | KDF 迭代 ≥ 256000 | regex |
| S-04 | [[sqlite/no-manual-salt]] | 禁止手动管理 salt/PBKDF2 | regex |
| S-05 | [[sqlite/no-self-aes]] | 禁止自实现AES 替代 SQLCipher | regex |

---

## 四、Git 域
| ID | 页面 | 检查方法|
|----|------|---------|
| G-01 | [[git/commit-format]] | `<类型>: <描述>` | regex |
| G-02 | [[git/commit-type-enum]] | 类型枚举 11 种 | regex |
| G-03 | [[git/commit-desc-length]]：描述 ≤ 50 字符 | regex |
| G-04 | [[git/commit-desc-style]] | 首字母小写，无句号| regex |

---

---

## 五、腾讯安全域

> 来源：Tencent_C++_Security_Guide.md | 优先级：**副规则**（冲突以公司主规则为准）
> 共 49 条规则，涵盖 8 大类别：C/C++ 使用错误、不推荐的编程习惯、多线程、加密解密、文件操作、内存操作、数字操作、指针操作

| # | 类别 | 页面数 |
|---|------|--------|
| §1 | C/C++ 使用错误 | 9 |
| §2 | 不推荐的编程习惯 | 14 |
| §3 | 多线程 | 3 |
| §4 | 加密解密 | 5 |
| §5 | 文件操作 | 3 |
| §6 | 内存操作 | 2 |
| §7 | 数字操作 | 6 |
| §8 | 指针操作 | 7 |

全部页面：[[tencent/no-unbounded-string-copy]] · [[tencent/safe-process-creation]] · [[tencent/no-alloca-vla]] · [[tencent/printf-format-match]] · [[tencent/no-pointer-leak]] · [[tencent/no-user-format-string]] · [[tencent/delete-array-match]] · [[tencent/implicit-integer-conversion]] · [[tencent/octal-literal-pitfall]] · [[tencent/switch-default]] · [[tencent/no-debug-info-leak]] · [[tencent/no-hardcoded-key]] · [[tencent/no-stack-address-return]] · [[tencent/parallel-array-check]] · [[tencent/decl-defn-match]] · [[tencent/no-copy-paste-duplicate]] · [[tencent/no-self-comparison]] · [[tencent/all-branches-return]] · [[tencent/no-uninitialized-stack]] · [[tencent/no-uninitialized-heap]] · [[tencent/check-alloc-return]] · [[tencent/no-assignment-in-if]] · [[tencent/bitwise-in-boolean]] · [[tencent/thread-safe-variables]] · [[tencent/signal-handler-race]] · [[tencent/toctou-race]] · [[tencent/no-plaintext-sensitive-data]] · [[tencent/secure-wipe-sensitive-data]] · [[tencent/srand-proper-init]] · [[tencent/use-csprng]] · [[tencent/prng-range-not-too-small]] · [[tencent/no-path-traversal]] · [[tencent/no-relative-path-load]] · [[tencent/file-permission-control]] · [[tencent/no-oob-write]] · [[tencent/no-arbitrary-write]] · [[tencent/no-int-overflow]] · [[tencent/no-off-by-one]] · [[tencent/avoid-endian-bug]] · [[tencent/no-div-zero]] · [[tencent/no-signed-unsigned-mismatch]] · [[tencent/check-index-bounds]] · [[tencent/sizeof-pointer-check]] · [[tencent/no-array-compare-zero]] · [[tencent/no-hardcoded-address]] · [[tencent/null-check-before-deref]] · [[tencent/null-after-free]] · [[tencent/no-type-confusion]] · [[tencent/smart-ptr-get-safety]]

---

## 六、Qt Wiki 对照

> 来源：Qt_Coding_Style.md（wiki.qt.io）| 优先级：**副规则**（冲突以公司主规则为准）

| 页面 | 内容 | 与公司规则 |
|------|------|-----------|
| [[qt-wiki/variable-declaration]] | 变量声明 | ✅ 一致 |
| [[qt-wiki/braces]] | 大括号风格 | ⚠️ 单行括号有冲突 |
| [[qt-wiki/parentheses]] | 括号显式分组 | ✅ 一致 |
| [[qt-wiki/switch-style]] | Switch 语句 | ✅ 一致 |
| [[qt-wiki/no-else-after-jump]] | 跳转语句后不加 else | 补充条款 |
| [[qt-wiki/whitespace]] | 空白与缩进 | ⚠️ 行宽冲突（公司 120 vs Qt 100） |
| [[qt-wiki/template-spacing]] | 模板空格 | 补充条款 |
| [[qt-wiki/general-exceptions]] | 通用例外原则 | 仅供参考 |

---

## 七、Google C++ 对照

> 来源：Google_C++_Style_Guide.md | 优先级：**副规则**（冲突以公司主规则为准）
> ⚠️ 命名约定、缩进、行宽等多项全面冲突——**全部以公司规则为准**

| 页面 | 内容 | 与公司规则 |
|------|------|-----------|
| [[google/headers]] | 头文件规范 | ❌ 前向声明冲突 |
| [[google/scoping]] | 作用域 | ❌ 全局变量定义更窄 |
| [[google/classes]] | 类设计 | ✅ 一致 + 补充 |
| [[google/functions]] | 函数规范 | ✅ 一致 + 补充 |
| [[google/smart-pointers]] | 智能指针 | ✅ 一致 |
| [[google/cpp-features]] | C++ 特性 | ❌ 异常、RTTI 冲突 |
| [[google/naming]] | 命名约定 | ❌ **全面冲突**（公司为准） |
| [[google/formatting]] | 代码格式 | ❌ 缩进 2 vs 4，行宽 80 vs 100 |
| [[google/comments]] | 注释规范 | 补充条款 |
| [[google/exceptions-windows]] | Windows 特例 | 仅供参考 |

---

## 跨域关系（Phase 3 裁决）
| # | 关系 | 涉及页面 | 裁决依据 |
|---|------|---------|---------|
| 1 | C++ Allman 大括号 vs Qt 控制流K&R | [[cpp/braces]] ：[[qt/braces-knr]] | 冲突，公司规范未规定，项目级裁决|
| 2 | C++ camelCase 变量 **覆盖** Qt 下划线变量| [[cpp/naming-variables]] ：[[qt/var-qclass-lowercase]] | C++ 硬约束变量 camelCase"最高优先级 |
| 3 | C++ 行宽 100 **覆盖** Qt 行宽 120 | [[cpp/line-width]] ：[[qt/line-width]] | C++ 硬约束行宽 100"最高优先级 |
| 4 | C++ include 顺序 vs Qt include 顺序 | [[cpp/include-order]] ：[[qt/include-order]] | 冲突，公司规范未规定，项目级裁决|

---

## 图例

| 标记 | 含义 |
|------|------|
| regex | 确定性检查找可程序化验证 |
| llm | LLM 可检查找需要语义理解 |
| advisory | 仅供参考据不计入覆盖率 |
| ⚠️ | 存在跨域关系（冲突或覆盖），需 Agent 注意 |
