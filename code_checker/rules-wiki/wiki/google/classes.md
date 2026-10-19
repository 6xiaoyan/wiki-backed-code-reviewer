---
domain: google
rule_id: google-classes
title: 类设计规范（Google C++ Style Guide 对照）
priority: sub
source_file: rules/Google_C++_Style_Guide.md
source_section: "第 3 章"
status: active
check_method: llm
deterministic_check: false
checkability: llm_checkable
conflicts_with: []
overrides: []
related_pages:
  - [[qt/no-virtual-on-override]]
  - [[cpp/no-bare-new-delete]]
  - [[cpp/move-ctors]]
---

# 类设计规范（Google C++ Style Guide 对照）

> 来源：Google C++ Style Guide 第 3 章 | 与公司规则大部分一致

## 与公司规则的对照

| Google 条款 | 公司规则 | 一致性 |
|------------|---------|--------|
| 构造函数中不得调用虚函数 | — | 补充条款 |
| 隐式类型转换必须 `explicit` | — | 补充条款 |
| 类必须明确可拷贝/仅移动/不可拷贝不可移动 | [[cpp/move-ctors]] | ✅ 一致 |
| `struct` 仅用于被动数据对象，其他用 `class` | — | 补充条款 |
| 组合优于继承，使用 `public` 继承 | — | 补充条款 |
| `override` 不重复 `virtual` | [[qt/no-virtual-on-override]] | ✅ 一致 |
| 谨慎使用运算符重载，禁止 `&&` `\|\|` `,` 重载 | — | 补充条款 |
| 禁止自定义字面量 | — | 补充条款 |
| 所有数据成员为 `private`（常量除外） | — | 补充条款 |

## 补充条款（公司规则未覆盖）

1. **`explicit` 要求**：类型转换运算符和单参数构造函数必须使用 `explicit`。拷贝/移动构造函数除外
2. **声明次序**：`public` → `protected` → `private`；各部分内：类型别名 → 静态常量 → 工厂函数 → 构造/赋值 → 析构 → 其他函数
3. **结构体 vs 类**：只能用 `struct` 定义储存数据的被动对象（所有成员公有、无不变式关系）
4. **继承**：仅在 "is-a" 关系下使用继承；不想被继承时使用 `final`
5. **禁止重载** `&&`、`||`、`,` 或一元 `&` 运算符
6. **结构体 vs 数对/元组**：给成员起有意义的名字时用结构体而非 `pair`/`tuple`
