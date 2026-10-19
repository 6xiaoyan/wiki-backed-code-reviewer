---
domain: cpp
rule_id: cpp-atomic-lockfree
title: 原子操作与无锁编程
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
  - [[cpp-atomics-vs-locks]]
  - [[cpp-memory-order]]
  - [[cpp-avoid-datarace-deadlock]]
---

# 原子操作与无锁编程

## 规则条款
对于简单的共享状态（计数器、标志位等），使用 `std::atomic` 原子操作进行无锁编程，避免互斥锁的开销。原子操作适用于状态简单、操作单一的并发场景。复杂的数据结构更新仍应使用互斥锁。

## 正确示例
```cpp
class RequestCounter {
public:
    void onRequest() {
        m_total.fetch_add(1, std::memory_order_relaxed);
        m_active.fetch_add(1, std::memory_order_release);
    }

    void onResponse() {
        m_active.fetch_sub(1, std::memory_order_acquire);
    }

    int totalRequests() const {
        return m_total.load(std::memory_order_relaxed);
    }

    int activeRequests() const {
        return m_active.load(std::memory_order_acquire);
    }

private:
    std::atomic<int> m_total{0};
    std::atomic<int> m_active{0};
};

class SpinLock {
public:
    void lock() {
        while (m_flag.test_and_set(std::memory_order_acquire)) {
            // 自旋等待
        }
    }

    void unlock() {
        m_flag.clear(std::memory_order_release);
    }

private:
    std::atomic_flag m_flag = ATOMIC_FLAG_INIT;
};
```

## 错误示例
```cpp
// 复杂操作不适合无锁编程：容易引入 ABA 问题
std::atomic<Node*> m_head;

void push(int value) {
    Node* newNode = new Node{value, nullptr};
    // 错误的 CAS 循环：未处理 ABA 问题
    newNode->next = m_head.load();
    while (!m_head.compare_exchange_weak(newNode->next, newNode)) {
        // 空循环体，可能需要重试多次
    }
}

// 原子操作不足以保护复杂数据
struct Widget {
    int a;
    double b;
    std::string c;  // std::string 不是 trivially copyable
};

std::atomic<Widget> w;  // 编译错误：不满足 is_trivially_copyable
```

## 检查方法
1. LLM 审查 `std::atomic` 的使用场景，判断操作的复杂度
2. 对于多变量原子操作，检查是否存在逻辑上的竞态窗口
3. 验证 CAS 循环中是否正确处理了 ABA 问题
4. 确认原子对象满足 `std::is_trivially_copyable`

## 修复指南
1. 简单标志/计数器 → 使用 `std::atomic`，默认 `memory_order_seq_cst`
2. CAS 循环 → 确保 compare-exchange 的 expected 参数在失败时被正确更新
3. 多个原子变量关联 → 考虑用 mutex 替代，或使用双缓冲/无锁队列
4. 复杂对象 → 使用 `std::shared_ptr` 的原子操作或回退到互斥锁
5. 对于指针 CAS，使用 `std::atomic<std::shared_ptr<T>>`（C++20）或 hazard pointer

## 审查清单
- [ ] 原子操作是否仅用于简单类型（int、指针、bool）
- [ ] CAS 循环是否正确处理失败重试
- [ ] 是否考虑了 ABA 问题（含指针的 CAS）
- [ ] 是否存在多个原子变量间的隐式不变量

## 关联页面
- [[cpp-atomics-vs-locks]] — 原子操作 vs 锁的选择
- [[cpp-memory-order]] — 内存顺序规范
- [[cpp-avoid-datarace-deadlock]] — 避免数据竞争与死锁
