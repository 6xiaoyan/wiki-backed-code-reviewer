---
domain: qt
rule_id: qt-no-abbreviations
title: 避免使用缩写，保持变量名语义清晰
priority: main
source_file: rules/QT代码开发规范.md
source_section: "§2.2"
status: active
check_method: llm
deterministic_check: false
checkability: llm_checkable
conflicts_with: []
overrides: []
related_pages:
  - [[qt-variable-camelcase]]
  - [[qt-no-short-names]]
---

# 避免使用缩写，保持变量名语义清晰

## 规则条款

变量名和函数名应避免使用缩写，确保代码自文档化。缩写会导致：- 新成员需要记忆项目特定的缩写约定
- 不同开发者对同一概念使用不同缩写
- 难以搜索和重构
允许的例外：
- 业界公认的通用缩写：`idx`（index）、`prev`（previous）、`init`（initialize）、`calc`（calculate）、`doc`（document）、`app`（application）- UI 控件前缀缩写（`lbl`、`btn`、`edt` 等，遵循 Qt 控件命名规范）- 循环计数器 `i`、`j`、`k`
- 模板类型参数 `T`、`U`、`V`

## 正确示例

```cpp
// 完整单词，语义清晰int maximumHeight = computeMaximumHeight();
QString errorMessage = generateErrorMessage();
double standardDeviation = calculateStandardDeviation(dataPoints);

// 公认通用缩写 —— 允许
int rowIdx = findInsertionIndex(value);
QString prevValue = history.previousEntry();
void initConnection();

// 循环计数器 —— 允许
for (int i = 0; i < count; ++i) { /* ... */ }

// 控件前缀 —— 允许（遵循 Qt 控件命名规范）QLabel *m_lblStatus;
QPushButton *m_btnSubmit;
```

## 错误示例

```cpp
// 错误：使用自定义缩写
int maxH = computeMaxH();            // 应改为 maximumHeight
QString errMsg = genErrMsg();        // 应改为 errorMessage、generateErrorMessage()
double stdDev = calcStdDev(data);    // 应改为 standardDeviation

// 错误：省略元音字母的缩写风格
int rcvdCnt = 0;                     // 应改为 receivedCount
QString usrNm;                       // 应改为 userName
void procEvt();                      // 应改为 processEvent

// 错误：拼音缩写或中英混合缩写
int zjCount = 0;                     // 应改为 rejectCount 或使用完整语义QString sfzhm;                       // 应改为 idCardNumber
```

## 检查方法
1. 使用 LLM 分析标识符中的缩写模式。2. 对照已知缩写字典（如 `addr`→`address`、`cfg`→`config`、`msg`→`message`）检测。3. 排除白名单（公认缩写、Qt 控件前缀、循环变量）。4. 标记可能为自定义缩写且非白名单的标识符。5. 输出建议的完整拼写。
## 修复指南

1. 将缩写的标识符替换为完整单词。2. 如缩写过长导致行超宽，考虑调整断行（参考 [[qt-line-width]]）。3. 批量重命名时使用 IDE 的重构工具（Qt Creator: `Ctrl+Shift+R`）。4. 示例修复：   ```cpp
   // 修改前：   int calcAvgTmp(const QList<int> &vals) { /* ... */ }
   // 修改后：   int calculateAverageTemperature(const QList<int> &values) { /* ... */ }
   ```

## 审查清单

- [ ] 所有新定义的变量名和函数名不使用自定义缩写
- [ ] 公认缩写（如 `idx`、`prev`、`init`）一致性使用 - [ ] 无拼音缩写或中英混合缩写
- [ ] 无省略元音字母的人造缩写
## 关联页面

- [[qt-variable-camelcase]] —— 变量名采用驼峰命名法
- [[qt-no-short-names]] —— 避免使用短变量名
