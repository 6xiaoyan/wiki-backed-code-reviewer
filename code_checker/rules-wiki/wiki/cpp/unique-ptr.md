---
domain: cpp
rule_id: cpp-unique-ptr
title: 优先使用 std::unique_ptr 管理独占所有权资源
priority: main
source_file: rules/C++代码规范.md
source_section: "§2.1 Smart Pointers — 优先使用 std::unique_ptr 管理独占所有权资源"
status: active
check_method: llm
deterministic_check: false
checkability: llm_checkable
conflicts_with: []
overrides: []
related_pages:
  - [[cpp-shared-ptr]]
  - [[cpp-make-smart-ptr]]
  - [[cpp-no-bare-ownership]]
  - [[cpp-move-ctors]]
---

# 优先使用 std::unique_ptr 管理独占所有权资源

## 规则条款

对于具有独占所有权语义的资源（文件句柄、动态分配对象、网络连接等），必须优先使用 `std::unique_ptr` 而非裸指针或 `std::shared_ptr`。`std::unique_ptr` 零开销（与裸指针相同大小），在编译期保证唯一所有权，无需引用计数开销，是 RAII 资源管理的首选方案。

## 正确示例

```cpp
#include <memory>
#include <string>
#include <vector>

// 1. 动态对象的独占所有权
class Engine {
public:
    Engine() = default;
    void start() { /* ... */ }
};

class Car {
public:
    // 构造函数中传递所有权，使用 std::move 显式标示
    explicit Car(std::unique_ptr<Engine> engine)
        : m_engine(std::move(engine))
    {
    }

    void drive()
    {
        if (m_engine) {
            m_engine->start();
        }
    }

private:
    std::unique_ptr<Engine> m_engine;  // Car 独占 Engine 的所有权
};

// 2. 工厂函数返回 unique_ptr，明确表示所有权转移
std::unique_ptr<Car> createCar()
{
    auto engine = std::make_unique<Engine>();
    return std::make_unique<Car>(std::move(engine));
}

// 3. 容器中持有不可拷贝的对象
class EventHandler {
public:
    virtual ~EventHandler() = default;
    virtual void handle() = 0;
};

std::vector<std::unique_ptr<EventHandler>> g_handlers;

void registerHandler(std::unique_ptr<EventHandler> handler)
{
    g_handlers.push_back(std::move(handler));
}

// 4. 自定义删除器用于非内存资源
struct FileCloser {
    void operator()(FILE* f) const noexcept
    {
        if (f) {
            fclose(f);
        }
    }
};

std::unique_ptr<FILE, FileCloser> openFile(const std::string& path)
{
    FILE* f = fopen(path.c_str(), "r");
    return std::unique_ptr<FILE, FileCloser>(f);
}

int main()
{
    auto car = createCar();
    car->drive();

    auto file = openFile("/tmp/data.txt");
    if (file) {
        // 读取文件...
    }
    // file 离开作用域时自动调用 FileCloser 关闭文件

    return 0;
    // car 和 engine 自动析构，无内存泄漏
}
```

## 错误示例

```cpp
#include <memory>
#include <string>

class Engine {
public:
    void start() { /* ... */ }
};

class Car {
public:
    // ? 错误1：使用裸指针持有所有权，谁负责 delete 不明确
    Engine* m_engine;
};

// ? 错误2：工厂函数返回裸指针，调用者必须手动 delete
Car* createCar()
{
    Engine* engine = new Engine();
    Car* car = new Car();
    car->m_engine = engine;
    return car;
    // 如果后续逻辑抛异常，engine 和 car 都会泄漏
}

// ? 错误3：不必要的 shared_ptr — 所有权是独占的
std::shared_ptr<Car> createCarShared()
{
    auto engine = std::make_shared<Engine>();
    auto car = std::make_shared<Car>();
    car->m_engine = engine.get();  // 所有权模型混乱
    return car;
    // shared_ptr 带来引用计数开销，但实际不需要共享所有权
}

// ? 错误4：使用 new 直接初始化 unique_ptr
std::unique_ptr<Car> createCarManual()
{
    std::unique_ptr<Car> car(new Car());  // 可能引起异常安全问题
    return car;
}

int main()
{
    Car* car = createCar();
    // ... 使用 car ...
    delete car;  // ? 容易忘记，异常路径下会泄漏
    return 0;
}
```

## 检查方法

1. 搜索代码中所有 `new` 表达式，检查其结果是否直接赋给了裸指针而不是 `std::unique_ptr`
2. 搜索函数返回类型为裸指针 `T*` 的声明，检查这些函数是否在转移所有权（若是，应改为 `std::unique_ptr<T>`）
3. 搜索类成员中类型为裸指针的字段，判断是否表示所有权关系（若是，应改为 `std::unique_ptr<T>`）
4. 搜索所有 `std::shared_ptr` 的使用，评估其所有权是否实际上是独占的，如果是则改为 `std::unique_ptr`
5. 检查 `std::unique_ptr` 的创建是否使用了 `std::make_unique`（C++14+），而非 `new` 表达式

## 修复指南

1. **裸指针成员改为 unique_ptr**：将 `T* m_xxx;` 改为 `std::unique_ptr<T> m_xxx;`，注意头文件中 `#include <memory>`
2. **工厂函数返回类型**：将 `T* create()` 改为 `std::unique_ptr<T> create()`，内部使用 `std::make_unique<T>()` 创建对象；调用方用 `auto` 接收或显式写 `std::unique_ptr<T>`；需要转移给其他函数时用 `std::move()`
3. **shared_ptr 降级为 unique_ptr**：检查引用计数是否有 >1 的场景；若不涉及共享所有权，将 `std::shared_ptr<T>` 和 `std::make_shared<T>()` 分别改为 `std::unique_ptr<T>` 和 `std::make_unique<T>()`
4. **C++11 兼容性**：若项目必须支持 C++11，`std::make_unique` 不可用（C++14 引入），可内联实现一个 `make_unique` 辅助函数作为临时方案，同时推动项目升级到 C++14 以上

## 审查清单

- [ ] 所有动态分配的对象是否通过 `std::unique_ptr` 持有独占所有权？
- [ ] 工厂函数是否返回 `std::unique_ptr` 而非裸指针？
- [ ] 类成员中表示所有权的裸指针是否已替换为 `std::unique_ptr`？
- [ ] 是否避免了不必要的 `std::shared_ptr`（独占场景改用 `unique_ptr`）？
- [ ] 是否使用了 `std::make_unique`（C++14+）创建 `unique_ptr`？
- [ ] 自定义删除器是否正确处理了非内存资源（如 `FILE*`、socket）？

## 关联页面

- [[cpp-shared-ptr]] — 共享所有权的正确场景与误用
- [[cpp-make-smart-ptr]] — 使用 make_unique/make_shared 创建智能指针
- [[cpp-no-bare-ownership]] — 禁止裸指针表示所有权
- [[cpp-move-ctors]] — 与 unique_ptr 配合的移动语义
