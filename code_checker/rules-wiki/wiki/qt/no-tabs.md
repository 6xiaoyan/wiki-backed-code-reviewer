---
domain: qt
rule_id: qt-no-tabs
title: 仅使用空格，禁止使用 TAB 字符
priority: main
source_file: rules/QT代码开发规范.md
source_section: "§2.1"
status: active
check_method: regex
deterministic_check: true
checkability: deterministic
conflicts_with: []
overrides: []
related_pages:
  - [[qt-indent-4-spaces]]
---

# 仅使用空格，禁止使用 TAB 字符
## 规则条款

源代码中**禁止使用制表符（Tab 字符，`\t`）**进行缩进或对齐。所有缩进必须使用空格字符（` `）。Tab 字符在不同编辑器中的显示宽度不一致（2、4、8 等），会导致代码对齐混乱、diff 难以阅读。如果文件来源于外部且已包含 Tab，应统一转换为空格后再提交。
## 正确示例

```cpp
void MainWindow::onActionTriggered()
{
    // 4 个空格缩进，无 Tab 字符
    if (!m_document) {
        m_document = new Document(this);
    }
    m_document->reload();
}
```

## 错误示例

```cpp
void MainWindow::onActionTriggered()
{
→  if (!m_document) {          // 错误：使用了 Tab 字符
→  →  m_document = new Document(this);  // 错误：Tab 缩进
→  }
}
```

## 检查方法
1. 读取源代码文件内容。2. 搜索 Tab 字符（`\t` 或 ASCII 0x09）。3. 若任意行包含 Tab 字符，标记违规。
正则表达式：`\t` —— 匹配文件中任意位置的制表符。
## 修复指南

1. Qt Creator：`Options > C++ > Edit > Tabs And Indentation`，Tab policy 设为 `Spaces Only`。2. VS Code：`"editor.insertSpaces": true`，`"editor.tabSize": 4`。3. 对已有文件执行批量替换：将 `\t` 替换为 4 个空格。4. 使用 `clang-format -i --style="{UseTab: Never, IndentWidth: 4}" <file>` 自动修正。5. 可在 pre-commit hook 中添加 `grep -P '\t'` 检查防止 Tab 提交。
## 审查清单

- [ ] 源代码文件不包含任何 Tab 字符（`\t`）- [ ] Makefile 等必须使用 Tab 的文件已加入豁免列表
- [ ] 编辑器已设置为「使用空格替代 Tab」- [ ] `.editorconfig` 中包含 `indent_style = space`

## 关联页面

- [[qt-indent-4-spaces]] —— 采用 4 个空格作为缩进单位