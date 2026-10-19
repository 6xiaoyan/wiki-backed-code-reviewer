---
domain: tencent
rule_id: tencent-sizeof-pointer-check
title: 检查在 pointer 上使用 sizeof
priority: sub
source_file: rules/Tencent_C++_Security_Guide.md
source_section: "§8.1"
status: active
check_method: regex
deterministic_check: true
checkability: deterministic
conflicts_with: []
overrides: []
related_pages: []
---

# 检查在 pointer 上使用 sizeof

> 来源：腾讯 C/C++ 安全指南 §8.1 | 风险：逻辑错误（中）
> 级别：【建议】

## 规则条款

`sizeof(pointer)` 得出指针大小（4 或 8 字节），而非指向类型的大小。当意图是获取所指类型的大小时，应使用 `sizeof(*ptr)` 或 `sizeof(T)`。

## 正确示例

```c++
size_t structure_length = sizeof(Foo);   // 结构体的大小
size_t structure_length = sizeof(*ptr);  // 指针所指类型的大小
```

## 错误示例

```c++
size_t structure_length = sizeof(Foo*);  // 可能意图为 sizeof(Foo)
// 这永远返回 4 或 8 字节（指针大小）
```

## 检查方法

1. 搜索 `sizeof(ptr)` 模式（其中 ptr 是指针变量）
2. 验证是否意图为 `sizeof(*ptr)` 或 `sizeof(T)`
3. 正则表达式：`sizeof\s*\(\s*\w+\s*\*\s*\)` 或 `sizeof\s*\(\s*\w*[pP]tr\s*\)`

## 修复指南

1. 将 `sizeof(ptr)` 改为 `sizeof(*ptr)`（取所指对象大小）
2. 或将 `sizeof(T*)` 改为 `sizeof(T)`（直接取类型大小）
