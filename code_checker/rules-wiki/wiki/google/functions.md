---
domain: google
rule_id: google-functions
title: 函数规范（Google C++ Style Guide 对照）
priority: sub
source_file: rules/Google_C++_Style_Guide.md
source_section: "第 4 章"
status: active
check_method: llm
deterministic_check: false
checkability: llm_checkable
conflicts_with: []
overrides: []
related_pages:
  - [[qt/function-max-lines]]
  - [[qt/method-verb-phrase]]
---

# 函数规范（Google C++ Style Guide 对照）

> 来源：Google C++ Style Guide 第 4 章 | 与公司规则大部分一致

## 与公司规则的对照

| Google 条款 | 公司规则 | 一致性 |
|------------|---------|--------|
| 倾向于按值返回，否则按引用返回 | — | 补充条款 |
| 倾向于编写简短函数（≤40 行） | [[qt/function-max-lines]] | ✅ 一致 |
| 函数重载必须在调用点立即理解 | — | 补充条款 |
| 虚函数中禁止使用缺省参数 | — | 补充条款 |
| 后置返回类型仅用于复杂模板和 Lambda | — | 补充条款 |

## 补充条款（公司规则未覆盖）

1. **参数类型选择**：
   - 非可选输入 → 按值或 `const` 引用
   - 非可选输出 → 按引用（不可为空）
   - 可选输入 → `const` 指针
   - 可选输出 → 非 `const` 指针
2. **参数排序**："将所有仅输入参数放在任何输出参数之前"
3. **缺省参数**：虚函数中禁止使用；默认值必须保持一致；通常优先使用重载
4. **避免返回裸指针**：除非它可以为空
