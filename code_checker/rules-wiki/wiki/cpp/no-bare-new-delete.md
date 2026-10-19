---
domain: cpp
rule_id: cpp-no-bare-new-delete
title: 禁止裸 new/delete
priority: main
source_file: rules/C++代码规范.md
source_section: "§3.2 内存泄漏预防"
status: active
check_method: regex
deterministic_check: true
checkability: deterministic
related_pages:
  - [[cpp-use-containers]]
  - [[cpp-weak-ptr-cycles]]
---

# 禁止裸 new/delete

## 规则条款
禁止使用裸 `new` 和 `delete` 操作符直接管理动态内存。所有动态分配必须通过智能指针（`std::unique_ptr`、`std::shared_ptr`）或标准库容器完成，以确保异常安全和自动资源释放。

**Qt 例外**：传入父对象（`this` 或其他 `QObject*`）的 `QObject` 派生类构造不受此限制。Qt 对象树通过父子关系自动管理子对象生命周期——父对象析构时递归销毁所有子对象，此时裸 `new` 是推荐做法。使用智能指针包裹 Qt 控件反而会导致双重删除（智能指针析构 + Qt 父对象析构）。未传入父对象的 Qt 堆对象仍应使用智能指针或转为栈对象。

## 正确示例
```cpp
#include <memory>
#include <vector>

// 使用 unique_ptr 管理单一对象
std::unique_ptr<Widget> widget = std::make_unique<Widget>();

// 使用 shared_ptr 管理共享对象
std::shared_ptr<Config> config = std::make_shared<Config>("app.conf");

// 使用 vector 管理动态数组
std::vector<int> values(100);

// 工厂函数返回智能指针
std::unique_ptr<Handler> createHandler(Type type) {
    return std::make_unique<ConcreteHandler>(type);
}

// Qt 例外：传入 this 的控件构造，由 Qt 对象树管理
class MyWidget : public QWidget {
    QLabel *m_lblName = new QLabel(this);     // OK — Qt 父对象管理
    QLineEdit *m_edtName = new QLineEdit(this); // OK — Qt 父对象管理
};
```

## 错误示例
```cpp
// 裸 new — 可能泄漏
Widget* widget = new Widget();
// ...
delete widget;  // 若中间抛异常，delete 永不被调用

// 裸数组 — 应用 vector 替代
int* arr = new int[100];
// ...
delete[] arr;

// 裸指针传递所有权不明确
Handler* createHandler(Type type) {
    return new ConcreteHandler(type);  // 谁负责 delete？
}
```

## 检查方法
使用正则表达式扫描源代码：

1. 匹配模式 `new\s+\w` 且上下文非智能指针构造函数（非 `make_unique`、`make_shared`、`unique_ptr<`、`shared_ptr<`）。
2. 匹配模式 `delete\s+` 且非 placement delete 或重载 `operator delete` 声明。
3. **排除 Qt 控件构造**：`new QWidget(this)` / `new QLayout(this)` 等传入父对象的 `QObject` 派生类构造不视为违规。
4. 允许例外：C 库互操作需掌握的裸指针可用 `// NOLINT(C-34)` 行注释豁免。

正则参考：
```
\bnew\s+(?!.*make_unique|.*make_shared|.*unique_ptr|.*shared_ptr)\w
\bdelete\s+\w
```

## 修复指南
1. 将 `T* p = new T(args)` 替换为 `auto p = std::make_unique<T>(args)`。
2. 将 `delete p` 移除，依赖智能指针析构自动释放。
3. 数组 `new T[n]` 替换为 `std::vector<T>(n)`。
4. 需要共享所有权时使用 `std::make_shared<T>(args)`。
5. 需传递裸指针给 C API 时用 `ptr.get()`，不转移所有权。

## 审查清单
- [ ] 代码中不存在裸 `new` 表达式（智能指针工厂和 Qt 父对象构造除外）
- [ ] 代码中不存在 `delete` 表达式（除自定义 deleter 外）
- [ ] 所有非 Qt 动态内存由 `unique_ptr`、`shared_ptr` 或容器管理
- [ ] Qt 控件构造传入了父对象（`this` 或 `QObject*`），由 Qt 对象树管理
- [ ] 工厂函数返回智能指针而非裸指针
- [ ] C API 互操作的裸指针获取已用 `// NOLINT(C-34)` 注释

## 关联页面
- [[cpp-use-containers]] — 使用标准库容器替代手动数组管理
- [[cpp-weak-ptr-cycles]] — 循环引用场景的 weak_ptr 使用
