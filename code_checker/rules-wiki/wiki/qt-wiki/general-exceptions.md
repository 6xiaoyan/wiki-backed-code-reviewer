---
domain: qt-wiki
rule_id: qtwiki-general-exceptions
title: 通用例外原则（Qt Coding Style 对照）
priority: sub
source_file: rules/Qt_Coding_Style.md
source_section: "通用例外"
status: active
check_method: llm
deterministic_check: false
checkability: advisory_only
conflicts_with: []
overrides: []
related_pages: []
---

# 通用例外原则（Qt Coding Style 对照）

> 来源：Qt Coding Style（[wiki.qt.io](https://wiki.qt.io/Qt_Coding_Style)）| 仅供参考

## 规则条款

Qt Coding Style 包含两条通用的例外原则：

1. **"当严格遵守某条规则使代码看起来很丑时，可以随意打破它。"**
2. **"如果在任何给定模块中存在争议，维护者对可接受的风格有最终决定权"**（根据 Qt 治理模型）。

## 与公司规则的关系

公司规则体系中**未**包含此类宽泛的例外条款。公司规则的目标是可程序化检查——每条规则有明确的确定性检查或 LLM 可检查的判断标准。歧义性例外不适合自动检查流程，但可以作为人工 Code Review 时的参考原则。

## 适用场景

- 当自动检查工具标记了违规，但修复会导致代码可读性明显下降时
- 当两个规则在同一位置产生冲突，且没有明确的优先级时
- 作为 Code Review 中讨论风格争议的参考框架

## 审查清单

- [ ] 例外有明确的注释说明原因
- [ ] 例外已在团队内达成共识
