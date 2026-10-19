---
domain: tencent
rule_id: tencent-parallel-array-check
title: 有逻辑联系的数组必须仔细检查
priority: sub
source_file: rules/Tencent_C++_Security_Guide.md
source_section: "§2.5"
status: active
check_method: llm
deterministic_check: false
checkability: llm_checkable
conflicts_with: []
overrides: []
related_pages: []
---

# 有逻辑联系的数组必须仔细检查

> 来源：腾讯 C/C++ 安全指南 §2.5 | 风险：内存损坏（高）

## 规则条款

平行数组（同一索引位置的不同数组存储同一实体的不同属性）必须具有相同长度。用其中一个数组的长度去索引另一个较短的数组会导致越界访问。

## 正确示例

```c++
const int nWeekdays[] = {1, 2, 3, 4, 5, 6, 7};
const char* sWeekdays[] = {"Mon","Tue","Wed","Thu","Fri","Sat","Sun"};
assert(ARRAY_SIZE(nWeekdays) == ARRAY_SIZE(sWeekdays));

for (int x = 0; x < ARRAY_SIZE(sWeekdays); x++) {
    if (strcmp(sWeekdays[x], input) == 0)
        return nWeekdays[x];  // 安全 — 两个数组长度已校验
}
```

## 错误示例

```c++
int nWeekdays[] = {1, 2, 3, 4, 5, 6};           // 6 个元素
const char* sWeekdays[] = {"Mon","Tue","Wed","Thu","Fri","Sat","Sun"}; // 7 个
for (int x = 0; x < ARRAY_SIZE(sWeekdays); x++) {
    if (strcmp(sWeekdays[x], input) == 0)
        return nWeekdays[x];  // 当 x == 6 时越界
}
```

## 检查方法

1. 搜索使用不同数组长度做循环上限的代码
2. 检查多个数组在同一循环中通过同一索引访问的模式
3. 静态分析工具可检测越界；LLM 审查

## 修复指南

1. 添加 `static_assert` 或运行时 `assert` 检查平行数组长度一致
2. 用 `struct` 将关联数据组织在一起（替代平行数组）
3. C++ 中优先使用 `std::vector` + `.size()` 一致性检查
