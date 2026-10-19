---
domain: tencent
rule_id: tencent-no-stack-return
title: 禁止返回栈上变量的地址
priority: sub
source_file: rules/Tencent_C++_Security_Guide.md
source_section: "§2.4"
status: active
check_method: llm
deterministic_check: false
checkability: llm_checkable
conflicts_with: []
overrides: []
related_pages: []
---

# 禁止返回栈上变量的地址

> 来源：腾讯 C/C++ 安全指南 §2.4 | 风险：内存损坏（高）

## 规则条款

函数返回后栈内存无效。返回栈上局部变量的地址或引用会导致悬空指针（dangling pointer），解引用时产生未定义行为。C++ 中优先返回 `std::string` 或 `std::vector`（值语义，自动管理内存）。

## 正确示例

```c++
// C 方式：用堆分配
char* Foo(char* sz, int len) {
    char* a = new char[300];
    if (len > 100) memcpy(a, sz, 100);
    a[len] = '\0';
    return a;
}

// C++ 方式（推荐）：返回值对象
std::string Foo(const char* sz, int len) {
    return std::string(sz, std::min(len, 100));
}
```

## 错误示例

```c++
char* Foo(char* sz, int len) {
    char a[300] = {0};
    if (len > 100) memcpy(a, sz, 100);
    a[len] = '\0';
    return a;  // 栈地址 — 返回后悬空
}
```

## 检查方法

1. 搜索返回 `char*` 或局部数组地址的函数
2. 编译器警告：`-Wreturn-stack-address`（Clang/GCC）
3. LLM 审查：判断返回的指针是否指向栈内存

## 修复指南

1. 用堆分配（`new`/`malloc`）替代栈数组
2. C++ 中优先返回值对象（`std::string`、`std::vector`）
3. 启用 `-Wreturn-stack-address` 编译警告
