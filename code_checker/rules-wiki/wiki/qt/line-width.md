---
domain: qt
rule_id: qt-line-width
title: 每行代码不超过120 字符（Qt 域放宽），超长断行
priority: main
source_file: rules/QT代码开发规则.md
source_section: "§2.7"
status: active
check_method: regex
deterministic_check: true
checkability: deterministic
conflicts_with: [cpp-line-width]
overrides: []
related_pages:
  - [[qt-line-break-style]]
  - [[cpp-line-width]]
---

# 每行代码不超过120 字符（Qt 域放宽），超长断行
## 规则条款

每行代码（包括注释）的*最大长度为 120 字符**。这是对 C++ 通用 100 字符规则的Qt 域放宽（Qt 信号/槽声明、较长的字符串字面量等需要更多空间）。超长行必须进行断行处理。
**跨域冲突**：本规则与C++ 的`cpp-line-width`（100 字符）存在冲突。公司C++ 硬约束"行宽 ≤ 100 字符"具有最高优先级，`cpp-line-width` 覆盖本规则。Qt 项目实际应遵循C++ 硬约束的 100 字符标准。
## 正确示例

```cpp
// 120 字符以内 — 无需断行
void MainWindow::updateStatusBar(const QString &message, int timeout) { /* ... */ }

// 超长行— 合理断行
void DataProcessor::processRecords(
        const QList<Record> &incomingRecords,
        const ProcessingOptions &options,
        QList<Result> *outputResults)
{
    QString errorText = tr("The operation '%1' failed with error code %2. "
                           "Please check the logs for details.")
                                .arg(operationName)
                                .arg(errorCode);
}

// 信号声明 — Qt 信号参数较多时可断行
signals:
    void dataProcessed(
            const QString &identifier,
            const ProcessingResult &result,
            QPrivateSignal);
```

## 错误示例

```cpp
// 错误：行超过 120 字符（未能断行）
void DataProcessor::processRecords(const QList<Record> &incomingRecords, const ProcessingOptions &options, QList<Result> *outputResults) {

// 错误：行超过 120 字符的长字符串QString errorText = tr("The operation '%1' failed with error code %2. Please check the logs for more detailed information.").arg(opName).arg(code);
```

## 检查方法
1. 逐行扫描源代码文件。2. 计算每行的字符长度（排除行尾换行符）。3. 若长度> 120，标记违规。4. 排除不可避免的超长场景（如URL 字符串、自动生成代码、长宏定义），但仍建议断行处理。
正则表达式：`^.{121,}$` 匹配超过 120 字符的行（需配合多行模式）。
## 修复指南

1. **函数参数断行**：参数在逗号后换行，后续参数对齐到第一个参数位置。2. **长字符串**：使用C++11 字符串字面量拼接（`"..." "..."`），或使用`QString` 的链式`.arg()` 调用断行。3. **长表达式**：在操作符处断行，操作符放在新行开头（参[[qt-line-break-style]]）。4. 使用 clang-format：`ColumnLimit: 120`。5. Qt Creator：`Options > C++ > Edit > Format > Column limit: 120`。
## 审查清单

- [ ] 所有代码行 ≤ 120 字符
- [ ] 超长行已按规则正确断行- [ ] 断行后的续行缩进合理（通常为8 空格或对齐参数）
- [ ] `.clang-format` 的`ColumnLimit` 设为 120

## 关联页面

- [[qt-line-break-style]]：断行风格：逗号置行尾，操作符置下行开头