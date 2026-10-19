---
domain: google
rule_id: google-comments
title: 注释规范（Google C++ Style Guide 对照）
priority: sub
source_file: rules/Google_C++_Style_Guide.md
source_section: "第 8 章"
status: active
check_method: llm
deterministic_check: false
checkability: llm_checkable
conflicts_with: []
overrides: []
related_pages: []
---

# 注释规范（Google C++ Style Guide 对照）

> 来源：Google C++ Style Guide 第 8 章 | 公司规则未覆盖注释风格，可作为补充

## 规则条款

Google 的注释规范较为完善，公司规则体系中未明确覆盖注释风格。以下条款可作为公司代码的补充参考：

### 注释风格
- 使用 `//` 或 `/* */`，保持一致即可

### 文件注释
- 每个文件顶部放置版权声明（公司可根据需要调整）

### 类注释
- 每个类定义应有注释描述其目的和用法（除非功能显而易见）

```cpp
// Iterates over the contents of a GargantuanTable.
class GargantuanTableIterator {
  ...
};
```

### 函数注释
- **声明**处注释描述*做了什么*
- **定义**处注释描述*如何做*

### 变量注释
- 类数据成员：每个数据成员应有注释解释其用途
- 全局变量：需要注释解释含义、用途和为何是全局的

### 实现注释
- 对巧妙、晦涩、有趣或重要的代码部分进行注释
- **禁止**："绝不要用自然语言翻译代码作为注释"——不描述显而易见的事

### TODO 注释
```cpp
// TODO(kl@gmail.com): Use a "*" here for concatenation operator.
// TODO(bug 12345): remove the "Last visitors" feature
```

### 弃用注释
- 用 `DEPRECATED` 注释标记弃用的接口点

## 审查清单

- [ ] 类/函数有足够的注释（非显而易见的逻辑）
- [ ] 注释不重复描述代码本身
- [ ] TODO 包含负责人或 bug ID
- [ ] 弃用接口有 `DEPRECATED` 标记
