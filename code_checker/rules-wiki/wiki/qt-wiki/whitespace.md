---
domain: qt-wiki
rule_id: qtwiki-whitespace
title: 空白与缩进（Qt Coding Style 对照）
priority: sub
source_file: rules/Qt_Coding_Style.md
source_section: "空白"
status: active
check_method: regex
deterministic_check: true
checkability: deterministic
conflicts_with: []
overrides: []
related_pages:
  - [[qt/no-tabs]]
  - [[qt/line-width]]
  - [[qt/binary-op-spacing]]
  - [[qt/keyword-spacing]]
  - [[qt/no-space-after-cast]]
  - [[qt/no-cstyle-cast]]
  - [[qt/line-break-style]]
---

# 空白与缩进（Qt Coding Style 对照）

> 来源：Qt Coding Style（[wiki.qt.io](https://wiki.qt.io/Qt_Coding_Style)）| 大部分与公司规则一致

## 与公司规则的对照

| Qt Coding Style 条款 | 公司规则页面 | 一致性 |
|---------------------|------------|--------|
| 每级缩进 4 个空格 | [[qt/no-tabs]] | ✅ 一致 |
| 仅使用空格，绝不使用制表符 | [[qt/no-tabs]] | ✅ 一致 |
| 每行 100 字符以内 | [[qt/line-width]] | ⚠️ 公司规则为 120 字符。**公司规则为准** |
| 逗号留在行尾，运算符放在新行开头 | [[qt/line-break-style]] | ✅ 一致 |
| 控制流关键字后和 `{` 前加一个空格 | [[qt/keyword-spacing]] | ✅ 一致 |
| 二元运算符周围加空格 | [[qt/binary-op-spacing]] | ✅ 一致 |
| 转换后不加空格 | [[qt/no-space-after-cast]] | ✅ 一致 |
| 优先使用 C++ 风格转换而非 C 风格转换 | [[qt/no-cstyle-cast]] | ✅ 一致 |
| 一行不要放多条语句 | [[qt/one-var-per-line]] | ✅ 一致 |

## ⚠️ 冲突项：行宽

- **Qt Coding Style**：每行 100 字符
- **公司规则**：[[qt/line-width]] 规定 **120 字符**
- **裁决**：**以公司规则为准（120 字符）**

## Qt Coding Style 补充：指针/引用空格

```cpp
char *x;                        // * 与类型之间有空格，与变量名之间无空格
const QString &myString;
const char * const y = "hello";
```

注意：Google C++ Style Guide 允许 `char* x` 和 `char *x` 两种风格，但 Qt Coding Style 要求 `char *x`。

## Qt Coding Style 补充：空行

- 使用空行分组相关语句
- 绝不超过一个空行
- 控制流体总是放在新行上（`if (foo) bar();` 是错误）
