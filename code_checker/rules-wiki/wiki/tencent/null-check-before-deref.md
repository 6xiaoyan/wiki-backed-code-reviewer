---
domain: tencent
rule_id: tencent-null-check-before-deref
title: 检查空指针
priority: sub
source_file: rules/Tencent_C++_Security_Guide.md
source_section: "§8.4"
status: active
check_method: llm
deterministic_check: false
checkability: llm_checkable
conflicts_with: []
overrides: []
related_pages: []
---

# 检查空指针

> 来源：腾讯 C/C++ 安全指南 §8.4 | 风险：拒绝服务（低）

## 规则条款

解引用必须在空检查*之后*进行，而非之前。先解引用再检查空指针毫无意义——如果指针为空，程序在检查之前已经崩溃。

## 正确示例

```c++
if (!foo) {
    ERROR("foobar");
    return;
}
*foo = 100;  // 空检查已通过
```

## 错误示例

```c++
*foo = 100;           // 解引用 — 如果 foo 为空则崩溃
if (!foo) {           // 太晚了 — 已经崩溃
    ERROR("foobar");
}
```

## 检查方法

1. 搜索模式：先解引用（`*ptr = x`），后空检查（`if (!ptr)`）
2. 对每个指针参数，验证解引用前是否有空检查
3. 静态分析：Coverity `FORWARD_NULL`、clang-tidy `bugprone-null-check-after-dereference`

## 修复指南

1. 将空检查移到解引用之前
2. 在函数入口对将使用的指针进行空检查
3. 使用引用（`T&`）而非指针（`T*`）表示永远非空的语义
