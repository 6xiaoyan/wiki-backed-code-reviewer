---
domain: qt
rule_id: qt-braces-ifelse-symmetry
title: if-else 结构中任意一支跨多行时两侧均需使用大括号
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
  - [[qt-braces-multiline-parent]]
---

# if-else 结构中任意一支跨多行时两侧均需使用大括号

## 规则条款

在`if-else if-else` 结构中，当*任意一个分支*的语句体跨多行（或用大括号包裹）时，**所有分支都必须使用大括号**。这是为了保持视觉对称性和代码一致性，避免阅读者在不同分支之间产生混淆。具体规则：
- 如果 `if` 分支使用了`{}`，`else`（或 `else if`）分支也必须使用
- 如果 `else` 分支有多行语句体，`if` 分支也必须使用`{}`（即使只有一行）
- 如果所有分支都是单行，可以全部省略 `{}`

## 正确示例

```cpp
// 所有分支都是单行，全部省略大括号
if (x > 0)
    doPositive();
else if (x < 0)
    doNegative();
else
    doZero();

// 有一个分支多行，全部使用大括号
if (m_isValid) {
    processData();
} else {
    cleanupResources();
    emit finished(false);
    return;
}

// 有else if 链，其中一支多行，全部使用大括号
if (state == State::Running) {
    updateProgress();
    emit statusChanged("Running");
} else if (state == State::Paused) {
    m_pauseTime = QDateTime::currentDateTime();
    emit statusChanged("Paused");
} else {
    finalize();
}
```

## 错误示例

```cpp
// 错误：if 分支有多行用大括号，else 分支单行却没用大括号
if (m_isValid) {
    processData();
    updateView();
} else
    handleError();  // 错误：不对称

// 错误：else 分支有多行用大括号，if 分支单行却没大括号
if (x > 0)
    doAction();     // 错误：不对称
else {
    undoAction();
    logChange();
}

// 错误：else if 链不对称
if (a) {
    handleA();
} else if (b)
    handleB();       // 错误：不对称
else {
    handleDefault();
}
```

## 检查方法
1. 解析 `if-else if-else` 链中的所有分支。2. 检查每个分支的语句体是单行还是多行（或是否使用了`{}`）。3. 如果分支间存在不一致（有的用`{}`，有的不用`{}`），标记违规。4. 适用于`if`、`else`、以及`if`、`else if` 的组合。
正则表达式（简化思路）：
- 先匹配完整的 `if-else` 链结构。- 然后检查各分支的`{}`使用是否一致。
## 修复指南

1. 统计 `if-else` 链中各分支的复杂度。2. 如果所有分支都是单行：全部省略大括号。3. 如果任一分支持大括号：为所有分支添加大括号。4. 示例修复：   ```cpp
   // 修改前
   if (x > 0) {
       doPositive();
   } else
       doOther();
   
   // 修改后（方案 1 ——全部单行）
   if (x > 0)
       doPositive();
   else
       doOther();
   
   // 修改后（方案 2 ——全部大括号，推荐用于复杂逻辑）
   if (x > 0) {
       doPositive();
   } else {
       doOther();
   }
   ```

## 审查清单

- [ ] `if-else` 链中所有分支的 `{}` 使用一致。- [ ] 若一个分支多行使用`{}`，其他分支也必须使用`{}`
- [ ] `else if` 写作 `} else if (...) {`（在同一行）
- [ ] 无「混合风格」的 if-else 结构

## 关联页面

- [[qt-braces-knr]]：控制流K&R 风格
- [[qt-braces-single-line]]：单行语句体省略大括号
- [[qt-braces-multiline-parent]]：父语句跨行必须使用大括号
