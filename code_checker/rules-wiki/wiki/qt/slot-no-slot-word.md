---
domain: qt
rule_id: qt-slot-no-slot-word
title: 槽函数名禁止包含 slot 标识
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
  - [[qt-signal-no-signal-word]]
  - [[qt-on-obj-slot-internal]]
  - [[qt-method-verb-phrase]]
---

# 槽函数名禁止包含 slot 标识

## 规则条款

禁止在槽函数名中添加 `slot` 标识。槽函数名应体现具体操作，使用动宾短语。

## 正确示例

```cpp
class MainWindow : public QMainWindow
{
    Q_OBJECT

public slots:
    // 动宾短语，体现具体操作
    void openFile();
    void saveDocument();
    void printPreview();
    void toggleFullScreen();
    void copySelection();
    void pasteContent();

    // Qt 标准方法
    void show();
    void hide();
    void setEnabled(bool enabled);
    void setVisible(bool visible);

    // 数据处理
    void refreshData();
    void clearLogs();
    void exportReport();
    void validateForm();

protected slots:
    void onTimeout();
    void onConnectionError(const QString &msg);

private slots:
    void onButtonClicked();
    void onItemSelected(int index);
    void onTextChanged(const QString &text);
};
```

## 错误示例

```cpp
class MainWindow : public QMainWindow
{
    Q_OBJECT

public slots:
    // 错误：槽名包含 "slot"
    void slotOpenFile();                      // 应为 openFile()
    void slotSave();                          // 应为 saveDocument()
    void fileOpenSlot();                      // 应为 openFile()
    void saveSlot();                          // 应为 saveDocument()

    // 错误：包含 "sl" 缩写暗示 slot
    void slOpenFile();                        // 应为 openFile()
    void slSave();                            // 应为 saveDocument()

    // 错误：前缀 "on" 但不是 Qt 自动关联格式 (on_obj_signal)
    // 这种前缀虽合法但应当保持一致。
    void onFileOpen();                        // 如果是手动 connect，建议用 openFile()
};
```

```cpp
// 错误对比
class DataProcessor : public QObject
{
    Q_OBJECT
public slots:
    void slotProcessData();    // 错误 → 应为 processData()
    void slotExportCsv();      // 错误 → 应为 exportCsv()
    void slotReset();          // 错误 → 应为 reset()
};

// 正确写法
class DataProcessor : public QObject
{
    Q_OBJECT
public slots:
    void processData();        // 正确
    void exportCsv();          // 正确
    void reset();              // 正确
};
```

## 检查方法
使用正则表达式检测：

1. 定位 `slots:` 访问说明符（`public slots:`、`protected slots:`、`private slots:`）下的所有函数声明。
2. 检查函数名是否包含以下模式（大小写不敏感）：
   - 包含 `slot` 单词：`\w*slot\w*`（如 `slotOpen`、`fileOpenSlot`）
   - 包含 `sl` 缩写前缀：`\bsl[A-Z]`（如 `slOpenFile`）
3. 所有匹配到的槽函数标记为违规。
4. 注意：`on_<obj>_<signal>()` 格式是 Qt 自动关联的特殊槽（由 uic 自动连接），不受此规则约束。

## 修复指南

1. 去掉槽名中的 `slot`/`Slot`/`sl` 标识。
   - `slotOpenFile()` → `openFile()`
   - `slotSave()` → `save()`
   - `fileOpenSlot()` → `openFile()`
   - `slOpenFile()` → `openFile()`
2. 确保去掉后方法名仍是动词或动宾短语（遵循 Q-29a 规则）。
3. 更新所有 `connect()` 调用中的槽引用。
4. 更新 `SLOT()` 宏调用（如果使用旧式连接）。

## 审查清单

- [ ] 槽函数名不包含 `slot` 字面
- [ ] 槽函数名不包含 `sl` 缩写前缀
- [ ] 槽函数名为动词或动宾短语
- [ ] 所有 `connect()` 和 `SLOT()` 宏已同步更新

## 关联页面

- [[qt-signal-no-signal-word]]：信号名禁止包含 signal 标识
- [[qt-on-obj-slot-internal]]：on_obj_signal 格式仅作内部实现
- [[qt-method-verb-phrase]]：普通方法名需为动词或动宾短语
