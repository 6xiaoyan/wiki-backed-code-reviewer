---
domain: tencent
rule_id: tencent-no-uninit-heap
title: 不得直接使用刚分配的未初始化的内存
priority: sub
source_file: rules/Tencent_C++_Security_Guide.md
source_section: "§2.11"
status: active
check_method: llm
deterministic_check: false
checkability: llm_checkable
conflicts_with: []
overrides: []
related_pages: []
---

# 不得直接使用刚分配的未初始化的内存

> 来源：腾讯 C/C++ 安全指南 §2.11 | 风险：逻辑错误（中）、信息泄露（中）
> 级别：【建议】

## 规则条款

刚分配的堆内存可能包含先前分配的残留数据（特别是使用 `malloc` 而非 `calloc` 时）。将未初始化的内存返回给调用者可能导致信息泄露或逻辑错误。C++ 优先使用 `std::string` 或 `std::vector`（自动初始化）。

## 正确示例

```c++
char* Foo() {
    char* a = new char[100];
    memcpy(a, "char", 4);
    a[4] = '\0';         // 显式终止 — 不使用 a[5..99]
    return a;
}
```

## 错误示例

```c++
char* Foo() {
    char* a = new char[100];
    a[99] = '\0';        // 只设置了最后一个字节
    memcpy(a, "char", 4);
    return a;            // a[4..98] 包含未初始化的堆数据
}
```

## 检查方法

1. 搜索 `new char[N]`、`malloc(N)` 等分配调用
2. 检查分配后是否完全初始化了使用的所有字节
3. 动态分析：Valgrind 的 `--track-origins=yes` 可追踪未初始化值的使用
4. LLM 审查

## 修复指南

1. 用 `calloc` 替代 `malloc`（自动清零）
2. C++ 中用 `std::string`、`std::vector`（值初始化）
3. 使用 `new char[N]()`（带括号 — 值初始化）替代 `new char[N]`
4. 确保返回前所有字节已写入或截断（设置正确的 null 终止）
