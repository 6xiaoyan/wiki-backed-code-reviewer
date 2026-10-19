---
domain: cpp
rule_id: cpp-forward-declarations
title: 前置声明优先
priority: main
source_file: rules/C++代码规范.md
source_section: "### 1.2 头文件规范"
status: active
check_method: llm
deterministic_check: false
checkability: llm_checkable
conflicts_with: []
overrides: []
related_pages:
  - [[cpp-include-order]]
  - [[cpp-header-guards]]
  - [[cpp-templates-in-headers]]
---

# 前置声明优先

## 规则条款

在头文件中，优先使用前置声明（forward declaration）而非 `#include` 引入其他头文件。前置声明可以减少编译依赖，加快编译速度，降低头文件变更引起的级联重新编译。
适用场景（可以使用前置声明替代 `#include` 的情况）：
- 声明函数参数为某类型的指针或引用
- 声明函数返回值为某类型（按值返回也可以前置声明）。
- 类成员变量为某类型的指针或引用
- 类包含 `std::unique_ptr` 或 `std::shared_ptr` 成员（配合自定义删除器）

不适用场景（必须使用 `#include` 的情况）：
- 继承自某个基类
- 类成员变量为某类型的值对象（非指针/引用）
- 在头文件中调用该类型的方法或访问其成员
- 使用模板类的具体实例化
**注意**：此规则为"优先"建议，非强制性硬约束。判断无法使用前置声明时，允许使用 `#include`。
## 正确示例

```cpp
// Instead of: #include "database/connection_pool.h"
#include <memory>
#include <string>

namespace database {
class ConnectionPool;     // forward declaration is sufficient
class ConnectionConfig;   // forward declaration is sufficient
}

namespace network {

class HttpClient {
public:
    explicit HttpClient(database::ConnectionConfig* config);
    void setPool(std::shared_ptr<database::ConnectionPool> pool);

private:
    database::ConnectionPool* m_pool;              // pointer — forward decl ok
    std::unique_ptr<database::ConnectionConfig> m_config; // unique_ptr — forward decl ok
};

} // namespace network
```

## 错误示例

```cpp
// unnecessary #include in header when forward declaration would suffice
#pragma once

#include "database/connection_pool.h"       // only used as pointer below
#include "database/connection_config.h"     // only used as shared_ptr below

namespace network {

class HttpClient {
public:
    void setPool(std::shared_ptr<database::ConnectionPool> pool);

private:
    database::ConnectionPool* m_pool;
};

} // namespace network
```

## 检查方法
此规则为 LLM 辅助检查（`checkability: llm_checkable`），无法通过纯正则精确判定。检查思路如下：
1. 遍历每个头文件中的 `#include` 指令。
2. 对每个被包含的头文件，判断其定义的符号在当前头文件中的使用方式：
   - 如果仅作为指针、引用或智能指针模板参数出现，标记为可替换为前置声明
   - 如果作为值成员、基类、或直接在头文件中调用其成员，保留 `#include` 是合理的
3. 利用 LLM 分析符号使用上下文，输出可优化项列表。
**正则辅助识别**：可用于初步筛选候选文件，但不能独立完成判定：
- 检测头文件中被引用的类型：`(?:\w+(?:::)?)*(\w+)\s*(?:\*|&|>)`
- 然后交叉比对 `#include` 引入的符号，看是否只以指针/引用形式出现。
## 修复指南

1. 分析头文件中每个 `#include` 的必要性。
2. 对仅以指针/引用形式使用的类型，将 `#include` 替换为前置声明（在命名空间内声明类名）。
3. 将对应的 `#include` 移到 `.cpp` 实现文件中（或者确保 `.cpp` 文件已包含）。
4. 对于 `std::unique_ptr<Foo>` 成员，确保析构函数在 `.cpp` 文件中实现（而非头文件内联默认），否则编译器无法处理不完整类型的 `delete`。
## 审查清单

- [ ] 头文件中是否存在仅用于指针/引用的 #include
- [ ] 被移除的 #include 是否已在对应 .cpp 中补充
- [ ] unique_ptr 成员的析构函数是否已移到 .cpp 中
- [ ] 模板参数类型是否也适用前置声明

## 关联页面

- [[cpp-include-order]]
- [[cpp-header-guards]]
- [[cpp-templates-in-headers]]
- [[cpp-inline-functions]]
- [[cpp-typing-conventions]]
