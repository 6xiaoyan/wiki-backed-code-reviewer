---
domain: qt
rule_id: qt-minimal-blank-lines
title: 空行使用原则：代码简洁优先，不提倡冗余空行
priority: main
source_file: rules/QT代码开发规则.md
source_section: "§2.9"
status: active
check_method: llm
deterministic_check: false
checkability: advisory_only
conflicts_with: []
overrides: []
related_pages:
  - [[qt-blank-line-grouping]]
  - [[qt-readability-over-rules]]
---

# 空行使用原则：代码简洁优先，不提倡冗余空行
## 规则条款

空行的使用应**恰到好处**，既要用空行分隔不同逻辑段落以增强可读性（参[[qt-blank-line-grouping]]），也要避免**过度使用空行导致代码稀疏、屏幕信息密度降低**。核心原则：
- 用空行分隔**不同逻辑关注点**（变量声明、核心逻辑、错误处理、返回语句）
- 不因个人偏好而插入装饰性空行- 不在一段紧密相关的代码内部插入空行
- 不在函数开头、结尾插入多余的空行

## 正确示例

```cpp
void DataExporter::exportToCsv(const QString &filePath)
{
    if (filePath.isEmpty()) {
        qWarning() << "Empty file path for CSV export";
        return;
    }
    QFile file(filePath);
    if (!file.open(QIODevice::WriteOnly | QIODevice::Text)) {
        emit exportFailed(file.errorString());
        return;
    }
    QTextStream stream(&file);
    // 写表头    stream << "Name,Value,Timestamp\n";
    // 写数据行
    for (const auto &record : m_records) {
        stream << record.name << ","
               << record.value << ","
               << record.timestamp.toString(Qt::ISODate) << "\n";
    }
    file.close();
    emit exportFinished(filePath);
}
```

## 错误示例

```cpp
void DataExporter::exportToCsv(const QString &filePath)
{

    if (filePath.isEmpty()) {           // 错误：函数开头多余空行
        qWarning() << "Empty file path";
        return;
    }

    QFile file(filePath);

    if (!file.open(QIODevice::WriteOnly)) {  // 错误：过多空行降低密度
        emit exportFailed(file.errorString());

        return;                       // 错误：简单返回前无需空行

    }

    QTextStream stream(&file);




    stream << "Name,Value\n";          // 错误：连续多个空行

    file.close();

    emit exportFinished(filePath);


}                                      // 错误：函数结尾多余空行```

## 检查方法
1. 此规则为**建议性规则（advisory_only）**，不会触发自动拦截。2. LLM 审查时评估空行密度和分布：   - 函数内部空行 / 代码行比率是否过高（如> 30%）   - 是否存在装饰性空行（纯属个人偏好的空行插入）
   - 函数开头和结尾是否有多余空行   - 两个空行是否紧密相邻（已被[[qt-blank-line-grouping]] 规则禁用）。3. 建议精简不合理的空行。
## 使用指南

1. **空行的目的**：仅用于分隔逻辑段落，而非装饰。2. **经验法则**：如果两段代码之间需要一个空行来提升可读性，加一个；如果加不加都能看清，不加。3. **常见不需要空行的场景**：   - 连续的赋值语句   - 简单的 if-return 检查   - 紧密相关的几行调用。4. **需要空行的场景**：   - 变量声明块与执行语句之间
   - 主逻辑与错误处理之间   - 不同阶段的处理之间   - 函数定义之间

## 审查清单

- [ ] 空行合理分隔逻辑段落，无装饰性空行- [ ] 函数开头和结尾无多余空行- [ ] 紧密相关语句之间无空行- [ ] 无连续多个空行（已被 qt-blank-line-grouping 禁用）- [ ] 空行密度适中，代码信息密度合理
## 关联页面

- [[qt-blank-line-grouping]]：空行分组语句，空行仅保留 1 个- [[qt-readability-over-rules]]：可读性优先于规则
