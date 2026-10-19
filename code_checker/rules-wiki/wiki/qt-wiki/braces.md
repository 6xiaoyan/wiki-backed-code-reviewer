---
domain: qt-wiki
rule_id: qtwiki-braces
title: 大括号风格（Qt Coding Style 对照）
priority: sub
source_file: rules/Qt_Coding_Style.md
source_section: "大括号"
status: active
check_method: regex
deterministic_check: true
checkability: deterministic
conflicts_with:
  - "qt/braces-single-line"
overrides: []
related_pages:
  - [[qt/braces-knr]]
  - [[qt/braces-function-class]]
  - [[qt/braces-empty-body]]
  - [[qt/braces-ifelse-symmetry]]
  - [[qt/braces-single-line]]
  - [[qt/braces-multiline-parent]]
---

# 大括号风格（Qt Coding Style 对照）

> 来源：Qt Coding Style（[wiki.qt.io](https://wiki.qt.io/Qt_Coding_Style)）| 部分与公司规则冲突，**公司规则为准**

## 与公司规则的对照

| Qt Coding Style 条款 | 公司规则页面 | 一致性 |
|---------------------|------------|--------|
| 控制流左大括号与语句同行（K&R） | [[qt/braces-knr]] | ✅ 一致 |
| 函数/类定义左大括号单独一行（Allman） | [[qt/braces-function-class]] | ✅ 一致 |
| 空体使用 `{}` 而非 `;` | [[qt/braces-empty-body]] | ✅ 一致 |
| if-else 对称性：任一分支多行则都加大括号 | [[qt/braces-ifelse-symmetry]] | ✅ 一致 |
| 父语句跨多行时加大括号 | [[qt/braces-multiline-parent]] | ✅ 一致 |

## ⚠️ 冲突项：单行体的括号

**Qt Coding Style 规定：** 单行体不需要大括号。

```cpp
// Qt Coding Style 认为正确
if (address.isEmpty())
    return false;

for (int i = 0; i < 10; ++i)
    qDebug("%i", i);
```

**公司规则：** [[qt/braces-single-line]] 可能有不同要求。**冲突时以公司规则为准。**

## Qt Coding Style 补充：`= default` 放置

`= default` 放在单独的缩进行上：

```cpp
// 正确
Class::~Class()
    = default;

// 错误
Class::~Class() = default;
```

理由：避免在用户定义和 `= default` 之间切换时需要触及不相关的行。
