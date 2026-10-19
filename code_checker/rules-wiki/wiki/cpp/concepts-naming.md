---
domain: cpp
rule_id: cpp-concepts-naming
title: Concepts 命名规范
priority: main
source_file: rules/C++代码规范.md
source_section: "§5.2 C++20 Concepts"
status: active
check_method: regex
deterministic_check: true
checkability: deterministic
conflicts_with: []
overrides: []
related_pages:
  - [[cpp-concepts-cpp20]]
  - [[cpp-concepts-std-first]]
  - [[cpp-concepts-precise]]
  - [[cpp-template-meaningful-names]]
---

# Concepts 命名规范

## 规则条款
概念应定义在命名空间范围内，具有描述性名称。命名应清晰传达该概念对类型的约束语义：

- 使用 PascalCase 命名（与类型、类的命名风格一致）。
- 名称应反映"是什么"而非"做什么"——如 `Sortable`、`StringLike`、`IndexableContainer`。
- 避免过于笼统的名称（如 `IsValid`、`Check`、`Satisfies`）——这些名称不能传达具体约束。
- 概念应定义在命名空间层级（非类内部、非函数内部），便于复用。
- 区分概念（concept）和类型特征（type trait）：概念用 PascalCase 名词，类型特征用 `snake_case` 后跟 `_v` 或 `_t`。

## 正确示例
```cpp
#include <concepts>
#include <string>
#include <iterator>

namespace mylib {

// 描述性概念名：传达"是什么"
template <typename T>
concept StringLike = std::convertible_to<T, std::string_view>;

template <typename T>
concept IndexableContainer = requires(T c, size_t i) {
    { c[i] } -> std::convertible_to<typename T::value_type>;
};

template <typename T>
concept Sortable = std::permutable<T> && requires(T c) {
    { std::ranges::sort(c) };
};

template <typename T>
concept Arithmetic = std::integral<T> || std::floating_point<T>;

template <typename T>
concept Hashable = requires(T v) {
    { std::hash<T>{}(v) } -> std::convertible_to<std::size_t>;
};

template <typename Func, typename... Args>
concept CallableWith = std::invocable<Func, Args...>;

template <typename T>
concept Printable = requires(T v, std::ostream& os) {
    { os << v } -> std::convertible_to<std::ostream&>;
};

} // namespace mylib

// 使用命名空间内的概念
template <mylib::StringLike S, mylib::Printable P>
void log(const S& key, const P& value) {
    std::cout << key << ": " << value << '\n';
}
```

## 错误示例
```cpp
// 无意义的名称：不传达任何约束信息
template <typename T>
concept IsValid = true;

template <typename T>
concept Check = requires(T t) { t.go(); };

template <typename T>
concept Satisfies = std::is_arithmetic_v<T>;
// "满足什么？"— 名称无法回答

// 类内部定义的概念 — 难以复用
class Widget {
public:
    template <typename T>
    concept WidgetLike = requires(T w) { w.process(); };  // 违规：定义在类内部
};

// 使用 snake_case 命名概念 — 与类型特征命名冲突
template <typename T>
concept string_like = std::convertible_to<T, std::string_view>;
// 应改为：StringLike

// 命名过度宽泛
template <typename T>
concept HasRequirements = requires {
    typename T::value_type;
};
// "HasRequirements" 不传达任何具体信息 — 应该是 "HasValueType" 或 "ContainerLike"

// 全局命名空间定义概念 — 可能与其他库冲突
template <typename T>
concept Number = std::integral<T> || std::floating_point<T>;
// 应放在项目命名空间内
```

## 检查方法
1. **确定性检测**：用正则匹配 `concept\s+(\w+)` 提取概念名称，验证命名是否符合 PascalCase。
2. 验证概念是否定义在命名空间内（`concept` 声明前应有 `namespace` 声明，或使用 `::` 限定）。
3. 检查概念名称是否具有描述性——排除 `IsValid`、`Check`、`Satisfies`、`Ok` 等模糊名称。
4. 确认没有 `concept` 声明在类体或函数体内。
5. 确认概念名称不与标准库概念（`std::integral`、`std::invocable` 等）冲突。

## 修复指南
- **命名风格**：`snake_case` 概念名 → 改为 PascalCase（如 `string_like` → `StringLike`）。
- **放入命名空间**：全局概念 → 移到项目命名空间（如 `namespace proj { template<typename T> concept ... }`）。
- **命名改善**：模糊名称 → 描述性名称：
  - `IsValid` → 具体的概念名（如 `Serializable`、`NetworkReady`）
  - `Check` → 具体的概念名（如 `HasProcessMethod`）
  - `HasValue` → `HasValueType` 或 `Dereferenceable`
- **类内概念**：移到命名空间层级，在类外定义。

## 审查清单
- [ ] 所有概念名是否使用 PascalCase？
- [ ] 概念是否定义在命名空间层级（非类内、非函数内）？
- [ ] 概念名称是否清晰传达"是什么"（而非模糊的 Is-/Has-/Check-）？
- [ ] 概念名是否与类型特征命名（`_v`/`_t` 后缀）有明确区分？
- [ ] 是否避免与标准库概念（`std::` 命名空间下）冲突？

## 关联页面
- [[cpp-concepts-cpp20]] — C++20 Concepts 强制使用
- [[cpp-concepts-std-first]] — 优先使用标准概念
- [[cpp-concepts-precise]] — Concepts 精确性要求
- [[cpp-template-meaningful-names]] — 模板参数命名规范
