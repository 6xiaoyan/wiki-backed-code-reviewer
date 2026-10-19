---
domain: cpp
rule_id: cpp-lambda-explicit-return
title: Lambda 显式返回类型
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
  - [[cpp-lambda-explicit-capture]]
  - [[cpp-lambda-small-scope]]
  - [[cpp-lambda-no-large-in-hotpath]]
---

# Lambda 显式返回类型

## 规则条款
多行 lambda 表达式（体包含多于一条语句）必须使用显式返回类型 `-> RetType`。
单行 lambda 在返回类型能从单一 `return` 语句推断时允许省略。

显式返回类型的作用：
- 让读者无需通读整个 lambda 体即可了解返回值类型
- 编译器能在返回类型不匹配时给出更清晰的错误信息
- 避免意外类型转换（如 `bool` 退化到 `int`）

## 正确示例
```cpp
#include <string>
#include <vector>
#include <algorithm>

// 单行 lambda：返回类型可推断，允许省略
auto square = [](int x) { return x * x; };

// 多行 lambda：必须显式写出返回类型
auto gradeStudent = [](int score) -> std::string {
    if (score >= 90) {
        return "A";
    } else if (score >= 80) {
        return "B";
    } else if (score >= 70) {
        return "C";
    } else if (score >= 60) {
        return "D";
    } else {
        return "F";
    }
};

// 多行 lambda 在算法中使用
std::vector<int> data = {1, 2, 3, 4, 5};
std::vector<int> result;
result.reserve(data.size());
std::transform(data.begin(), data.end(), std::back_inserter(result),
               [](int x) -> int {
                   if (x % 2 == 0) {
                       return x * x;
                   } else {
                       return x * x * x;
                   }
               });

// 即使返回类型较复杂，多行也必须写出
auto processConfig = [](const Config& cfg) -> std::optional<Settings> {
    if (!cfg.isValid()) {
        return std::nullopt;
    }
    Settings s;
    s.timeout = cfg.getValue("timeout", 30);
    s.retries = cfg.getValue("retries", 3);
    return s;
};

// auto 返回类型配合尾随返回
auto factory = [](int type) -> std::unique_ptr<BaseHandler> {
    switch (type) {
    case 1:
        return std::make_unique<HandlerA>();
    case 2:
        return std::make_unique<HandlerB>();
    default:
        return std::make_unique<DefaultHandler>();
    }
};
```

## 错误示例
```cpp
#include <string>
#include <vector>
#include <algorithm>

// 多行 lambda 缺少显式返回类型——违规
auto gradeStudent = [](int score) {  // 缺少 -> std::string
    if (score >= 90) {
        return "A";
    } else if (score >= 80) {
        return "B";
    } else {
        return "C";
    }
};

// 多行 lambda 在 transform 中缺少返回类型——违规
std::transform(data.begin(), data.end(), std::back_inserter(result),
               [](int x) {  // 缺少 -> int
                   if (x % 2 == 0) {
                       return x * x;
                   } else {
                       return x + 1;
                   }
               });

// 多个 return 分支返回不同类型可能导致推断歧义
auto ambiguous = [](int flag) {  // 缺少 -> std::variant<int, std::string>
    if (flag == 1) {
        return 42;
    } else {
        return std::string("unknown");
    }
};
```

## 检查方法
正则表达式检测 lambda 定义：

1. 识别多行 lambda：`\[\s*[^\]]*\]\s*\(\s*[^)]*\s*\)\s*\{` 后跟换行符，且函数体包含多条语句
2. 对于多行 lambda，检查是否存在 `->` 尾随返回类型声明
3. 对于单行 lambda（仅有 `return expr;`），允许省略返回类型

自动检测逻辑：
- 统计 `{` `}` 之间分号的数量
- 若分号数量 >= 2（包含多条语句）且无 `->` 声明 → 违规
- 若分号数量 == 1（单一 return 语句）→ 允许省略

## 修复指南
1. 定位缺少显式返回类型的多行 lambda
2. 分析 lambda 体中所有 `return` 语句的返回类型
3. 在参数列表后添加 `-> ReturnType`，使用最宽泛的公共类型
4. 如返回类型来自 `auto` 变量，考虑使用 `decltype` 或明确写出具体类型
5. 验证编译通过（编译器可帮助检测返回类型是否一致）

## 审查清单
- [ ] 所有多行 lambda 包含显式返回类型 `->`
- [ ] 显式返回类型与函数体中所有 `return` 语句兼容
- [ ] 无因缺少返回类型导致的意外隐式转换
- [ ] 单行 lambda 的返回类型推断结果符合预期

## 关联页面
- [[cpp-lambda-over-bind]] — Lambda 优先于 std::bind
- [[cpp-lambda-explicit-capture]] — Lambda 显式捕获
- [[cpp-lambda-small-scope]] — Lambda 适用范围
- [[cpp-lambda-no-large-in-hotpath]] — Lambda 性能考量
