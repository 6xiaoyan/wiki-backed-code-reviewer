---
domain: cpp
rule_id: cpp-concepts-cpp20
title: C++20 Concepts 强制使用
priority: main
source_file: rules/C++代码规范.md
source_section: "§5.2 C++20 Concepts"
status: active
check_method: regex
deterministic_check: true
checkability: deterministic
conflicts_with: []
overrides: []
related_pages:
  - [[cpp-concepts-naming]]
  - [[cpp-concepts-std-first]]
  - [[cpp-concepts-precise]]
  - [[cpp-template-constraints]]
---

# C++20 Concepts 强制使用

## 规则条款
C++20 及以上项目必须使用概念（Concepts）约束模板。禁止在 C++20 或更高标准配置的项目中编写无 Concepts 约束的普通模板。Concepts 将模板的接口契约显式化，让编译器在模板声明处而非数千行后的实例化处捕获错误，大幅改善错误信息的可读性。

强制范围：
- 所有新编写或修改的模板都必须包含 Concepts 约束
- 存量无约束模板应在维护迭代中逐步添加约束
- 仅对极少数通用类型（如标准库级别的 `std::swap` 签名）允许省略

## 正确示例
```cpp
#include <concepts>
#include <ranges>
#include <iterator>

// 概念约束模板函数：仅接受整数类型
template <std::integral Integer>
Integer gcd(Integer a, Integer b) {
    while (b != 0) {
        Integer t = b;
        b = a % b;
        a = t;
    }
    return a;
}

// requires 子句形式：多类型约束
template <typename T>
    requires std::integral<T> || std::floating_point<T>
T square(T value) {
    return value * value;
}

// 概念约束类模板
template <std::semiregular T>
class RingBuffer {
public:
    void push(const T& value) { /* ... */ }
    T pop() { /* ... */ }
};

// 概念约束的函数模板：Range 操作
template <std::ranges::input_range Range, std::integral Value>
    requires std::equality_comparable_with<
        std::ranges::range_value_t<Range>, Value>
auto count(Range&& r, const Value& v) {
    return std::ranges::count(std::forward<Range>(r), v);
}
```

## 错误示例
```cpp
// C++20 项目中：无概念约束的模板 — 违规
template <typename T>
T add(T a, T b) {
    return a + b;   // 对没有 operator+ 的类型：错误信息指向模板内部
}

// C++20 项目中：无概念约束的类模板 — 违规
template <typename T>
class Stack {
    std::vector<T> m_elements;
public:
    void push(const T& value) { m_elements.push_back(value); }
    T pop() {
        auto v = m_elements.back();
        m_elements.pop_back();
        return v;
    }
};

// 使用 SFINAE 而非 Concepts（在 C++20 项目中）— 不推荐
template <typename T>
std::enable_if_t<std::is_integral_v<T>, T>
legacyMod(T a, T b) {
    return a % b;
}
// 应改为：
// template <std::integral T>
// T mod(T a, T b) { return a % b; }
```

## 检查方法
1. **确定性检测**：用正则表达式匹配 `template<...>` 声明，验证其后是否紧跟 `requires` 子句或概念约束的类型参数名。
   - 检测模式：`template\s*<\s*typename\s+\w+\s*>` 后若无 `requires` 或概念名 → 标记违规。
2. 检查项目 C++ 标准配置（CMake `CMAKE_CXX_STANDARD`、编译器标志 `-std=c++20` 或 `/std:c++20`）。
3. 对于 `template<typename T, typename U, ...>` 多参数模板，检查每个参数是否都有约束。
4. 排除标准库兼容代码和显式标记为例外的模板。

## 修复指南
- **单类型约束**：`template<std::integral T>` — 直接在参数位置使用概念。
- **多类型约束**：使用 `requires` 子句表达类型间关系。
- **自定义概念**：
  ```cpp
  template<typename T>
  concept Sortable = std::permutable<T> && requires(T c) {
      { std::ranges::sort(c) };
  };

  template<Sortable Container>
  void sort(Container& c) { std::ranges::sort(c); }
  ```
- **存量代码迁移**：从公开 API 头文件开始，逐文件添加 Concepts 约束。
- **SFINAE 替换**：将 `std::enable_if` 替换为 `requires` 子句或概念名。

## 审查清单
- [ ] C++ 标准设置为 C++20 或更高？
- [ ] 所有 `template<typename ...>` 声明是否都有 Concepts 约束？
- [ ] 是否不存在使用 `std::enable_if` 替代 Concepts 的 C++20 新代码？
- [ ] 约束是否准确反映了模板体中对类型参数的实际要求？
- [ ] 是否已排除标准库兼容代码或显式例外？

## 关联页面
- [[cpp-concepts-naming]] — Concepts 命名规范
- [[cpp-concepts-std-first]] — 优先使用标准概念
- [[cpp-concepts-precise]] — Concepts 精确性要求
- [[cpp-template-constraints]] — 模板约束的通用规则
