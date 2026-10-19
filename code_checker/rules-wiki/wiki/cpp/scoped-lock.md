---
domain: cpp
rule_id: cpp-scoped-lock
title: scoped_lock 多锁获取
priority: main
source_file: rules/C++代码规范.md
source_section: "§6.2 原子操作与锁"
status: active
check_method: regex
deterministic_check: true
checkability: deterministic
conflicts_with: []
overrides: []
related_pages:
  - [[cpp-lock-guard]]
  - [[cpp-avoid-datarace-deadlock]]
---

# scoped_lock 多锁获取

## 规则条款
当需要同时持有多个互斥锁时，必须使用 `std::scoped_lock`（C++17）一次性获取所有锁，避免因不同代码路径以不同顺序加锁而导致死锁。`std::scoped_lock` 使用与 `std::lock` 相同的死锁避免算法，安全地同时锁定多个 mutex。

## 正确示例
```cpp
class BankSystem {
public:
    // scoped_lock 同时获取两个锁，无死锁风险
    bool transfer(Account& from, Account& to, int amount) {
        std::scoped_lock lock(from.m_mutex, to.m_mutex);
        if (from.m_balance >= amount) {
            from.m_balance -= amount;
            to.m_balance += amount;
            return true;
        }
        return false;
    }

    // 同时锁定三个资源
    void mergeRecords(Account& a, Account& b, Account& c) {
        std::scoped_lock lock(a.m_mutex, b.m_mutex, c.m_mutex);
        c.m_balance = a.m_balance + b.m_balance;
        a.m_balance = 0;
        b.m_balance = 0;
    }

    // 单一锁场景可用 scoped_lock 或 lock_guard
    void simpleUpdate(Account& a, int delta) {
        std::scoped_lock lock(a.m_mutex);  // C++17 同样支持单锁
        a.m_balance += delta;
    }
};

struct Account {
    std::mutex m_mutex;
    int m_balance = 0;
};
```

## 错误示例
```cpp
class BankSystem {
public:
    // 嵌套 lock_guard：以不同参数顺序调用时可死锁
    // transfer(acc1, acc2, 100) 和 transfer(acc2, acc1, 50) 同时执行 → 死锁
    bool transferBad(Account& from, Account& to, int amount) {
        std::lock_guard<std::mutex> lock1(from.m_mutex);
        std::lock_guard<std::mutex> lock2(to.m_mutex);
        // 临界区
        from.m_balance -= amount;
        to.m_balance += amount;
        return true;
    }

    // 手动 lock 顺序也可死锁
    bool transferManual(Account& from, Account& to, int amount) {
        from.m_mutex.lock();
        to.m_mutex.lock();  // 不同调用顺序 = 死锁
        from.m_balance -= amount;
        to.m_balance += amount;
        to.m_mutex.unlock();
        from.m_mutex.unlock();
        return true;
    }
};
```

## 检查方法
1. 正则检测：搜索同一作用域内存在多个 `std::lock_guard` 声明的情况
2. 正则检测：搜索连续的多个 `.lock()` 调用
3. 验证是否有代码路径以不同顺序获取同一组锁
4. 对于 C++17 之前的代码，检查是否使用了 `std::lock` + `std::lock_guard` + `std::adopt_lock` 惯用法

## 修复指南
1. 同一作用域多锁 → 替换为 `std::scoped_lock lock(m1, m2, ...)`
2. C++14 及之前 → 使用 `std::lock(m1, m2); std::lock_guard l1(m1, std::adopt_lock); std::lock_guard l2(m2, std::adopt_lock);`
3. 如果锁的类型不同（如 mutex + shared_mutex），`std::scoped_lock` 同样适用
4. 如果 C++17 不可用，定义 `std::scoped_lock` 的等效替代

## 审查清单
- [ ] 不存在多个 lock_guard 嵌套获取锁的代码
- [ ] 不存在连续的手动 .lock() 调用
- [ ] 所有多锁获取使用了 scoped_lock 或 std::lock + adopt_lock
- [ ] 锁获取顺序在所有代码路径中一致

## 关联页面
- [[cpp-lock-guard]] — lock_guard 优先
- [[cpp-avoid-datarace-deadlock]] — 避免数据竞争与死锁
