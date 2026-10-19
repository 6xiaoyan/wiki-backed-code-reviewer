---
domain: google
rule_id: google-cpp-features
title: C++ 特性使用规范（Google C++ Style Guide 对照）
priority: sub
source_file: rules/Google_C++_Style_Guide.md
source_section: "第 6 章"
status: active
check_method: llm
deterministic_check: false
checkability: llm_checkable
conflicts_with:
  - "cpp/exception-inherit-std"
  - "cpp/exception-throw-by-value"
overrides: []
related_pages:
  - [[cpp/no-cstyle-strings-arrays]]
  - [[cpp/no-reinterpret-c-cast]]
  - [[cpp/no-varargs]]
  - [[cpp/lambda-explicit-capture]]
  - [[cpp/no-macro-constants]]
---

# C++ 特性使用规范（Google C++ Style Guide 对照）

> 来源：Google C++ Style Guide 第 6 章 | 多处冲突，**公司规则为准**

## 与公司规则的对照

| Google 条款 | 公司规则 | 一致性 |
|------------|---------|--------|
| **不使用 C++ 异常**，用错误码和断言替代 | [[cpp/exception-inherit-std]] 等 | ❌ **冲突！公司允许并使用异常，以公司规则为准** |
| 禁止 RTTI（`typeid`、`dynamic_cast`） | — | 补充条款 |
| 使用 C++ 风格转换，禁止 C 风格 `(int)x` | [[cpp/no-reinterpret-c-cast]] | ✅ 一致 |
| 禁止 VLA 和 `alloca()` | [[cpp/no-cstyle-strings-arrays]] | ✅ 一致 |
| Lambda 禁止默认捕获 `[=]` `[&]` | [[cpp/lambda-explicit-capture]] | ✅ 一致 |
| 非常谨慎使用宏 | [[cpp/no-macro-constants]] | ✅ 一致 |
| 指针用 `nullptr`，字符用 `'\0'` | — | ✅ 一致 |
| 禁止 `...` 可变参数 | [[cpp/no-varargs]] | ✅ 一致 |
| 优先使用前置自增 `++i` | — | 补充条款 |
| 流仅用于日志记录，其他用 `printf` 风格 | — | 与 Qt 习惯不同，**公司规则无约束** |

## ❌ 关键冲突：C++ 异常

| 方面 | Google | 公司 |
|------|--------|------|
| C++ 异常 | **完全不使用** | 允许且规范使用（[[cpp/exception-inherit-std]]） |
| 裁决 | **以公司规则为准** | |

## 补充条款（公司规则未覆盖）

1. **禁止 RTTI**：`typeid` 和 `dynamic_cast` 禁止使用（单元测试例外）。替代：虚函数、访问者模式
2. **`const` 用法**：尽可能使用 `const`；不会修改的参数为 `const`；成员函数为 `const`
3. **`constexpr` 优先于 `const`**（真正的常量）
4. **`auto` 仅用于局部变量**：不用于文件作用域、命名空间作用域或类数据成员
5. **列表初始化警告**：绝不大括号初始化 `auto` 变量（`auto x{1}` → `initializer_list`）
6. **前置自增**：对迭代器和其他模板对象使用前置形式（`++i`）
7. **`sizeof` 用法**：优先使用 `sizeof(varname)` 而非 `sizeof(type)`
8. **整型选择**：内置整数类型中仅使用 `int`；需要特定大小时使用 `stdint.h` 类型
