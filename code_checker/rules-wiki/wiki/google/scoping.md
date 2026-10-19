---
domain: google
rule_id: google-scoping
title: 作用域规范（Google C++ Style Guide 对照）
priority: sub
source_file: rules/Google_C++_Style_Guide.md
source_section: "第 2 章"
status: active
check_method: regex
deterministic_check: true
checkability: deterministic
conflicts_with:
  - "cpp/no-global-variables"
overrides: []
related_pages:
  - [[cpp/no-using-namespace-in-header]]
  - [[cpp/no-global-variables]]
  - [[cpp/thread-local]]
  - [[qt/late-declaration]]
---

# 作用域规范（Google C++ Style Guide 对照）

> 来源：Google C++ Style Guide 第 2 章 | 大部分与公司规则一致或互补

## 与公司规则的对照

| Google 条款 | 公司规则 | 一致性 |
|------------|---------|--------|
| **禁止** `using namespace foo` 指令 | [[cpp/no-using-namespace-in-header]] | ✅ 一致 |
| 禁止内联命名空间 | — | 补充条款 |
| `.cc` 文件中不需要被外部访问的定义应放入匿名命名空间或 `static` | — | 补充条款 |
| 尽可能缩小变量作用域，声明时初始化 | [[qt/late-declaration]] | ✅ 一致 |
| 禁止非平凡析构的静态/全局变量 | [[cpp/no-global-variables]] | ⚠️ 公司规则更严格（全部禁止全局变量），**公司规则为准** |
| `thread_local` 变量必须用编译时常量初始化 | [[cpp/thread-local]] | 一致 |

## ❌ 关键冲突：静态/全局变量

| 方面 | Google | 公司 |
|------|--------|------|
| 全局变量 | 允许平凡析构的全局变量 | [[cpp/no-global-variables]] **完全禁止** |
| 裁决 | **以公司规则为准**（更严格） | |

## 补充条款（公司规则未覆盖）

1. **匿名命名空间优先于 `static`**：`.cc` 文件中的内部链接优先使用匿名命名空间
2. **非成员函数放入命名空间**：避免完全全局的函数，不要仅为了分组静态成员而创建类
3. **单行嵌套命名空间**：`namespace foo::bar { ... }` 对新代码鼓励使用
