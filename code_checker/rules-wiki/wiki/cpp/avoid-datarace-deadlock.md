---
domain: cpp
rule_id: cpp-avoid-datarace-deadlock
title: 避免数据竞争与死锁
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
  - [[cpp-mutex-shared-data]]
  - [[cpp-atomic-lockfree]]
  - [[cpp-scoped-lock]]
  - [[cpp-lock-guard]]
---

# 避免数据竞争与死锁

## 规则条款
避免数据竞争和死锁。对于数据竞争，确保所有对共享可变数据的访问都在同步机制的保护下。对于死锁，使用锁层次（lock hierarchy）约定或 `std::scoped_lock` 同时获取多个锁，避免循环等待。

## 正确示例
```cpp
class AccountManager {
public:
    // 使用 scoped_lock 同时获取两个锁，避免死锁
    void transfer(Account& from, Account& to, int amount) {
        std::scoped_lock lock(from.m_mutex, to.m_mutex);
        if (from.m_balance >= amount) {
            from.m_balance -= amount;
            to.m_balance += amount;
        }
    }

    // 锁层次约定：先锁外层再锁内层
    void updateLedger(Account& account) {
        std::lock_guard<std::mutex> lock(m_ledgerMutex);  // 外层
        std::lock_guard<std::mutex> acctLock(account.m_mutex);  // 内层
        m_ledger.push_back(account.m_balance);
    }

private:
    std::mutex m_ledgerMutex;
    std::vector<int> m_ledger;
};

struct Account {
    std::mutex m_mutex;
    int m_balance = 0;
};
```

## 错误示例
```cpp
class AccountManager {
public:
    // 两个线程以相反顺序加锁 → 死锁风险
    // 线程A: transfer(acc1, acc2, 100)
    // 线程B: transfer(acc2, acc1, 50)
    void transfer(Account& from, Account& to, int amount) {
        std::lock_guard<std::mutex> lock1(from.m_mutex);
        std::lock_guard<std::mutex> lock2(to.m_mutex);
        from.m_balance -= amount;
        to.m_balance += amount;
    }

    // 数据竞争：m_counter 在无保护下被多线程读写
    int m_counter = 0;

    void increment() {
        ++m_counter;  // 非原子操作，数据竞争
    }
};
```

## 检查方法
1. LLM 扫描存在多个 mutex 的作用域，识别可能的循环锁定顺序
2. 检查是否存在对同一变量的无保护并发读写
3. 验证使用了 RAII 锁管理（lock_guard、scoped_lock 等）
4. 识别可能存在锁反转（lock inversion）的代码路径

## 修复指南
1. 多个锁同时获取：使用 `std::scoped_lock` 一次性锁定
2. 定义锁获取顺序规范（如按地址排序），所有代码路径遵守
3. 对单一共享变量使用 `std::atomic` 替代 mutex
4. 考虑无锁设计：消息队列、不可变数据结构、写时复制
5. 使用 ThreadSanitizer（TSan）运行时检测数据竞争

## 审查清单
- [ ] 是否存在同时持有多个锁的代码路径
- [ ] 多锁获取顺序是否在所有路径中一致
- [ ] 所有共享数据是否在同步原语保护下访问
- [ ] 是否使用了 RAII 锁管理避免异常导致的死锁

## 关联页面
- [[cpp-scoped-lock]] — scoped_lock 多锁获取
- [[cpp-lock-guard]] — lock_guard 优先
- [[cpp-atomic-lockfree]] — 原子操作与无锁编程
