---
domain: cpp
rule_id: cpp-exception-throw-by-value
title: 异常抛出与捕获规范
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
  - [[cpp-exception-inherit-std]]
  - [[cpp-no-throw-dtor]]
---

# 异常抛出与捕获规范

## 规则条款
抛出异常时使用值类型（栈对象），禁止抛出指针类型；捕获异常时使用常量引用（`const T&`），禁止按值捕获或捕获指针。此规范确保异常对象的生命周期由编译器正确管理，并避免对象切片（slicing）。

## 正确示例
```cpp
#include <stdexcept>
#include <string>

// 抛出：按值
void validate(int value) {
    if (value < 0) {
        throw std::invalid_argument("value must be non-negative");
    }
    if (value > 100) {
        throw std::out_of_range("value must be <= 100");
    }
}

// 捕获：常量引用
void process(int v) {
    try {
        validate(v);
    } catch (const std::invalid_argument& e) {
        // 按 const 引用捕获 — 无切片，无拷贝
        std::cerr << "Invalid argument: " << e.what() << std::endl;
    } catch (const std::out_of_range& e) {
        std::cerr << "Out of range: " << e.what() << std::endl;
    } catch (const std::exception& e) {
        // 基类引用捕获所有 std 异常
        std::cerr << "Error: " << e.what() << std::endl;
    }
}

// 重新抛出 — 保持原始异常类型
void wrapper() {
    try {
        doWork();
    } catch (const std::exception& e) {
        log(e);
        throw;  // 重新抛出原始异常对象，不拷贝不切片
    }
}
```

## 错误示例
```cpp
// 错误 1: 抛出指针
void badThrow1() {
    throw new std::runtime_error("error");  // 谁负责 delete？内存泄漏
}
// 调用方：
try {
    badThrow1();
} catch (std::runtime_error* e) {  // 必须捕获指针，还需要 delete
    delete e;
}

// 错误 2: 按值捕获 — 对象切片
class NetworkError : public std::runtime_error {
public:
    int errorCode;
    NetworkError(int code) : std::runtime_error("network"), errorCode(code) {}
};
void badCatch() {
    try {
        throw NetworkError(404);
    } catch (std::runtime_error e) {  // 切片！NetworkError::errorCode 丢失
        // e 的类型是 std::runtime_error，不是 NetworkError
    }
}

// 错误 3: 捕获非 const 引用（不应该修改异常对象）
void anotherBadCatch() {
    try {
        riskyOperation();
    } catch (std::exception& e) {  // 应使用 const
        e = std::runtime_error("new");  // 无意义且容易误用
    }
}
```

## 检查方法
使用正则表达式扫描：

1. 匹配 `throw\s+new\s+`——抛出异常指针，禁止。
2. 匹配 `catch\s*\(\s*\w+\s*\*\s*`——捕获指针类型，禁止。
3. 匹配 `catch\s*\(\s*\w+(\s+\w+)?\s*\)`——按值捕获（不含 `const` 和 `&`），应标警告。

正则参考：
```
throw\s+new\s+\w+                    # 抛指针
catch\s*\(\s*\w+\s*\*\s*\w*\s*\)     # 捕获指针
catch\s*\(\s*(?!const)\w+(\s+\w+)?\s*\)  # 按值捕获（无 const &）
```

## 修复指南
1. `throw new SomeException(...)` 改为 `throw SomeException(...)`。
2. `catch (SomeException* e)` 改为 `catch (const SomeException& e)`，并移除 `delete e`。
3. `catch (SomeException e)` 改为 `catch (const SomeException& e)`，防止对象切片。
4. `catch (std::exception& e)` 改为 `catch (const std::exception& e)`。
5. 重新抛出时使用 `throw;` 而非 `throw e;`。

## 审查清单
- [ ] 所有 `throw` 语句抛出的是值类型而非指针
- [ ] 所有 `catch` 子句使用常量引用（`const T&`）
- [ ] 没有按值捕获异常的 `catch` 子句
- [ ] 重新抛出使用裸 `throw;` 而非 `throw e;`
- [ ] 捕获顺序从最派生到最基类

## 关联页面
- [[cpp-exception-not-for-flow]] — 异常不应用于控制流
- [[cpp-exception-inherit-std]] — 自定义异常继承自 std::exception
- [[cpp-no-throw-dtor]] — 析构函数禁止抛异常
