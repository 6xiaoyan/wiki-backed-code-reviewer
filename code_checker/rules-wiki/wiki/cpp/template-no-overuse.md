---
domain: cpp
rule_id: cpp-template-no-overuse
title: 模板元编程节制
priority: main
source_file: rules/C++代码规范.md
source_section: "§5.1 模板编程"
status: active
check_method: llm
deterministic_check: false
checkability: advisory_only
conflicts_with: []
overrides: []
related_pages:
  - [[cpp-template-meaningful-names]]
  - [[cpp-template-constraints]]
  - [[cpp-template-over-macros]]
---

# 模板元编程节制

## 规则条款
避免过度使用模板元编程（Template Meta-Programming, TMP），保持代码可读性。TMP 虽然强大，但过度使用会导致：
- 编译时间显著增加
- 错误信息难以理解
- 代码可读性严重下降
- 调试困难（无运行时状态）
- 新人难以维护

模板元编程应保留给真正的核心需求——当需要编译期多态、类型列表操作、或无可替代的性能优化时。在绝大多数场景下，运行期多态、`constexpr` 函数、或简单的泛型模板已经足够。

判断标准：如果模板代码中大量使用递归实例化、类型特征推导链、或超过 3 层的模板嵌套，则很可能属于过度使用。

## 正确示例
```cpp
// 简洁的泛型模板 —— 可读性好
template <typename Container>
auto findMin(const Container& c) {
    return *std::min_element(c.begin(), c.end());
}

// 用 constexpr 替代 TMP 编译期计算
constexpr int factorial(int n) {
    return n <= 1 ? 1 : n * factorial(n - 1);
}

// 用运行期多态替代 TMP —— 更清晰
class DataProcessor {
public:
    virtual ~DataProcessor() = default;
    virtual void process(const Data& data) = 0;
};

void executeAll(const std::vector<std::unique_ptr<DataProcessor>>& processors,
                const Data& data) {
    for (const auto& proc : processors) {
        proc->process(data);
    }
}

// 适度的 TMP：简单的类型特征
template <typename T>
struct IsStringLike
    : std::disjunction<
        std::is_constructible<std::string, T>,
        std::is_convertible<T, std::string_view>
    > {};

template <typename T>
inline constexpr bool isStringLikeV = IsStringLike<T>::value;
```

## 错误示例
```cpp
// 过度 TMP：深递归编译期列表
template <typename... Types>
struct TypeList {};

template <typename List>
struct Length;

template <typename... Types>
struct Length<TypeList<Types...>>
    : std::integral_constant<size_t, sizeof...(Types)> {};

template <typename List>
struct Reverse;

template <>
struct Reverse<TypeList<>>
    : TypeList<> {};

template <typename T, typename... Rest>
struct Reverse<TypeList<T, Rest...>>
    : Concat<
        typename Reverse<TypeList<Rest...>>::type,
        TypeList<T>
    > {};

// ... 还需要 Concat、Filter、Transform、Find ...

// 过度 TMP：编译期表达式模板（简单算术不应如此复杂）
template <typename L, typename Op, typename R>
struct BinaryExpr {
    L m_left;
    R m_right;
    auto eval() const { return Op::apply(m_left.eval(), m_right.eval()); }
};

template <typename T>
struct Literal {
    T m_value;
    auto eval() const { return m_value; }
};

template <typename L, typename R>
auto operator+(L left, R right) {
    return BinaryExpr<L, std::plus<>, R>{left, right};
}
// 每层操作都产生不同类型，复杂表达式类型长达数百字符

// 过度 TMP：用 SFINAE 实现简单的 if-else 逻辑（应用 if constexpr）
template <typename T>
typename std::enable_if<std::is_integral_v<T>, void>::type
processValue(T value) {
    handleIntegral(value);
}

template <typename T>
typename std::enable_if<!std::is_integral_v<T>, void>::type
processValue(T value) {
    handleOther(value);
}
```

## 检查方法
1. 审查模板代码中的递归实例化深度——超过 3 层的递归 TMP 应该被标记。
2. 评估是否可以用 `constexpr` 函数替代编译期类型计算。
3. 评估是否可以用运行期多态（虚函数）替代编译期多态（CRTP、表达式模板）。
4. 评估是否可以用 `if constexpr`（C++17）替代 SFINAE 重载。
5. LLM 辅助判断：模板代码块的圈复杂度、嵌套深度、以及是否对非模板专家可读。
6. 检查编译时间——模板密集的文件编译时间是否显著长于项目平均水平。

## 修复指南
- **编译期计算 → constexpr**：将用 TMP 实现的纯值计算（阶乘、斐波那契等）替换为 `constexpr` 函数。
- **SFINAE 重载 → if constexpr**：C++17 项目将简单的 SFINAE 二选一用 `if constexpr` 替代。
- **CRTP → 虚函数（权衡）**：如果 CRTP 的唯一目的是多态，考虑是否可以用虚函数替代（接受微小的虚调用开销换取可读性）。
- **类型列表操作 → 标准库**：用标准库设施（`std::tuple`、`std::variant`、折叠表达式）替代手写的类型列表操作。
- **表达式模板 → 评估必要性**：表达式模板应仅用于领域特定库（线性代数、DSL），常规业务代码中不应出现。
- **适度分层**：将 TMP 核心局限在少数几个 utility 头文件中，避免散布到业务代码中。

## 审查清单
- [ ] 是否存在超过 3 层递归深度的 TMP 代码？
- [ ] 是否有可以用 `constexpr` 函数替代的编译期值计算？
- [ ] 是否有可以用 `if constexpr` 替代的 SFINAE 重载对？
- [ ] 是否有可以用运行期多态替代的 CRTP / 表达式模板？
- [ ] 类型操作是否可以使用标准库设施（`std::tuple`、`std::variant`、折叠表达式）？
- [ ] 模板密集文件的编译时间是否在可接受范围内？

## 关联页面
- [[cpp-template-meaningful-names]] — 模板参数命名规范
- [[cpp-template-constraints]] — 模板约束的正确使用
- [[cpp-template-over-macros]] — 模板与宏的选择
