---
domain: cpp
rule_id: cpp-atomics-vs-locks
title: 原子操作 vs 锁的选择
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
  - [[cpp-memory-order]]
  - [[cpp-lock-guard]]
  - [[cpp-scoped-lock]]
---

# 原子操作 vs 锁的选择

## 规则条款
简单操作用原子操作，复杂操作用锁。判断标准：如果临界区包含单个读写操作（计数器递增、标志位翻转），使用 `std::atomic`；如果临界区涉及多个变量、分支逻辑或多步骤操作，使用 `std::mutex`。

## 正确示例
```cpp
class ConnectionManager {
public:
    // 简单计数器 → 原子操作
    void acceptConnection() {
        m_connectedCount.fetch_add(1, std::memory_order_relaxed);
    }

    void dropConnection() {
        m_connectedCount.fetch_sub(1, std::memory_order_relaxed);
    }

    int getConnectionCount() const {
        return m_connectedCount.load(std::memory_order_relaxed);
    }

    // 复杂操作：更新多个字段 → 互斥锁
    void updateSession(int connId, const SessionInfo& info) {
        std::lock_guard<std::mutex> lock(m_sessionsMutex);
        auto it = m_sessions.find(connId);
        if (it != m_sessions.end()) {
            it->second.lastActive = info.lastActive;
            it->second.dataTransferred += info.bytesTransferred;
            if (info.bytesTransferred > m_maxTransferThreshold) {
                it->second.isThrottled = true;
            }
        }
    }

private:
    std::atomic<int> m_connectedCount{0};

    std::mutex m_sessionsMutex;
    std::unordered_map<int, SessionInfo> m_sessions;
    int m_maxTransferThreshold = 1024;
};
```

## 错误示例
```cpp
// 简单标志位却使用了重量级 mutex
bool m_isReady = false;
std::mutex m_readyMutex;

void setReady() {
    std::lock_guard<std::mutex> lock(m_readyMutex);  // 过度设计
    m_isReady = true;
}

// 复杂多变量更新却使用了原子操作（逻辑竞态）
std::atomic<int> m_size{0};
std::atomic<int> m_sum{0};

void addValue(int val) {
    m_size.fetch_add(1);  // 两步之间可能出现不一致窗口
    m_sum.fetch_add(val);  // 其他线程可能读到 size 已更新但 sum 未更新
}
```

## 检查方法
1. LLM 分析临界区复杂度：单一变量 vs 多变量，简单操作 vs 分支逻辑
2. 对于原子操作，检查是否存在多个原子变量之间的逻辑关联
3. 对于 mutex，评估是否可以用 `std::atomic` 简化
4. 判断临界区是否包含 I/O、系统调用或未知耗时的函数调用

## 修复指南
1. 单个 `int`/`bool`/指针 → 替换为 `std::atomic`
2. 多个变量需保持一致性 → 使用 mutex 保护整个临界区
3. 简单读写锁 → 考虑 `std::atomic` + 适当 `memory_order`
4. 只在确需条件变量或等待时使用 `std::condition_variable` + mutex
5. 性能热点处的简单操作优先考虑无锁方案

## 审查清单
- [ ] 是否存在用 mutex 保护单个简单变量的情况
- [ ] 是否存在多个 atomic 变量之间存在隐式关联
- [ ] 临界区复杂度是否与同步机制匹配
- [ ] 是否考虑了性能与正确性的权衡

## 关联页面
- [[cpp-atomic-lockfree]] — 原子操作与无锁编程
- [[cpp-memory-order]] — 内存顺序规范
- [[cpp-lock-guard]] — lock_guard 优先
- [[cpp-scoped-lock]] — scoped_lock 多锁获取
