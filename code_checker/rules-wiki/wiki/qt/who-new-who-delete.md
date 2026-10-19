---
domain: qt
rule_id: qt-who-new-who-delete
title: 谁 new 谁 delete 原则
priority: main
source_file: rules/QT代码开发规范.md
source_section: "§4.4 内存管理"
status: active
check_method: llm
deterministic_check: false
checkability: llm_checkable
conflicts_with: []
overrides: []
related_pages:
  - [[qt-parent-child-memory]]
  - [[qt-no-boost-smart-ptr]]
---

# 谁 new 谁 delete 原则

## 规则条款

普通指针管理遵循"谁 new 谁 delete"原则：分配资源的代码负责释放资源。同一个 `new` 操作的配对 `delete` 应在同一责任范围内执行，不建议将所有权和责任分散到不同模块或层级。

对于 Qt 对象树管理的控件（已设置父对象），父对象析构时自动调用子对象的 `delete`，此时父对象即为"delete 者"。对于不属于 Qt 对象树的普通指针，创建者必须在适当的时机显式释放。

## 正确示例

```cpp
// 示例 1：Qt 父对象管理——new 和 delete 在同一责任范围
class DataPanel : public QWidget
{
public:
    DataPanel(QWidget *parent = nullptr) : QWidget(parent)
    {
        // 由 DataPanel（即 this）new，也由 DataPanel 析构时自动 delete
        m_table = new QTableWidget(this);
        m_model = new QStandardItemModel(this);
    }
    // DataPanel 析构时，Qt 自动 delete m_table 和 m_model

private:
    QTableWidget *m_table;
    QStandardItemModel *m_model;
};

// 示例 2：非 Qt 对象的普通指针——new 和 delete 在同一函数内
void processFile(const QString &path)
{
    QFile *file = new QFile(path);
    if (file->open(QIODevice::ReadOnly)) {
        QByteArray data = file->readAll();
        // 处理 data ...
    }
    delete file;  // 创建者负责释放
}

// 示例 3：工厂函数之一贯的所有权转移模式
// 调用方明确知道获得了所有权，负责 delete
QThread* createWorkerThread(QObject *parent)
{
    QThread *thread = new QThread(parent);  // parent 为 null 时由调用方管理
    return thread;
}

void useWorkerThread()
{
    // 调用方获得了所有权，调用方负责清理
    QThread *worker = createWorkerThread(nullptr);
    worker->start();
    worker->wait();
    delete worker;  // 由 new 的最终接收方处理
}
```

## 错误示例

```cpp
// 错误 1：跨模块的隐藏所有权转移
// module_a.cpp
QFile* openConfigFile()
{
    return new QFile("config.ini");  // module_a new，谁 delete？不清楚
}

// module_b.cpp
void readConfig()
{
    QFile *file = openConfigFile();  // module_b 获得了指针但不知道是否需要 delete
    // ... 使用 file
    // 没人 delete —— 内存泄漏
    // 或者 delete 了但 module_a 不知道 —— 所有权混乱
}

// 错误 2：new 和 delete 分属不同函数且责任不明
void createData(DataManager *mgr)
{
    DataObject *obj = new DataObject();  // 此处 new
    mgr->registerObject(obj);           // 所有权模糊转移
    // 谁该 delete obj？createData 还是 DataManager？规则不明确
}

// 错误 3：普通指针分配后没有对应 delete
void leakExample()
{
    QByteArray *data = new QByteArray(1024, '\0');  // 普通指针，非 QObject
    // 使用 data ...
    // 没有 delete data —— 内存泄漏
    // QByteArray 不是 QObject，不能设置父对象
}
```

## 检查方法
1. LLM 分析所有 `new` 表达式，记录分配点及其所在的函数/类。
2. 追踪每个分配点的配对 `delete`：
   - Qt 对象树管理：检查是否设置了父对象（构造时传入 parent 或后续 `setParent()`）
   - 显式 delete：检查同一作用域或同一类中是否有对应的 `delete` 语句
3. 对于跨函数/跨模块的所有权转移，检查是否有明确的所有权约定（如函数注释、命名约定）
4. 未发现配对 `delete` 且无 Qt 父对象管理的标记为潜在泄漏

## 修复指南

1. 确定指针所有权模式：
   - **Qt 对象树模式**（推荐）：构造时传入父对象，由 Qt 自动管理
   - **作用域模式**：在同一函数内 `new` 和 `delete`，或使用栈对象
   - **显式所有权转移**：通过函数名或注释明确表示所有权转移（如 `createXxx()` 返回需调用方 delete 的指针）
2. 对于跨模块的所有权模糊情况：
   - 改为在构造时传入父对象
   - 或使用 `std::unique_ptr` / `QScopedPointer` 明确所有权
   - 或在接口注释中明确说明所有权语义
3. 为每个 `new` 找到明确的 `delete` 路径：
   - Qt 父对象自动 delete
   - 同一作用域内手动 delete
   - 智能指针自动释放

## 审查清单

- [ ] 每个 `new` 表达式的分配点有明确的释放路径
- [ ] Qt 对象通过父对象机制管理（构造时传入 parent）
- [ ] 非 Qt 对象的普通指针有配对 `delete`
- [ ] 跨模块所有权转移有明确的约定和文档
- [ ] 无"孤儿指针"——既无父对象又无对应 `delete`

## 关联页面

- [[qt-parent-child-memory]]：Qt 父类管理子类内存
- [[qt-no-boost-smart-ptr]]：避免 boost 智能指针
