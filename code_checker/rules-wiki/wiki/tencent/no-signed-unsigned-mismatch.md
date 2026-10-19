---
domain: tencent
rule_id: tencent-no-signed-unsigned-mismatch
title: 防止数字类型的错误强转
priority: sub
source_file: rules/Tencent_C++_Security_Guide.md
source_section: "§7.5"
status: active
check_method: llm
deterministic_check: false
checkability: llm_checkable
conflicts_with: []
overrides: []
related_pages:
  - [[tencent/implicit-integer-conversion]]
---

# 防止数字类型的错误强转

> 来源：腾讯 C/C++ 安全指南 §7.5 | 风险：内存损坏（高）、逻辑错误（中）

## 规则条款

在比较中混合有符号和无符号类型由于隐式转换规则可能导致意外结果。当一个有符号负数与无符号数比较时，有符号数被隐式转换为无符号数，负数变成巨大的正数，比较结果完全出乎意料。

## 正确示例

```c++
void Foo() {
    int len = 1;
    int size = 9;
    if (len < size - 10)  // 两者都带符号 — 行为明确
        printf("Bad\n");
}
```

## 错误示例

```c++
int Foo() {
    int len = 1;
    unsigned int size = 9;
    if (len < size - 10)  // size - 10 == UINT_MAX - 0（回绕！）
        printf("Bad\n");  // 可能被错误执行
}
```

## 检查方法

1. 编译器警告：`-Wsign-compare`（`-Wall` 中）
2. 搜索有符号/无符号混合的比较表达式
3. LLM 审查

## 修复指南

1. 统一为有符号类型，或统一为无符号类型
2. 混合比较时添加显式转换
3. 参见 [[tencent/implicit-integer-conversion]]
