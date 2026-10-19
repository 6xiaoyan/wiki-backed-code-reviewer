---
domain: cpp
rule_id: cpp-no-macro-constants
title: 禁止宏定义常量/函数
priority: main
source_file: rules/C++代码规范.md
source_section: "§7 明确禁止项"
status: active
check_method: regex
deterministic_check: true
checkability: deterministic
conflicts_with: []
overrides: []
related_pages:
  - [[cpp-no-cstyle-strings-arrays]]
  - [[cpp-no-using-namespace-in-header]]
---

# 禁止宏定义常量/函数

## 规则条款
禁止使用 `#define` 定义常量或函数式宏（头文件保护宏除外）。常量应使用 `constexpr` 或 `const`，函数式宏应使用模板或 `constexpr` 函数替代。宏绕过类型系统、命名空间和作用域规则，导致难以调试的错误。

## 正确示例
```cpp
// 常量：使用 constexpr
constexpr int MaxConnections = 100;
constexpr double Pi = 3.141592653589793;
constexpr const char* AppName = "MyApplication";

// 函数式宏 → constexpr 函数模板
template<typename T>
constexpr T maxValue(T a, T b) {
    return (a > b) ? a : b;
}

// 带类型的常量
namespace Config {
    constexpr std::size_t BufferSize = 4096;
    constexpr std::chrono::seconds Timeout{30};
}

// 字符串常量
constexpr std::string_view WelcomeMessage = "Hello, World!";

// 位掩码常量
enum class Permissions : unsigned int {
    Read    = 1 << 0,
    Write   = 1 << 1,
    Execute = 1 << 2
};
```

## 错误示例
```cpp
// 宏常量
#define MAX_CONNECTIONS 100        // 应使用 constexpr int
#define PI 3.141592653589793       // 应使用 constexpr double

// 函数式宏
#define MAX(a, b) ((a) > (b) ? (a) : (b))  // 多重求值、无类型安全
#define SQUARE(x) ((x) * (x))              // SQUARE(++i) 行为未定义

// 使用宏模拟命名空间
#define CONFIG_BUFFER_SIZE 4096

// 调试宏开关
#define DEBUG_MODE 1
#if DEBUG_MODE
    // ...
#endif
```

## 检查方法
1. 正则检测：搜索 `#define` 行
2. 排除头文件保护宏（模式：`[A-Z_]+_H_$` 或 `[A-Z_]+_H$`）
3. 分类剩余的宏定义：常量宏、函数式宏、条件编译宏
4. 标记所有非头文件保护的宏定义为违规

## 修复指南
1. 数值常量 → `constexpr` 变量（带明确类型）
2. 字符串常量 → `constexpr std::string_view` 或 `const char* const`
3. 函数式宏 → `constexpr` 函数模板或 `inline` 函数
4. 枚举集合 → `enum class` 或 `constexpr` 变量组
5. 条件编译（`#ifdef`）→ 尽可能用 `if constexpr` 或构建系统配置替代
6. 确实必须使用宏的场景（如 `#include` 守卫、日志源位置）：保留但限制使用

## 审查清单
- [ ] 不存在 #define 常量（constexpr 替代）
- [ ] 不存在 #define 函数式宏（模板/constexpr 替代）
- [ ] #define 仅限头文件保护宏
- [ ] 枚举值使用了 enum class 而非宏

## 关联页面
- [[cpp-no-cstyle-strings-arrays]] — 禁止 C 风格字符串和数组
- [[cpp-no-using-namespace-in-header]] — 头文件禁止 using namespace
