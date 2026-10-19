---
domain: cpp
rule_id: cpp-thread-safe-marking
title: 线程安全标识
priority: main
source_file: rules/C++编程规范.md
source_section: "2.1 线程安全"
status: active
check_method: none
deterministic_check: false
checkability: advisory_only
conflicts_with: []
overrides: []
related_pages:
  - [[cpp-mutex-shared-data]]
  - [[cpp-thread-local]]
  - [[cpp-avoid-datarace-deadlock]]
---

# 线程安全标识

## 规则条款
明确标识线程安全的类和函数：任何可以在多线程环境中被安全调用的类或函数，必须
通过文档注释明确标注线程安全特性。对于非线程安全的代码，也应标注并说明预期的
使用方式（例如仅限主线程调用）。

## 正确示例
```cpp
/**
 * @brief 线程安全计数器
 *
 * 所有公有成员函数均为线程安全，可在多线程环境中直接调用。
 */
class ThreadSafeCounter {
public:
    void increment() {
        std::lock_guard<std::mutex> lock(m_mutex);
        ++m_count;
    }

    int get() const {
        std::lock_guard<std::mutex> lock(m_mutex);
        return m_count;
    }

private:
    mutable std::mutex m_mutex;
    int m_count = 0;
};

/**
 * @brief UI 控制器（非线程安全）
 *
 * 所有方法仅限主线程（GUI 线程）调用。
 */
class UiController {
public:
    void updateDisplay(const std::string& text);
    // 主线程专用
};
```

## 错误示例
```cpp
// 未标注线程安全特性，调用者无法判断是否可跨线程使用
class DataCache {
public:
    void insert(const std::string& key, int value);
    int lookup(const std::string& key) const;

private:
    std::unordered_map<std::string, int> m_data;
};
```

## 检查方法
1. LLM 检查类和函数的文档注释，判断是否包含线程安全说明。
2. 对于公共 API（头文件中声明的类），检查是否缺少并发使用说明。
3. 对于内部实现类，检查注释约定是否标注清晰。

## 修复指南
1. 在类级别的 Doxygen 注释中使用 `@brief` 包含线程安全说明。
2. 线程安全类：标注"线程安全"/"thread-safe"并说明同步机制。
3. 非线程安全类：标注预期的调用方式（单线程、主线程、特定线程）。
4. 部分线程安全类：详细说明哪些方法是线程安全的。

## 审查清单
- [ ] 公共 API 类是否有线程安全文档注释？
- [ ] 非线程安全类是否说明了调用约束？
- [ ] 线程安全类是否说明了使用的同步机制？

## 关联页面
- [[cpp-mutex-shared-data]] — mutex 保护共享数据
- [[cpp-thread-local]] — 线程局部存储
- [[cpp-avoid-datarace-deadlock]] — 避免数据竞争和死锁
