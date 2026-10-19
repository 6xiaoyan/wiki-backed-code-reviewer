---
domain: cpp
rule_id: cpp-memory-order
title: 内存顺序规范
priority: main
source_file: rules/C++代码规范.md
source_section: "§6.2 原子操作与锁"
status: active
check_method: llm
deterministic_check: false
checkability: llm_checkable
conflicts_with: []
overrides: []
related_pages:
  - [[cpp-atomic-lockfree]]
  - [[cpp-atomics-vs-locks]]
---

# 内存顺序规范

## 规则条款
使用适当的内存顺序（`memory_order`），默认使用 `std::memory_order_seq_cst`（顺序一致性）。仅在性能关键路径且经过充分分析后，才使用更弱的内存顺序。错误的内存顺序是难以调试的并发 bug 来源。

## 正确示例
```cpp
class ThreadSafeQueue {
public:
    // 默认 seq_cst：安全但可能有性能开销
    void push(int value) {
        m_data.store(value, std::memory_order_seq_cst);
        m_ready.store(true, std::memory_order_seq_cst);
    }

    int pop() {
        while (!m_ready.load(std::memory_order_seq_cst)) {
            std::this_thread::yield();
        }
        int value = m_data.load(std::memory_order_seq_cst);
        m_ready.store(false, std::memory_order_seq_cst);
        return value;
    }

    // 经过性能分析后，使用适当宽松顺序
    void pushOptimized(int value) {
        m_data.store(value, std::memory_order_relaxed);
        m_ready.store(true, std::memory_order_release);  // 发布数据
    }

    int popOptimized() {
        while (!m_ready.load(std::memory_order_acquire)) {  // 获取数据
            std::this_thread::yield();
        }
        int value = m_data.load(std::memory_order_relaxed);
        m_ready.store(false, std::memory_order_relaxed);
        return value;
    }

private:
    std::atomic<int> m_data{0};
    std::atomic<bool> m_ready{false};
};
```

## 错误示例
```cpp
// 错误的 acquire-release 配对：可能读到数据竞争的值
std::atomic<int> m_flag{0};
std::atomic<int> m_sharedData{0};

void writer() {
    m_sharedData.store(42, std::memory_order_relaxed);
    m_flag.store(1, std::memory_order_relaxed);  // 错误：relaxed 不保证发布语义
}

void reader() {
    if (m_flag.load(std::memory_order_relaxed)) {
        // 可能读到 m_sharedData 的旧值
        int x = m_sharedData.load(std::memory_order_relaxed);
    }
}
```

## 检查方法
1. LLM 审查所有显式指定 `memory_order` 的原子操作
2. 验证 acquire-release 配对是否正确：
   - `store(release)` 必须与 `load(acquire)` 配对使用
   - `memory_order_acq_rel` 用于 read-modify-write 操作
3. 检查 `memory_order_relaxed` 的使用是否安全（不依赖跨线程顺序保证）
4. 标记 `memory_order_consume` 的使用（不被推荐，语义模糊）

## 修复指南
1. 不确定时使用默认的 `memory_order_seq_cst`
2. 仅在有性能数据支撑时才降级内存顺序
3. acquire-release 模式：
   - `store(memory_order_release)` 用于"发布"数据
   - `load(memory_order_acquire)` 用于"获取"数据
   - 配对保证所有在 release 前的写入对 acquire 后可见
4. `memory_order_relaxed`：仅适用于独立计数器，不依赖与其他变量的顺序关系
5. 添加注释说明为何选择特定的 memory_order

## 审查清单
- [ ] 是否默认使用了 memory_order_seq_cst
- [ ] acquire 和 release 是否成对出现
- [ ] relaxed 操作是否确实不需要顺序保证
- [ ] 是否避免了 memory_order_consume
- [ ] 弱内存顺序的使用是否有注释说明

## 关联页面
- [[cpp-atomic-lockfree]] — 原子操作与无锁编程
- [[cpp-atomics-vs-locks]] — 原子操作 vs 锁的选择
