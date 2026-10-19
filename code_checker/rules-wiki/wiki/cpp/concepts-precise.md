---
domain: cpp
rule_id: cpp-concepts-precise
title: Concepts 精确性
priority: main
source_file: rules/C++代码规范.md
source_section: "§5.2 C++20 Concepts"
status: active
check_method: llm
deterministic_check: false
checkability: advisory_only
conflicts_with: []
overrides: []
related_pages:
  - [[cpp-concepts-cpp20]]
  - [[cpp-concepts-naming]]
  - [[cpp-concepts-std-first]]
  - [[cpp-template-constraints]]
---

# Concepts 精确性

## 规则条款
概念应尽可能精确地约束 requirements：既不过于宽松（accepts types that don't actually work），也不过于严格（rejects types that would work）。精确的概念让模板的接口契约一目了然，同时避免误用或不必要的限制。

精确性原则：
1. **必要且充分**：约束应包含模板体实际使用的所有操作，不多于也不少于。
2. **语义正确**：约束应表达语义需求（如 `std::equality_comparable`），而非仅语法需求（如 `a == b` 编译通过即可）。
3. **可组合**：精确的概念更容易组合出更复杂的概念。
4. **可读**：精确的概念本身就是一份文档，清晰表达了对类型的要求。

## 正确示例
```cpp
#include <concepts>
#include <ranges>
#include <iterator>

// 精确约束：需要输入范围 + 可排序的值类型
template <std::ranges::input_range Range>
    requires std::sortable<std::ranges::iterator_t<Range>>
void sort(Range&& r) {
    std::ranges::sort(std::forward<Range>(r));
}

// 精确约束：需要可调用且返回可转换为 size_t
template <typename Func, typename... Args>
    requires std::invocable<Func, Args...> &&
             std::convertible_to<std::invoke_result_t<Func, Args...>, size_t>
size_t measureExecution(Func&& f, Args&&... args) {
    auto start = std::chrono::high_resolution_clock::now();
    auto result = std::invoke(std::forward<Func>(f), std::forward<Args>(args)...);
    return static_cast<size_t>(result);
}

// 精确的自定义概念：迭代器必须可解引用且值类型可写入流
template <typename Iterator>
concept PrintableIterator =
    std::input_iterator<Iterator> &&
    requires(std::iter_value_t<Iterator> v, std::ostream& os) {
        { os << v } -> std::convertible_to<std::ostream&>;
    };

template <PrintableIterator Iter>
void printAll(Iter first, Iter last, std::ostream& os = std::cout) {
    while (first != last) {
        os << *first << ' ';
        ++first;
    }
}

// 语义正确的概念：不仅语法通过，语义也正确
template <typename T>
concept HashKey = std::semiregular<T> &&              // 可拷贝/移动
                  std::equality_comparable<T> &&       // 可相等比较（语义）
                  requires(T v) {
                      { std::hash<T>{}(v) } -> std::convertible_to<std::size_t>;
                  };

template <HashKey Key, typename Value>
class HashTable {
    // Key 不仅可哈希（语法），还满足语义前提（可比较）
};
```

## 错误示例
```cpp
// 过于宽松：模板体需要 operator+ 但概念不要求
template <typename T>
concept Addable = true;  // 接受所有类型，完全不检查

template <Addable T>
T sum(T a, T b) {
    return a + b;        // 对无 operator+ 的类型，错误信息在内部
}

// 过于宽松：约束了语法但忽略了语义前提
template <typename T>
concept HasMultiply = requires(T a, T b) {
    { a * b };           // 只检查语法：a * b 能编译
};                       // 不要求返回类型，不要求结合律等语义

template <HasMultiply T>
T matrixDet(const T& m) {
    // 需要 matrix * matrix = matrix 的语义，但概念只检查语法通过
}

// 过于严格：概念要求了并非实际需要的操作
template <typename T>
concept MyContainer = requires(T c) {
    typename T::value_type;
    { c.size() } -> std::convertible_to<size_t>;
    { c[0] } -> std::convertible_to<typename T::value_type>;
    { c.begin() } -> std::input_iterator;  // 约束了迭代器类型
    { c.clear() };                          // 函数内部并不需要 clear
    { c.reserve(0) };                       // 函数内部并不需要 reserve
};

// 语义问题：只检查操作存在，不检查操作的语义关系
template <typename T>
concept BadComparable = requires(T a, T b) {
    { a == b } -> std::convertible_to<bool>;  // 语法 OK
};  // 但未要求 a == b 的语义：自反性、对称性、传递性
    // 正确做法：直接使用 std::equality_comparable
```

## 检查方法
1. 审查每个概念的 `requires` 表达式，逐项检查约束是否被模板体实际使用。
2. 检查是否存在"missing constraints"——模板体内使用了未在概念中约束的操作。
3. 检查是否存在"extraneous constraints"——概念中约束了模板体未使用的操作。
4. 评估语义层次：概念是否仅约束了语法（操作可编译），还是也约束了语义（操作之间的关系）。
5. LLM 分析：概念约束与模板体之间的差异——是否有缺失、多余或不精确的约束。
6. 对自定义概念，判断是否可以用标准概念组合出更精确的表达。

## 修复指南

### 缺失约束（过于宽松）
```cpp
// 之前：概念未约束 operator+
template <typename T>
concept Numeric = std::integral<T> || std::floating_point<T>;
// 但模板体内使用了 a + b、a * b 等——这些需要明确的算术约束

// 修复：确保概念涵盖所有实际使用的操作
```

### 多余约束（过于严格）
```cpp
// 之前：约束了不需要的操作
template <typename T>
concept MovableAndDefault = std::movable<T> && requires { T{}; };
// 如果模板体不需要默认构造，不应约束它

// 修复：移除不需要的约束
template <typename T>
concept MovableOnly = std::movable<T>;
```

### 提升语义层次
```cpp
// 之前：仅语法约束
template <typename T>
concept Eq = requires(T a, T b) { { a == b } -> std::convertible_to<bool>; };

// 修复：使用标准语义概念
// 直接使用 std::equality_comparable
```

## 审查清单
- [ ] 概念中每个约束项是否在模板体中实际使用？
- [ ] 模板体中每个类型操作是否在概念中有对应约束？
- [ ] 概念是否表达了语义需求而不仅是语法需求？
- [ ] 是否避免了仅检查"是否可编译"而无语义保证的约束？
- [ ] 概念能否在不破坏调用方的前提下被更精确地表达？
- [ ] 复杂概念是否通过组合更简单、更精确的子概念构建？

## 关联页面
- [[cpp-concepts-cpp20]] — C++20 Concepts 强制使用
- [[cpp-concepts-naming]] — Concepts 命名规范
- [[cpp-concepts-std-first]] — 优先使用标准概念
- [[cpp-template-constraints]] — 模板约束的通用规则
