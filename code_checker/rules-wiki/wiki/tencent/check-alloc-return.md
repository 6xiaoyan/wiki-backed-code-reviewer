---
domain: tencent
rule_id: tencent-check-alloc-return
title: 校验内存相关函数的返回值
priority: sub
source_file: rules/Tencent_C++_Security_Guide.md
source_section: "§2.12"
status: active
check_method: llm
deterministic_check: false
checkability: llm_checkable
conflicts_with: []
overrides: []
related_pages: []
---

# 校验内存相关函数的返回值

> 来源：腾讯 C/C++ 安全指南 §2.12 | 风险：越界操作（高）、逻辑错误（中）

## 规则条款

内存分配函数（`malloc`、`mmap`、`new` 等）可能失败。忽略返回值或在调用后不检查返回值会导致空指针解引用或越界写。`mmap` 失败时返回 `MAP_FAILED` 而非 `NULL`——检查 `NULL` 是不够的。

## 正确示例

```c++
char* bar = mmap(0, 0x800000, ...);
if (bar == MAP_FAILED) {
    return;
}
*(bar + 0x400000) = '\x88';
```

## 错误示例

```c++
char* bar = mmap(0, 0x800000, ...);
// 未检查 bar 是否为 MAP_FAILED
*(bar + 0x400000) = '\x88';  // 如果 mmap 失败，可能写到地址 (void*)-1
```

## 检查方法

1. 搜索内存分配/映射函数：`malloc`、`calloc`、`realloc`、`mmap`、`new`
2. 检查分配调用后是否有空指针/失败检查
3. 特别注意 `mmap` — 错误返回值是 `MAP_FAILED`，而非 `NULL`
4. LLM 审查

## 修复指南

1. 每次内存分配后立即检查返回值
2. `malloc` 系列：检查 `== NULL`
3. `mmap`：检查 `== MAP_FAILED`
4. C++ `new`：默认抛异常；`new(std::nothrow)` 需要检查 `nullptr`
