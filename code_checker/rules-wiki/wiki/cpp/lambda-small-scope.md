---
domain: cpp
rule_id: cpp-lambda-small-scope
title: Lambda 适用范围
priority: main
source_file: rules/C++代码规范.md
source_section: "§2.3 Lambda"
status: active
check_method: llm
deterministic_check: false
checkability: advisory_only
conflicts_with: []
overrides: []
related_pages:
  - [[cpp-lambda-over-bind]]
  - [[cpp-lambda-explicit-capture]]
  - [[cpp-lambda-explicit-return]]
  - [[cpp-lambda-no-large-in-hotpath]]
---

# Lambda 适用范围

## 规则条款
对于小函数和算法参数，使用 lambda 表达式就地定义以提高代码可读性。当一段逻辑仅在一处使用、
且体量较小（通常不超过 5-10 行）时，将其写成 lambda 而非独立函数或函数对象，可以让读者无需
跳转到其他位置即可理解代码意图。反之，如果逻辑需要在多处复用，或体量较大，应提取为具名函数。

## 正确示例
```cpp
#include <algorithm>
#include <vector>
#include <string>
#include <numeric>

std::vector<int> scores = {85, 92, 78, 95, 88};

// 小规模就地 lambda：过滤逻辑一目了然
auto it = std::remove_if(scores.begin(), scores.end(),
                         [](int s) { return s < 80; });
scores.erase(it, scores.end());

// 排序就地 lambda：比较逻辑紧邻调用点
std::sort(scores.begin(), scores.end(),
          [](int a, int b) { return a > b; });

// 简单累加逻辑——无需命名函数
int total = std::accumulate(scores.begin(), scores.end(), 0,
                            [](int sum, int s) { return sum + s; });

// std::transform 就地逻辑
std::vector<std::string> names = {"alice", "bob", "charlie"};
std::transform(names.begin(), names.end(), names.begin(),
               [](const std::string& s) {
                   std::string result = s;
                   if (!result.empty()) {
                       result[0] = static_cast<char>(std::toupper(result[0]));
                   }
                   return result;
               });

// 当逻辑需要在多处复用时，提取为具名函数更合适
bool isPassingGrade(int score) {
    return score >= 60 && score <= 100;
}

// 多处复用具名函数
auto passIt = std::find_if(scores.begin(), scores.end(), isPassingGrade);
auto failIt = std::find_if(scores.begin(), scores.end(),
                           [](int s) { return !isPassingGrade(s); });
```

## 错误示例
```cpp
#include <algorithm>
#include <vector>
#include <string>
#include <map>

// 不适合作 lambda：体量过大，逻辑复杂
std::map<int, std::string> transformData(const std::vector<int>& input) {
    std::map<int, std::string> result;
    std::for_each(input.begin(), input.end(), [&result](int value) {
        // 以下逻辑应提取为具名函数
        std::string category;
        if (value < 0) {
            category = "negative";
        } else if (value == 0) {
            category = "zero";
        } else if (value < 10) {
            category = "small";
        } else if (value < 100) {
            category = "medium";
        } else {
            category = "large";
        }

        auto it = result.find(value % 10);
        if (it != result.end()) {
            it->second += ", " + category;
        } else {
            result[value % 10] = category;
        }
    });
    return result;
}

// 不适合作 lambda：同一逻辑在多处出现
auto isEven = [](int x) { return x % 2 == 0; };
// ... 后面又出现相同逻辑
auto checkEven = [](int x) { return x % 2 == 0; };
// 应提取为具名函数，单一数据源
```

## 检查方法
由 LLM 进行启发式检查：
1. 识别体量超过 10 行的 lambda（建议改为具名函数）
2. 检测项目中相同或高度相似 lambda 在多处重复出现（建议提取）
3. 评估 lambda 体中是否包含多层嵌套或复杂控制流（建议提取）
4. 确认算法调用（`std::sort`、`std::find_if` 等）中的 lambda 是否简洁

## 修复指南
1. **提取大 lambda**：将体量超过 10 行的 lambda 逻辑提取为具名函数或函数对象
2. **消除重复**：在多处出现相同意图的 lambda 时，提取为单一具名函数并在各处引用
3. **命名反映意图**：提取后的函数名应清楚描述其行为，如 `isPassingGrade` 优于内联 lambda
4. **保持就地 lambda**：对于 3-5 行的简单条件/转换/比较逻辑，保留 lambda 更清晰

## 审查清单
- [ ] 算法参数 lambda 体量适中（一般不超过 10 行）
- [ ] 无不必要的复杂多行 lambda 嵌套在算法调用中
- [ ] 相同逻辑未以 lambda 形式在多处重复出现
- [ ] 需要复用的逻辑已提取为具名函数

## 关联页面
- [[cpp-lambda-over-bind]] — Lambda 优先于 std::bind
- [[cpp-lambda-explicit-capture]] — Lambda 显式捕获
- [[cpp-lambda-explicit-return]] — Lambda 显式返回类型
- [[cpp-lambda-no-large-in-hotpath]] — Lambda 性能考量
