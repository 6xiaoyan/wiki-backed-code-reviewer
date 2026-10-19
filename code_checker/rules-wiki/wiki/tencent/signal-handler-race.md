---
domain: tencent
rule_id: tencent-signal-handler-race
title: 注意 signal handler 导致的条件竞争
priority: sub
source_file: rules/Tencent_C++_Security_Guide.md
source_section: "§3.2"
status: active
check_method: llm
deterministic_check: false
checkability: llm_checkable
conflicts_with: []
overrides: []
related_pages:
  - [[cpp/mutex-shared-data]]
---

# 注意 signal handler 导致的条件竞争

> 来源：腾讯 C/C++ 安全指南 §3.2 | 风险：内存损坏（高）、逻辑错误（中）

## 规则条款

信号处理器异步运行。从处理器调用非重入函数（如 `free`、`malloc`、`syslog`）可能损坏全局状态，导致 double-free、use-after-free 或代码执行。

## 缓解措施

1. 避免信号处理器间的共享状态
2. 如需在处理器内使用同步
3. 屏蔽无关信号以保证原子性
4. 仅调用 [async-signal-safe](https://www.man7.org/linux/man-pages/man7/signal-safety.7.html) 函数：`write`、`_exit`、`signal`、`abort` 等，禁止调用 `printf`、`malloc`、`free`

## 检查方法

1. 搜索 `signal()` 和 `sigaction()` 调用
2. 检查信号处理函数中是否调用了非 async-signal-safe 函数
3. LLM 审查

## 修复指南

1. 信号处理函数中只做最少的操作（如设置 `volatile sig_atomic_t` 标志）
2. 将实际处理逻辑放在主循环中轮询标志
3. 使用 `sigaction` 而非 `signal`（行为更明确）
