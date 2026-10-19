---
domain: cpp
rule_id: cpp-noexcept-spec
title: noexcept 规范
priority: main
source_file: rules/C++代码规范.md
source_section: "§4.1 异常使用规范"
status: active
check_method: llm
deterministic_check: false
checkability: llm_checkable
conflicts_with: []
overrides: []
related_pages:
  - [[cpp-no-throw-spec]]
  - [[cpp-no-throw-dtor]]
  - [[cpp-exception-not-for-flow]]
---

# noexcept 规范

## 规则条款
使用 `noexcept` 关键字正确标记不抛出异常的函数。以下函数应标记为 `noexcept`：析构函数（默认已是）、移动构造函数、移动赋值运算符、swap 函数、以及所有已确认不抛出异常的函数。正确使用 `noexcept` 有助于编译器生成更优化的代码，也帮助调用方了解函数的异常安全性。

## 正确示例
```cpp
#include <utility>
#include <vector>

class SafeType {
public:
    // 析构函数隐式 noexcept
    ~SafeType() = default;

    // 移动构造函数和移动赋值标记 noexcept
    SafeType(SafeType&& other) noexcept
        : m_data(std::exchange(other.m_data, nullptr))
        , m_size(std::exchange(other.m_size, 0)) {}

    SafeType& operator=(SafeType&& other) noexcept {
        if (this != &other) {
            delete[] m_data;
            m_data = std::exchange(other.m_data, nullptr);
            m_size = std::exchange(other.m_size, 0);
        }
        return *this;
    }

    // swap 标记 noexcept
    friend void swap(SafeType& a, SafeType& b) noexcept {
        using std::swap;
        swap(a.m_data, b.m_data);
        swap(a.m_size, b.m_size);
    }

    // 确定不抛异常的工具函数
    size_t size() const noexcept { return m_size; }
    bool empty() const noexcept { return m_size == 0; }

private:
    int* m_data = nullptr;
    size_t m_size = 0;
};

// 条件 noexcept：取决于模板参数的操作是否不抛异常
template <typename T>
void conditionalSwap(T& a, T& b)
    noexcept(std::is_nothrow_move_constructible_v<T> &&
             std::is_nothrow_move_assignable_v<T>) {
    T tmp = std::move(a);
    a = std::move(b);
    b = std::move(tmp);
}
```

## 错误示例
```cpp
class BadType {
public:
    // 错误 1: 移动操作未标记 noexcept
    // 标准库容器在使用时不会选择移动优化，会退化为拷贝
    BadType(BadType&& other) : m_data(other.m_data) {  // 缺少 noexcept
        other.m_data = nullptr;
    }

    BadType& operator=(BadType&& other) {  // 缺少 noexcept
        m_data = other.m_data;
        other.m_data = nullptr;
        return *this;
    }

    // 错误 2: 明确不抛异常的函数未标记 noexcept
    int getValue() const { return m_value; }  // 应标记 noexcept
    // 正确: int getValue() const noexcept { return m_value; }

private:
    int* m_data = nullptr;
    int m_value = 0;
};

// std::vector 使用 BadType 时：
void test() {
    std::vector<BadType> vec;
    vec.push_back(BadType{});
    // 扩容时因移动操作非 noexcept，vector 会拷贝而非移动，
    // 降低性能且可能改变语义
}
```

## 检查方法
LLM 辅助检查（非确定性）：

1. 检查移动构造函数和移动赋值运算符是否标记 `noexcept`。
2. 检查 `swap` 函数（自定义或特化）是否标记 `noexcept`。
3. 检查明确不抛出异常的函数（如简单的 getter、empty/size 检查）是否标记 `noexcept`。
4. 审查 `noexcept` 标记是否与函数体实际行为一致——标记了 `noexcept` 但内部可能抛异常是严重错误。
5. 对于模板函数，检查是否使用条件 `noexcept` 表达式。

## 修复指南
1. 对所有移动构造函数添加 `noexcept` 关键字。
2. 对所有移动赋值运算符添加 `noexcept` 关键字。
3. 自定义 `swap` 函数添加 `noexcept`。
4. 简单的只读访问函数（getter、empty、size、capacity）添加 `noexcept`。
5. 使用条件 `noexcept` 表达式编写泛型代码：`noexcept(noexcept(expr))`。
6. 不要在没有把握时随意添加 `noexcept`——标记后实际抛异常会调用 `std::terminate()`。

## 审查清单
- [ ] 移动构造函数标记 `noexcept`
- [ ] 移动赋值运算符标记 `noexcept`
- [ ] 自定义 `swap` 函数标记 `noexcept`
- [ ] 析构函数不额外添加 `noexcept(false)`（默认 `noexcept(true)` 是正确的）
- [ ] `noexcept` 标记与函数实际行为一致（未虚假标记）
- [ ] 模板代码使用条件 `noexcept` 表达式
- [ ] `noexcept` 的使用不阻碍可恢复的错误处理路径

## 关联页面
- [[cpp-no-throw-spec]] — 禁止废弃的 throw() 异常规范
- [[cpp-no-throw-dtor]] — 析构函数禁止抛异常
- [[cpp-exception-not-for-flow]] — 异常不应用于控制流
