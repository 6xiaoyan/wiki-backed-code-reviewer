---
domain: cpp
rule_id: cpp-no-bare-ownership
title: 禁止在接口中使用裸指针表示所有权
priority: main
source_file: rules/C++代码规范.md
source_section: "§2.1 Smart Pointers — 禁止在接口中使用裸指针表示所有权"
status: active
check_method: llm
deterministic_check: false
checkability: llm_checkable
conflicts_with: []
overrides: []
related_pages:
  - [[cpp-unique-ptr]]
  - [[cpp-shared-ptr]]
  - [[cpp-std-move-usage]]
  - [[cpp-move-ctors]]
---

# 禁止在接口中使用裸指针表示所有权

## 规则条款

裸指针（`T*`）只能用于表示"可选的引用"或"非拥有的观察"，绝不可用于表示所有权。当函数返回一个动态分配的对象、或参数接收一个对象并表示接管其所有权时，必须使用 `std::unique_ptr` 或 `std::shared_ptr` 明确表达所有权语义。

所有权类型对照表：

| 语义 | 接口类型 |
|------|----------|
| 转移独占所有权（返回） | `std::unique_ptr<T>` |
| 转移独占所有权（参数） | `std::unique_ptr<T>` 按值传参 |
| 转移共享所有权 | `std::shared_ptr<T>` |
| 共享所有权（不转移） | `const std::shared_ptr<T>&` |
| 非拥有、不可为空的引用 | `T&` |
| 非拥有、可为空的引用 | `T*` |

## 正确示例

```cpp
#include <memory>
#include <string>
#include <vector>

class Connection {
public:
    Connection(const std::string& url) : m_url(url) {}
    void send(const std::string& data) { /* ... */ }

private:
    std::string m_url;
};

class Logger {
public:
    virtual void log(const std::string& msg) = 0;
    virtual ~Logger() = default;
};

class FileLogger : public Logger {
public:
    void log(const std::string& msg) override { /* ... */ }
};

// ? 返回智能指针：明确表示调用者获得所有权
std::unique_ptr<Connection> createConnection(const std::string& url)
{
    return std::make_unique<Connection>(url);
}

// ? 接收智能指针：明确表示接管所有权
class ConnectionPool {
public:
    void addConnection(std::unique_ptr<Connection> conn)
    {
        m_connections.push_back(std::move(conn));
    }

private:
    std::vector<std::unique_ptr<Connection>> m_connections;
};

// ? 非拥有引用：使用引用表示"不可为空、不拥有"
void processConnection(Connection& conn)
{
    conn.send("data");
}

// ? 非拥有、可为空的引用：使用裸指针表示"观察者"
void processConnectionIfExists(Connection* conn)
{
    if (conn) {
        conn->send("data");
    }
}

// ? 共享所有权：返回 shared_ptr
std::shared_ptr<Logger> createLogger()
{
    return std::make_shared<FileLogger>();
}

int main()
{
    auto conn = createConnection("tcp://localhost:8080");  // 获得所有权

    ConnectionPool pool;
    pool.addConnection(std::move(conn));  // 转移所有权给 pool

    // 使用引用访问（非拥有）
    Connection localConn("tcp://localhost:9090");
    processConnection(localConn);
    processConnectionIfExists(&localConn);

    return 0;
}
```

## 错误示例

```cpp
#include <memory>
#include <string>

class Connection {
public:
    Connection(const std::string& url) : m_url(url) {}
    void send(const std::string& data) { /* ... */ }

private:
    std::string m_url;
};

// ? 错误1：工厂函数返回裸指针——谁负责 delete？
Connection* createConnection(const std::string& url)
{
    return new Connection(url);
    // 调用者必须记得 delete，否则泄漏
    // 异常路径下极易泄漏
}

// ? 错误2：参数接收裸指针，语义不明确
class ConnectionPool {
public:
    void addConnection(Connection* conn)
    {
        // ? 这是接管所有权还是仅仅引用？
        m_connections.push_back(conn);
        // 调用者不知道是否应继续使用 conn，也不知道是否应 delete
    }

private:
    std::vector<Connection*> m_connections;  // ? 谁负责释放？
};

// ? 错误3：void** 或 T** 表示输出参数/所有权
bool createConnection(int id, Connection** outConn)
{
    *outConn = new Connection("tcp://default");
    return true;
    // ? C 风格接口在 C++ 中应用智能指针替代
}

// ? 错误4：函数注释声称不拥有，但用 shared_ptr 表示
// "仅读取" 的函数不应要求 shared_ptr
void readConfig(std::shared_ptr<Connection> conn)
{
    conn->send("ping");  // 只调用 const 方法，不需要所有权
}

int main()
{
    Connection* conn = createConnection("tcp://localhost");
    // 使用 conn...
    delete conn;  // ? 容易忘记，异常路径会泄漏

    // 更糟：有时不记得是否需要 delete
    Connection* conn2 = nullptr;
    createConnection(42, &conn2);
    // conn2 需要 delete 吗？代码没说清楚

    return 0;
}
```

## 检查方法

1. 搜索返回类型为 `T*` 的函数声明，逐一检查返回值是否由函数内部分配（如 `new`）——若是，则为所有权转移，应返回智能指针
2. 搜索参数类型为 `T*` 且函数内部将其存入容器/成员的场景——若函数接管了该指针的生命周期，则为所有权接收，应接收智能指针
3. 搜索使用 `T**` 或 `void**` 作为输出参数的接口——应用智能指针引用或返回 `std::optional<std::unique_ptr<T>>` 替代
4. 搜索函数注释或文档中声明"调用者负责释放"或"调用者拥有"的裸指针——应用智能指针消除歧义
5. 检查参数为 `std::shared_ptr<T>` 但函数只使用对象而不参与所有权的场景——应降级为 `T&` 或 `T*`

## 修复指南

1. **返回 new 对象的函数**：将返回类型从 `T*` 改为 `std::unique_ptr<T>`；内部将 `return new T(...)` 改为 `return std::make_unique<T>(...)`；调用方用 `auto` 接收或 `std::unique_ptr<T>` 显式声明，用 `std::move()` 转移所有权
2. **接管所有权的参数**：将函数签名从 `void add(T* obj)` 改为 `void add(std::unique_ptr<T> obj)`；调用方调用时写作 `add(std::move(obj))`；若原参数允许传 `nullptr`，改为 `void add(std::unique_ptr<T> obj)` 不变（unique_ptr 可以为空）
3. **C 风格输出参数**：如果确实需要返回"可能为空的对象"，改为 `std::unique_ptr<T> create()` 返回空指针表示失败；或返回值类型改为 `std::optional<std::unique_ptr<T>>`；如果是与 C API 互操作，在边界处包装/解包智能指针并使用 `// NOLINT(C-21)` 豁免
4. **不需要所有权的 shared_ptr 参数**：改为 `T&`（不可为空）或 `T*`（可为空），调用方传 `*ptr` 或 `ptr.get()`
5. **批量分析**：使用编译器的 `-Wreturn-std-move` 或静态分析工具（clang-tidy `cppcoreguidelines-owning-memory`）扫描所有权裸指针

## 审查清单

- [ ] 所有返回动态分配对象的函数是否返回智能指针而非裸指针？
- [ ] 所有接管所有权的函数参数是否使用智能指针按值传参？
- [ ] 是否消除了所有 `T**` 的 C 风格输出参数（C API 互操作除外）？
- [ ] 不需要所有权的函数参数是否避免了 `std::shared_ptr`？
- [ ] `T*` 参数是否仅用于"可选的、非拥有的引用"？
- [ ] C API 边界的裸指针是否有明确的文档和 NOLINT 标注？

## 关联页面

- [[cpp-unique-ptr]] — 独占所有权的首选方案
- [[cpp-shared-ptr]] — 共享所有权的场景
- [[cpp-std-move-usage]] — 所有权转移的语法
- [[cpp-move-ctors]] — 与所有权转移配合的移动构造函数
