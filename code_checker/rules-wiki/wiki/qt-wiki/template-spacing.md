---
domain: qt-wiki
rule_id: qtwiki-template-spacing
title: 模板空格风格（Qt Coding Style 对照）
priority: sub
source_file: rules/Qt_Coding_Style.md
source_section: "模板"
status: active
check_method: regex
deterministic_check: true
checkability: deterministic
conflicts_with: []
overrides: []
related_pages: []
---

# 模板空格风格（Qt Coding Style 对照）

> 来源：Qt Coding Style（[wiki.qt.io](https://wiki.qt.io/Qt_Coding_Style)）| 公司 Qt 规则未明确覆盖

## 规则条款

Qt 历史上在模板初始化器的 `<` 前使用空格。在向 qt5.git 添加 `_clang-format` 文件后，代码库现在"各种风格混杂"。

**指导原则：** 选择你文件/模块中最流行的风格。

```cpp
// 传统 Qt 风格（带空格）
template <typename T> void foo();

// 新式风格（不带空格）
template<typename T> void foo();
```

## 检查方法

1. 对每个文件，扫描模板声明的空格风格
2. 报告与文件主导风格不一致的模板声明
3. 正则表达式：`template\s*<` vs `template <`

## 修复指南

1. 确定文件/模块的主导模板空格风格
2. 将不一致的声明统一为同一风格
3. **公司规则无强制要求**，但文件内部应保持一致

## 审查清单

- [ ] 同一文件内的模板空格风格一致
