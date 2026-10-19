---
domain: qt
rule_id: qt-braces-knr
title: 控制流左大括号与语句同行（K&R 风格）
priority: main
source_file: rules/QT代码开发规则.md
source_section: "§2.4"
status: active
check_method: regex
deterministic_check: true
checkability: deterministic
related_pages:
  - [[qt-braces-function-class]]
  - [[qt-braces-single-line]]
  - [[cpp-braces]]
---

# 控制流左大括号与语句同行（K&R 风格）

## 规则条款

所有控制流语句（`if`、`else`、`for`、`while`、`do`、`switch`、`try`、`catch`）的**左大括号 `{` 必须与语句头部在同一行**，这是 K&R（Kernighan & Ritchie）风格。右大括号 `}` 单独占一行（除非后跟 `else` 或 `catch`）。这与函数/类定义的 Allman 风格形成对比（见 [[qt-braces-function-class]]）。

**跨域说明**：C++ 规范 [[cpp-braces]] 要求所有大括号使用 Allman 风格（`{` 独占一行），与本规则冲突。公司规范对大括号风格未做硬性规定，属于项目级裁决。在同时遵循 C++ 和 Qt 规范的项目中，建议在 `.clang-format` 中统一配置一种风格。
## 正确示例

```cpp
if (x > 0) {
    doSomething();
}

for (int i = 0; i < count; ++i) {
    process(i);
}

while (m_isRunning) {
    eventLoop();
}

do {
    retry();
} while (shouldRetry);

switch (value) {
case 1:
    handleOne();
    break;
default:
    handleDefault();
    break;
}

try {
    riskyOperation();
} catch (const std::exception& e) {
    handleError(e);
}

if (condition) {
    branchA();
} else if (otherCondition) {
    branchB();
} else {
    defaultAction();
}
```

## 错误示例

```cpp
// 错误：左大括号单独占一行（Allman 风格用于控制流）
if (x > 0)
{
    doSomething();
}

// 错误：控制流左大括号单独一行
for (int i = 0; i < count; ++i)
{
    process(i);
}

// 错误：左大括号单独一行
while (m_isRunning)
{
    eventLoop();
}
```

## 检查方法
1. 搜索控制流关键字（`if`、`for`、`while`、`do`、`switch`、`try`、`catch`）。2. 检测控制流头部行的下一行是否为孤立的`{`（即控制流头部所在行不以 `{` 结尾）。3. 排除函数定义和类定义（这些允许Allman 风格，见 [[qt-braces-function-class]]）。
正则表达式：`\b(if|for|while|switch|catch)\b.*\n\s*\{`。控制流头部行后紧跟单独一行的 `{`，即为违规。
## 修复指南

1. 将左大括号`{` 从独立行移动到控制流头部行的末尾。2. 在`)`与`{` 之间保留一个空格。3. 使用 clang-format：`BreakBeforeBraces: Attach`（或 `Custom` + `BraceWrapping: { AfterControlStatement: Never }`）。4. Qt Creator：`Options > C++ > Edit > Format > Braces` 中选择 `Attach`。
## 审查清单

- [ ] 所有控制流语句（`if`/`for`/`while`/`switch`/`try`/`catch`）的 `{` 与语句同行。- [ ] `else`与`else if` 与前一个`}` 同行：`} else {`
- [ ] `catch` 与前一个`}` 同行：`} catch (...) {`
- [ ] 函数和类定义的`{` 仍然遵循 Allman 风格（单独一行）

## 关联页面

- [[qt-braces-function-class]]：函数与类定义左大括号单独占一行（Allman 例外）。- [[qt-braces-single-line]]：单行控制语句体不使用大括号