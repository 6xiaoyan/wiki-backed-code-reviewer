---
domain: qt
rule_id: qt-method-verb-phrase
title: 普通方法名必须为动词或动宾短语
priority: main
source_file: rules/QT代码开发规则.md
source_section: "§3.3 方法命名"
status: active
check_method: llm
deterministic_check: false
checkability: llm_checkable
conflicts_with: []
overrides: []
related_pages:
  - [[qt-getter-no-get]]
  - [[qt-method-no-classname]]
---

# 普通方法名必须为动词或动宾短语

## 规则条款

普通方法（成员函数）名必须为动词或动宾短语，体现动作含义。方法名应清楚表达该方法执行什么操作。
## 正确示例

```cpp
class DataManager : public QObject
{
public:
    // 动词：单一动作
    void save();
    void load();
    void reset();
    void refresh();
    void validate();

    // 动宾短语：动词+ 宾语
    void importFile(const QString &path);
    void updateRecord(int id);
    void sendNotification(const QString &msg);
    void parseXmlData(const QByteArray &data);
    void clearCache();
    void reloadConfiguration();

    // 状态变更    void enableFeature(FeatureId id);
    void disableLogging();
};
```

## 错误示例

```cpp
class DataManager : public QObject
{
public:
    // 错误：名为名词短语，不体现动作
    void fileImporter(const QString &path);    // 应为 importFile()
    void dataValidator(const QByteArray &d);   // 应为 validateData()
    void notification(const QString &msg);     // 应为 sendNotification()

    // 错误：形容词，不体现动作
    void visible(bool on);                     // 应为 setVisible(bool on)
    void enabled(FeatureId id);                // 应为 enableFeature(FeatureId id)

    // 错误：语义不明，看不出做什么    void process();                            // process 什么？
    void handle();                             // handle 什么？
    void execute();                            // execute 什么？

    // 错误：与"获取属性"混淆的名词方法（非getter 场景）    void configuration();                      // 应为 loadConfiguration() 或initConfiguration()

    // 正确写法（对比）
    // void importFile(const QString &path);  // 动宾短语
    // void validateData(const QByteArray &d); // 动宾短语
    // void sendNotification(const QString &msg); // 动宾短语
    // void setVisible(bool on); // set + 属性};
```

## 检查方法
此规则依赖LLM 语义分析。
1. 提取类中所有public/protected 成员函数声明。2. 过滤掉以下不适用此规则的函数：   - 构造函数和析构函数
   - 属性getter（遵循Q-29b 规则）   - 属性setter（`setXxx` 形式）   - 信号函数（遵循Q-31 规则）   - 槽函数（遵循 Q-32 规则）   - 运算符重载   - 事件处理函数（`*Event` 形式）。3. 对剩余普通方法名，由 LLM 判断：   - 是否为动词（如`save`、`load`、`reset`）   - 是否为动宾短语（如`importFile`、`updateRecord`）   - 是否清晰表达操作方法执行的操作。4. 标记纯名词或语义不明的方法名。
## 修复指南

1. 纯名词方法名改为动宾短语：   - `fileImporter()` → `importFile()`
   - `dataValidator()` → `validateData()`
2. 语义不明的方法名添加宾语使其具体：   - `process()` → `processQueue()` 或`processRequest()`
   - `handle()` → `handleEvent()` 或`handleError()`
3. 若方法名与已有getter 混淆，按 Q-29b 规则归类处理。4. 更新所有调用处的函数名。
## 审查清单

- [ ] 普通方法名为动词或动宾短语
- [ ] 方法名能清晰表达操作内容
- [ ] 无不含宾语的模糊动词（如单独的process/handle/execute）- [ ] 方法名与实际行为一致（不产生误导）

## 关联页面

- [[qt-getter-no-get]]：getter 不加 get 前缀
- [[qt-method-no-classname]]：方法名禁止包含当前类名- [[qt-signal-no-signal-word]]：信号名不含signal
- [[qt-slot-no-slot-word]]：槽名不加 slot
