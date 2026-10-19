---
domain: qt
rule_id: qt-no-boost-smart-ptr
title: 避免 boost 智能指针
priority: main
source_file: rules/QT代码开发规范.md
source_section: "§4.4 内存管理"
status: active
check_method: llm
deterministic_check: false
checkability: advisory_only
conflicts_with: []
overrides: []
related_pages:
  - [[qt-parent-child-memory]]
  - [[qt-who-new-who-delete]]
---

# 避免 boost 智能指针

## 规则条款

不建议日常使用 boost 智能指针（如 `boost::shared_ptr`、`boost::scoped_ptr`、`boost::weak_ptr` 等），因为 boost 的内存管理思路与 Qt 的父子对象树机制存在差异，混用可能导致所有权混乱、双重析构等问题。在必要情况下（如与第三方库接口对接、需要非 Qt 对象的引用计数共享）可特殊使用，但需明确说明理由。
## 正确示例

```cpp
// 推荐：使用 Qt 父子对象树管理 Qt 对象生命周期
class MyWidget : public QWidget
{
    Q_OBJECT
public:
    MyWidget(QWidget *parent = nullptr) : QWidget(parent)
    {
        // Qt 对象由父对象管理——推荐方式        m_label = new QLabel(tr("Status"), this);
        m_timer = new QTimer(this);
        m_model = new QStandardItemModel(this);
    }
    // 父对象 this 析构时自动销毁所有子对象

private:
    QLabel *m_label;
    QTimer *m_timer;
    QStandardItemModel *m_model;
};

// 推荐：非 Qt 堆对象使用 QScopedPointer 或 std::unique_ptr
void processData()
{
    // QScopedPointer：Qt 风格的独占所有权智能指针
    QScopedPointer<QFile> file(new QFile("data.bin"));
    if (file->open(QIODevice::ReadOnly)) {
        // 处理数据...
    }
    // file 自动 delete，无需手动管理
}

// 推荐：需要共享所有权的非 Qt 对象使用 QSharedPointer
class DataCache
{
public:
    QSharedPointer<CacheEntry> getEntry(const QString &key)
    {
        QSharedPointer<CacheEntry> entry(new CacheEntry(key));
        m_entries.insert(key, entry);
        return entry;  // 引用计数自动管理
    }

private:
    QMap<QString, QSharedPointer<CacheEntry>> m_entries;
};

// 推荐：使用 std::unique_ptr 管理非 Qt 堆对象class ResourceManager
{
private:
    std::unique_ptr<Resource> m_resource;  // 自动 delete
};
```

## 错误示例

```cpp
// 错误：混用 boost 智能指针与 Qt 父子对象树class BadWidget : public QWidget
{
    Q_OBJECT
public:
    BadWidget(QWidget *parent = nullptr) : QWidget(parent)
    {
        // 错误：boost::shared_ptr 管理 QLabel，同时又传了 this 作为父对象        // this 析构时会 delete m_label，boost::shared_ptr 析构时也会 delete
        // 导致双重析构，crash！        boost::shared_ptr<QLabel> label(new QLabel(tr("Bad"), this));
        m_label = label;
    }

private:
    boost::shared_ptr<QLabel> m_label;
};

// 错误：Qt 对象用 boost::scoped_ptr 管理，与 Qt 对象树冲突 void badFunction()
{
    QWidget window;
    // boost::scoped_ptr 会在作用域结束时 delete label
    // 而 window 作为父对象也会在析构时 delete label
    // 导致双重析构！    boost::scoped_ptr<QLabel> label(new QLabel(tr("Bad"), &window));
}

// 错误：不需要 boost 的场景却引入 boost 依赖
#include <boost/shared_ptr.hpp>
#include <boost/scoped_ptr.hpp>

class SimpleClass
{
    // 完全没有必要——使用 std::unique_ptr 或 Qt 父子关系即可
    boost::shared_ptr<QString> m_data;  // QString 应直接作为值成员，无需指针
    boost::scoped_ptr<QTimer> m_timer;  // QTimer 可传 this 做父对象，无需 boost
};
```

## 检查方法
1. LLM 或正则扫描 `#include` 指令，检测 boost 智能指针头文件：
   - `<boost/shared_ptr.hpp>`
   - `<boost/scoped_ptr.hpp>`
   - `<boost/weak_ptr.hpp>`
   - `<boost/intrusive_ptr.hpp>`
   - `<boost/smart_ptr.hpp>`
2. 同时扫描代码中 boost 智能指针的使用：
   - `boost::shared_ptr<...>`
   - `boost::scoped_ptr<...>`
   - `boost::weak_ptr<...>`
   - `boost::intrusive_ptr<...>`
3. 对于检测到的使用，判断是否属于"必要情况"（如第三方库接口要求、跨模块共享非 Qt 对象等）
4. 非必要的 boost 智能指针使用标记为 advisory（建议替换，不强制阻止）

## 修复指南

1. 对于 Qt 对象：   - 删除 `boost::shared_ptr` / `boost::scoped_ptr` 包装
   - 改为通过 Qt 父子对象树管理（构造时传入父对象指针）
2. 对于非 Qt 对象且需要独占所有权：   - `boost::scoped_ptr<T>` → `QScopedPointer<T>` → `std::unique_ptr<T>`
3. 对于非 Qt 对象且需要共享所有权：   - `boost::shared_ptr<T>` → `QSharedPointer<T>` → `std::shared_ptr<T>`
4. 移除 boost 智能指针相关的 `#include` 头文件。5. 检查 CMakeLists.txt / .pro 文件，移除不必要的 boost 库链接。
## 特殊例外

以下场景可视为必要情况，允许使用 boost 智能指针：
- 第三方 C++ 库接口要求传入或接收 `boost::shared_ptr`
- 需要跨模块与使用 boost 的旧代码互操作- Qt 项目中使用非 Qt 的纯 C++ 库，且该库内部使用 boost 智能指针

使用例外时应在代码中添加注释说明理由：```cpp
#include <boost/shared_ptr.hpp>  // 第三方库 FooLib 接口要求 boost::shared_ptr

boost::shared_ptr<FooLib::Context> m_ctx;  // FooLib 内部管理，与 Qt 对象无关。```

## 审查清单

- [ ] 无 boost 智能指针头文件引用（`boost/shared_ptr.hpp` 等）
- [ ] 无 `boost::shared_ptr`、`boost::scoped_ptr` 等使用 - [ ] Qt 对象通过父子对象树管理，不使用任何智能指针包裹- [ ] 如有 boost 智能指针使用，已确认属于必要例外且有注释说明
- [ ] 已使用 Qt 替代方案（`QScopedPointer`、`QSharedPointer`）或 C++11 标准方案

## 关联页面

- [[qt-parent-child-memory]] —— Qt 父类管理子类内存
- [[qt-who-new-who-delete]] —— 谁 new 谁 delete 原则
