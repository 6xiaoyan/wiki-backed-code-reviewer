---
domain: tencent
rule_id: tencent-no-self-comparison
title: 左右一致的重复判断/永远为真或假的判断
priority: sub
source_file: rules/Tencent_C++_Security_Guide.md
source_section: "§2.8"
status: active
check_method: regex
deterministic_check: true
checkability: deterministic
conflicts_with: []
overrides: []
related_pages: []
---

# 左右一致的重复判断 / 永远为真或假的判断

> 来源：腾讯 C/C++ 安全指南 §2.8 | 风险：逻辑错误（中）

## 规则条款

变量与自身的比较条件永远为真（或永远为假），表明可能来自自动完成工具的错误——本应比较两个不同变量，却不小心比较了同一个变量。

常见的自比较模式：`x == x`、`x != x`（永远为真/假）、`x > x`、`x < x`（永远为假）

## 正确示例

```c++
if (foo1.bar == foo2.bar) {  // 比较两个不同对象的同名属性
    // ...
}
```

## 错误示例

```c++
if (foo1.bar == foo1.bar) {  // 永远为真 — 可能是自动完成错误
    // ...
}
```

## 检查方法

1. 搜索自比较模式：`(\w+)\s*[=!<>]=\s*\1`
2. 编译器警告：`-Wtautological-compare`（Clang）、`-Wself-assign`（GCC）

## 修复指南

1. 确认比较两端的变量名是否正确
2. 如果确实应比较同一变量，删除无效条件
3. 启用 `-Wtautological-compare` 编译警告
