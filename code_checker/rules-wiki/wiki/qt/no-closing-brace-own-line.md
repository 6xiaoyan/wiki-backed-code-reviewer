---
domain: qt
rule_id: qt-no-closing-brace-own-line
title: 语句右括号不单独换行
priority: main
source_file: rules/QT代码开发规范.md
source_section: "§2.9"
status: active
check_method: regex
deterministic_check: true
checkability: deterministic
conflicts_with: []
overrides: []
related_pages:
  - [[qt-braces-knr]]
---

# 语句右括号不单独换行

## 规则条款

代码中的**右大括号 `}` 不应单独构成一行无其他内容的行**。`}` 应该与其后续内容合理组合，避免不必要的空行或单独存在的 `}`。具体规则：
- `if-else` 链中：`} else {` 和 `} else if (...) {` 写在同一行- `try-catch` 中：`} catch (...) {` 写在同一行- `do-while` 中：`} while (...);` 写在同一行- 区分逻辑段落时 `}` 允许独占一行且后续直接写下行代码（这是正常的段落分隔）

此规则的意图是避免在一行中仅放置一个 `}` 而没有伴随任何其他语义信息，特别是当它可以和前后的控制流关键字自然衔接时。
## 正确示例

```cpp
// if-else 链：} else 同行
if (x > 0) {
    doPositive();
} else if (x < 0) {
    doNegative();
} else {
    doZero();
}

// try-catch：} catch 同行
try {
    riskyOperation();
} catch (const std::runtime_error &e) {
    handleError(e);
} catch (const std::exception &e) {
    handleGenericError(e);
}

// do-while：} while 同行
do {
    attemptRetry();
} while (shouldRetry);

// 正常段落结束：} 允许独占一行void MyClass::cleanup()
{
    if (m_resource) {
        m_resource->release();
    }
    // } 独占一行是 OK 的 —— 这是控制流的自然结束
    m_resource = nullptr;
}
```

## 错误示例

```cpp
// 错误：} 和 else 单独各占一行if (x > 0) {
    doPositive();
}
else {                        // 错误：else 应和 } 在同一行    doNegative();
}

// 错误：} 和 catch 分开
try {
    riskyOperation();
}
catch (const std::exception &e) {  // 错误：catch 应和 } 在同一行    handleError(e);
}

// 错误：do-while 的 } 和 while 分开
do {
    attemptRetry();
}
while (shouldRetry);          // 错误：while 应和 } 在同一行```

## 检查方法
1. 搜索独立的 `}` 行后紧跟 `else`、`catch`、`while`（do-while 中的 `while`）的行模式。2. 验证 `}` 后面是否应该紧跟关键字但被分开了。
正则表达式：
- `\}\s*\n\s*\belse\b` → `}` 单独一行后有 `else`
- `\}\s*\n\s*\bcatch\b` → `}` 单独一行后有 `catch`
- `\}\s*\n\s*\bwhile\b` → `}` 单独一行后有 `while`（需排除独立 while 循环）
## 修复指南

1. 将 `else`、`catch`、`while` 移动到前一行 `}` 的后面。2. 在 `}` 和后续关键字之间保留一个空格：
   ```cpp
   // 修改前：   }
   else {
   
   // 修改后：   } else {
   ```
3. 使用 clang-format：`BreakBeforeBraces: Attach` 通常会自动处理此问题。
## 审查清单

- [ ] `} else {` 和 `} else if (...) {` 在同一行- [ ] `} catch (...) {` 在同一行- [ ] `} while (...);`（do-while）在同一行- [ ] 逻辑段落结束时 `}` 允许独占一行
## 关联页面

- [[qt-braces-knr]] —— 控制流 K&R 风格
