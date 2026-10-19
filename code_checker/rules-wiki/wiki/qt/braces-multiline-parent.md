---
domain: qt
rule_id: qt-braces-multiline-parent
title: 父语句跨多行时必须使用大括号
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
  - [[qt-braces-single-line]]
  - [[qt-braces-ifelse-symmetry]]
---

# 父语句跨多行时必须使用大括号

## 规则条款

当控制流语句的条件表达式或循环头（父语句）**跨越多行**时，其语句体**必须使用大括号`{}`** 包裹，即使语句体仅有一行。这是为了在视觉上清晰界定条件表达式结束和语句体开始的位置，避免阅读者将语句体误认为条件表达式的一部分。
## 正确示例

```cpp
// 条件跨多行——必须使用大括号
if (m_networkReply->error() != QNetworkReply::NoError
    && m_networkReply->error() != QNetworkReply::OperationCanceledError) {
    handleNetworkError(m_networkReply->error());
}

// for 循环头跨多行 ——必须使用大括号
for (int row = 0;
     row < m_tableModel->rowCount();
     ++row) {
    updateRow(row);
}

// 如果没有跨行，单行语句体可以不使用大括号
if (error == QNetworkReply::NoError)
    handleSuccess();  // OK：条件未跨行，语句体单行，无 else
```

## 错误示例

```cpp
// 错误：条件跨多行，但语句体未使用大括号
if (m_networkReply->error() != QNetworkReply::NoError
    && m_networkReply->error() != QNetworkReply::OperationCanceledError)
    handleNetworkError(m_networkReply->error());  // 很难看出这是语句体
// 错误：for 头跨多行，但省略了大括号
for (QList<Item>::const_iterator it = m_items.constBegin();
     it != m_items.constEnd();
     ++it)
    processItem(*it);  // 易被误读为for 头的第四行
```

## 检查方法
1. 解析控制流语句的头部（`(` 到匹配的 `)` 之间的内容）。2. 检查控制流头部是否跨越了多行（即`(`与`)` 不在同一行）。3. 若跨行，验证语句体是否使用了 `{}`（复合语句）。4. 若跨行且未使用`{}`，标记违规。
正则表达式方法：由于 C++ 语法复杂性，建议使用 AST 解析器。简化检测：匹配 `if`/`for`/`while` 关键字所在行与匹配的 `)` 所在行不同，且下一行不是`{`。
## 修复指南

1. 为语句体添加 `{` 和`}`。2. `{` 放在条件表达式末尾`)` 的同一行（K&R 风格，见 [[qt-braces-knr]]）。3. 示例修复：   ```cpp
   // 修改前
   if (cond1
       && cond2)
       action();
   
   // 修改后
   if (cond1
       && cond2) {
       action();
   }
   ```

## 审查清单

- [ ] 所有跨行的控制流头部都使用了`{}` 包裹语句体。- [ ] 跨行条件的`{`与`)` 在同一行（K&R 风格）。- [ ] 即使语句体只有一行，只要条件跨行就必须使用大括号

## 关联页面

- [[qt-braces-knr]]：控制流K&R 风格
- [[qt-braces-single-line]]：单行语句体省略大括号
- [[qt-braces-ifelse-symmetry]]：if-else 对称使用大括号