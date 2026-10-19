---
domain: tencent
rule_id: tencent-prng-range
title: 自己实现的 rand 范围不应过小
priority: sub
source_file: rules/Tencent_C++_Security_Guide.md
source_section: "§4.5"
status: active
check_method: llm
deterministic_check: false
checkability: llm_checkable
conflicts_with: []
overrides: []
related_pages:
  - [[tencent/use-csprng]]
---

# 自己实现的 rand 范围不应过小

> 来源：腾讯 C/C++ 安全指南 §4.5 | 风险：逻辑漏洞（高）

## 规则条款

自定义 PRNG 实现不得无意中减少输出范围。使用 `&` 和非 2 的幂次掩码会不均匀地丢弃位（某些值出现频率更高）。应使用 `%` 取模或 `&` 2 的幂次掩码来保持均匀分布。

## 正确示例

```c++
int32_t val = ((state[0] * 1103515245U) + 12345U) % 1000000;
// 或使用 2 的幂次掩码
int32_t val = ((state[0] * 1103515245U) + 12345U) & 0x7fffffff;
```

## 错误示例

```c++
int32_t val = ((state[0] * 1103515245U) + 12345U) & 999999;
// & 999999（非 2 的幂）会导致某些位始终为 0，输出范围减半
```

## 检查方法

1. 搜索自定义 PRNG 中 `&` 非 2 的幂次常数的操作
2. LLM 审查：自定义 PRNG 的分布是否均匀

## 修复指南

1. 使用 CSPRNG（参见 [[tencent/use-csprng]]）替代自定义 PRNG
2. 如必须自定义，使用 `%` 取模而非 `&` 掩码（非 2 的幂次时）
3. 均匀分布用 `& (POW2-1)` 而非 `& ARBITRARY_NUM`
