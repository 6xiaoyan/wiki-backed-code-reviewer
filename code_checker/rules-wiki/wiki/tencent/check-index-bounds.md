---
domain: tencent
rule_id: tencent-check-index-bounds
title: 比较数据大小时加上最小/最大值的校验
priority: sub
source_file: rules/Tencent_C++_Security_Guide.md
source_section: "§7.6"
status: active
check_method: llm
deterministic_check: false
checkability: llm_checkable
conflicts_with: []
overrides: []
related_pages:
  - [[tencent/no-oob-write]]
---

# 比较数据大小时加上最小/最大值的校验

> 来源：腾讯 C/C++ 安全指南 §7.6 | 风险：内存损坏（高）

## 规则条款

数组索引验证必须同时检查上界和下界。仅检查上界的检查会放过负索引——负索引访问数组之前的内存，同样是越界写/读。

## 正确示例

```c++
void Foo(int index) {
    int a[30] = {0};
    if (index >= 0 && index < 30) {  // 同时检查下界和上界
        a[index] = 1;
    }
}
```

## 错误示例

```c++
void Foo(int index) {
    int a[30] = {0};
    if (index < 30) {      // 仅检查上界
        a[index] = 1;      // 如果 index < 0，越界写在数组之前
    }
}
```

## 检查方法

1. 搜索数组索引的边界检查代码
2. 验证下界检查（`>= 0` 或使用 `size_t`/`unsigned`）
3. 将索引类型改为 `size_t`（无符号 — 消除下溢）可避免负索引但需额外注意回绕问题

## 修复指南

1. 始终同时检查上界和下界：`if (idx >= 0 && idx < size)`
2. 或使用 `size_t` 类型索引（隐式消除负值，但需检查回绕）
3. 使用 `std::array::at()` 或 `std::vector::at()` — 自动边界检查
