---
domain: cpp
rule_id: cpp-weak-ptr-cycles
title: weak_ptr 打破循环引用
priority: main
source_file: rules/C++代码规范.md
source_section: "§3.2 内存泄漏预防"
status: active
check_method: llm
deterministic_check: false
checkability: llm_checkable
conflicts_with: []
overrides: []
related_pages:
  - [[cpp-no-bare-new-delete]]
  - [[cpp-use-containers]]
---

# weak_ptr 打破循环引用

## 规则条款
当两个或多个对象通过 `std::shared_ptr` 相互引用形成循环时，会导致引用计数永不归零，造成内存泄漏。必须使用 `std::weak_ptr` 打破循环——在不需要延长对象生命周期的方向上使用 `weak_ptr`。

## 正确示例
```cpp
#include <memory>
#include <vector>

class Node;  // 前置声明

class Node {
public:
    std::string name;
    // 子节点拥有所有权 — shared_ptr
    std::vector<std::shared_ptr<Node>> children;
    // 父节点不拥有所有权 — weak_ptr 打破循环
    std::weak_ptr<Node> parent;

    explicit Node(std::string n) : name(std::move(n)) {}

    void addChild(std::shared_ptr<Node> child) {
        child->parent = shared_from_this();  // 需要继承 enable_shared_from_this
        children.push_back(std::move(child));
    }
};

// 使用 enable_shared_from_this 获取自身的 shared_ptr
class Node : public std::enable_shared_from_this<Node> {
    // ... 同上
};
```

```cpp
// 观察者模式 — 主题持有观察者的 weak_ptr
class Subject {
    std::vector<std::weak_ptr<Observer>> observers;
public:
    void registerObserver(std::shared_ptr<Observer> obs) {
        observers.push_back(obs);  // shared_ptr 隐式转换为 weak_ptr
    }
    void notify() {
        for (auto& weak : observers) {
            if (auto obs = weak.lock()) {  // 提升为 shared_ptr 临时使用
                obs->update();
            } else {
                // 观察者已销毁，可清理
            }
        }
    }
};
```

## 错误示例
```cpp
// 循环引用 — parent 和 child 互相持有 shared_ptr
class BadNode {
public:
    std::vector<std::shared_ptr<BadNode>> children;
    std::shared_ptr<BadNode> parent;  // 错误：应使用 weak_ptr
};

void createCycle() {
    auto root = std::make_shared<BadNode>();
    auto child = std::make_shared<BadNode>();
    root->children.push_back(child);
    child->parent = root;  // 循环引用！root 和 child 都无法释放
}
// 函数退出后 root 和 child 的引用计数仍为 1，内存泄漏
```

```cpp
// 缓存持有 shared_ptr 阻止对象释放
class TextureCache {
    std::map<std::string, std::shared_ptr<Texture>> cache;  // 永不过期
    // 应使用 weak_ptr 让未使用的纹理能被回收
};
```

## 检查方法
LLM 辅助检查（非确定性）：

1. 识别所有使用 `std::shared_ptr` 作为成员变量的类。
2. 分析类之间的引用关系图，检测是否存在双向 `shared_ptr` 持有路径。
3. 检查 `std::shared_ptr` 成员是否可被替换为 `std::weak_ptr`（当该引用不需要所有权语义时）。
4. 特别关注父子关系、观察者模式、缓存、回调用 `shared_ptr` 捕获等模式。

## 修复指南
1. 确定循环中哪个方向不需要所有权——通常是父到子拥有（`shared_ptr`），子到父引用（`weak_ptr`）。
2. 将非所有权方向的 `std::shared_ptr<T>` 替换为 `std::weak_ptr<T>`。
3. 使用前通过 `weak_ptr::lock()` 获取临时 `shared_ptr`，检查对象是否仍然存活。
4. 需要从 `this` 获取 `shared_ptr` 时，类必须继承 `std::enable_shared_from_this<T>`。
5. 缓存场景考虑使用 `weak_ptr` 配合定期清理过期条目。

## 审查清单
- [ ] 所有 `shared_ptr` 成员变量已审查是否必须为所有权语义
- [ ] 父子关系中的回指引用使用 `weak_ptr`
- [ ] 观察者/监听器集合使用 `weak_ptr` 存储
- [ ] 回调和缓存中不阻止对象正常释放
- [ ] 使用 `weak_ptr` 处有 `lock()` 检查和空指针处理
- [ ] 需要 `shared_from_this()` 的类正确继承了 `enable_shared_from_this`

## 关联页面
- [[cpp-no-bare-new-delete]] — 统一使用智能指针管理内存
- [[cpp-use-containers]] — 使用标准库容器
