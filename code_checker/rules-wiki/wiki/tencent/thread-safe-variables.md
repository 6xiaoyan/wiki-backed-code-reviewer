---
domain: tencent
rule_id: tencent-thread-safe-vars
title: 变量应确保线程安全性
priority: sub
source_file: rules/Tencent_C++_Security_Guide.md
source_section: "§3.1"
status: active
check_method: llm
deterministic_check: false
checkability: llm_checkable
conflicts_with: []
overrides: []
related_pages:
  - [[cpp/atomics-vs-locks]]
  - [[cpp/mutex-shared-data]]
  - [[cpp/atomic-lockfree]]
---

# 变量应确保线程安全性

> 来源：腾讯 C/C++ 安全指南 §3.1 | 风险：内存损坏（高）、逻辑错误（中）

## 规则条款

多线程访问的变量必须使用原子操作或锁进行保护。非原子的读写操作在多个线程之间可能产生撕裂读（torn read）、撕裂写（torn write）或数据竞争，导致未定义行为。

C11 推荐 `<stdatomic.h>`；C++11 推荐 `std::atomic`。

## 正确示例

```c++
// C++11 原子操作
std::atomic<char> g_somechar;
void foo_thread1() { g_somechar += 3; }
void foo_thread2() { g_somechar += 1; }

// 或使用互斥锁
volatile char g_somechar;
std::mutex g_mutex;
void foo_thread1() {
    std::lock_guard<std::mutex> lock(g_mutex);
    g_somechar += 3;
}
```

## 错误示例

```c++
char g_somechar;  // 无保护
void foo_thread1() { g_somechar += 3; }  // 数据竞争！
void foo_thread2() { g_somechar += 1; }  // 同时写入 — 未定义行为
```

## 检查方法

1. 搜索全局变量和静态变量被多个函数修改的模式
2. 检查是否有线程入口函数访问共享变量但未使用 `std::atomic` 或锁
3. ThreadSanitizer（TSan）可在运行时检测数据竞争
4. LLM 审查

## 修复指南

1. 使用 `std::atomic<T>` 保护简单类型的共享变量
2. 使用 `std::mutex` + `std::lock_guard` 保护复杂数据结构的访问
3. 参见 [[cpp/mutex-shared-data]] 和 [[cpp/atomics-vs-locks]]
