---
domain: qt
rule_id: qt-signal-no-signal-word
title: 信号名禁止包含 signal 标识
priority: main
source_file: rules/QT代码开发规范.md
source_section: "§3.3 方法命名"
status: active
check_method: regex
deterministic_check: true
checkability: deterministic
conflicts_with: []
overrides: []
related_pages:
  - [[qt-slot-no-slot-word]]
  - [[qt-on-obj-slot-internal]]
  - [[qt-method-verb-phrase]]
---

# 信号名禁止包含 signal 标识

## 规则条款

禁止在信号名中添加 `signal` 标识。信号名应体现类的状态变化，使用动词短语的完成时或状态变化描述。

## 正确示例

```cpp
class DataLoader : public QObject
{
    Q_OBJECT

signals:
    // 动词完成时或状态变化通知
    void dataReady();
    void dataReady(const QByteArray &data);

    // 状态变化描述
    void loadingStarted();
    void loadingFinished();
    void loadingProgress(int percent);

    // Qt 风格：xxxChanged() 信号带参数
    void nameChanged(const QString &newName);
    void statusChanged(int newStatus);
    void windowIconChanged(const QIcon &icon);
    void windowTitleChanged(const QString &title);

    // 用户操作通知
    void itemSelected(int index);
    void itemDoubleClicked(int index);
    void buttonClicked();

    // 错误/事件通知
    void errorOccurred(const QString &message);
    void connectionLost();
    void connectionRestored();
};
```

## 错误示例

```cpp
class DataLoader : public QObject
{
    Q_OBJECT

signals:
    // 错误：信号名包含 "signal"
    void dataReadySignal();                   // 应为 dataReady()
    void dataReadySignal(const QByteArray &); // 应为 dataReady(const QByteArray &)

    // 错误：信号名包含 "signal" 片段
    void loadingStartedSignal();              // 应为 loadingStarted()
    void nameChangedSignal(const QString &);  // 应为 nameChanged(const QString &)

    // 错误：包含 "sig" 缩写也是禁止的
    void sigDataReady();                      // 应为 dataReady()
    void sigError(const QString &msg);        // 应为 errorOccurred(const QString &msg)

    // 错误：信号名使用名词而非状态变化
    void data();                              // 应为 dataReady() 或 dataChanged()
    void error(const QString &msg);           // 应为 errorOccurred(const QString &msg)
};
```

## 检查方法
使用正则表达式检测：

1. 定位 `signals:` 访问说明符下的所有函数声明。
2. 检查信号名是否包含以下模式（大小写不敏感）：
   - 包含 `signal` 单词：`\w*signal\w*`（如 `Signal`、`signal`、`_signal`）
   - 包含 `sig` 缩写：`\bsig[A-Z]`（如 `sigDataReady`）
3. 匹配到的信号标记为违规。
4. 额外检查：信号名是否为名词形式（非状态变化）——这需要 LLM 辅助判断。

## 修复指南

1. 去掉信号名中的 `Signal`/`signal`/`Sig`。
   - `dataReadySignal()` → `dataReady()`
   - `sigDataReady()` → `dataReady()`
2. 以 `sig` 开头的重命名为状态变化的描述。
   - `sigError()` → `errorOccurred()`
   - `sigUpdate()` → `updated()`
3. 确保信号名表达了"发生了什么变化"。
   - 数据就绪 → `dataReady()`
   - 加载完成 → `loadingFinished()`
   - 值改变 → `valueChanged(int)`
4. 更新所有 `connect()` 调用中的信号引用。

## 审查清单

- [ ] 信号名不包含 `signal` 字面
- [ ] 信号名不包含 `sig` 缩写
- [ ] 信号名表达了类的状态变化
- [ ] 所有 `connect()` 和 `SIGNAL()` 宏已同步更新

## 关联页面

- [[qt-slot-no-slot-word]]：槽函数名禁止包含 slot 标识
- [[qt-on-obj-slot-internal]]：on_obj_signal 格式仅作内部实现
- [[qt-method-verb-phrase]]：普通方法名需为动词或动宾短语
