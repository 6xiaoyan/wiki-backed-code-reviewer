---
domain: qt
rule_id: qt-blank-line-grouping
title: 空行分组语句，空行仅保留 1 个
priority: main
source_file: rules/QT代码开发规则.md
source_section: "§2.3"
status: active
check_method: regex
deterministic_check: true
checkability: deterministic
conflicts_with: []
overrides: []
related_pages:
  - [[qt-minimal-blank-lines]]
---

# 空行分组语句，空行仅保留 1 个
## 规则条款

利用**单个空行**对逻辑上相关的语句进行分组，提升代码层次感和可读性。禁止连续出现多个空行（2 行及以上）。文件末尾仅保留一个换行符（即 1 个空行）。空行分组原则：
- 变量声明块与后续执行语句之间
- 不同逻辑段落之间
- return 语句之前（当它代表一个独立逻辑段落时）
- 函数定义之间

## 正确示例

```cpp
void MainWindow::loadSettings()
{
    QSettings settings("MyCompany", "MyApp");

    m_windowWidth = settings.value("windowWidth", 800).toInt();
    m_windowHeight = settings.value("windowHeight", 600).toInt();
    m_isMaximized = settings.value("maximized", false).toBool();

    m_lastFile = settings.value("lastFile", "").toString();
    m_recentFiles = settings.value("recentFiles").toStringList();

    bool needsResize = (width() != m_windowWidth) || (height() != m_windowHeight);
    if (needsResize) {
        resize(m_windowWidth, m_windowHeight);
    }
}

void MainWindow::saveSettings()
{
    QSettings settings("MyCompany", "MyApp");
    settings.setValue("windowWidth", width());
    settings.setValue("windowHeight", height());
}
```

## 错误示例

```cpp
void MainWindow::loadSettings()
{
    QSettings settings("MyCompany", "MyApp");


    m_windowWidth = settings.value("windowWidth", 800).toInt();  // 错误：双空行


    m_windowHeight = settings.value("windowHeight", 600).toInt();


    bool needsResize = (width() != m_windowWidth);  // 错误：连续空多行
}
```

## 检查方法
1. 扫描源代码文件。2. 检测连续出现的空行（两个或更多连续的仅包含空白字符的行）。3. 检测文件开头的空行和文件末尾的多余空行。
正则表达式：`\n\s*\n\s*\n` 匹配连续两个及以上空行。
## 修复指南

1. 将连续多个空行压缩为单个空行。2. 删除文件开头的空行。3. 文件末尾保留恰好一个换行符。4. 使用 clang-format：`MaxEmptyLinesToKeep: 1`。5. 使用编辑器功能：VS Code 中`Files: Trim Trailing Whitespace` 和 `Files: Insert Final Newline`。
## 审查清单

- [ ] 代码中无连续 2 个及以上空行
- [ ] 空行合理分组语句，增强可读性- [ ] 文件开头无空行
- [ ] 文件末尾恰好一个换行符

## 关联页面

- [[qt-minimal-blank-lines]]：空行使用原则：代码简洁优先