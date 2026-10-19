---
domain: tencent
rule_id: tencent-no-debug-info-leak
title: 不应当在 Debug 或错误信息中提供过多内容
priority: sub
source_file: rules/Tencent_C++_Security_Guide.md
source_section: "§2.2"
status: active
check_method: llm
deterministic_check: false
checkability: llm_checkable
conflicts_with: []
overrides: []
related_pages:
  - [[cpp/no-unvalidated-input]]
---

# 不应当在 Debug 或错误信息中提供过多内容

> 来源：腾讯 C/C++ 安全指南 §2.2 | 风险：信息泄露（中）

## 规则条款

包含内存地址或内部数据的调试输出不应到达最终用户——它帮助攻击者利用程序。调试级别的详细错误信息应使用条件编译（`#ifdef DEBUG`）仅在调试构建中使用。

## 正确示例

```c++
int foo(int* bar) {
#ifdef DEBUG
    if (bar && *bar == 5) {
        OutputDebugInfo("Wrong value for bar.\n");
    }
#endif
}
```

## 错误示例

```c++
int Foo(int* bar) {
    if (bar && *bar == 5) {
        OutputDebugInfoToUser("Wrong value for bar %p = %d\n", bar, *bar);
        // 向最终用户泄露内存地址和内部值
    }
}
```

## 检查方法

1. 搜索用户可见的错误输出函数
2. 检查错误消息中是否包含指针值、内存地址、内部状态信息
3. LLM 审查：判断错误输出是否向用户暴露了内部实现细节

## 修复指南

1. 使用 `#ifdef DEBUG` / `#ifndef NDEBUG` 包裹调试级别输出
2. 面向用户的错误消息只包含必要的操作指导，不含内部数据
3. 区分日志级别：debug（开发用）vs info（生产用）vs error（用户可见）
