---
domain: cpp
rule_id: cpp-parameter-alignment
title: 参数列表换行对齐
priority: main
source_file: rules/C++代码规范.md
source_section: "### 1.3 代码格式"
status: active
check_method: llm
deterministic_check: false
checkability: llm_checkable
conflicts_with: []
overrides: []
related_pages:
  - [[cpp-line-width]]
  - [[cpp-indentation]]
  - [[cpp-braces]]
  - [[cpp-operator-spacing]]
---

# 参数列表换行对齐

## 规则条款

当函数参数列表或模板参数列表过长需要换行时，必须进行适当的对齐，以保持代码的可读性。具体要求：
- 当参数列表超过行宽限制（100 字符）时，必须换行
- 换行后的参数应在同一缩进层级，推荐比函数名多 4 个空格（即 8 空格缩进），或对齐到第一个参数的起始位置
- 多个参数每行放一个（推荐）或按逻辑分组排列
- 模板参数列表过长时同样需要换行
- 函数调用参数列表换行规则与函数声明保持一致
- 初始化列表和成员初始化列表遵循同样的对齐原则

**注意**：此规则由 LLM 辅助检查（`checkability: llm_checkable`），因为"适当对齐"涉及可读性判断，无法用纯正则做精确的确定性判定。

## 正确示例

```cpp
// each parameter on its own line, 4-space indent relative to function
bool processRequest(
    const std::string& requestId,
    const RequestHeaders& headers,
    int timeoutMs,
    bool useCache);

// aligned to first parameter column
bool sendData(const std::string&  destination,
              const Payload&       payload,
              Priority             priority);

// template parameters wrapped
template <
    typename KeyType,
    typename ValueType,
    typename HashFunc = std::hash<KeyType>,
    typename Allocator = std::allocator<std::pair<const KeyType, ValueType>>
>
class CustomMap {
    // ...
};

// function call with wrapped arguments
auto result = processRequest(
    generatedRequestId,
    requestHeaders,
    defaultTimeout,
    shouldUseCache);

// constructor initializer list
HttpClient::HttpClient(
    const std::string& host,
    int port,
    std::shared_ptr<Logger> logger)
    : m_host(host)
    , m_port(port)
    , m_logger(std::move(logger))
    , m_isConnected(false)
{
}

// multiple parameters logically grouped on one line (when within width limit)
void configureConnection(
    const std::string& host, int port,
    const std::string& username, const std::string& password);
```

## 错误示例

```cpp
// inconsistent indentation — parameters at random depths
bool processRequest(
  const std::string& requestId,
        const RequestHeaders& headers,
    int timeoutMs,
            bool useCache);

// parameters crammed into a single line exceeding width limit
bool processRequest(const std::string& requestId, const RequestHeaders& headers,
    int timeoutMs, bool useCache, const std::string& callbackUrl);

// misaligned template parameters
template <typename KeyType,
    typename ValueType,
typename HashFunc,
        typename Allocator>
class CustomMap {
};

// trailing comma-leading style without visual alignment
void configure(
    const std::string& host
    , int port
    , bool secure);    // comma-first without consistent indent is confusing
```

## 检查方法
此规则为 LLM 辅助检查。检查思路如下：

1. **超长检查**：首先用 `cpp-line-width` 规则检测超过 100 字符的行（确定性检查）。
2. **对齐审查**（LLM 辅助）：对已换行的参数列表，检查：
   - 参数是否在同一缩进层级
   - 后缀逗号是否对齐
   - 参数分组是否合理
   - 是否使用了被禁止的逗号前置风格（项目规范中是允许逗号前置的，但需缩进正确）
3. **风格一致性**：同一个文件（甚至整个项目）内参数对齐风格应一致——要么全部使用缩进 4 空格方式，要么全部对齐到首个参数列。
4. 正则辅助模式（用于发现需要 LLM 审查的候选区域）：
   - 检测跨越多行的函数声明：识别包含 `(` 后有大段内容且在 `)` 前出现换行的函数签名
   - 检测跨越多行的模板参数：`template\s*<[^>]*\n[^>]*>`

## 修复指南

1. **选择对齐风格**（二选一，项目内保持一致）：
   - **缩进风格**：每个参数换行后比函数名多缩进 4 空格
   - **对齐风格**：每个参数换行后对齐到第一个参数的起始位置
2. **参数排列**：
   - 推荐每个参数独占一行
   - 允许逻辑相关的参数共行（如 `host, port`、`username, password`），前提是不超过行宽限制
3. **使用 clang-format 配置**：
   ```yaml
   AlignAfterOpenBracket: Align        # 或 DontAlign
   BinPackParameters: false            # 每个参数一行
   AllowAllParametersOfDeclarationOnNextLine: false
   ```
4. **IDE 帮助**：
   - 大多数 IDE 的自动换行功能可以处理参数对齐
   - 配置 IDE 的代码风格设置与项目规范一致

## 审查清单

- [ ] 超长参数列表是否已换行
- [ ] 换行后参数缩进是否一致
- [ ] 项目内参数对齐风格是否统一
- [ ] 模板参数列表换行是否合理
- [ ] 初始化列表格式是否规范

## 关联页面

- [[cpp-line-width]]
- [[cpp-indentation]]
- [[cpp-braces]]
- [[cpp-operator-spacing]]
- [[cpp-inline-functions]]
