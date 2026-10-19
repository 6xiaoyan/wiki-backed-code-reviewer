---
domain: google
rule_id: google-formatting
title: 代码格式（Google C++ Style Guide 对照）
priority: sub
source_file: rules/Google_C++_Style_Guide.md
source_section: "第 9 章"
status: active
check_method: regex
deterministic_check: true
checkability: deterministic
conflicts_with:
  - "cpp/indentation"
  - "cpp/line-width"
  - "qt/line-width"
overrides: []
related_pages:
  - [[cpp/indentation]]
  - [[cpp/line-width]]
  - [[cpp/braces]]
  - [[qt/line-width]]
  - [[qt/no-tabs]]
  - [[qt/keyword-spacing]]
---

# 代码格式（Google C++ Style Guide 对照）

> 来源：Google C++ Style Guide 第 9 章 | **多处冲突，公司规则为准**

## ❌ 格式冲突汇总

| 项目 | Google 风格 | 公司规则 | 裁决 |
|------|-----------|---------|------|
| **缩进** | **2 个空格** | [[cpp/indentation]] **4 个空格** | ❌ **公司规则为准** |
| **行宽** | **80 字符** | [[cpp/line-width]] **100** / [[qt/line-width]] **120** | ❌ **公司规则为准** |
| **访问修饰符** | 缩进 **1 空格** (` public:`) | 公司无此约束 | ⚠️ 不冲突 |
| **命名空间内** | **不缩进** | 公司无此约束 | ⚠️ 不冲突 |
| **预处理指令** | 从第 0 列开始，不缩进 | 公司无此约束 | ⚠️ 不冲突 |

## ✅ 一致的格式规则

| Google 条款 | 公司规则 | 一致性 |
|------------|---------|--------|
| 仅使用空格，无制表符 | [[qt/no-tabs]] | ✅ 一致 |
| 控制流关键字后加空格 | [[qt/keyword-spacing]] | ✅ 一致 |
| `switch` 必须含 `default` | — | ✅ 一致 |
| 空循环体用 `{}` 或 `continue` | [[qt/braces-empty-body]] | ✅ 一致 |
| 指针/引用 `*`/`&` 后无空格 | — | ✅ 一致 |

## Google 补充条款（公司规则未覆盖）

1. **非 ASCII 字符**：尽量避免；必须使用时为 UTF-8。不使用 `char16_t`、`char32_t` 或 `wchar_t`（Windows API 除外）
2. **垂直留白**：越少越好。函数定义之间 ≤2 空行。函数体首尾无空行
3. **构造函数初始化列表**：
```cpp
MyClass::MyClass(int var)
    : some_var_(var),
      some_other_var_(var + 1) {
  DoSomething();
}
```
4. **水平留白**：一元运算符与操作数之间无空格；模板尖括号周围无空格
