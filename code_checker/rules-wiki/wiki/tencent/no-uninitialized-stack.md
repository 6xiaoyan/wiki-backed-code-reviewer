---
domain: tencent
rule_id: tencent-no-uninit-stack
title: 不得使用栈上未初始化的变量
priority: sub
source_file: rules/Tencent_C++_Security_Guide.md
source_section: "§2.10"
status: active
check_method: llm
deterministic_check: false
checkability: llm_checkable
conflicts_with: []
overrides: []
related_pages: []
---

# 不得使用栈上未初始化的变量

> 来源：腾讯 C/C++ 安全指南 §2.10 | 风险：逻辑错误（中）、信息泄露（中）

## 规则条款

栈变量必须在所有代码路径中使用前初始化。当某个条件分支没有给变量赋值时，使用该变量会读到栈上的残留数据（未定义行为）。编译器标志 `-Wuninitialized` 可捕获大多数情况。

## 正确示例

```c++
void Foo() {
    int foo = 0;         // 声明时初始化
    if (Bar()) {
        foo = 1;
    }
    Foobar(foo);         // foo 始终有确定值
}
```

## 错误示例

```c++
void Foo() {
    int foo;              // 未初始化
    if (Bar()) {
        foo = 1;
    }
    Foobar(foo);          // Bar() 返回 false 时 foo 未定义
}
```

## 检查方法

1. 编译器警告：`-Wuninitialized`（`-Wall` 中），`-Wsometimes-uninitialized`（Clang）
2. 静态分析：clang-tidy `cppcoreguidelines-init-variables`
3. LLM 审查：变量声明时是否初始化，是否所有分支都给变量赋值

## 修复指南

1. 始终在声明变量时初始化（使用 `= {}` 或明确的初始值）
2. C++ 核心指南 ES.20：始终初始化对象
3. 编译时启用 `-Werror=uninitialized`
