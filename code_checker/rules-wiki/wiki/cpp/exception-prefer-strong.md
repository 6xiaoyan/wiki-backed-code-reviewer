---
domain: cpp
rule_id: cpp-exception-prefer-strong
title: 异常安全保证优先级
priority: main
source_file: rules/C++代码规范.md
source_section: "§4.2 异常安全"
status: active
check_method: llm
deterministic_check: false
checkability: llm_checkable
conflicts_with: []
overrides: []
related_pages:
  - [[cpp-exception-safety-guarantees]]
  - [[cpp-exception-raii-safety]]
---

# 异常安全保证优先级

## 规则条款
在编写函数时，应按以下优先级选择异常安全保证：
1. **首选不抛保证（nothrow）** — 如果函数逻辑不会抛出异常，显式标记 `noexcept`。
2. **次选强异常安全保证** — 操作失败时状态完全回滚（事务语义）。
3. **基本异常安全保证是底线** — 最差也必须保证异常发生时无资源泄漏、对象可安全析构。

不允许存在"无保证"（no guarantee）的代码。基本异常安全保证是所有函数的最小要求。

## 正确示例
```cpp
// 优先级 1：不抛保证 — 简单的数据访问和交换
class Widget {
public:
    int getId() const noexcept { return m_id; }
    void setId(int id) noexcept { m_id = id; }

    void swap(Widget& other) noexcept {
        using std::swap;
        swap(m_id, other.m_id);
        swap(m_name, other.m_name);
    }

private:
    int m_id = 0;
    std::string m_name;
};

// 优先级 2：强异常安全保证 — 使用 copy-and-swap
Widget& Widget::operator=(const Widget& other) {
    Widget temp(other);    // 可能抛异常，但 *this 未改变
    swap(temp);            // 不抛，提交修改
    return *this;
}                          // temp 析构，释放旧资源

// 优先级 3：基本异常安全保证 — 至少不泄漏
void appendLog(const std::string& entry) {
    m_entries.push_back(entry);   // 如果抛异常，vector 保持原样且不泄漏
    m_lastUpdate = now();         // 如果抛异常，entries 已添加但无泄漏
}
```

## 错误示例
```cpp
// 无保证：抛异常导致资源泄漏
void processRecords(const std::string& path) {
    auto* conn = new DatabaseConnection(path);  // 裸指针
    conn->open();                                // 可能抛异常
    auto* transaction = conn->beginTransaction(); // 可能抛异常 → conn 泄漏
    transaction->execute("UPDATE ...");           // 可能抛异常 → 两者均泄漏
    delete transaction;                           // 永远执行不到
    delete conn;
}

// 无保证：抛异常导致对象状态损坏
void badVector::pushMany(const int* items, size_t count) {
    m_size = 0;                            // 先破坏状态
    for (size_t i = 0; i < count; ++i) {
        m_data[i] = items[i];              // 可能抛异常 → m_size 为 0，数据不一致
        ++m_size;
    }
}
```

## 检查方法
1. 审查每个公开函数是否显式标注了异常安全保证等级。
2. 对存在修改操作的函数，检查是否可以通过不抛操作（swap、移动）重构为强保证。
3. 标记为 `noexcept` 的函数是否存在内部调用可能抛异常的函数。
4. 用 LLM 分析函数路径：是否存在"先破坏旧状态、再逐步构建新状态"的模式——这种模式在异常时无法回滚。
5. 检查是否有 `new`、裸指针手动管理、或异常路径上缺少 `catch` 导致的资源泄漏。

## 修复指南
- **提升到 noexcecept**：将析构函数、移动构造函数、移动赋值运算符、swap 函数标记为 `noexcept`（这些在 C++ 标准实践中通常不应抛异常）。
- **重构为强保证**：采用 copy-and-swap 惯用法，确保修改操作在异常发生时能完全回滚。
- **至少满足基本保证**：将所有堆资源用智能指针或 RAII 类包装，确保析构函数在异常路径上被调用。
- **消除裸 new/delete**：用 `std::make_unique` / `std::make_shared` 替代手动内存管理。

## 审查清单
- [ ] 析构函数是否隐式 `noexcept`（默认）或显式标记？
- [ ] 移动构造函数和移动赋值运算符是否标记了 `noexcept`？
- [ ] swap 函数是否标记了 `noexcept`？
- [ ] 赋值运算符是否使用 copy-and-swap 提供强保证？
- [ ] 所有资源是否由 RAII 对象管理（无裸露的 `new`/`delete`）？

## 关联页面
- [[cpp-exception-safety-guarantees]] — 三种异常安全保证的详细定义
- [[cpp-exception-raii-safety]] — RAII 与异常安全的配合使用
