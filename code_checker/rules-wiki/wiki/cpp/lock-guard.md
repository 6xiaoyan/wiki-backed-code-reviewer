---
domain: cpp
rule_id: cpp-lock-guard
title: lock_guard 优先
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
  - [[cpp-scoped-lock]]
  - [[cpp-avoid-datarace-deadlock]]
  - [[cpp-no-user-code-under-lock]]
---

# lock_guard 优先

## 规则条款
优先使用 `std::lock_guard` 进行自动锁管理。仅在需要延迟锁定、提前解锁或与条件变量配合时使用 `std::unique_lock`。禁止手动调用 `.lock()` / `.unlock()`，这容易导致异常不安全和死锁。

## 正确示例
```cpp
class ThreadSafeMap {
public:
    // 标准场景：lock_guard 足够
    void insert(const std::string& key, int value) {
        std::lock_guard<std::mutex> lock(m_mutex);
        m_data[key] = value;
    }

    std::optional<int> find(const std::string& key) const {
        std::lock_guard<std::mutex> lock(m_mutex);
        auto it = m_data.find(key);
        if (it != m_data.end()) {
            return it->second;
        }
        return std::nullopt;
    }

    // 需要延迟锁定 → unique_lock
    void deferredUpdate() {
        std::unique_lock<std::mutex> lock(m_mutex, std::defer_lock);
        // ... 一些不需要锁的准备工作 ...
        lock.lock();
        m_data["status"] = 1;
        lock.unlock();  // 提前释放，减少持锁时间
        // ... 后续不需要锁的工作 ...
    }

    // 配合条件变量 → 必须 unique_lock
    void waitForData() {
        std::unique_lock<std::mutex> lock(m_mutex);
        m_cv.wait(lock, [this] { return !m_data.empty(); });
    }

private:
    mutable std::mutex m_mutex;
    std::unordered_map<std::string, int> m_data;
    std::condition_variable m_cv;
};
```

## 错误示例
```cpp
class BadLocking {
public:
    // 手动 lock/unlock → 异常不安全
    void unsafeInsert(const std::string& key, int value) {
        m_mutex.lock();
        if (key.empty()) {
            m_mutex.unlock();  // 容易忘记 unlock
            return;
        }
        m_data[key] = value;  // 如果这里抛异常，锁永远不被释放
        m_mutex.unlock();
    }

    // 简单场景误用 unique_lock
    void simpleRead(const std::string& key) {
        std::unique_lock<std::mutex> lock(m_mutex);  // lock_guard 更合适
        auto it = m_data.find(key);
    }

private:
    std::mutex m_mutex;
    std::unordered_map<std::string, int> m_data;
};
```

## 检查方法
1. 正则检测：搜索 `.lock()` 和 `.unlock()` 的直接调用
   - 模式：`\w+\.lock\(\)` 和 `\w+\.unlock\(\)`
   - 排除：`lock_guard`、`scoped_lock`、`unique_lock` 内部实现
2. 验证 `std::unique_lock` 的使用是否必要（条件变量、延迟锁定、转移所有权）
3. 检查是否存在未被 RAII 管理的互斥锁对象

## 修复指南
1. 替换所有手动 `.lock()`/`.unlock()` 为 `std::lock_guard`
2. 将简单场景的 `std::unique_lock` 改为 `std::lock_guard`
3. 仅在以下场景保留 `std::unique_lock`：
   - 配合 `std::condition_variable`
   - 使用 `std::defer_lock`、`std::try_to_lock`、`std::adopt_lock`
   - 需要提前 `unlock()` 缩小临界区
   - 需要转移锁所有权
4. 对于同时获取多个锁，使用 `std::scoped_lock`（C++17）

## 审查清单
- [ ] 不存在手动 lock() / unlock() 调用
- [ ] unique_lock 的使用有明确理由
- [ ] 所有 mutex 都由 RAII 锁管理
- [ ] 多锁场景考虑使用 scoped_lock

## 关联页面
- [[cpp-scoped-lock]] — scoped_lock 多锁获取
- [[cpp-avoid-datarace-deadlock]] — 避免数据竞争与死锁
- [[cpp-no-user-code-under-lock]] — 持锁不调用户代码
