---
domain: cpp
rule_id: cpp-no-throw-spec
title: 禁止异常规范 throw()
priority: main
source_file: rules/C++代码规范.md
source_section: "§4.1 异常使用规范"
status: active
check_method: regex
deterministic_check: true
checkability: deterministic
conflicts_with: []
overrides: []
related_pages:
  - [[cpp-noexcept-spec]]
  - [[cpp-no-throw-dtor]]
  - [[cpp-exception-not-for-flow]]
---

# 禁止异常规范 throw()

## 规则条款
禁止使用动态异常规范 `throw()`（C++17 已从标准移除，C++20 中 `throw()` 已不再是合法语法）。所有不抛出异常的函数必须使用 `noexcept` 替代 `throw()`。

## 正确示例
```cpp
#include <stdexcept>

// noexcept — 正确的不抛异常标记
void safeFunction() noexcept {
    // 保证不抛异常
}

int getValue() const noexcept {
    return m_value;
}

// noexcept 可带编译期条件
template <typename T>
void maybeSwap(T& a, T& b)
    noexcept(noexcept(std::swap(a, b))) {
    std::swap(a, b);
}

// noexcept 运算符用于编译期查询
static_assert(noexcept(safeFunction()), "safeFunction must be noexcept");

// 析构函数默认 noexcept(true) — 无需显式标注
class Resource {
public:
    ~Resource() = default;  // 隐式 noexcept
};
```

## 错误示例
```cpp
// 错误 1: throw() 动态异常规范 — C++17 移除，任何标准下都不应使用
void oldStyle() throw() {  // 禁止！
    // ...
}

// 错误 2: throw(type-list) — 同样已移除
void mightThrowInt() throw(int, std::runtime_error) {  // 禁止！
    // ...
}

// 错误 3: noexcept(false) 在析构函数中 — 大部分情况下错误
class BadClass {
public:
    ~BadClass() noexcept(false) {  // 极其危险，通常为设计错误
        // ...
    }
};

// 错误 4: throw() 在 typedef 或函数指针类型中
typedef void (*OldCallback)() throw();  // 禁止！
```

## 检查方法
使用正则表达式扫描（确定性）：

1. 匹配 `throw\s*\(\s*\)`——空的动态异常规范，替换为 `noexcept`。
2. 匹配 `throw\s*\([^)]+\)`——带类型列表的动态异常规范，替换为 `noexcept(false)` 或移除。
3. 在函数声明、typedef、using 别名中查找上述模式。

正则参考：
```
throw\s*\(\s*\)              # throw() → 替换为 noexcept
throw\s*\([^)]+\)            # throw(type1, type2, ...) → 替换为 noexcept(false) 或移除
```

## 修复指南
1. `void f() throw()` 改为 `void f() noexcept`。
2. `void f() throw(SomeException)` 改为 `void f() noexcept(false)`，如函数确实不抛异常则直接用 `noexcept`。
3. `typedef void (*Callback)() throw()` 改为 `typedef void (*Callback)() noexcept`。
4. 全局搜索项目中所有 `throw(` 出现（排除实际的 `throw` 语句），逐一替换。
5. 如项目需兼容 C++14 或更早标准，确保编译器支持 `noexcept`（GCC 4.6+、Clang 3.0+、MSVC 2015+）。

## 审查清单
- [ ] 代码中不存在 `throw()` 空异常规范
- [ ] 代码中不存在 `throw(type-list)` 动态异常规范
- [ ] 所有不抛异常的函数使用 `noexcept` 标记
- [ ] typedef/using 中的函数指针类型不使用 `throw()`
- [ ] C++ 标准版本设置 >= C++17（确保 `throw()` 语法不被接受）

## 关联页面
- [[cpp-noexcept-spec]] — noexcept 规范的正确使用
- [[cpp-no-throw-dtor]] — 析构函数禁止抛异常
- [[cpp-exception-not-for-flow]] — 异常不应用于控制流
