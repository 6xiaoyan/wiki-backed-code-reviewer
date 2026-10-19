---
domain: qt
rule_id: qt-parent-child-memory
title: Qt 父类管理子类内存
priority: main
source_file: rules/QT代码开发规范.md
source_section: "§4.4 内存管理"
status: active
check_method: llm
deterministic_check: false
checkability: llm_checkable
related_pages:
  - [[qt-who-new-who-delete]]
  - [[qt-no-boost-smart-ptr]]
---

# Qt 父类管理子类内存

## 规则条款

Qt 对象内存管理应优先通过"父类管理子类"机制实现。在创建 Qt 对象时传入父对象指针（通常为 `this`），父对象析构时会自动递归销毁其所有子对象，从而避免内存泄漏。
这是 Qt 对象模型的核心特性：`QObject` 及其子类通过父子关系树自动管理子对象生命周期。只要父对象被正确销毁，其管理的子对象就不需要手动 `delete`。
## 正确示例

```cpp
class MyWidget : public QWidget
{
    Q_OBJECT

public:
    MyWidget(QWidget *parent = nullptr) : QWidget(parent)
    {
        // 正确：传入 this 作为父对象，MyWidget 析构时自动销毁这些控件        QLabel *nameLabel = new QLabel(tr("Name:"), this);
        QLineEdit *nameEdit = new QLineEdit(this);
        QPushButton *submitBtn = new QPushButton(tr("Submit"), this);

        // 布局也会自动管理——布局中的控件由父控件管理
        QVBoxLayout *layout = new QVBoxLayout(this);
        layout->addWidget(nameLabel);
        layout->addWidget(nameEdit);
        layout->addWidget(submitBtn);
    }
    // 无需手动 delete nameLabel、nameEdit、submitBtn
};

// 对话框示例void showSettingsDialog()
{
    // 正确：dialog 在栈上，其所有子控件自动管理
    QDialog dialog;
    QLabel *label = new QLabel(tr("Server:"), &dialog);
    QLineEdit *edit = new QLineEdit(&dialog);
    QPushButton *okBtn = new QPushButton(tr("OK"), &dialog);
    // dialog 出作用域时自动销毁 label、edit、okBtn
    dialog.exec();
}

// 模型/视图示例
void setupTableView(QTableView *view)
{
    // 正确：model 的父对象为 view
    QStandardItemModel *model = new QStandardItemModel(view);
    view->setModel(model);
    // view 析构时自动销毁 model
}
```

## 错误示例

```cpp
class MyWidget : public QWidget
{
public:
    MyWidget(QWidget *parent = nullptr) : QWidget(parent)
    {
        // 错误：未指定父对象，这些控件无人管理
        QLabel *nameLabel = new QLabel(tr("Name:"));
        QLineEdit *nameEdit = new QLineEdit();
        QPushButton *submitBtn = new QPushButton(tr("Submit"));
        // 这些对象永远泄漏——除非 MyWidget 析构函数中手动 delete

        // 错误：虽然设置了布局但控件无父对象        QVBoxLayout *layout = new QVBoxLayout(this);
        // 以下控件不会自动进入父子树——addWidget 本身不改变父对象。        // 需要使用 QWidget::setParent() 或构造时传入父对象        QLabel *orphanLabel = new QLabel(tr("Orphan"));
        layout->addWidget(orphanLabel);  // addWidget 内部会调用 setParent！这种写法其实 OK
        // 注意：Qt 的 QLayout::addWidget 会调用 QWidget::setParent，实际上上述代码没有问题。        // 真正的错误是：不传入父对象也不添加到布局
    }
};

// 严重错误：new 出来的对象没有父对象且未 delete
void leakingFunction()
{
    QDialog *dialog = new QDialog();  // 泄漏！没有父对象也没有 delete
    QLabel *label = new QLabel(tr("Info"), dialog);  // 有父对象 dialog，但 dialog 本身泄漏了    dialog->exec();
    // dialog 没有 delete，label 虽由 dialog 管理但 dialog 未销毁，两者均泄漏
}
```

## 检查方法
1. LLM 分析 `new` 表达式中创建 `QObject` 子类实例的语句。2. 检查构造函数调用是否传入了父对象指针（第一个参数后若有 `QObject *parent` 参数的隐式或显式传递）
3. 对于未指定父对象的情况，检查：
   - 是否为栈对象（作用域结束自动析构）——允许   - 后续是否通过 `setParent()` 设置了父对象——允许   - 后续是否通过 `QLayout::addWidget()` 添加到布局（会自动调用 `setParent()`）——允许   - 是否有对应的手动 `delete` 语句——允许但非推荐（违反 `who-new-who-delete`）4. 完全无父对象又无 delete 的情况标记为违规

## 修复指南

1. 对于无父对象的堆分配 Qt 控件：   - 在构造函数调用时添加 `this` 指针作为父对象   - 或使用 `setParent()` 建立父子关系
2. 对于局部作用域中的 Qt 对象：   - 优先使用栈对象（自动析构）替代堆分配
   - 必须堆分配时，确保指定了有效的父对象
3. 检查对象所有权链：如果父对象本身泄漏（无父对象且未销毁），其所有子对象实际也泄漏。4. Qt 对象树机制保证父对象析构时递归销毁子对象，因此设置父对象后**不要**手动 `delete` 子对象（会导致二次删除 crash！）
## 审查清单

- [ ] 所有 `QObject` 派生类的堆分配对象有明确的父对象或生命周期管理- [ ] 未使用父对象机制的，有明确的 `delete` 语句或使用智能指针- [ ] 同一对象树中没有既有父对象又手动 `delete` 的情况（双重析构风险）- [ ] 临时对象优先使用栈分配
## 关联页面

- [[qt-who-new-who-delete]] —— 谁 new 谁 delete 原则
- [[qt-no-boost-smart-ptr]] —— 避免 boost 智能指针
