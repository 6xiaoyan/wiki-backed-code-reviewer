---
domain: qt
rule_id: qt-class-max-lines
title: 单个类代码量超1000 行时评估是否拆分
priority: main
source_file: rules/QT代码开发规则.md
source_section: "§4.1 代码行数限制"
status: active
check_method: regex
deterministic_check: false
checkability: advisory_only
conflicts_with: []
overrides: []
related_pages:
  - [[qt-function-max-lines]]
  - [[qt-member-declaration-order]]
  - [[qt-cpp-function-order]]
---

# 单个类代码量超1000 行时评估是否拆分

## 规则条款

单个类的实现文件代码量达到1000 行时，应评估是否需要拆分为多个更小的类。此规则为建议性质（advisory），不强制要求拆分，但必须进行评估并给出结论。
## 正确示例

```cpp
// 类职责单一，即使接近1000 行也可接受//（如包含大量格式化逻辑的报表生成器）
class ReportGenerator : public QObject
{
    Q_OBJECT

public:
    explicit ReportGenerator(QObject *parent = nullptr);

    void generatePdfReport(const QString &path);
    void generateCsvReport(const QString &path);
    void generateHtmlReport(const QString &path);

private:
    // ~50 行配置与初始化
    // ~200 行PDF 生成
    // ~150 行CSV 生成
    // ~180 行HTML 生成
    // ~120 行通用辅助
    // ~100 行错误处理
    // ~50 行资源清理
    // 总计约850 行，职责内聚，无需拆分
};

// 如果超过 1000 行，拆分后的良好设计
class PdfReportSection : public QObject { /* 200 行 */ };
class CsvReportSection : public QObject { /* 150 行 */ };
class HtmlReportSection : public QObject { /* 180 行 */ };

class ReportGenerator : public QObject
{
    Q_OBJECT

public:
    explicit ReportGenerator(QObject *parent = nullptr);

private:
    PdfReportSection *m_pdfSection;
    CsvReportSection *m_csvSection;
    HtmlReportSection *m_htmlSection;
    // ReportGenerator 自身约120 行（编排逻辑）
};
```

## 错误示例

```cpp
// 反例：MainWindow 包含所有业务逻辑，一个文件3000+ 行
class MainWindow : public QMainWindow
{
    Q_OBJECT

public:
    // 100+ 行公共接口
    // ...

private slots:
    // 200+ 行文件操作槽
    // 300+ 行网络请求槽
    // 250+ 行数据处理槽
    // 150+ 行UI 状态管理
    // ...

private:
    // 200+ 行私有辅助函数
    // 500+ 行业务逻辑（文件、网络、数据库混合）
    // ...
    // 总计 3000+ 行，明确需要拆分
};
```

## 检查方法
1. 统计每个类实现文件（`.cpp`）中的非空行数（排除纯注释和空行）。2. 如果单个类的总行数（包括头文件中的内联实现）达到 1000 行：
   - 评估该类的职责数量。   - 如果类承担了多个独立职责（如文件操作 + 网络请求 + 数据计算），建议拆分。   - 如果类职责高度内聚且拆分反而增加复杂度，记录评估结论即可。3. 行数统计可自动化（正常WC），是否拆分需人工判断。
统计方法：- 使用 `wc -l` 或IDE 的代码统计功能。- 排除自动生成的代码（如MOC 生成代码、UI 文件生成代码）。
## 修复指南

1. 分析类的职责，识别可拆分的独立功能模块。2. 按单一职责原则提取新类：   - 数据管理 → `XxxDataManager`
   - 网络通信 → `XxxNetworkClient`
   - 文件 I/O → `XxxFileHandler`
   - UI 逻辑 → `XxxWidget` 或`XxxController`
3. 在原类中使用组合代替内联实现。4. 为新类编写独立的头文件（遵循 Q-25 规则）和实现文件。5. 更新 `.pro` / `CMakeLists.txt`，确保新文件参与编译。
## 审查清单

- [ ] 已统计每个类的代码行数。- [ ] 超1000 行的类已完成是否拆分的评估。- [ ] 需拆分的类已按职责拆分为更小的类。- [ ] 拆分后每个子类职责单一、行数合理。- [ ] 新类的文件命名符合Q-25 规范
- [ ] 项目编译通过，测试通过

## 关联页面

- [[qt-function-max-lines]]：单个函数超2000 行必须拆分。- [[qt-member-declaration-order]]：类成员声明顺序。- [[qt-cpp-function-order]]：.cpp 函数顺序与.h 一致。