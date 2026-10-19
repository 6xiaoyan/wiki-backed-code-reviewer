---
domain: qt
rule_id: qt-line-break-style
title: 断行规则：逗号置行尾，操作符置下行开头
priority: main
source_file: rules/QT代码开发规则.md
source_section: "§2.7"
status: active
check_method: regex
deterministic_check: true
checkability: deterministic
conflicts_with: []
overrides: []
related_pages:
  - [[qt-line-width]]
---

# 断行规则：逗号置行尾，操作符置下行开头
## 规则条款

当代码行过长需要断行时，遵循以下断行风格：
- **逗号放在行尾**：参数列表中，逗号紧跟前一个参数，不放在下一行开头。- **操作符放在下一行开头**：续行中的二元操作符（`&&`、`||`、`+` 等）放在新行的行首而非行尾。- 续行缩进一级（4 个空格）或对齐到上一行的对应位置。
这样做的原因：- 逗号在行尾：与自然语言书写习惯一致- 操作符在行首：视觉上容易扫描所有续行的操作符，快速理解表达式逻辑

## 正确示例

```cpp
// 参数列表断行 — 逗号在行尾void processData(
        const QString &name,
        int count,
        double factor,
        QWidget *parent)
{
    // ...
}

// 初始化列表断行— 逗号在行尾MainWindow::MainWindow(QWidget *parent)
    : QMainWindow(parent)
    , m_centralWidget(new QWidget(this))
    , m_layout(new QVBoxLayout)
    , m_statusLabel(new QLabel(this))
{
    // ...
}

// 条件表达式断行— 操作符在行首
if (m_connectionState == QAbstractSocket::ConnectedState
    && m_dataReady
    && !m_isPaused) {
    startProcessing();
}

// 长表达式断行 — 操作符在行首
int total = baseValue
            + adjustmentValue
            + correctionFactor * multiplier
            - penaltyAmount;
```

## 错误示例

```cpp
// 错误：逗号放在行首
void processData(
        const QString &name
        , int count          // 错误：逗号在行首        , double factor      // 错误：逗号在行首        , QWidget *parent)
{
    // ...
}

// 错误：操作符放在行尾
if (m_connectionState == QAbstractSocket::ConnectedState &&
    m_dataReady &&           // 错误：&& 在行尾    !m_isPaused) {
    startProcessing();
}

// 错误：初始化列表逗号在行尾（而非 Qt 风格的行首）
MainWindow::MainWindow(QWidget *parent) :
    QMainWindow(parent),     // 错误：冒号在行尾，逗号也在行尾
    m_centralWidget(new QWidget(this)),
{
    // Qt 风格要求初始化列表逗号在行首}
```

## 检查方法
1. **逗号位置检查**：   - 搜索行首为逗号（`, `开头）的模式 — 违规
   - 正则表达式：`^\s*,` 匹配行首逗号

2. **操作符位置检查**：   - 搜索行尾为二元操作符（`&&`、`||`、`+` 等结尾）的模式 — 违规
   - 正则表达式：`[&&|\|]{2}\s*$` 或`[+\-*/%]\s*$` 匹配行尾操作符
3. **初始化列表检查**：   - Qt 风格：冒号在行尾（构造声明行），逗号在成员初始化项的**下一行行首*
   - 检查成员初始化列表的`,` 是否在每行的开头
## 修复指南

1. **逗号**：将行首的`, ` 移动到上一行末尾。2. **操作符**：将行尾的`&&` 等移动到下一行开头。3. **初始化列表**（Qt 风格）：
   ```cpp
   // 修改为标准Qt 风格
   ClassName::ClassName(QWidget *parent)
       : QMainWindow(parent)
       , m_member1(value1)
       , m_member2(value2)
   ```

## 审查清单

- [ ] 所有参数列表中的逗号在上一行末尾- [ ] 所有续行的操作符在行首
- [ ] 初始化列表的逗号在每行开头（Qt 风格）- [ ] 续行缩进一致
## 关联页面

- [[qt-line-width]]：每行代码不超过120 字符
