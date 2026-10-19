---
domain: cpp
rule_id: cpp-line-width
title: 行宽限制
priority: main
source_file: rules/C++代码规范.md
source_section: "### 1.3 代码格式"
status: active
check_method: regex
deterministic_check: true
checkability: deterministic
conflicts_with: []
overrides: [qt-line-width]
related_pages:
  - [[cpp-indentation]]
  - [[cpp-braces]]
  - [[cpp-parameter-alignment]]
  - [[cpp-operator-spacing]]
  - [[qt-line-width]]
---

# 行宽限制

## 规则条款

所有 C++ 源代码文件每行最大宽度为 **100 字符**。超过此限制的行必须进行拆分换行。此规则适用于：
- 代码行（包括注释）
- 函数声明和定义
- `#include` 指令（虽然通常不会超限）
- 模板参数列表
- 函数调用参数列表
- 长字符串字面量
- 长的条件表达式
不适用（不检查）的场景：
- 纯注释行中的 URL 等无法拆分的连续字符串（但应尽量避免）
- 通过 `// NOLINT` 显式豁免的行

**跨域覆盖**：Qt 域 `qt-line-width`（120 字符）与本规则冲突。公共 C++ 硬约束 行宽 "100 字符"具有最高优先级，本规则覆盖 Qt 域的行宽放宽。Qt 代码同样受 C++ 硬约束 100 限制，公司规范优先。
## 正确示例

```cpp
// line wrapping for long parameter lists
bool processRequest(
    const std::string& requestId,
    const RequestHeaders& headers,
    const RequestBody& body,
    ResponseWriter& writer);

// long expression wrapped
if (state == ConnectionState::Authenticated
    && user.hasPermission(Permission::Write)
    && !isRateLimited(user.id()))
{
    executeOperation();
}

// long template parameter list wrapped
std::unordered_map<
    std::string,
    std::vector<std::pair<int, std::chrono::system_clock::time_point>>
> timeSeriesData;

// long string literal split across lines
const char* message =
    "This is a very long error message that needs to be split "
    "across multiple lines for readability and to comply with "
    "the 100-character line length limit.";
```

## 错误示例

```cpp
// this line is obviously wider than 100 characters and should have been broken
// into multiple lines to comply with the coding standard
auto result = std::find_if(container.begin(), container.end(),
    [&filter, &maxRetries, &state](const auto& item) {
        return item.isValid() && item.matches(filter)
            && state.retryCount < maxRetries;
    });

// similar issue with a very long conditional that is hard to read
// and exceeds the 100-character limit
if (state == ConnectionState::Authenticated
    && user.hasPermission(Permission::Write)
    && !isRateLimited(user.id())
    && requestQueue.size() < MAX_QUEUE_SIZE)
{
    executeOperation();
}
```

## 检查方法
1. 对每个源代码文件（`.h`、`.hpp`、`.cpp`、`.cc`），逐行计算字符长度。
2. 若行长度 > 100，标记为违规。
3. 注意：行尾的 `\r\n` 或 `\n` 不计入字符数。计算时应排除行结束符。
4. 处理 Tab 字符的特殊情况：
   - Tab 字符先按 `cpp-indentation` 规则标记为违规
   - 若 Tab 存在，为计算行宽，将 Tab 展开为 4 空格后计算
5. 排除机制：
   - 行尾包含 `// NOLINT` 的行 → 豁免
   - 指定豁免模式（如 `.clang-format` 或规则配置文件中预先定义的豁免行）→ 跳过

正则辅助模式（检测超长行）：
```
^.{101,}$
```

此模式匹配所有长度超过 101 字符的行。在应用前需先对 Tab 展开做预处理。
## 修复指南

**换行规则（优先级从高到低）：**

1. **函数声明/定义**：参数列表在逗号后换行，每个参数单独一行，缩进 4 空格或对齐到第一个参数：
   ```cpp
   void longFunction(
       const std::string& param1,
       int param2,
       double param3);
   ```

2. **函数调用**：与声明保持一致的换行风格。
3. **条件表达式**：在逻辑运算符（`&&`、`||`）后换行，运算符放在新行首。
4. **字符串字面量**：利用 C++ 字符串字面量拼接规则：
   ```cpp
   const char* msg = "part one"
                     "part two";
   ```

5. **模板参数**：在逗号后换行，`<` 和 `>` 与模板名在同一行或在各自行。
6. **长注释**：手动断行，确保每行 ≤ 100 字符。

**格式化工具**：使用 `clang-format`（设置 `ColumnLimit: 100`）自动处理大部分情况。
## 审查清单

- [ ] 是否所有行（排除 NOLINT 豁免行）都在 100 字符以内
- [ ] 换行方式是否符合项目风格
- [ ] 字符串拆分后是否正确拼接
- [ ] 条件表达式换行后逻辑是否仍清晰
- [ ] 是否有不应在一行的过长注释

## 关联页面

- [[cpp-indentation]]
- [[cpp-braces]]
- [[cpp-parameter-alignment]]
- [[cpp-operator-spacing]]
