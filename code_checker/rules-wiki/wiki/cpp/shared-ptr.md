---
domain: cpp
rule_id: cpp-shared-ptr
title: std::shared_ptr 仅用于真正需要共享所有权的场景
priority: main
source_file: rules/C++代码规范.md
source_section: "§2.1 Smart Pointers — std::shared_ptr 仅用于真正需要共享所有权的场景"
status: active
check_method: llm
deterministic_check: false
checkability: llm_checkable
conflicts_with: []
overrides: []
related_pages:
  - [[cpp-unique-ptr]]
  - [[cpp-weak-ptr]]
  - [[cpp-make-smart-ptr]]
  - [[cpp-no-bare-ownership]]
---

# std::shared_ptr 仅用于真正需要共享所有权的场景

## 规则条款

`std::shared_ptr` 引入引用计数开销（控制块分配、原子增减），只有当一个对象确实被多个所有者共享、且最后一个所有者才能安全释放资源的场景下才应使用。独占所有权的场景必须用 `std::unique_ptr`。避免将 `shared_ptr` 当作"方便"的默认选择——它的开销并非零。

## 正确示例

```cpp
#include <memory>
#include <vector>
#include <string>
#include <iostream>

class Texture {
public:
    explicit Texture(const std::string& name) : m_name(name)
    {
        std::cout << "Loading texture: " << m_name << std::endl;
    }
    ~Texture()
    {
        std::cout << "Unloading texture: " << m_name << std::endl;
    }

    const std::string& name() const { return m_name; }

private:
    std::string m_name;
};

class Sprite {
public:
    // 多个 Sprite 可以共享同一个 Texture — 这是真正的共享所有权
    explicit Sprite(std::shared_ptr<Texture> texture)
        : m_texture(std::move(texture))
    {
    }

    const Texture& texture() const { return *m_texture; }

private:
    std::shared_ptr<Texture> m_texture;
};

class Scene {
public:
    void addSprite(const std::shared_ptr<Texture>& texture)
    {
        m_sprites.push_back(std::make_shared<Sprite>(texture));
    }

    // 也持有一份引用，防止 Texture 在 Scene 销毁前被释放
    void setBackground(std::shared_ptr<Texture> texture)
    {
        m_background = std::move(texture);
    }

private:
    std::vector<std::shared_ptr<Sprite>> m_sprites;
    std::shared_ptr<Texture> m_background;
};

int main()
{
    // 多个 Sprite 和 Scene 共享同一个 Texture
    auto grassTex = std::make_shared<Texture>("grass.png");

    Scene scene;
    scene.setBackground(grassTex);    // 引用计数+1
    scene.addSprite(grassTex);        // 引用计数+1
    scene.addSprite(grassTex);        // 引用计数+1

    // grassTex 离开作用域，引用计数减少但仍 >0
    // 当 Scene 和所有 Sprite 都销毁后，Texture 才真正释放

    return 0;
}
```

## 错误示例

```cpp
#include <memory>
#include <vector>

class Connection {
public:
    void send(const std::string& data) { /* ... */ }
};

// ? 错误1：独占所有权却使用 shared_ptr
class NetworkManager {
public:
    NetworkManager()
        : m_connection(std::make_shared<Connection>())  // 只有 NetworkManager 持有
    {
    }

    void process()
    {
        m_connection->send("data");
    }

private:
    std::shared_ptr<Connection> m_connection;  // ? 应用 unique_ptr
};

// ? 错误2：不必要地创建 shared_ptr 只是为了传递给函数
void logConnection(std::shared_ptr<Connection> conn)  // ? 不应要求 shared_ptr
{
    conn->send("log");
}

void caller()
{
    // ? 仅仅为了调用 logConnection，强行创建 shared_ptr
    auto conn = std::make_shared<Connection>();
    logConnection(conn);
    // conn 随后立即销毁 — 不存在共享所有权
}

// ? 错误3：shared_ptr + this 的误用
class Handler {
public:
    std::shared_ptr<Handler> getShared()
    {
        // ? 多个 shared_ptr 独立管理同一个 this，会导致 double-free
        return std::shared_ptr<Handler>(this);
    }
};

// ? 错误4：到处传递 shared_ptr 作为参数
void drawCircle(std::shared_ptr<Canvas> canvas, int x, int y, int r)
{
    // drawCircle 不持有所有权，不应该拿 shared_ptr
    canvas->draw(x, y, r);
}

int main()
{
    // 这段代码中没有任何共享所有权的需求
    NetworkManager mgr;
    mgr.process();
    caller();
    return 0;
}
```

## 检查方法

1. 统计每个 `std::shared_ptr` 实例指向的对象的实际引用计数峰值：如果始终为 1，则为误用
2. 审查函数参数中的 `std::shared_ptr`：若函数不参与所有权共享，应改为裸指针或引用
3. 审查类成员中的 `std::shared_ptr`：评估是否存在多个对象独立持有同一对象的强引用；若该成员的生命周期严格包含在所有者内部，改为 `std::unique_ptr`
4. 检查是否存在"先创建 `shared_ptr` 再立即 `get()` 取裸指针使用"的模式：这通常表示不需要 `shared_ptr`
5. 搜索 `std::enable_shared_from_this` 的使用，确认 `this` 指针的共享管理是正确的（非误用）

## 修复指南

1. **shared_ptr 降级为 unique_ptr**：确认引用计数从未超过 1 后，将所有 `std::shared_ptr<T>` 替换为 `std::unique_ptr<T>`，`std::make_shared<T>` 替换为 `std::make_unique<T>`
2. **函数参数修复**：若函数只"使用"对象而不"拥有"它，将参数类型从 `std::shared_ptr<T>` 改为 `T&` 或 `T*`；调用方可以继续持有 `std::shared_ptr`，传入 `*ptr` 或 `ptr.get()` 即可
3. **enable_shared_from_this 修复**：如果需要从 `this` 安全创建 `shared_ptr`，让类继承 `std::enable_shared_from_this<T>`，通过 `shared_from_this()` 获取，而非直接 `std::shared_ptr<T>(this)`
4. **性能敏感路径**：在热路径上，避免频繁创建/销毁 `std::shared_ptr` 导致的原子操作开销，考虑改为 `std::unique_ptr` + 引用传递

## 审查清单

- [ ] 每个 `std::shared_ptr` 的使用是否确实对应共享所有权场景？
- [ ] 是否存在引用计数始终为 1 的 `shared_ptr`（暗示应用 `unique_ptr`）？
- [ ] 函数参数中不必要的 `std::shared_ptr` 是否已替换为 `T*` 或 `T&`？
- [ ] 是否正确使用了 `std::enable_shared_from_this`（如需要）？
- [ ] 是否有直接用 `shared_ptr<T>(this)` 的错误用法？
- [ ] 性能敏感路径上是否避免了不必要的 `shared_ptr` 开销？

## 关联页面

- [[cpp-unique-ptr]] — 独占所有权的首选方案
- [[cpp-weak-ptr]] — 打破 shared_ptr 循环引用
- [[cpp-make-smart-ptr]] — 使用 make_shared 创建 shared_ptr
- [[cpp-no-bare-ownership]] — 禁止裸指针表示所有权
