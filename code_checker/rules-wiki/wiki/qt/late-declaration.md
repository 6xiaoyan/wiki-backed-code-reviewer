---
domain: qt
rule_id: qt-late-declaration
title: 变量延迟定义，在真正需要使用时再声明
priority: main
source_file: rules/QT代码开发规则.md
source_section: "§2.2"
status: active
check_method: llm
deterministic_check: false
checkability: llm_checkable
conflicts_with: []
overrides: []
related_pages:
  - [[qt-one-var-per-line]]
---

# 变量延迟定义，在真正需要使用时再声明
## 规则条款

变量应在**真正需要使用时才声明和初始化**，而非在函数作用域开头集中声明。这符合 C++ 最佳实践（C++ Core Guidelines C.48），好处包括：- 减少变量的作用域，降低误用风险- 声明即初始化，避免未初始化使用- 提高代码可读性，读者无需记忆前文声明的变量- 便于重构和提取函数
## 正确示例

```cpp
void DataProcessor::process(const QList<Record> &records)
{
    if (records.isEmpty()) {
        qWarning() << "No records to process";
        return;
    }

    int totalValue = 0;  // 在使用前声明
    for (const auto &record : records) {
        totalValue += record.value;
    }

    double averageValue = static_cast<double>(totalValue) / records.size();
    emit statisticsReady(averageValue);
}
```

## 错误示例

```cpp
void DataProcessor::process(const QList<Record> &records)
{
    // 错误：在函数顶部集中声明所有变量    int totalValue = 0;
    double averageValue = 0.0;
    QFile outputFile;
    bool hasError = false;
    QString errorMessage;

    if (records.isEmpty()) {
        qWarning() << "No records to process";
        return;  // 上面声明的totalValue、averageValue 等均未使用    }

    // ... 后续代码
}
```

## 检查方法
1. 使用 LLM 分析函数体。2. 提取变量声明与其首次使用之间的位置关系。3. 若声明位置和首次使用位置之间的代码行数超过阈值（如15 行），标记为违规。4. 特别关注：函数开头集中声明多个变量，但早期return/continue/throw 导致部分变量从未使用的模式。
## 修复指南

1. 将变量声明移动到首次使用行的紧前方。2. 如果变量在多个分支中使用，声明放在分支公共父作用域的最晚位置。3. 结合 RAII 思想：声明即初始化，避免先声明后赋值的两步模式。4. 示例修复：   ```cpp
   // 修改前   int result;
   // ... 20 行代码...
   result = compute();
   
   // 修改后   // ... 20 行代码...
   int result = compute();
   ```

## 审查清单

- [ ] 变量声明位置紧邻首次使用位置
- [ ] 无不必要的顶部集中声明- [ ] 声明与初始化合并在同一条语句中
- [ ] 提前 return 的路径不会跨越未使用的变量声明
## 关联页面

- [[qt-one-var-per-line]]：每行仅声明一个变量