---
domain: qt
rule_id: qt-cpp-function-order
title: .cpp 中函数定义顺序与 .h 声明顺序一致
priority: main
source_file: rules/QT代码开发规则.md
source_section: "§4.2 代码顺序规范"
status: active
check_method: none
deterministic_check: false
checkability: advisory_only
conflicts_with: []
overrides: []
related_pages:
  - [[qt-member-declaration-order]]
  - [[qt-include-order]]
---

# .cpp 中函数定义顺序与 .h 声明顺序一致
## 规则条款

实现文件（`.cpp`）中的函数定义顺序，建议与头文件（`.h`）中的声明顺序保持一致。此规则为建议性质（advisory），目的是提高代码可读性和可维护性，方便在 .cpp 中快速定位函数实现。
## 正确示例

```cpp
// ===== inswidget.h =====
class InsWidget : public QWidget
{
    Q_OBJECT

public:
    explicit InsWidget(QWidget *parent = nullptr);
    ~InsWidget() override;

    void setTitle(const QString &title);
    QString title() const;
    void refreshData();

protected:
    void paintEvent(QPaintEvent *event) override;

signals:
    void titleChanged(const QString &newTitle);

private slots:
    void onDataReady();

private:
    void setupUI();
    void setupConnections();

    QLabel *m_lblTitle;
    QString m_strTitle;
};

// ===== inswidget.cpp =====
// 函数定义顺序与 .h 声明顺序一致
// --- public ---

InsWidget::InsWidget(QWidget *parent)
    : QWidget(parent)
{
    setupUI();
    setupConnections();
}

InsWidget::~InsWidget() = default;

void InsWidget::setTitle(const QString &title)
{
    if (m_strTitle != title) {
        m_strTitle = title;
        m_lblTitle->setText(title);
        emit titleChanged(title);
    }
}

QString InsWidget::title() const
{
    return m_strTitle;
}

void InsWidget::refreshData()
{
    // 刷新逻辑
}

// --- protected ---

void InsWidget::paintEvent(QPaintEvent *event)
{
    QWidget::paintEvent(event);
    // 自定义绘制
}

// --- private slots ---

void InsWidget::onDataReady()
{
    refreshData();
}

// --- private ---

void InsWidget::setupUI()
{
    m_lblTitle = new QLabel(this);
    // UI 初始化
}

void InsWidget::setupConnections()
{
    // 信号连接
}
```

## 错误示例

```cpp
// ===== inswidget.cpp：函数定义顺序混乱 =====

// 错误：private 函数出现在 public 函数之前
void InsWidget::setupUI()
{
    // ...
}

// 错误：public 函数混在中间
InsWidget::InsWidget(QWidget *parent)
    : QWidget(parent)
{
}

// 错误：又回到 private 函数
void InsWidget::setupConnections()
{
}

// 错误：public 函数散落各处
void InsWidget::setTitle(const QString &title)
{
}

// 错误：槽函数出现在构造函数之前
void InsWidget::onDataReady()
{
}

// 顺序混乱导致：
// 1. 难以在 .cpp 中找到特定函数的实现
// 2. 代码审查时需反复跳转对比 .h 和 .cpp
// 3. 新增函数时容易随意插入，进一步加剧混乱
```

```cpp
// 另一个反例：无任何组织结构
// Widget.cpp
void Widget::methodZ() { }   // 应先声明 methodA
void Widget::methodA() { }
void Widget::methodM() { }
void Widget::methodB() { }
// 完全无序，无法与 .h 对应
```

## 检查方法
1. 从头文件中提取所有成员函数声明，记录顺序和所在访问块。2. 从实现文件中提取所有成员函数定义，记录出现顺序。3. 比较两者的顺序：   - 首先检查访问块的顺序是否一致（public → protected → private）。   - 然后检查组内函数顺序是否一致。4. 报告顺序不一致的函数（偏移超过一定阈值）。
自动化工具辅助：
- 可用脚本提取 .h 声明和 .cpp 定义的函数名列表，计算顺序相似度。- IDE 插件（如 Qt Creator 的 "Go to Definition"）可辅助手动验证。
由于此规则为 advisory_only，检测结果作为建议而非阻断项。
## 修复指南

1. 打开对应的头文件，记录函数声明的顺序。2. 在 .cpp 中按相同顺序重新排列函数定义。3. 保持访问级别分组的顺序（public → protected → private）。4. 在每个访问组内的子顺序：
   - 构造/析构 → 普通函数 → 信号（不可定义）→ 槽 → 成员变量初始化（如有）。5. 如果文件很大，可以使用 IDE 的代码折叠功能，逐块调整。6. 调整完成后编译确认无语法错误。
## 审查清单

- [ ] .cpp 中函数定义的访问块顺序与 .h 一致
- [ ] 同一访问块内函数定义的相对顺序与 .h 一致
- [ ] 新增函数时按正确位置插入，而非追加到文件末尾
- [ ] 重构过的方法在 .cpp 中的位置也同步调整
## 关联页面

- [[qt-member-declaration-order]]：类成员声明顺序
- [[qt-include-order]]：头文件包含顺序