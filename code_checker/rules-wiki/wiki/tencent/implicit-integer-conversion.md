---
domain: tencent
rule_id: tencent-implicit-int-conversion
title: 注意隐式符号转换
priority: sub
source_file: rules/Tencent_C++_Security_Guide.md
source_section: "§1.8"
status: active
check_method: llm
deterministic_check: false
checkability: llm_checkable
conflicts_with: []
overrides: []
related_pages: []
---

# 注意隐式符号转换

> 来源：腾讯 C/C++ 安全指南 §1.8 | 风险：逻辑错误（中）

## 规则条款

两个无符号值相减得到大无符号数。但小于 `int` 的类型在减法*之前*会进行整型提升，意外改变行为。

小于 `int` 的无符号类型会被提升为*有符号* `int`：
```c++
unsigned char a = 1, b = 2;
if (a - b < 0)  // a - b == -1 作为有符号 int → 条件为真
    a = 6;

unsigned short a = 1, b = 2;
if (a - b < 0)  // 同样提升为有符号 int
    a = 6;
```

`unsigned int` 保持无符号：
```c++
unsigned int a = 1, b = 2;
if (a - b < 0)  // a - b == 0xFFFFFFFF（无符号）→ 条件为假
    a = 8;      // a 变成 8 — 意外行为！
```

## 正确示例

```c++
// 安全做法 — 显式转换以确保无符号比较
if ((unsigned int)a - (unsigned int)b < 0)
    a = 6;
else
    a = 8;
```

## 检查方法

1. 搜索有符号和无符号类型混合的算术表达式
2. 特别关注 `unsigned char` 和 `unsigned short` — 它们先被提升为 `signed int`
3. 编译器警告：`-Wsign-compare`、`-Wconversion`
4. LLM 审查：判断混合符号表达式是否存在隐式提升陷阱

## 修复指南

1. 混合符号运算时使用显式转换
2. 避免在比较和减法中混合有符号和无符号类型
3. 启用编译器警告 `-Wsign-compare` 和 `-Wconversion`

## 审查清单

- [ ] 无混合符号类型的未防护算术比较
- [ ] `unsigned char`/`unsigned short` 减法前做了显式转换
- [ ] `-Wsign-compare` 编译警告已启用
