---
domain: cpp
rule_id: cpp-lambda-explicit-capture
title: Lambda 显式捕获
priority: main
source_file: rules/C++代码规范.md
source_section: "§2.3 Lambda"
status: active
check_method: regex
deterministic_check: true
checkability: deterministic
conflicts_with: []
overrides: []
related_pages:
  - [[cpp-lambda-over-bind]]
  - [[cpp-lambda-small-scope]]
  - [[cpp-lambda-explicit-return]]
  - [[cpp-lambda-no-large-in-hotpath]]
---

# Lambda 显式捕获

## 规则条款
Lambda 表达式的捕获方式必须明确写出，`[=]`、`[&]`、`[this]` 或显式捕获列表均视为明确指定。
注意：§7 进一步收窄此规则，**禁止**使用默认捕获 `[=]` 和 `[&]`；必须使用显式捕获列表逐一列出捕获变量。

本规则确保每个 lambda 的捕获行为一目了然，避免隐式捕获导致的悬空引用、意外拷贝或生命周期问题。

## 正确示例
```cpp
#include <string>
#include <vector>
#include <algorithm>

// 显式捕获列表——逐个列出
int threshold = 10;
std::string filterName = "admin";

auto pred = [threshold, &filterName](const User& user) {
    return user.score > threshold && user.name == filterName;
};

// 按值捕获所有需要的变量
auto calc = [a, b, c](int x) {
    return a * x * x + b * x + c;
};

// this 指针显式捕获
class Widget {
    int factor_ = 2;
public:
    auto makeMultiplier() {
        return [this](int x) { return x * factor_; };
    }

    // C++17: 捕获 *this 避免悬空
    auto makeSafeMultiplier() {
        return [*this](int x) { return x * factor_; };
    }
};

// 初始化捕获（C++14）
auto ptr = std::make_unique<int>(42);
auto owner = [p = std::move(ptr)]() { return *p; };
```

## 错误示例
```cpp
#include <string>
#include <vector>
#include <algorithm>

// 禁止：默认引用捕获——filterName 为局部变量时极易悬空
auto filterUsers(std::vector<User>& users, const std::string& filterName) {
    std::vector<User> result;
    std::copy_if(users.begin(), users.end(), std::back_inserter(result),
                 [&](const User& user) {
                     return user.name == filterName;
                 });
    return result;
} // filterName 是引用参数，lambda 捕获的引用可能在其生命周期结束后仍存在

// 禁止：默认值捕获——§7 严禁 [=]
auto makePrinter() {
    int value = 42;
    return [=]() { return value; };  // 违规：使用默认值捕获
}

// 禁止：隐式捕获混合模式
auto bad = [=, &counter]() {  // 违规：默认捕获与显式混用
    counter++;
    return base + offset;
};
```

## 检查方法
正则表达式检测以下模式并标记违规：
- `\[\s*=\s*\]` — 默认值捕获 `[=]`
- `\[\s*&\s*\]` — 默认引用捕获 `[&]`
- `\[\s*=\s*,\s*&` — 混合默认值捕获

仅允许的模式：
- `\[this\]` 或 `\[\*this\]`
- 完全显式列表：`[var1, &var2, var3]` 形式
- 初始化捕获：`[p = std::move(ptr)]` 形式
- 空捕获：`[]`

## 修复指南
1. 将 `[=]` 替换为显式列出所有在 lambda 体内使用的变量（按值捕获）
2. 将 `[&]` 替换为显式列出所有在 lambda 体内使用的变量（按引用捕获）
3. 对于混合捕获，仅保留显式列表部分
4. 审查每个捕获变量的生命周期，确保引用捕获不会形成悬空引用
5. 对于需要转移所有权的场景，使用初始化捕获 `[p = std::move(ptr)]`

## 审查清单
- [ ] 无 `[=]` 默认值捕获（§7 禁止）
- [ ] 无 `[&]` 默认引用捕获（§7 禁止）
- [ ] 所有 lambda 使用显式捕获列表或空捕获 `[]`
- [ ] 引用捕获变量的生命周期覆盖 lambda 的所有调用路径
- [ ] 对于异步或延迟调用的 lambda，按值捕获或使用 `*this`

## 关联页面
- [[cpp-lambda-over-bind]] — Lambda 优先于 std::bind
- [[cpp-lambda-small-scope]] — Lambda 适用范围
- [[cpp-lambda-explicit-return]] — Lambda 显式返回类型
- [[cpp-lambda-no-large-in-hotpath]] — Lambda 性能考量
