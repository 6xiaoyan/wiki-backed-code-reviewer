---
domain: cpp
rule_id: cpp-no-varargs
title: 禁止可变参数
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
  - [[cpp-no-macro-constants]]
---

# 禁止可变参数

## 规则条款
禁止使用 C 风格可变参数（`...`），用模板参数包（variadic templates）替代。C 风格可变参数（`va_list`、`va_start`、`va_arg`、`va_end`）缺乏类型安全，不进行类型检查，容易导致未定义行为。日志和格式化函数等特定场景可作为例外，但应优先考虑类型安全的替代方案。

## 正确示例
```cpp
// 类型安全的可变参数模板
template<typename... Args>
void logMessage(const char* format, Args&&... args) {
    char buffer[1024];
    snprintf(buffer, sizeof(buffer), format, std::forward<Args>(args)...);
    // 或使用 C++20 std::format
    // std::string msg = std::format(format, std::forward<Args>(args)...);
    writeToLog(std::string{buffer});
}

// 使用折叠表达式处理多个参数
template<typename... Args>
int sum(Args... args) {
    return (args + ...);  // C++17 折叠表达式
}

// 使用可变模板构造容器
template<typename... Args>
std::vector<int> makeVector(Args... args) {
    return std::vector<int>{args...};
}

// std::initializer_list 用于同类型多参数
void processValues(std::initializer_list<int> values) {
    for (int v : values) {
        handleValue(v);
    }
}
```

## 错误示例
```cpp
// C 风格可变参数：无类型安全
void logMessage(const char* format, ...) {
    va_list args;
    va_start(args, format);
    vprintf(format, args);  // 参数类型错误无法在编译期检测
    va_end(args);
}

// 危险的混合类型可变参数
int sum(int count, ...) {
    va_list args;
    va_start(args, count);
    int total = 0;
    for (int i = 0; i < count; ++i) {
        total += va_arg(args, int);  // 调用者传 double 会出错
    }
    va_end(args);
    return total;
}

// 格式化函数的参数错误不会被捕获
logMessage("%s %d", 123, "hello");  // 类型不匹配，运行时崩溃
```

## 检查方法
1. 正则检测：搜索函数声明中的 `...` 参数
   - 模式：`\([^)]*\b\.\.\.\b[^)]*\)`
   - 排除：模板参数包（`Args...`、`typename... Args` 等）
2. 正则检测：搜索 `va_list`、`va_start`、`va_arg`、`va_end` 宏
3. 标记所有 C 风格可变参数使用为违规
4. 日志/格式化场景：检查是否使用了 `std::format`（C++20）、`fmt` 库或模板包装

## 修复指南
1. 通用可变参数 → 可变参数模板 `template<typename... Args>`
2. 同类型多参数 → `std::initializer_list<T>`
3. 格式化字符串场景 → `std::format`（C++20）或 `fmtlib`
4. C 库桥接 → 封装为模板函数，内部使用 `va_list` 并标注 `// NOLINT(C-67)`
5. 递归处理参数 → 使用折叠表达式（C++17）或编译期递归展开

## 审查清单
- [ ] 不存在 C 风格的 `...` 可变参数声明（模板除外）
- [ ] 不存在 va_list / va_start / va_arg / va_end 的使用
- [ ] 格式化函数使用了类型安全的替代方案
- [ ] 多参数场景使用了模板参数包或 initializer_list

## 关联页面
- [[cpp-no-cstyle-strings-arrays]] — 禁止 C 风格字符串和数组
- [[cpp-no-macro-constants]] — 禁止宏定义常量/函数
