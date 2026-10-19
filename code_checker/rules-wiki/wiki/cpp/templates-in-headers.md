---
domain: cpp
rule_id: cpp-templates-in-headers
title: 模板定义必须在头文件中
priority: main
source_file: rules/C++代码规范.md
source_section: "### 1.2 头文件规范"
status: active
check_method: regex
deterministic_check: true
checkability: deterministic
conflicts_with: []
overrides: []
related_pages:
  - [[cpp-include-order]]
  - [[cpp-inline-functions]]
  - [[cpp-forward-declarations]]
---

# 模板定义必须在头文件中

## 规则条款

所有函数模板和类模板的完整定义（不仅是声明）必须放在头文件中。这是因为 C++ 模板采用编译期实例化模型：编译器在遇到模板使用时，需要看到模板的完整定义才能生成具体代码。

如果模板定义放在 `.cpp` 文件中，会导致链接错误（未定义引用），除非使用显式实例化（explicit instantiation）。项目中统一要求将模板定义放在头文件中，避免隐式实例化带来的跨翻译单元问题。

对于类模板，成员函数的定义也应放在同一个头文件中（通常放在类定义之后）。

## 正确示例

```cpp
// file: math/vector_operations.h
#ifndef PROJECT_MATH_VECTOR_OPERATIONS_H_
#define PROJECT_MATH_VECTOR_OPERATIONS_H_

#include <algorithm>
#include <vector>

namespace math {

// template definition in header — correct
template <typename T>
T sum(const std::vector<T>& values) {
    T result = T{};
    for (const auto& v : values) {
        result += v;
    }
    return result;
}

// class template member defined in same header — correct
template <typename T>
class Accumulator {
public:
    void add(const T& value);
    T total() const;

private:
    std::vector<T> m_values;
};

template <typename T>
void Accumulator<T>::add(const T& value) {
    m_values.push_back(value);
}

template <typename T>
T Accumulator<T>::total() const {
    return sum(m_values);
}

} // namespace math

#endif // PROJECT_MATH_VECTOR_OPERATIONS_H_
```

## 错误示例

```cpp
// file: math/vector_operations.h
#ifndef PROJECT_MATH_VECTOR_OPERATIONS_H_
#define PROJECT_MATH_VECTOR_OPERATIONS_H_

#include <vector>

namespace math {

// declaration only — definition in .cpp, WILL CAUSE LINKER ERROR
template <typename T>
T sum(const std::vector<T>& values);

} // namespace math

#endif // PROJECT_MATH_VECTOR_OPERATIONS_H_
```

```cpp
// file: math/vector_operations.cpp
#include "math/vector_operations.h"

namespace math {

template <typename T>
T sum(const std::vector<T>& values) {
    T result = T{};
    for (const auto& v : values) {
        result += v;
    }
    return result;
}

// no explicit instantiation — linker will not find specialization
// template <> double sum(const std::vector<double>&) — not generated!

} // namespace math
```

## 检查方法
1. 遍历所有 `.cpp` 文件，搜索模板定义，正则模式：
   ```
   ^\s*template\s*<.*>\s*$
   ```
2. 若模式在 `.cpp` 文件中匹配，且后续若干行内存在函数体 `{...}` 或类定义体，则标记为违规。
3. 忽略显式实例化声明（格式为 `template class Foo<int>;` 或 `template void bar<double>();`），这些允许出现在 `.cpp` 中。
4. 显式实例化正则（应排除）：
   ```
   ^\s*template\s+(class|struct)\s+\w+<[^>]+>\s*;
   ^\s*template\s+(?!<)(\w+(?:::)?)+\s+\w+<[^>]+>\s*\([^)]*\)\s*;
   ```
5. 违规：`.cpp` 文件中的非显式实例化模板定义。

## 修复指南

1. 将 `.cpp` 中的模板函数或类模板定义剪切到头文件中。
2. 对于类模板成员函数，放在头文件的类定义之后（同一头文件内）。
3. 如果模板仅在当前翻译单元内部使用，也可考虑将模板定义移入匿名命名空间或使用 `inline` 关键字标记（但放在头文件中是更通用的做法）。
4. 如果出于编译时间考虑确实需要显式实例化，在 `.cpp` 文件末尾添加显式实例化声明，并在头文件中保留声明。但这种做法不推荐作为常规方案。

## 审查清单

- [ ] 所有模板定义是否都在 `.h` / `.hpp` 文件中
- [ ] `.cpp` 文件中是否存在未加显式实例化的模板体
- [ ] 类模板成员函数定义是否也在同一头文件中
- [ ] 头文件中模板定义是否有适当的 include 依赖

## 关联页面

- [[cpp-inline-functions]]
- [[cpp-include-order]]
- [[cpp-header-guards]]
- [[cpp-forward-declarations]]
