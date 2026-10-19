---
domain: cpp
rule_id: cpp-template-constraints
title: 模板约束
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
  - [[cpp-template-meaningful-names]]
  - [[cpp-template-over-macros]]
  - [[cpp-concepts-cpp20]]
---

# 模板约束

## 规则条款
使用 SFINAE（Substitution Failure Is Not An Error）或 C++20 Concepts 进行模板约束，避免意外实例化。未约束的模板可能被用于不满足前置条件的类型，产生晦涩的编译错误或静默的错误行为。模板约束使接口契约显式化，让编译器在实例化时给出清晰的错误信息。

- C++17 及更早版本：使用 SFINAE（`std::enable_if`、`std::void_t`、`decltype` 检测）。
- C++20 及以上版本：必须使用 Concepts（见 C-51/C-52/C-53/C-54）。

## 正确示例
```cpp
// C++17 SFINAE：约束为算术类型
template <typename T,
          typename = std::enable_if_t<std::is_arithmetic_v<T>>>
T multiply(T a, T b) {
    return a * b;
}

// C++17 SFINAE：约束为可比较类型
template <typename T>
auto lessThan(const T& a, const T& b)
    -> std::enable_if_t<std::is_same_v<decltype(a < b), bool>, bool>
{
    return a < b;
}

// C++20 Concepts：约束为整数类型
template <std::integral Integer>
Integer gcd(Integer a, Integer b) {
    while (b != 0) {
        Integer t = b;
        b = a % b;
        a = t;
    }
    return a;
}

// C++20 Concepts：多类型约束
template <typename T, typename U>
    requires std::convertible_to<U, T>
T safeCast(U value) {
    return static_cast<T>(value);
}
```

## 错误示例
```cpp
// 无约束的模板：任何类型均可实例化
template <typename T>
T divide(T a, T b) {
    return a / b;   // 对 std::string 实例化 → 编译错误，错误信息晦涩
}

// 无约束的模板：静默错误
template <typename T>
bool compare(const T& a, const T& b) {
    return a < b;   // 对没有 operator< 的类型 → 概念上不合理的错误
}

// 无约束的模板：重载决议混乱
template <typename T>
void serialize(T& output, const T& value) {
    output = value;  // 对不可赋值的类型 → 错误信息指向模板内部实现
}

// 手动类型检查（不推荐）—— 应在编译期用 SFINAE/Concepts 而非运行期
template <typename T>
T process(T value) {
    if constexpr (std::is_arithmetic_v<T>) {  // 允许但不明确约束
        return value * 2;
    } else {
        static_assert(sizeof(T) == 0, "Unsupported type"); // 错误的排错方式
    }
}
```

## 检查方法
1. 扫描模板声明，检查是否存在未约束的类型参数——即 `template<typename T>` 后没有任何 `enable_if`、`requires` 或概念约束。
2. 检查模板体内部是否依赖某些未被约束的操作（如 `a + b`、`*it`、`a < b`）——这些操作应通过约束显式声明。
3. 对于 C++20 项目，检查是否存在无 Concepts 约束的模板（违反 C-51）。
4. LLM 分析：模板的 Type Requirement 是否在声明中可读地表达？错误信息是否会在约束处（而非实现深处）产生？

## 修复指南
- **C++17 SFINAE**：
  ```cpp
  // 之前
  template<typename T>
  T add(T a, T b) { return a + b; }

  // 之后
  template<typename T,
           typename = std::enable_if_t<std::is_arithmetic_v<T>>>
  T add(T a, T b) { return a + b; }
  ```
- **C++20 Concepts**：
  ```cpp
  // 更清晰的方式
  template<std::integral T>
  T add(T a, T b) { return a + b; }

  // 或使用 requires 子句
  template<typename T>
      requires std::is_arithmetic_v<T>
  T add(T a, T b) { return a + b; }
  ```
- **多类型约束**：使用 `requires` 子句表达类型间关系。
- **逐步迁移**：对现有无约束模板，从公开 API 开始逐层添加约束。

## 审查清单
- [ ] 每个模板的每个类型参数是否都有约束？
- [ ] 约束是否准确反映了模板体中对类型参数的实际要求？
- [ ] C++20 项目中，是否所有模板都使用 Concepts 约束？
- [ ] 约束产生的错误信息是否在模板声明处即可理解？
- [ ] 是否存在"过度约束"——约束比实际需要的更多？

## 关联页面
- [[cpp-template-meaningful-names]] — 模板参数命名规范
- [[cpp-template-over-macros]] — 模板与宏的选择
- [[cpp-concepts-cpp20]] — C++20 Concepts 强制使用
- [[cpp-concepts-precise]] — Concepts 精确性要求
