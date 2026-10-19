---
domain: cpp
rule_id: cpp-template-meaningful-names
title: 模板参数命名
priority: main
source_file: rules/C++代码规范.md
source_section: "§5.1 模板编程"
status: active
check_method: llm
deterministic_check: false
checkability: llm_checkable
conflicts_with: []
overrides: []
related_pages:
  - [[cpp-template-over-macros]]
  - [[cpp-template-constraints]]
  - [[cpp-concepts-cpp20]]
---

# 模板参数命名

## 规则条款
模板参数应使用有意义的名称，遵循所期望的概念约束。命名应传达该类型参数的语义角色，而非仅仅使用单字母占位符。例如：
- 需要算术运算的类型用 `typename Arithmetic` 而非 `typename T`
- 需要迭代器的类型用 `typename Iterator` 而非 `typename IT`
- 需要容器的类型用 `typename Container` 而非 `typename C`

当模板参数有明确的概念时，命名应反映该概念，使代码自文档化。只有在概念非常通用、无法更精确描述时（如泛型 swap 的 `T`），才允许使用短名称。

## 正确示例
```cpp
// 有意义的模板参数名称
template <typename Arithmetic>
Arithmetic average(Arithmetic a, Arithmetic b) {
    return (a + b) / static_cast<Arithmetic>(2);
}

template <typename Iterator>
void sortRange(Iterator first, Iterator last) {
    std::sort(first, last);
}

template <typename Container>
auto firstElement(const Container& container) -> decltype(*container.begin()) {
    return *container.begin();
}

template <typename KeyType, typename ValueType>
class HashMap {
    // KeyType 和 ValueType 明确表达了角色
};

template <typename Predicate>
auto filterIf(const std::vector<int>& data, Predicate pred) -> std::vector<int> {
    std::vector<int> result;
    for (const auto& item : data) {
        if (pred(item)) {
            result.push_back(item);
        }
    }
    return result;
}

// C++20 Concepts 配合有意义的命名
template <std::integral Integer>
Integer gcd(Integer a, Integer b) {
    while (b != 0) {
        Integer t = b;
        b = a % b;
        a = t;
    }
    return a;
}
```

## 错误示例
```cpp
// 无意义的单字母模板参数（在非通用场景下）
template <typename T>           // T 是什么？数字？字符串？容器？
T process(const T& input) {     // 函数名和参数名都没有揭示 T 的语义
    return T{};
}

template <typename A, typename B, typename C>  // A、B、C 各代表什么？
class DataProcessor {                           // 完全无法从命名推断角色
    A m_data;
    B m_config;
    C m_result;
};

template <typename T1, typename T2>  // 没有表达 T1 和 T2 的关系或角色
auto combine(T1 a, T2 b) {
    return a + b;
}
```

## 检查方法
1. 扫描所有 `template<typename ...>` 声明，检查模板参数名是否为单字母或无意义的短名称。
2. 分析参数的实际用途——如果参数有明确角色（算术类型、迭代器、谓词等），命名是否反映了该角色。
3. 对于多参数模板，命名是否足以区分各参数的语义角色。
4. 检查 C++20 Concepts 约束的模板中，参数名是否与概念的语义一致（如 `std::integral` 约束的参数命名为 `Integer` 或 `Integral`）。
5. LLM 辅助判断：模板参数名是否能从名称推断其预期用途。

## 修复指南
- **算术类型参数** → 命名为 `Arithmetic`、`Number`、`Integral`、`FloatingPoint` 等。
- **迭代器参数** → 命名为 `Iterator`、`InputIterator`、`RandomAccessIterator` 等。
- **容器参数** → 命名为 `Container`、`Sequence`、`AssociativeContainer` 等。
- **谓词/可调用对象** → 命名为 `Predicate`、`UnaryOp`、`BinaryOp`、`Callable` 等。
- **分配器参数** → 命名为 `Allocator`。
- **通用场景** → 如果确实无法更精确表达（如 `std::swap<T>`），允许使用 `T`。
- **多模板参数** → 使用 `Key`/`Value`、`Input`/`Output`、`Source`/`Destination` 等配对命名。

## 审查清单
- [ ] 所有模板参数的命名是否传达了该类型的预期语义角色？
- [ ] 是否避免了无意义的单字母命名（`T`、`U`、`V` 等）在非通用场景下的使用？
- [ ] 多参数模板中，每个参数名是否能唯一且清晰地表达其角色？
- [ ] C++20 项目中的模板参数名是否与概念约束的语义一致？
- [ ] 是否存在 `T1`、`T2`、`T3` 这类仅靠数字区分的命名？

## 关联页面
- [[cpp-template-over-macros]] — 模板优于宏的泛型编程方式
- [[cpp-template-constraints]] — 使用 SFINAE 或 Concepts 约束模板
- [[cpp-concepts-cpp20]] — C++20 Concepts 强制使用规则
