---
domain: cpp
rule_id: cpp-weak-ptr
title: std::weak_ptr 用于打破 std::shared_ptr 的循环引用
priority: main
source_file: rules/C++代码规范.md
source_section: "§2.1 Smart Pointers — std::weak_ptr 用于打破 std::shared_ptr 的循环引用"
status: active
check_method: llm
deterministic_check: false
checkability: llm_checkable
conflicts_with: []
overrides: []
related_pages:
  - [[cpp-shared-ptr]]
  - [[cpp-unique-ptr]]
---

# std::weak_ptr 用于打破 std::shared_ptr 的循环引用

## 规则条款

当两个或多个对象通过 `std::shared_ptr` 相互持有引用时，会形成循环引用，导致引用计数永远无法归零、对象永远不被释放（内存泄漏）。必须使用 `std::weak_ptr` 打破这种循环——在循环中至少有一方使用弱引用，使引用计数可以正常降到零。

## 正确示例

```cpp
#include <memory>
#include <string>
#include <iostream>
#include <vector>

class Folder;  // 前置声明

class File {
public:
    explicit File(const std::string& name) : m_name(name) {}
    ~File() { std::cout << "File '" << m_name << "' destroyed\n"; }

    const std::string& name() const { return m_name; }

    // 设置所属文件夹 — weak_ptr 不增加 Folder 的引用计数
    void setParent(std::shared_ptr<Folder> parent)
    {
        m_parent = parent;  // weak_ptr，不会阻止 Folder 析构
    }

    std::shared_ptr<Folder> parent() const
    {
        return m_parent.lock();  // 临时提升为 shared_ptr 使用
    }

private:
    std::string m_name;
    std::weak_ptr<Folder> m_parent;  // ? 弱引用父节点，打破循环
};

class Folder {
public:
    explicit Folder(const std::string& name) : m_name(name) {}
    ~Folder()
    {
        std::cout << "Folder '" << m_name << "' destroyed"
                  << " (contains " << m_files.size() << " files)\n";
    }

    const std::string& name() const { return m_name; }

    void addFile(std::shared_ptr<File> file)
    {
        file->setParent(shared_from_this());  // 设置子→父的 weak_ptr
        m_files.push_back(std::move(file));   // 父持有子的 shared_ptr
    }

private:
    std::string m_name;
    std::vector<std::shared_ptr<File>> m_files;
};

class Folder : public std::enable_shared_from_this<Folder> {
    // ... 同上，需 enable_shared_from_this 才能用 shared_from_this()
};

// 另一个常见场景：观察者模式
class Subject;  // 前置声明

class Observer {
public:
    virtual ~Observer() = default;
    virtual void update(const Subject& subject) = 0;
};

class Subject {
public:
    void addObserver(std::shared_ptr<Observer> observer)
    {
        m_observers.push_back(observer);  // weak_ptr 不阻止 Observer 析构
    }

    void notify()
    {
        // 清理失效的 observer，通知仍然存活的
        auto it = m_observers.begin();
        while (it != m_observers.end()) {
            if (auto observer = it->lock()) {
                observer->update(*this);
                ++it;
            } else {
                it = m_observers.erase(it);  // 自动清理已销毁的 observer
            }
        }
    }

private:
    std::vector<std::weak_ptr<Observer>> m_observers;  // ? 弱引用
};

int main()
{
    auto folder = std::make_shared<Folder>("Documents");
    auto file1 = std::make_shared<File>("report.pdf");
    auto file2 = std::make_shared<File>("notes.txt");

    folder->addFile(file1);
    folder->addFile(file2);

    // folder 析构时：
    // 1. m_files 中的 shared_ptr<File> 释放 → File 引用计数降为 0（因为 File 只有 weak_ptr 回指）
    // 2. File 析构 → m_parent (weak_ptr) 自动失效
    // 3. Folder 引用计数降为 0 → Folder 析构
    // 无内存泄漏

    return 0;
}
```

## 错误示例

```cpp
#include <memory>
#include <string>
#include <vector>
#include <iostream>

class Folder;  // 前置声明

class File {
public:
    explicit File(const std::string& name) : m_name(name) {}
    ~File() { std::cout << "File '" << m_name << "' destroyed\n"; }

    void setParent(std::shared_ptr<Folder> parent)
    {
        m_parent = parent;  // ? shared_ptr 造成循环引用
    }

private:
    std::string m_name;
    std::shared_ptr<Folder> m_parent;  // ? 强引用—循环引用
};

class Folder {
public:
    explicit Folder(const std::string& name) : m_name(name) {}
    ~Folder()
    {
        std::cout << "Folder '" << m_name << "' (supposedly) destroyed\n";
    }

    void addFile(std::shared_ptr<File> file)
    {
        file->setParent(shared_from_this());
        m_files.push_back(file);
    }

private:
    std::string m_name;
    std::vector<std::shared_ptr<File>> m_files;
};

class Folder : public std::enable_shared_from_this<Folder> {
    // ...
};

int main()
{
    auto folder = std::make_shared<Folder>("Documents");
    auto file = std::make_shared<File>("report.pdf");
    folder->addFile(file);

    // folder 和 file 离开作用域后，它们的引用计数都不会归零：
    // Folder → shared_ptr<File> (m_files) → File 引用计数+1
    // File → shared_ptr<Folder> (m_parent) → Folder 引用计数+1
    // 循环引用 → 两者都无法销毁 → 内存泄漏！
    return 0;
}
```

## 检查方法

1. 绘制对象的引用关系图：列出所有持有 `std::shared_ptr` 的成员，检查是否存在 A→B 且 B→A 的环
2. 搜索涉及双向关联的数据结构（树节点的父子、链表的双向、图的节点间边），特别关注双方是否都用了 `shared_ptr`
3. 搜索 `std::weak_ptr` 的使用，确认每个 `weak_ptr` 是否为打破循环而引入（即对应方向存在一个反向的 `shared_ptr`）；若不存在反向 `shared_ptr`，`weak_ptr` 可能不必要
4. 使用内存检测工具（Valgrind、AddressSanitizer）验证是否存在 `shared_ptr` 泄漏
5. 检查 `lock()` 调用是否做了空指针判断（`weak_ptr` 可能已失效）

## 修复指南

1. **识别循环方向**：列出所有 `shared_ptr` 成员指向关系，画出有向图
2. **选择打破方向**：通常选择"上级→下级"为 `shared_ptr`，"下级→上级"为 `weak_ptr`（如 File→Folder）；或者在观察者模式中，"被观察者→观察者"为 `weak_ptr`
3. **修改成员类型**：将循环中一方的 `std::shared_ptr<T>` 改为 `std::weak_ptr<T>`；使用处通过 `.lock()` 获取临时的 `std::shared_ptr<T>`
4. **添加 lock() 检查和空处理**：每次使用 `weak_ptr` 时调用 `.lock()` 检查返回值，因为指向的对象可能已经被销毁
5. **清理过期 weak_ptr**：如果 `weak_ptr` 存储在容器中，定期调用 `.lock()` 检查并清理已失效的条目（`expired() == true` 的条目）

## 审查清单

- [ ] 双向关联的结构中是否存在循环引用（A 持有 shared_ptr<B>，B 持有 shared_ptr<A>）？
- [ ] 循环引用中是否至少有一方已改用 `std::weak_ptr`？
- [ ] `weak_ptr` 的使用处是否都通过 `.lock()` 检查了有效性？
- [ ] 容器中的 `weak_ptr` 是否有定期清理过期条目的机制？
- [ ] 是否避免了不必要的 `weak_ptr`（没有反向 `shared_ptr` 的场景）？
- [ ] 对象析构顺序是否经过验证（无泄漏）？

## 关联页面

- [[cpp-shared-ptr]] — shared_ptr 的正确使用场景
- [[cpp-unique-ptr]] — 独占所有权场景
