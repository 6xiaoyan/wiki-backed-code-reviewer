---
domain: qt
rule_id: qt-braces-function-class
title: 函数定义与类定义的左大括号单独占一行（Allman 例外）
priority: main
source_file: rules/QT代码开发规则.md
source_section: "§2.4"
status: active
check_method: regex
deterministic_check: true
checkability: deterministic
conflicts_with: []
overrides: []
related_pages:
  - [[qt-braces-knr]]
---

# 函数定义与类定义的左大括号单独占一行（Allman 例外）
## 规则条款

在Qt 代码风格中，**函数定义**（包括普通函数、成员函数、构造函数、析构函数）和*类定义*（`class`/`struct`）的**左大括号 `{` 必须单独占一行**，即使用 Allman 风格。这与控制流语句的K&R 风格（[[qt-braces-knr]]）形成互补。原因：
- 函数开头的初始化列表（`:` 后跟成员初始值）需要清晰可读- 函数签名可能较长，`{` 单独一行使签名与实现体分离
- 这是 Qt 源码的一致约定
## 正确示例

```cpp
// 类定义——{ 单独一行class MainWindow : public QMainWindow
{
    Q_OBJECT

public:
    explicit MainWindow(QWidget *parent = nullptr);
    ~MainWindow();

protected:
    void closeEvent(QCloseEvent *event) override;

private:
    QLabel *m_lblTitle;
};

// 函数定义 ——{ 单独一行MainWindow::MainWindow(QWidget *parent)
    : QMainWindow(parent)
    , m_lblTitle(new QLabel(this))
{
    setWindowTitle("My Application");
    m_lblTitle->setText("Welcome");
}

// 普通函数 ——{ 单独一行void processData(const QList<int> &values)
{
    for (int i = 0; i < values.size(); ++i) {
        handleValue(values[i]);
    }
}

// 简短内联函数 ——也可以放在一行int value() const { return m_value; }
```

## 错误示例

```cpp
// 错误：类定义使用 K&R 风格
class MainWindow : public QMainWindow {
    Q_OBJECT
    // ...
};

// 错误：函数定义使用K&R 风格
void processData(const QList<int> &values) {
    for (int i = 0; i < values.size(); ++i) {
        handleValue(values[i]);
    }
}

// 错误：带初始化列表的函数 { 没有单独一行MainWindow::MainWindow(QWidget *parent)
    : QMainWindow(parent)  {
    setWindowTitle("My Application");
}
```

## 检查方法
1. 识别函数定义（非声明）和类结构体定义的头部行。2. 检测头部行是否以`{` 结尾（K&R 风格，应改Allman）。3. 排除短小的内联函数（允许在单行中：`int value() const { return m_value; }`）。
正则表达式：`^\s*(?:class|struct)\s+\w+.*\{`：类定义的 `{` 在同一行（违规）。正则表达式：函数定义：`\)\s*(?:const|override|noexcept|final)*\s*\{`：`{` 与函数签名同行（违规，但排除内联单行函数）。
## 修复指南

1. 将类定义和函数定义末尾的 `{` 移动到下一行，与`class`/返回类型对齐或缩进。2. 类定义中 `{` 与`class` 关键字对齐（无缩进）。3. 函数定义中`{` 与函数返回类型对齐（无缩进）。4. clang-format 配置：`BreakBeforeBraces: Custom` + `BraceWrapping: { AfterClass: true, AfterFunction: true, AfterControlStatement: Never }`。
## 审查清单

- [ ] 所有`class`/`struct` 定义中`{` 在单独一行- [ ] 所有函数定义（含析、构造）中`{` 在单独一行- [ ] 初始化列表的 `:` 在函数参数后，`{` 在初始化列表下方的独立行
- [ ] 简单的内联函数可以在一行中：`int x() const { return m_x; }`

## 关联页面

- [[qt-braces-knr]]：控制流左大括号与语句同行（K&R 风格）