---
domain: cpp
rule_id: cpp-mutex-shared-data
title: mutex 保护共享数据
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
  - [[cpp-atomic-lockfree]]
  - [[cpp-atomics-vs-locks]]
---

# mutex 保护共享数据

## 规则条款
使用 `std::mutex` 保护多线程间共享的可变数据，但应避免过度使用导致不必要的锁争用。仅在确实存在并发访问的场景下加锁，控制临界区范围尽可能小，避免长时间持锁。

## 正确示例
```cpp
class SharedBuffer {
public:
    void write(int value) {
        std::lock_guard<std::mutex> lock(m_mutex);
        m_buffer.push_back(value);
    }

    std::optional<int> read() {
        std::lock_guard<std::mutex> lock(m_mutex);
        if (m_buffer.empty()) {
            return std::nullopt;
        }
        int val = m_buffer.front();
        m_buffer.pop_front();
        return val;
    }

private:
    std::mutex m_mutex;
    std::deque<int> m_buffer;
};
```

## 错误示例
```cpp
class OverLocked {
public:
    int getSum() const {
        std::lock_guard<std::mutex> lock(m_mutex);
        // 耗时计算在锁内执行，阻塞其他线程过久
        int result = 0;
        for (int i = 0; i < 1000000; ++i) {
            result += heavyComputation(i);
        }
        return m_base + result;
    }

    // 线程独占使用，不需要 mutex
    void initOnce() {
        std::lock_guard<std::mutex> lock(m_mutex);
        m_initialized = true;
    }

private:
    int heavyComputation(int x) const;

    mutable std::mutex m_mutex;
    int m_base = 0;
    bool m_initialized = false;
};
```

## 检查方法
1. LLM 扫描类定义，识别声明了 `std::mutex` 或类似同步原语的成员
2. 检查每个加锁临界区的长度和内容
3. 判断是否存在过度加锁（临界区包含耗时操作）或漏加锁（共享数据无保护）
4. 对于仅在单线程场景使用的类，标记不必要的 mutex 使用

## 修复指南
1. 确认共享数据被多个线程访问时才引入 mutex
2. 缩小临界区：将耗时操作（I/O、复杂计算）移到锁外
3. 使用 `std::lock_guard` 确保异常安全
4. 对于初始化场景，考虑使用 `std::call_once` + `std::once_flag` 替代互斥锁
5. 对于读多写少场景，考虑 `std::shared_mutex` 提升并发读性能

## 审查清单
- [ ] 每个 mutex 对应的共享数据是否明确
- [ ] 临界区是否尽可能小
- [ ] 是否避免了在锁内执行耗时操作
- [ ] 是否存在不必要的 mutex（单线程场景）

## 关联页面
- [[cpp-thread-safe-marking]] — 线程安全标识
- [[cpp-atomic-lockfree]] — 原子操作与无锁编程
- [[cpp-atomics-vs-locks]] — 原子操作 vs 锁的选择
