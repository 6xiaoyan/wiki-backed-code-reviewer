---
domain: qt
rule_id: qt-braces-single-line
title: 单行控制语句体不使用大括号
priority: main
source_file: rules/QT代码开发规则.md
source_section: "§2.4"
status: active
check_method: regex
deterministic_check: true
checkability: deterministic
conflicts_with: []
overrides: []
related_pages:
  - [[qt-braces-knr]]
  - [[qt-braces-multiline-parent]]
  - [[qt-braces-ifelse-symmetry]]
---

# 单行控制语句体不使用大括号

## 规则条款

当控制流语句（`if`、`for`、`while` 等），**语句体仅包含 1 行代码且该分支无 `else`** 时，可以**省略大括号`{}`**。这减少视觉噪音，让简洁逻辑更紧凑。必须同时满足两个条件：
1. 语句体只有1 行（不含注释）。2. 该`if` 没有对应的`else` 分支

如果添加 `else`、语句体变为多行、或父语句跨行，必须添加大括号（见[[qt-braces-multiline-parent]]、[[qt-braces-ifelse-symmetry]]）。
## 正确示例

```cpp
// 单行语句体，无else ——省略大括号
if (m_data.isEmpty())
    return;

for (int i = 0; i < count; ++i)
    processItem(i);

while (m_hasMore)
    fetchNext();

// 单语句体有else ——必须用大括号（不满足"无else"条件）
if (m_isValid)
    process();
else
    handleInvalid();  // 有else，两侧均应加大括号（见qt-braces-ifelse-symmetry）
// 正确：加上大括号
if (m_isValid) {
    process();
} else {
    handleInvalid();
}
```

## 错误示例

```cpp
// 错误：单行语句体加了大括号（冗余但不算严重违规——注释说明即可）
if (m_data.isEmpty()) {
    return;
}

// 更严重的违规：有 else 但省略了一侧大括号
if (m_isValid)
    process();
else {
    cleanup();
    reportError();
}

// 错误：多行语句体省略大括号
if (condition)
    step1();
    step2();  // 只有 step1 受if 控制，step2 始终执行（逻辑错误）
```

## 检查方法
1. 解析控制流语句的语句体。2. 检测语句体为单行（非复合语句）且无对应 `else` 时存在`{}`。3. 反之，检测语句体为多行（或存在`else`）却缺少 `{}`。
正则表达式（检测多余大括号）：
```regex
\b(if|for|while)\s*\([^)]*\)\s*\{\s*\n\s*[^{}\n]+\n\s*\}
```
匹配单行语句体被大括号包裹的模式。
## 修复指南

1. 对于仅有 1 行语句体且无 `else` 的控制流：删除`{` 和`}`。2. 确保单行语句体缩进一级（4 个空格）。3. 如果单行太长（>120 字符），考虑保留大括号并换行（参见[[qt-line-width]]）。4. 使用 clang-format：`AllowShortBlocksOnASingleLine: true`，`AllowShortIfStatementsOnASingleLine: true`。
## 审查清单

- [ ] 单行 + 无else → 无大括号
- [ ] 多行或有 else → 有大括号
- [ ] 单行语句体缩进正确。- [ ] 没有把多行语句误认为单行而省略大括号

## 关联页面

- [[qt-braces-knr]]：控制流K&R 风格
- [[qt-braces-multiline-parent]]：父语句跨多行必须使用大括号- [[qt-braces-ifelse-symmetry]]：if-else 两侧都需要大括号
