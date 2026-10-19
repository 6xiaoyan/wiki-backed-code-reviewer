---
domain: qt-wiki
rule_id: qtwiki-no-else-after-jump
title: 跳转语句后不要写 else（Qt Coding Style 对照）
priority: sub
source_file: rules/Qt_Coding_Style.md
source_section: "跳转语句"
status: active
check_method: regex
deterministic_check: true
checkability: deterministic
conflicts_with: []
overrides: []
related_pages: []
---

# 跳转语句后不要写 else（Qt Coding Style 对照）

> 来源：Qt Coding Style（[wiki.qt.io](https://wiki.qt.io/Qt_Coding_Style)）| 公司 Qt 规则未明确覆盖

## 规则条款

跳转语句（`break`、`continue`、`return`、`goto`）后不要写 `else`。因为跳转语句后的代码仅在跳转不发生时执行——此时 `else` 是冗余的，删除它可以减少嵌套层级。

## 正确示例

```cpp
if (thisOrThat)
    return;
somethingElse();        // 隐式的 "else"
```

## 错误示例

```cpp
if (thisOrThat)
    return;
else
    somethingElse();    // else 是冗余的 — return 已经跳出了
```

## 例外

如果代码"本质上是对称的"，使用 `else` 是被允许的，以使对称性更明显。

## 检查方法

1. 搜索 `if (...) return/break/continue/goto; else ...` 模式
2. 正则表达式：`\b(?:return|break|continue|goto)\b[^}]*\n\s*\}?\s*else\b`

## 修复指南

1. 删除跳转语句后的 `else` 关键字
2. 将 else 分支代码提升一级缩进
3. 如果对称性很重要（如 if-else 两个分支结构完全相同），保留 else 并加注释

## 审查清单

- [ ] 跳转语句后无冗余的 `else`
- [ ] 对称场景中保留的 `else` 有注释说明
