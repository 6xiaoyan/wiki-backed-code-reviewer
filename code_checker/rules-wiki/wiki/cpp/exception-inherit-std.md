---
domain: cpp
rule_id: cpp-exception-inherit-std
title: 自定义异常继承规范
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
  - [[cpp-exception-not-for-flow]]
  - [[cpp-exception-throw-by-value]]
  - [[cpp-no-throw-dtor]]
---

# 自定义异常继承规范

## 规则条款
自定义异常类型必须继承自 `std::exception` 或其子类（如 `std::runtime_error`、`std::logic_error`），并正确覆写 `what()` 方法。禁止使用非标准类型作为异常（如 `int`、`const char*`、`std::string` 直接作为异常对象）。

## 正确示例
```cpp
#include <stdexcept>
#include <string>

// 方式 1: 继承 std::runtime_error（推荐）
class ConfigError : public std::runtime_error {
public:
    explicit ConfigError(const std::string& key)
        : std::runtime_error("Missing config key: " + key)
        , m_key(key) {}

    const std::string& key() const noexcept { return m_key; }

private:
    std::string m_key;
};

// 方式 2: 继承 std::exception 并提供 what()
class DatabaseError : public std::exception {
public:
    explicit DatabaseError(std::string msg) : m_message(std::move(msg)) {}

    const char* what() const noexcept override {
        return m_message.c_str();
    }

private:
    std::string m_message;
};

// 方式 3: 多层继承层次
class NetworkError : public std::runtime_error {
public:
    explicit NetworkError(const std::string& msg)
        : std::runtime_error(msg) {}
};

class TimeoutError : public NetworkError {
public:
    TimeoutError() : NetworkError("Connection timed out") {}
};
```

## 错误示例
```cpp
// 错误 1: 抛出非标准类型
void badThrow1() {
    throw 42;                          // 抛出 int — 禁止
}

void badThrow2() {
    throw "something went wrong";      // 抛出 const char* — 禁止
}

void badThrow3() {
    throw std::string("error");        // 抛出 std::string — 禁止
}

// 错误 2: 自定义异常不继承 std::exception
class MyError {                        // 不继承任何标准异常 — 禁止
public:
    std::string message;
};

// 错误 3: what() 非 noexcept 或返回类型错误
class BadException : public std::exception {
public:
    std::string what() {               // 应返回 const char* 且为 noexcept
        return "error";
    }
};
```

## 检查方法
使用正则表达式扫描：

1. 匹配 `throw\s+(?!std::)\w+[^(]`——抛出非标准库类型（排除字符串字面量和整数常量需进一步确认）。
2. 匹配 `throw\s+\d+` 和 `throw\s+"`——抛出基本类型和字符串字面量。
3. 对于自定义异常类，检查其继承列表是否包含 `std::exception` 或其派生类。
4. 检查自定义异常的 `what()` 声明是否正确：`const char* what() const noexcept override`。

正则参考：
```
throw\s+\d+\s*[;)]                          # 抛整数
throw\s+"[^"]*"\s*[;)]                      # 抛字符串字面量
throw\s+std::string                         # 抛 std::string
class\s+(\w*[Ee]rror\w*|.*[Ee]xception.*)   # 异常类候选
```

## 修复指南
1. `throw 42` 替换为 `throw std::runtime_error("error code 42")`。
2. `throw "msg"` 替换为 `throw std::runtime_error("msg")`。
3. `throw std::string("msg")` 替换为 `throw std::runtime_error("msg")`。
4. 自定义异常类添加继承 `std::runtime_error`（推荐）或 `std::exception`。
5. 确保 `what()` 方法签名正确并标记 `noexcept`。

## 审查清单
- [ ] 所有自定义异常类继承自 `std::exception` 或其派生类
- [ ] 没有抛出基本类型（int、char*、string 等）
- [ ] `what()` 方法正确覆写：`const char* what() const noexcept override`
- [ ] 异常层次结构设计合理（派生关系清晰）
- [ ] 异常类型名称清晰地表达了错误语义

## 关联页面
- [[cpp-exception-not-for-flow]] — 异常不应用于控制流
- [[cpp-exception-throw-by-value]] — 异常的抛出与捕获规范
- [[cpp-no-throw-dtor]] — 析构函数禁止抛异常
