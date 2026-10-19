---
domain: cpp
rule_id: cpp-braces
title: 大括号风格（Allman）
priority: main
source_file: rules/C++代码规范.md
source_section: "### 1.3 代码格式"
status: active
check_method: regex
deterministic_check: true
checkability: deterministic
related_pages:
  - [[cpp-indentation]]
  - [[cpp-line-width]]
  - [[cpp-parameter-alignment]]
  - [[qt-braces-knr]]
---

# 大括号风格（Allman）
## 规则条款

C++ 代码中的大括号必须使用**Allman 风格**（也称**ANSI 风格**）：左大括号 `{` 独占一行，与前置语句的首字符对齐。右大括号 `}` 同样独占一行，与对应的左大括号对齐。
适用范围（所有使用大括号的代码块）：
- 函数/方法定义
- `if` / `else if` / `else` 语句。
- `for` / `while` / `do...while` 循环
- `switch` 语句。
- `try` / `catch` / `finally` 块
- `class` / `struct` / `union` 定义
- `namespace` 定义

**跨域冲突**：本规则（Allman 风格）与 Qt 的 [[qt-braces-knr]]（K&R 风格）存在冲突。公司规范对大括号风格未做硬性规定（见 C++ 硬约束），属于项目级裁决冲突。在同时遵循 C++ 和 Qt 规范的项目中，需明确选择一种统一风格。
## 正确示例

```cpp
// 函数定义：左大括号独占一行
int calculateTotal(const std::vector<int>& values)
{
    int result = 0;
    for (const auto& v : values)
    {
        result += v;
    }
    return result;
}

// if-else：每个大括号独占一行
if (connection.isActive())
{
    sendHeartbeat();
}
else if (connection.isConnecting())
{
    waitForConnection();
}
else
{
    reconnect();
}

// 类定义
class NetworkManager
{
public:
    NetworkManager();

    void initialize();

private:
    SocketManager m_socketManager;
};

// 命名空间
namespace myproject
{
namespace internal
{

class Helper
{
public:
    void run();
};

} // namespace internal
} // namespace myproject

// switch 语句
switch (state)
{
case State::Idle:
    handleIdle();
    break;
case State::Running:
    handleRunning();
    break;
default:
    handleUnknown();
    break;
}

// try-catch 块
try
{
    riskyOperation();
}
catch (const std::exception& e)
{
    logError(e.what());
}
```

## 错误示例

```cpp
// K&R 风格：左大括号与语句同行（本规则禁止）
if (connection.isActive()) {
    sendHeartbeat();
} else {
    reconnect();
}

// K&R 风格函数：左大括号与函数签名同行（禁止）
int calculateTotal(const std::vector<int>& values) {
    int result = 0;
    return result;
}

// 类使用 K&R 风格：左大括号与类名同行（禁止）
class NetworkManager {
public:
    NetworkManager();
};

// 左大括号在下一行但缩进错误
if (connection.isActive())
    {
    sendHeartbeat();
    }
```

## 检查方法
1. 搜索控制流关键字后的 `{`，正则模式：
   ```
   (if|else|for|while|switch|do|try|catch)\s*\(.*\)\s*\{[^\n]*$
   ```
   若匹配（即 `{` 与关键字在同一行），标记为违规（应使用 Allman 风格）。
2. 搜索函数定义的 `{`，正则模式（简化版）：
   ```
   ^\s*[\w:~]+\s+[\w:*&]+\s*\([^)]*\)\s*(?:const\s*)?(?:noexcept\s*)?(?:override\s*)?(?:final\s*)?\{
   ```
   若 `{` 在同一行而非独占一行，标记为违规。
3. 搜索 class/struct/namespace 的 `{`：
   ```
   (class|struct|namespace)\s+\w+.*\{[^\n]*$
   ```
   若匹配，标记为违规。
4. 验证 `{` 独占一行时，其缩进深度是否与前置关键字一致（非严格检查，仅报告明显的不对齐）。
5. 检测空语句体：
   ```
   \{\s*\}
   ```
   允许，但仍需保持 Allman 风格（`{` 独占一行，`}` 独占一行，或连续的 `{}` 在一行）。
## 修复指南

1. **自动格式化**：使用 `clang-format`（设置 `BreakBeforeBraces: Allman`）或 `astyle`（`--style=allman`）批量转换。
2. **手动修复**：将同一行的 `{` 移到下一行，确保缩进对齐。
   - K&R `if (x) {` → Allman `if (x)\n{`
3. **IDE 设置**：
   - VS Code：C/C++ 扩展设置 `C_Cpp.clang_format_style` 为 `{ BasedOnStyle: Microsoft, BreakBeforeBraces: Allman }`
   - Visual Studio：Tools → Options → Text Editor → C/C++ → Formatting → New Lines → 勾选所有 "Place open brace on new line" 选项
   - Qt Creator：Tools → Options → C++ → Code Style → Edit → 在 "Declarations" / "Statements" 中所有 brace 选项设置为 "On next line"
4. **注意冲突处理**：若项目同时遵循 Qt K&R 规范，需在 `.clang-format` 中针对不同目录设置不同规则，或统一选择一种风格。
## 审查清单

- [ ] 所有控制流语句的 `{` 是否独占一行
- [ ] 函数定义的 `{` 是否独占一行
- [ ] class/struct/namespace 的 `{` 是否独占一行
- [ ] 嵌套大括号缩进是否正确
- [ ] 是否存在 K&R 风格遗漏

## 关联页面

- [[cpp-indentation]]
- [[cpp-line-width]]
- [[cpp-parameter-alignment]]
- [[cpp-operator-spacing]]
