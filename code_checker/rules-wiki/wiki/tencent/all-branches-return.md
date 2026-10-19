---
domain: tencent
rule_id: tencent-all-branches-return
title: 函数每个分支都应有返回值
priority: sub
source_file: rules/Tencent_C++_Security_Guide.md
source_section: "§2.9"
status: active
check_method: llm
deterministic_check: false
checkability: llm_checkable
conflicts_with: []
overrides: []
related_pages: []
---

# 函数每个分支都应有返回值

> 来源：腾讯 C/C++ 安全指南 §2.9 | 风险：逻辑错误（中）、信息泄露（中）

## 规则条款

每个代码路径必须返回值。缺少 return 的路径会导致未定义行为（函数退出时调用者读取未初始化的返回值）。编译器可通过 `-Wreturn-type` 捕获（`-Wall` 中包含）。

## 正确示例

```c++
int Foo(int bar) {
    if (bar > 100) return 10;
    else if (bar > 10) return 1;
    return 0;  // 覆盖所有剩余情况
}
```

## 错误示例

```c++
int Foo(int bar) {
    if (bar > 100) return 10;
    else if (bar > 10) return 1;
    // bar <= 10 时缺少 return — 未定义行为
}
```

## 检查方法

1. 编译器警告：`-Wreturn-type`（`-Wall` 中包含）
2. 对每个非 void 函数，验证所有控制流路径都有 return 语句
3. 静态分析工具（Coverity、clang-tidy）可检测

## 修复指南

1. 在函数末尾添加兜底 `return` 或 `default` case
2. 如果某些路径逻辑上不可达，使用 `assert(false)` 或 `std::unreachable()`（C++23）
3. 确保编译时启用 `-Wall -Werror`
