---
domain: tencent
rule_id: tencent-no-array-compare-zero
title: 检查直接将数组和 0 比较的代码
priority: sub
source_file: rules/Tencent_C++_Security_Guide.md
source_section: "§8.2"
status: active
check_method: regex
deterministic_check: true
checkability: deterministic
conflicts_with: []
overrides: []
related_pages: []
---

# 检查直接将数组和 0 比较的代码

> 来源：腾讯 C/C++ 安全指南 §8.2 | 风险：逻辑错误（中）

## 规则条款

将数组名称与 0 比较是在比较第一个元素的地址，该地址永远非空。这意味着条件永远为真——这几乎总是 bug（很可能意图为比较数组的第一个*元素*的值）。

编译器标志 `-Waddress`（`-Wall` 中）可捕获 `array > 0` 的比较。

## 正确示例

```c++
int a[3];
if (a[0] > 0)  // 比较第一个元素的值
    // ...
```

## 错误示例

```c++
int a[3];
if (a > 0)     // 永远为真 — a 是数组首元素的地址（非零）
    // ...
```

## 检查方法

1. 搜索数组名直接与数值（0、NULL、nullptr）比较的表达式
2. 编译器警告：`-Waddress`（`-Wall` 中）
3. 正则表达式：`\b\w+(?:\[\w*\])*\s*[><=!]=\s*(?:0|NULL|nullptr)\b`

## 修复指南

1. 如果意图是检查第一个元素：改为 `arr[0] > 0`
2. 如果意图是检查空数组：检查长度而非地址
