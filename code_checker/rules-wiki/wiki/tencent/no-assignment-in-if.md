---
domain: tencent
rule_id: tencent-no-assign-in-if
title: 不要在 if 里面赋值
priority: sub
source_file: rules/Tencent_C++_Security_Guide.md
source_section: "§2.13"
status: active
check_method: regex
deterministic_check: true
checkability: deterministic
conflicts_with: []
overrides: []
related_pages: []
---

# 不要在 if 里面赋值

> 来源：腾讯 C/C++ 安全指南 §2.13 | 风险：逻辑错误（中）

## 规则条款

`if` 条件内的赋值几乎总是等于比较（`==`）的拼写错误。编译器标志 `-Wparentheses`（`-Wall` 中）可捕获此问题，但最好在代码层面避免这种写法。

## 正确示例

```c++
void Foo() {
    int bar = GetBar();
    if (bar == 0x99) {  // 显式比较 — 意图明确
        // ...
    }
}
```

## 错误示例

```c++
void Foo() {
    int bar;
    if (bar = 0x99)  // 赋值而非比较！条件测试的是赋值的副作用
        // ...
}
```

## 检查方法

1. 搜索 if/while 条件中的赋值操作符 `=`
2. 正则表达式：`\b(?:if|while)\s*\([^)]*[^!=<>]=(?!=)[^=]`
3. 编译器警告：`-Wparentheses`（`-Wall` 中）

## 修复指南

1. 将 `if (x = y)` 改为 `if (x == y)`（最常见情况）
2. 有意在条件中赋值时，用双重括号 `if ((x = y))` 并加注释说明
