---
domain: cpp
rule_id: cpp-thread-local
title: 线程局部存储优先
priority: main
source_file: rules/C++代码规范.md
source_section: "§6.1 线程安全"
status: active
check_method: llm
deterministic_check: false
checkability: llm_checkable
conflicts_with: []
overrides: []
related_pages:
  - [[cpp-thread-safe-marking]]
  - [[cpp-mutex-shared-data]]
  - [[cpp-avoid-datarace-deadlock]]
---

# 线程局部存储优先

## 规则条款
在需要每个线程拥有独立实例的场景中，优先使用 `thread_local` 线程局部存储，而非全局或静态变量加锁保护。`thread_local` 变量每个线程拥有独立副本，天然避免数据竞争，且无需同步开销。

## 正确示例
```cpp
// 每个线程拥有独立的随机数生成器，无需加锁
thread_local std::mt19937 t_randomEngine(std::random_device{}());

int generateRandomId() {
    std::uniform_int_distribution<int> dist(1000, 9999);
    return dist(t_randomEngine);
}

// 每个线程独立的日志缓冲区，避免全局锁争用
thread_local std::ostringstream t_logBuffer;

void appendLog(const std::string& message) {
    t_logBuffer << message << '\n';
}
```

## 错误示例
```cpp
// 全局变量 + 互斥锁：每个线程调用都需要获取锁
static std::mt19937 s_randomEngine(std::random_device{}());
static std::mutex s_randomMutex;

int generateRandomId() {
    std::lock_guard<std::mutex> lock(s_randomMutex);
    std::uniform_int_distribution<int> dist(1000, 9999);
    return dist(s_randomEngine);
}
```

## 检查方法
1. LLM 识别全局或静态变量，判断是否为每线程独立使用的场景
2. 检查是否存在为了消除竞态而给全局变量加锁的模式
3. 评估是否可以用 `thread_local` 替代加锁方案
4. 注意 `thread_local` 不适用于需要跨线程共享状态的场景

## 修复指南
1. 将每线程独立的全局变量改为 `thread_local` 声明
2. 移除因此不再需要的互斥锁
3. 注意 `thread_local` 变量的生命周期：随线程创建而构造，随线程退出而析构
4. 对于大量 `thread_local` 变量，注意可能的初始化开销
5. 不能用 `thread_local` 替代的场景：线程间确实需要共享状态时，保留 mutex 方案

## 审查清单
- [ ] 是否存在仅被单线程使用的全局/静态变量
- [ ] 是否可以用 thread_local 消除不必要的锁
- [ ] thread_local 变量的析构顺序是否考虑
- [ ] 是否正确区分了"每线程独立"与"线程间共享"

## 关联页面
- [[cpp-thread-safe-marking]] — 线程安全标识
- [[cpp-mutex-shared-data]] — mutex 保护共享数据
- [[cpp-avoid-datarace-deadlock]] — 避免数据竞争与死锁
