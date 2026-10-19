---
domain: qt
rule_id: qt-on-obj-slot-internal
title: on_obj_signal 格式槽函数仅作内部实现
priority: main
source_file: rules/QT代码开发规范.md
source_section: "§3.3 方法命名"
status: active
check_method: llm
deterministic_check: false
checkability: llm_checkable
conflicts_with: []
overrides: []
related_pages:
  - [[qt-signal-no-signal-word]]
  - [[qt-slot-no-slot-word]]
---

# on_obj_signal 格式槽函数仅作内部实现
## 规则条款

`on_<对象名>_<信号名()` 格式的槽函数（Qt 自动关联格式）仅用作内部实现，不对外暴露。不应在 `public slots:` 中声明此类槽函数，也不应手动调用它们。
## 正确示例

```cpp
class MainWindow : public QMainWindow
{
    Q_OBJECT

public:
    explicit MainWindow(QWidget *parent = nullptr);

public slots:
    // 对外暴露的槽：动宾短语，清晰表达操作
    void openRecentFile(const QString &path);
    void refreshDocumentList();

private slots:
    // on_obj_signal 格式：仅 private slots，仅由 Qt 自动关联
    // 由 uic 生成的 connect() 或命名约定自动连接    void on_btnSave_clicked();
    void on_edtSearch_textChanged(const QString &text);
    void on_cmbType_currentIndexChanged(int index);
    void on_chbEnable_toggled(bool checked);
    void on_tblUsers_cellClicked(int row, int column);

private:
    QPushButton *m_btnSave;
    QLineEdit *m_edtSearch;
    QComboBox *m_cmbType;
    QCheckBox *m_chbEnable;
    QTableWidget *m_tblUsers;
};
```

## 错误示例

```cpp
class MainWindow : public QMainWindow
{
    Q_OBJECT

public slots:
    // 错误：on_obj_signal 格式暴露在 public slots 中    void on_btnSave_clicked();            // 应为 private slots

    // 错误：手动调用 on_obj_signal 格式的槽
    void triggerSave()
    {
        on_btnSave_clicked();             // 错误！不应手动调用        // 应调用独立的 saveData() 函数
    }

private slots:
    // 同样是 on_obj_signal，但无对应的 UI 控件（命名不匹配）    // 这个槽永远不会被 Qt 自动关联
    void on_nonexistent_clicked();        // 可能写错
    // 错误：on_obj_signal 槽内包含业务逻辑，无法复用    void on_btnSave_clicked()
    {
        // 100 行保存逻辑全写在这里。        // 本应抽取为 saveDocument() 供多处复用    }
};
```

```cpp
// 正确做法：分离自动关联槽和业务逻辑
class MainWindow : public QMainWindow
{
    Q_OBJECT

public slots:
    void saveDocument();                  // 对外暴露的业务槽

private slots:
    void on_btnSave_clicked()             // 仅作桥接
    {
        saveDocument();                   // 委托给业务槽
    }

    void on_edtSearch_textChanged(const QString &text)
    {
        performSearch(text);              // 委托给业务函数    }

private:
    void performSearch(const QString &text);
};
```

## 检查方法
此规则依赖 LLM 语义分析和代码结构分析：

1. 提取所有 `on_<obj>_<signal>()` 格式的槽函数声明。2. 检查其访问级别：   - 如果在 `public slots:` 或 `protected slots:` 中，标记为违规。   - 正确的访问级别是 `private slots:`。3. 检查是否有代码手动调用这些槽函数（非信号触发）：   - 搜索 `on_btnXxx_xxx(` 的显式调用。   - 如果有，标记为违规——应抽取独立的业务函数。4. 检查 `on_obj_signal` 槽中是否包含了大量业务逻辑：   - 如果函数体超过 10 行且包含非 UI 操作的业务代码，建议重构抽取。
## 修复指南

1. 将 `on_obj_signal` 槽从 `public slots:` 或 `protected slots:` 移至 `private slots:`。2. 如果外部需要调用相同功能，抽取独立的 public 函数：   - `on_btnSave_clicked()` 委托给 `saveDocument()`
   - `on_edtSearch_textChanged()` 委托给 `performSearch(const QString &)`
3. 移除所有手动调用 `on_obj_signal` 的代码，改为调用抽取后的业务函数。4. 确保 `on_obj_signal` 的控件名和信号名与实际 UI 控件匹配，否则 Qt 无法自动关联。
## 审查清单

- [ ] `on_obj_signal` 格式槽仅在 `private slots:` 中声明- [ ] 无手动调用 `on_obj_signal` 格式槽的代码
- [ ] `on_obj_signal` 槽函数体简短（仅作桥接委托）- [ ] 实际的业务逻辑已抽取到独立函数中- [ ] `on_obj_signal` 中的对象名和信号名与实际控件匹配

## 关联页面

- [[qt-signal-no-signal-word]] —— 信号名禁止包含 signal 标识
- [[qt-slot-no-slot-word]] —— 槽函数名禁止包含 slot 标识
