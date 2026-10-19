---
domain: qt-wiki
rule_id: qtwiki-parentheses
title: 括号——显式分组表达式（Qt Coding Style 对照）
priority: sub
source_file: rules/Qt_Coding_Style.md
source_section: "括号"
status: active
check_method: llm
deterministic_check: false
checkability: llm_checkable
conflicts_with: []
overrides: []
related_pages:
  - [[qt/parentheses-precedence]]
---

# 括号——显式分组表达式（Qt Coding Style 对照）

> 来源：Qt Coding Style（[wiki.qt.io](https://wiki.qt.io/Qt_Coding_Style)）| 与公司规则一致

## 规则条款

使用括号显式分组表达式以明确优先级，不依赖运算符优先级。

## 正确示例

```cpp
if ((a && b) || c)       // 意图明确
(a + b) & c              // 意图明确
```

## 错误示例

```cpp
if (a && b || c)         // 依赖 && 优先于 || — 不清晰
a + b & c                // 位 & 优先级低于 + — 容易被误解
```

## 与公司规则的对照

与 [[qt/parentheses-precedence]] 完全一致。Qt Coding Style 未添加额外的约束或例外。

## 审查清单

- [ ] 混合运算符的表达式使用括号明确优先级
- [ ] 位运算与算术运算混合时使用括号
