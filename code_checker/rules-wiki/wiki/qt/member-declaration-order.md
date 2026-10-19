---
domain: qt
rule_id: qt-member-declaration-order
title: 类成员声明顺序规则
priority: main
source_file: rules/QT代码开发规则.md
source_section: "§4.2 代码顺序规范"
status: active
check_method: regex
deterministic_check: true
checkability: deterministic
conflicts_with: []
overrides: []
related_pages:
  - [[qt-include-order]]
  - [[qt-cpp-function-order]]
---

# 类成员声明顺序规则
## 规则条款

Qt 类成员声明按访问权限分组：`public` -> `protected` -> `private`。每组内部按以下子顺序排列：

1. 构造函数/ 析构函数
2. 普通成员函数3. 信号（`signals:`）4. 槽函数（`slots:`）5. 成员变量

信号和槽使用 Qt 的`signals:` 和`slots:` 访问说明符，它们有其固定的位置。
## 正确示例

```cpp
class MainWindow : public QMainWindow
{
    Q_OBJECT

// ===== public =====
public:
    // 1. 构造/ 析构
    explicit MainWindow(QWidget *parent = nullptr);
    ~MainWindow() override;

    // 2. 普通函数    void loadSettings();
    QString currentFileName() const;
    bool isModified() const;

// ===== protected =====
protected:
    // 2. 普通函数（事件处理）    void closeEvent(QCloseEvent *event) override;
    void resizeEvent(QResizeEvent *event) override;

// ===== signals =====
signals:
    // 3. 信号
    void fileOpened(const QString &path);
    void documentModified(bool modified);

// ===== protected slots =====
protected slots:
    // 4. 槽函数    void onDocumentChanged();

// ===== private slots =====
private slots:
    // 4. 槽函数    void on_btnOpen_clicked();
    void on_btnSave_clicked();
    void on_edtSearch_textChanged(const QString &text);

// ===== private =====
private:
    // 2. 普通函数    void setupUI();
    void setupConnections();
    bool saveDocument(const QString &path);

    // 5. 成员变量
    QPushButton *m_btnOpen;
    QPushButton *m_btnSave;
    QLineEdit *m_edtSearch;
    QTabWidget *m_tabMain;
    QString m_currentFilePath;
    bool m_bModified;
};
```

## 错误示例

```cpp
// 错误：成员声明顺序混乱class MainWindow : public QMainWindow
{
    Q_OBJECT

public:
    QString currentFileName() const;     // 普通函数    QPushButton *m_btnSave;              // 错误：成员变量不该在 public

    explicit MainWindow(QWidget *parent = nullptr); // 构造函数    // 构造函数应在public 区域最前
private:
    void setupUI();                      // OK

public:                                  // 错误：重复的 public 块    void loadSettings();

signals:
    void fileOpened(const QString &path);

private:
    QLineEdit *m_edtSearch;

public slots:                            // 错误：public slots 在signals 之前声明
    void refreshView();

signals:                                 // 错误：重复的 signals 块    void documentSaved();
};
```

```cpp
// 另一个反例：成员变量散布在各处class BadExample : public QObject
{
    Q_OBJECT

public:
    explicit BadExample(QObject *parent = nullptr);

private:
    int m_count;                         // 成员变量

public slots:
    void process();

private:
    QString m_name;                      // 成员变量又出现了

signals:
    void finished();

private:
    QTimer *m_timer;                     // 成员变量再次出现…混乱};
```

## 检查方法
使用正则表达式和结构分析：
1. 提取类的完整声明（从 `class` 到`};`）。2. 识别所有访问说明符及其顺序：   - 标准：`public:`、`protected:`、`private:`
   - Qt 专用：`signals:`、`public slots:`、`protected slots:`、`private slots:`
3. 检查访问分组顺序是否遵循：public → protected（含 protected slots）→ signals → private slots → private。4. 在每个访问分组内检查子顺序：   - 构造析构是否在最前   - 成员变量是否在最后   - 信号是否在`signals:` 中   - 槽是否在相应 `slots:` 中。5. 检查是否存在同一访问级别的重复块（如两个 `private:` 块）。
Qt 推荐的完整顺序参考：

```
public:
    构造析构
    普通函数signals:
    信号
protected:
    构造析构（如有）
    普通函数protected slots:
    槽函数private slots:
    槽函数private:
    普通函数    成员变量
```

## 修复指南

1. 合并同一访问级别的重复块。2. 按规范顺序重排各访问块。3. 在每个块内按子顺序排列成员。4. 检查Q_OBJECT 宏的存在和位置（紧跟 `class` 行之后）。5. 使用 IDE 的重构工具或 `clang-format` 辅助格式化。
## 审查清单

- [ ] 访问块顺序：public → signals → protected → protected slots → private slots → private
- [ ] 构造析构函数在所在访问块的最前面
- [ ] 成员变量在所在访问块的最后面
- [ ] 信号统一在`signals:` 块中，不散布
- [ ] 槽函数统一在对应的 `*slots:` 块中
- [ ] 无同一访问级别的重复块

## 关联页面

- [[qt-include-order]]：头文件包含顺序- [[qt-cpp-function-order]]：.cpp 函数顺序与.h 一致