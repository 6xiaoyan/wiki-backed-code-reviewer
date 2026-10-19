---
domain: cpp
rule_id: cpp-concepts-std-first
title: 优先使用标准概念
priority: main
source_file: rules/C++代码规范.md
source_section: "§5.2 C++20 Concepts"
status: active
check_method: llm
deterministic_check: false
checkability: llm_checkable
conflicts_with: []
overrides: []
related_pages:
  - [[cpp-concepts-cpp20]]
  - [[cpp-concepts-naming]]
  - [[cpp-concepts-precise]]
---

# 优先使用标准概念

## 规则条款
优先使用 C++20 标准库提供的概念（定义在 `<concepts>`、`<ranges>`、`<iterator>` 等头文件中），而非自行定义语义相同的概念。标准概念经过委员会审查、被广泛理解、且编译器对其有优化的错误信息支持。

常见标准概念及其用途：

| 标准概念 | 头文件 | 约束语义 |
|---|---|---|
| `std::integral<T>` | `<concepts>` | 整数类型 |
| `std::floating_point<T>` | `<concepts>` | 浮点类型 |
| `std::signed_integral<T>` | `<concepts>` | 有符号整数 |
| `std::unsigned_integral<T>` | `<concepts>` | 无符号整数 |
| `std::invocable<F, Args...>` | `<concepts>` | 可调用对象 |
| `std::predicate<F, Args...>` | `<concepts>` | 返回 bool 的可调用对象 |
| `std::regular<T>` | `<concepts>` | 正则类型 |
| `std::semiregular<T>` | `<concepts>` | 半正则类型 |
| `std::equality_comparable<T>` | `<concepts>` | 可相等比较 |
| `std::totally_ordered<T>` | `<concepts>` | 全序类型 |
| `std::movable<T>` | `<concepts>` | 可移动 |
| `std::copyable<T>` | `<concepts>` | 可拷贝 |
| `std::convertible_to<From, To>` | `<concepts>` | 可转换 |
| `std::derived_from<Derived, Base>` | `<concepts>` | 派生关系 |
| `std::ranges::range<T>` | `<ranges>` | 范围（range） |
| `std::ranges::view<T>` | `<ranges>` | 视图（view） |
| `std::ranges::input_range<T>` | `<ranges>` | 输入范围 |
| `std::ranges::forward_range<T>` | `<ranges>` | 前向范围 |
| `std::ranges::bidirectional_range<T>` | `<ranges>` | 双向范围 |
| `std::ranges::random_access_range<T>` | `<ranges>` | 随机访问范围 |
| `std::ranges::contiguous_range<T>` | `<ranges>` | 连续范围 |
| `std::ranges::sized_range<T>` | `<ranges>` | 已知大小范围 |
| `std::input_iterator<T>` | `<iterator>` | 输入迭代器 |
| `std::forward_iterator<T>` | `<iterator>` | 前向迭代器 |
| `std::random_access_iterator<T>` | `<iterator>` | 随机访问迭代器 |

只有当标准概念无法精确表达项目语义，或需要组合多个标准概念并赋予项目特定含义时，才应定义自定义概念。

## 正确示例
```cpp
#include <concepts>
#include <ranges>
#include <iterator>
#include <algorithm>

// 直接使用标准概念
template <std::integral T>
T gcd(T a, T b) {
    while (b != 0) { T t = b; b = a % b; a = t; }
    return a;
}

template <std::ranges::input_range Range>
    requires std::equality_comparable<std::ranges::range_value_t<Range>>
auto countUnique(Range&& r) {
    auto sorted = std::vector(std::ranges::begin(r), std::ranges::end(r));
    std::ranges::sort(sorted);
    return std::ranges::distance(
        std::ranges::unique(sorted).begin(),
        sorted.end()
    );
}

// 组合标准概念形成自定义概念——合理的使用场景
template <typename T>
concept Numeric = std::integral<T> || std::floating_point<T>;

template <Numeric T>
T clamp(T value, T min, T max) {
    return value < min ? min : (value > max ? max : value);
}

// 使用标准概念作为约束的基础
template <std::regular Key, std::semiregular Value>
class Cache {
    std::unordered_map<Key, Value> m_store;
public:
    void put(const Key& k, const Value& v) { m_store[k] = v; }
    std::optional<Value> get(const Key& k) const {
        auto it = m_store.find(k);
        return it != m_store.end() ? std::optional{it->second} : std::nullopt;
    }
};
```

## 错误示例
```cpp
// 重复发明轮子：定义了与标准概念等价的自定义概念
template <typename T>
concept Integer = std::is_integral_v<T>;  // 应直接用 std::integral

template <typename T>
concept Range = requires(T t) {           // 应直接用 std::ranges::range
    std::ranges::begin(t);
    std::ranges::end(t);
};

template <typename T>
concept CanCopy = std::is_copy_constructible_v<T>  // 应直接用 std::copyable
    && std::is_copy_assignable_v<T>;

// 更糟糕：用 SFINAE 实现已有的标准概念
template <typename T>
std::enable_if_t<std::is_invocable_v<T, int, int>, int>
invokeWithInts(T func) {
    return func(1, 2);
}
// 应改为：template <std::invocable<int, int> F>

// 自定义概念名冲突：与标准库概念同名
template <typename T>
concept integral = std::is_integral_v<T>;  // 冲突：标准库已有 std::integral
// 如果必须定义，应放入命名空间且使用不同名称
```

## 检查方法
1. 扫描项目中的 `concept` 定义，检查是否存在与标准概念语义等价的自定义版本。
2. 对每个自定义概念，判断是否可以用一个或多个标准概念的组合表达。
3. 检查模板约束中是否使用了 `std::enable_if` 配合 `std::is_*` 而非标准概念（在 C++20 项目中）。
4. LLM 分析：自定义概念的语义与标准概念的语义是否重叠。

## 修复指南
- **等价替换**：
  - 自定义 `Integral`/`Integer` → `std::integral`
  - 自定义 `Float`/`FloatingPoint` → `std::floating_point`
  - 自定义 `Range` → `std::ranges::range` / `std::ranges::input_range`
  - 自定义 `Callable` → `std::invocable`
  - 自定义 `Copyable` → `std::copyable`
- **组合保留**：如果自定义概念组合了多个标准概念并赋予项目语义（如 `Numeric = std::integral || std::floating_point`），可以保留。
- **项目特定概念**：只有涉及项目特定类型层次或领域语义时，才定义全新概念。
- **检查头文件**：确保包含了正确的标准概念头文件（`<concepts>`、`<ranges>`、`<iterator>` 等）。

## 审查清单
- [ ] 是否已包含 `<concepts>` 头文件？
- [ ] 自定义概念是否与标准概念语义等价？
- [ ] 模板约束中是否使用了 `std::enable_if` + `std::is_*` 而非标准概念？
- [ ] 是否引用了不存在或错误的标准概念名？
- [ ] 自定义概念名是否与 `std::` 命名空间下的概念冲突？

## 关联页面
- [[cpp-concepts-cpp20]] — C++20 Concepts 强制使用
- [[cpp-concepts-naming]] — Concepts 命名规范
- [[cpp-concepts-precise]] — Concepts 精确性要求
