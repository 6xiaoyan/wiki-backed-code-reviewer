---
domain: qt
rule_id: qt-indent-4-spaces
title: 采用 4 个空格作为缩进单位
priority: main
source_file: rules/QT代码开发规则.md
source_section: "§2.1"
status: active
check_method: regex
deterministic_check: true
checkability: deterministic
conflicts_with: []
overrides: []
related_pages: []
---

# 采用 4 个空格作为缩进单位
## 规则条款

所有Qt/C++ 源代码文件采用**4 个空格* 作为一级缩进单位。禁止使用2 空格、空格或制表符（Tab）进行缩进。这是Qt 项目的基础格式规范，确保代码在任意编辑器和 diff 工具中呈现一致。
## 正确示例

```cpp
void MyWidget::updateDisplay()
{
    if (m_enabled) {
        m_label->setText(m_text);
        m_label->setVisible(true);
    } else {
        m_label->setVisible(false);
    }
}
```

## 错误示例

```cpp
void MyWidget::updateDisplay()
{
  if (m_enabled) {        // 错误：使用了 2 个空格缩进    m_label->setText(m_text);
      m_label->setVisible(true);  // 错误：缩进不一致  }
}
```

## 检查方法
1. 扫描源代码文件中的每一行。2. 提取行首空白字符（空格和制表符）。3. 验证每一级缩进的空格数是否为 4 的整数倍。4. 若发现非 4 倍数缩进（排除空行和仅含注释的行），标记违规。
正则表达式：`^( {1,3}| {5,7}| {9,11}| {13,15}| {17,19}| {21,23}| {25,27}| {29,31}| {33,35}| {37,39}|[ \t]*(?:[^ ]|[ ]{0,3}$))` 的变体用于检测缩进偏差。实际检测建议逐行计算缩进深度并取模。
## 修复指南

1. 使用编辑器的「转换缩进为空格」功能（如VS Code 中`Convert Indentation to Spaces`，设置tab size 为4）。2. 或手动替换：将每行前导的 2 空格替换为4 空格，依此类推。3. Qt Creator 中：`Options > C++ > Edit > Tabs And Indentation`，设置Tab policy 为`Spaces Only`，Tab size 为4，Indent size 为4。4. 运行 clang-format 配置 `IndentWidth: 4` 自动修正。
## 审查清单

- [ ] 代码中所有缩进均为4 个空格的整数倍- [ ] 未混用2 空格、8 空格缩进
- [ ] 编辑器已配置为spaces-only 模式

## 关联页面

- [[qt-no-tabs]]：仅使用空格，禁止使用 TAB 。