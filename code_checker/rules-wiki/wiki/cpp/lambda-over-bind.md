---
domain: cpp
rule_id: cpp-lambda-over-bind
title: Lambda 优先于 std::bind
priority: main
source_file: rules/C++代码规范.md
source_section: "§2.3 Lambda"
status: active
check_method: llm
deterministic_check: false
checkability: llm_checkable
conflicts_with: []
overrides: []
related_pages:
  - [[cpp-lambda-explicit-capture]]
  - [[cpp-lambda-small-scope]]
  - [[cpp-lambda-explicit-return]]
  - [[cpp-lambda-no-large-in-hotpath]]
---

# Lambda 优先于 std::bind

## 规则条款
在需要创建可调用对象时，优先使用 lambda 表达式而非 `std::bind`。Lambda 表达式比 `std::bind` 更可读、更容易优化，
且在编译期错误信息方面更友好。`std::bind` 应仅在与现有 `std::bind` 密集的代码库交互或需要延迟求值占位符的
极端边缘场景中使用。

## 正确示例
```cpp
#include <algorithm>
#include <functional>
#include <vector>

// Lambda 方式：意图一目了然
auto greaterThan = [](int threshold, int value) {
    return value > threshold;
};

std::vector<int> data = {1, 5, 3, 9, 2};
auto it = std::find_if(data.begin(), data.end(),
                       [threshold = 5](int v) { return v > threshold; });

// 成员函数绑定也推荐 lambda
class Processor {
public:
    void process(int x) { /* ... */ }
};

Processor proc;
auto bound = [&proc](int x) { proc.process(x); };

// 参数重排也用 lambda 而非 std::bind 占位符
auto lessThan = [](int a, int b) { return a < b; };
auto flipped  = [](int a, int b) { return lessThan(b, a); };
```

## 错误示例
```cpp
#include <functional>
#include <vector>
#include <algorithm>

// std::bind 方式：难以阅读，编译错误冗长
using namespace std::placeholders;
auto greaterThan = std::bind(std::greater<int>(), _2, _1);

// 成员函数绑定——bind 方式隐晦
Processor proc;
auto bound = std::bind(&Processor::process, &proc, _1);

// 嵌套 bind 几乎不可读
auto nested = std::bind(std::logical_and<bool>(),
                        std::bind(std::greater<int>(), _1, 0),
                        std::bind(std::less<int>(), _1, 100));
```

## 检查方法
由 LLM 审查代码，检测是否使用了 `std::bind`；除以下豁免情景外均标记违规：
- 与以 `std::bind` 为主的遗留代码库交互
- 需要 `std::placeholders` 且 lambda 替代会显著降低可读性的极端边缘场景

## 修复指南
1. 定位 `std::bind` 调用点
2. 将绑定的参数映射为 lambda 的捕获或参数
3. 将 `_1`, `_2` 等占位符替换为显式 lambda 参数名
4. 验证语义等价性（特别注意参数顺序是否被 `std::bind` 重排）
5. 移除 `using namespace std::placeholders`

## 审查清单
- [ ] 代码中无 `std::bind` 调用（豁免场景除外）
- [ ] 所有可调用对象创建使用 lambda 表达式
- [ ] 成员函数绑定的 lambda 替代语义正确

## 关联页面
- [[cpp-lambda-explicit-capture]] — Lambda 显式捕获
- [[cpp-lambda-small-scope]] — Lambda 适用范围
- [[cpp-lambda-explicit-return]] — Lambda 显式返回类型
- [[cpp-lambda-no-large-in-hotpath]] — Lambda 性能考量
