---
domain: qt-wiki
rule_id: qtwiki-variable-declaration
title: 变量声明（Qt Coding Style 对照）
priority: sub
source_file: rules/Qt_Coding_Style.md
source_section: "变量声明"
status: active
check_method: regex
deterministic_check: true
checkability: deterministic
conflicts_with: []
overrides: []
related_pages:
  - [[qt/one-var-per-line]]
  - [[qt/variable-camelcase]]
  - [[qt/no-abbreviations]]
  - [[qt/no-short-names]]
  - [[qt/class-naming-pascal]]
  - [[qt/var-qclass-lowercase]]
---

# 变量声明（Qt Coding Style 对照）

> 来源：Qt Coding Style（[wiki.qt.io](https://wiki.qt.io/Qt_Coding_Style)）| 与公司规则一致

## 与公司规则的对照

Qt Coding Style 中关于变量声明的条款与公司 Qt 规则**整体一致**，以下为详细对照：

| Qt Coding Style 条款 | 公司规则页面 | 一致性 |
|---------------------|------------|--------|
| 每个变量单独一行声明 | [[qt/one-var-per-line]] | ✅ 一致 |
| 名称应有意义，避免缩写 | [[qt/no-abbreviations]]、[[qt/no-short-names]] | ✅ 一致 |
| 单字符名称仅用于计数器/临时变量 | [[qt/no-short-names]] | ✅ 一致 |
| 变量尽晚声明 | [[qt/late-declaration]] | ✅ 一致 |
| 变量/函数以小写开头，驼峰命名 | [[qt/variable-camelcase]] | ✅ 一致 |
| 类以大写开头，公共类 Q 前缀 | [[qt/class-naming-pascal]]、[[qt/var-qclass-lowercase]] | ✅ 一致 |
| 缩写遵循驼峰：`QXmlStreamReader` | [[qt/class-naming-pascal]] | ✅ 一致 |

## Qt Coding Style 补充示例

```cpp
// 每个变量单独一行
int height;
int width;
char *nameOfThis;
char *nameOfThat;

// 小写开头驼峰
short counter;
char itemDelimiter = ' ';
```

## 冲突说明

无冲突。Qt Coding Style 与公司 Qt 规则在变量声明方面完全一致。
