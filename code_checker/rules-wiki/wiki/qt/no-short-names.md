---
domain: qt
rule_id: qt-no-short-names
title: 避免使用短变量名
priority: main
source_file: rules/QT代码开发规范.md
source_section: "§2.2"
status: active
check_method: llm
deterministic_check: false
checkability: llm_checkable
conflicts_with: []
overrides: []
related_pages:
  - [[qt-variable-camelcase]]
  - [[qt-no-abbreviations]]
---

# 避免使用短变量名

## 规则条款

避免使用无意义的短变量名（如 `a`、`rbarr`、`nughdeget`）。变量名应当清晰表达其用途和含义。单字符变量仅允许用于：
- 循环计数变量（`i`、`j`、`k`）- 临时变量，作用域不超过 3 行- 数学/矩阵运算中的坐标（`x`、`y`、`z`）- 模板元编程中的类型参数（`T`、`U`）
## 正确示例

```cpp
// 循环计数器 —— 允许
for (int i = 0; i < rowCount; ++i) {
    for (int j = 0; j < columnCount; ++j) {
        table[i][j] = 0;
    }
}

// 语义清晰的变量名
int elapsedSeconds = timer.elapsed() / 1000;
QString errorMessage = tr("Connection failed");
double averageSalary = totalSalary / employeeCount;

// 数学坐标 —— 允许
void setPosition(double x, double y, double z) { /* ... */ }
```

## 错误示例

```cpp
int a = computeValue();            // 错误：'a' 无意义QString s = getUserInput();        // 错误：'s' 不清晰double rbarr = getRatio();         // 错误：'rbarr' 含义不明
int nd = fetchData();              // 错误：'nd' 无法理解

// 非循环场景使用单字符
for (int q = 0; q < items.size(); ++q) {  // 错误：应使用 i/j/k
    items[q]->update();
}
```

## 检查方法
1. 使用 LLM 对变量名进行语义分析。2. 提取所有局部变量和参数名。3. 排除允许的单字符场景（循环计数器、坐标、模板参数）。4. 标记长度过短（通常 < 2 字符）或无法推断含义的变量名。5. 建议重命名为描述性名称。
## 修复指南

1. 将短变量名替换为描述性名称。2. 遵循驼峰命名法（另见 [[qt-variable-camelcase]]）。3. 循环计数器统一使用 `i`、`j`、`k`（非 `q` 或 `idx`，除非语义需要）。4. 示例修复：   ```cpp
   // 修改前：   int nd = fetchData();
   // 修改后：   int networkDelay = fetchData();
   ```

## 审查清单

- [ ] 所有变量名（除循环计数器和坐标外）长度 ≥ 3 字符
- [ ] 变量名能直观表达其用途和含义
- [ ] 循环计数器统一使用 `i`、`j`、`k`
- [ ] 无 `a`、`b`、`tmp`、`buf` 等含义模糊的变量名
## 关联页面

- [[qt-variable-camelcase]] —— 变量名采用驼峰命名法
- [[qt-no-abbreviations]] —— 避免使用缩写
