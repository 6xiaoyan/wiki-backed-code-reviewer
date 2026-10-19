---
domain: qt
rule_id: qt-keyword-spacing
title: 关键字与后续括号、括号与大括号之间加 1 个空格
priority: main
source_file: rules/QT代码开发规则.md
source_section: "§2.3"
status: active
check_method: regex
deterministic_check: true
checkability: deterministic
conflicts_with: []
overrides: []
related_pages:
  - [[qt-braces-knr]]
  - [[qt-binary-op-spacing]]
---

# 关键字与后续括号、括号与大括号之间加 1 个空格
## 规则条款

控制流关键字（`if`、`for`、`while`、`switch`、`catch`）与后续左括号之间必须**添加 1 个空格**。右括号与后续左大括号之间也**必须添加 1 个空格**。函数调用时函数名与括号之间不加空格（区分关键字和函数调用）。具体规则：
- `if (condition) {` — 关键字`if` 与`(` 之间有空格；`)` 与`{` 之间有空格- `for (int i = 0; i < n; ++i) {` — 同上
- `while (running) {` — 同上
- `switch (value) {` — 同上
- `catch (const std::exception &e) {` — 同上
- `func(args)` — 函数调用，名称与 `(` 之间不加空格

## 正确示例

```cpp
if (m_hasData) {
    processData();
}

for (int i = 0; i < rowCount; ++i) {
    updateRow(i);
}

while (m_isRunning) {
    eventLoop();
}

switch (m_currentState) {
case State::Idle:
    break;
default:
    handleUnknownState();
    break;
}

try {
    riskyOperation();
} catch (const std::runtime_error &error) {
    handleError(error);
}

// 函数调用 — 无空格updateModel(index);
QString name = object.metaObject()->className();
```

## 错误示例

```cpp
if(m_hasData) {             // 错误：if 与( 之间缺少空格
    processData();
}

for(int i = 0; i < n; ++i){  // 错误：for 与( 之间无空格；) 与{ 之间无空格    updateRow(i);
}

if (condition ){             // 错误： )与{ 之间无空格（) 前多余空格）
    doSomething();
}

// 函数调用误加空格
updateModel (index);          // 错误：函数名与( 之间不应有空格```

## 检查方法
正则表达式规则：
1. **关键字后缺少空格**：`\b(if|for|while|switch|catch)\(` — 关键字与 `(` 之间无空格。2. **`)` 与`{` 之间缺少空格**：`\)\{` — 右括号与大括号无空格
3. **函数调用误加空格**：`\w+\s+\(` — 但需排除关键字场景
实际检测建议解析AST 或使用上下文感知的正则匹配。
正则表达式：
- 缺少关键字空格：`\b(if|for|while|switch|catch)\(`
- 缺少大括号空格：`\)\{`

## 修复指南

1. 使用 clang-format 配置：`SpaceBeforeParens: ControlStatements`，`SpaceBeforeParensOptions: { AfterControlStatements: true }`。2. Qt Creator：`Options > C++ > Edit > Format` 中选择 Qt 预设风格。3. 手动修复：在关键字和 `(` 之间插入空格，在 `)` 与`{` 之间插入空格。
## 审查清单

- [ ] `if`/`for`/`while`/`switch`/`catch` 与`(` 之间有1 个空格- [ ] `)` 与`{` 之间有1 个空格- [ ] 函数调用时函数名与`(` 之间无空格- [ ] `else` 与`{` 之间有1 个空格：`} else {`

## 关联页面

- [[qt-braces-knr]]：控制流左大括号与语句同行（K&R 风格）- [[qt-binary-op-spacing]]：二元操作符前后加空白字符
