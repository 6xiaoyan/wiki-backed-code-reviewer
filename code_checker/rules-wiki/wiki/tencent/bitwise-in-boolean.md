---
domain: tencent
rule_id: tencent-bitwise-in-boolean
title: 确认 if 里面的按位操作
priority: sub
source_file: rules/Tencent_C++_Security_Guide.md
source_section: "§2.14"
status: active
check_method: llm
deterministic_check: false
checkability: llm_checkable
conflicts_with: []
overrides: []
related_pages: []
---

# 确认 if 里面的按位操作

> 来源：腾讯 C/C++ 安全指南 §2.14 | 风险：逻辑错误（中）
> 级别：【建议】

## 规则条款

在布尔上下文中使用位 `&` 而不是逻辑 `&&` 通常是一个错误。位 `&` 的结果是一个整数，而非布尔值——两个非零值按位与可能产生零（false），而逻辑 `&&` 的结果才是"两者都非零"。

## 正确示例

```c++
int bar = 0x1;     // binary 01
int foobar = 0x2;  // binary 10
if (foobar && bar)  // 逻辑与 — 两者都非零 → 条件为真
    // ...
```

## 错误示例

```c++
int bar = 0x1;     // binary 01
int foobar = 0x2;  // binary 10
if (foobar & bar)  // result = 0 (false) — 可能意图为 &&
    // ...
```

## 检查方法

1. 搜索 `if`/`while` 条件中的单个 `&` 或 `|` 操作符（非 `&&`/`||`）
2. LLM 审查：判断布尔上下文中的位操作是否是有意的

## 修复指南

1. 如果意图是逻辑判断，将 `&` 改为 `&&`，将 `|` 改为 `||`
2. 如果意图确实是位操作（如检查标志位），添加注释说明
3. 标志位检查推荐使用 `(flags & MASK) != 0` 的显式写法
