---
domain: cpp
rule_id: cpp-template-over-macros
title: 模板优先于宏
priority: main
source_file: rules/C++编程规范.md
source_section: "2.1 模板规则"
status: active
check_method: llm
deterministic_check: false
checkability: llm_checkable
conflicts_with: []
overrides: []
related_pages:
  - [[cpp-template-meaningful-names]]
  - [[cpp-template-constraints]]
---

# 模板优先于宏

## 规则条款
优先使用模板而非宏定义泛型代码。宏缺乏类型安全、不遵循作用域规则、难以调试，错误信息晦涩且可能产生副作用或多次求值。模板提供编译期类型检查、清晰的错误信息、完全融入 C++ 类型系统。

## 正确示例
```cpp
// 模板版本：类型安全，无副作用
template <typename Arithmetic>
Arithmetic max(Arithmetic a, Arithmetic b) {
    return a > b ? a : b;
}

// 模板版本：适用于任何容器
template <typename Container>
typename Container::value_type sum(const Container& c) {
    typename Container::value_type total{};
    for (const auto& item : c) {
        total += item;
    }
    return total;
}

// 模板变量用于常量
template <typename T>
constexpr T pi = T(3.14159265358979323846);

// 使用 constexpr 函数替代宏常量
constexpr int bufferSize(int multiplier) {
    return 1024 * multiplier;
}
```

## 错误示例
```cpp
// 宏版本：类型不安全，多次求值
#define MAX(a, b) ((a) > (b) ? (a) : (b))

// 宏的副作用问题
int x = 0;
int y = 5;
int z = MAX(++x, y);   // 展开为 ((++x) > (y) ? (++x) : (y))
                        // ++x 被求值两次，x 变为 2 而非预期为 1

// 类型不安全问题：
MAX(3.14, 10);          // 参数类型不确定，隐式转换

// 宏版本的泛型代码，不可调试
#define SUM(c) ({                              \
    typeof((c).begin()) it = (c).begin();      \
    typeof(*(c).begin()) total = 0;            \
    while (it != (c).end()) total += *it++;    \
    total;                                     \
})

// 宏版本的常量，无类型信息
#define PI 3.14159265358979323846
#define BUFFER_SIZE 1024
// PI 是 double 而非 float，无法控制精度
```

## 检查方法
1. 使用正则表达式扫描 `#define` 语句，排除合法的保护宏（`_H_` 结尾的头文件保护宏和平台宏）。
2. 检查宏是否包含计算逻辑：任何包含 `(` 参数列表、`{}` 或 `#define` 都应触发审查。
3. 宏定义内容是否为类函数宏（带参数的宏），这类宏几乎总可以用 `template` 函数或 `constexpr` 函数替代。
4. 宏常量（`#define CONSTANT value`）是否可用 `constexpr` 或 `const` 变量替代。

## 修复指南
- **类函数宏 -> 模板函数**：将 `#define FUNC(args) ...` 替换为 `template<typename T> auto func(T args) { ... }`。
- **宏常量 -> constexpr**：将 `#define CONSTANT value` 替换为 `constexpr auto CONSTANT = value;`。
- **条件编译 -> if constexpr**：将 `#ifdef`/`#if` 逻辑替换为 C++17 的 `if constexpr` 和模板特化。
- **合法宏保留**：平台检测（`#ifdef _WIN32`）、调试宏（`NDEBUG`）、头文件保护（`#pragma once`）是宏的合理用途。
- **X 宏技术**：如果使用宏进行代码生成（X 宏），检查是否可用 `constexpr` 映射或模板替代。

## 审查清单
- [ ] 是否有类函数宏（`#define NAME(args) ...`）可用模板或 constexpr 函数替代？
- [ ] 是否有宏常量可用 `constexpr` 变量替代？
- [ ] 是否有条件编译可用 `if constexpr` 替代？
- [ ] 保留的宏是否有充分理由（平台检测、头文件保护等）？
- [ ] 是否使用了宏实现复杂逻辑（如 `#define TYPE_SWITCH`）？

## 关联页面
- [[cpp-template-meaningful-names]] — 模板参数有意义命名
- [[cpp-template-constraints]] — 模板约束（SFINAE 或 Concepts）
