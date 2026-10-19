---
domain: cpp
rule_id: cpp-make-smart-ptr
title: 始终使用 std::make_unique 和 std::make_shared 创建智能指针
priority: main
source_file: rules/C++代码规范.md
source_section: "§2.1 Smart Pointers — 始终使用 std::make_unique 和 std::make_shared 创建智能指针"
status: active
check_method: regex
deterministic_check: true
checkability: deterministic
conflicts_with: []
overrides: []
related_pages:
  - [[cpp-unique-ptr]]
  - [[cpp-shared-ptr]]
  - [[cpp-std-move-usage]]
---

# 始终使用 std::make_unique 和 std::make_shared 创建智能指针

## 规则条款

创建 `std::unique_ptr` 和 `std::shared_ptr` 时，必须优先使用 `std::make_unique`（C++14+）和 `std::make_shared`（C++11+），禁止使用 `new` 表达式直接构造智能指针。使用 `make_*` 函数可以避免异常安全问题、提高内存局部性（shared_ptr 场景），并消除重复的类型书写。

注：本规则可通过静态分析进行确定性检查——搜索 `new` 表达式的结果直接传递给 `std::shared_ptr` 或 `std::unique_ptr` 构造函数即为违规。

## 正确示例

```cpp
#include <memory>
#include <string>
#include <utility>
#include <vector>

class Connection {
public:
    Connection(const std::string& url, int port)
        : m_url(url), m_port(port)
    {
    }

    void send(const std::string& data) { /* ... */ }

private:
    std::string m_url;
    int m_port;
};

class ConnectionPool {
public:
    ConnectionPool(const std::string& url, int port, size_t size)
    {
        for (size_t i = 0; i < size; ++i) {
            m_pool.push_back(
                std::make_unique<Connection>(url, port)  // ?
            );
        }
    }

private:
    std::vector<std::unique_ptr<Connection>> m_pool;
};

void processData(const std::string& url)
{
    // ? make_unique：参数完美转发
    auto conn = std::make_unique<Connection>(url, 8080);

    // ? make_shared：单次内存分配（对象+控制块）
    auto sharedConn = std::make_shared<Connection>(url, 9090);

    // ? 异常安全：即使第二个 make_unique 抛异常，
    //    第一个已经创建的对象也会被正确销毁
    auto pool = std::make_unique<ConnectionPool>(
        url, 8080, 10
    );

    conn->send("hello");

    // ? make_shared + 自定义删除器的场景（仍需用 make_* 为主体）
    //    创建时用 make_shared，release 后传自定义删除器
}

// ? 批量初始化
std::vector<std::shared_ptr<std::string>> createMessages(
    const std::vector<std::string>& words)
{
    std::vector<std::shared_ptr<std::string>> result;
    result.reserve(words.size());
    for (const auto& w : words) {
        result.push_back(std::make_shared<std::string>(w));
    }
    return result;
}

int main()
{
    processData("tcp://localhost");
    return 0;
}
```

## 错误示例

```cpp
#include <memory>
#include <string>

class Connection {
public:
    Connection(const std::string& url, int port) { /* ... */ }
    void send(const std::string& data) { /* ... */ }
};

// ? 错误1：用 new 创建 shared_ptr
std::shared_ptr<Connection> createBad1(const std::string& url)
{
    return std::shared_ptr<Connection>(new Connection(url, 80));
    //   类型写了两次（Connection 重复）、两次内存分配（对象+控制块）
}

// ? 错误2：用 new 创建 unique_ptr
std::unique_ptr<Connection> createBad2(const std::string& url)
{
    return std::unique_ptr<Connection>(new Connection(url, 80));
    //   类型重复，且可能引起异常安全问题：
    //   function(std::unique_ptr<X>(new X), std::unique_ptr<Y>(new Y))
    //   如果 new Y 抛异常，new X 已分配的对象会泄漏
    //   （在 C++17 中此问题已修复，但仍应使用 make_* 以避免歧义）
}

// ? 错误3：异常安全漏洞
void processTwo(const std::string& url)
{
    // 假设 MayThrow 构造可能抛异常
    auto data = std::unique_ptr<Connection>(new Connection(url, 80));
    auto more = std::unique_ptr<Connection>(new Connection(url, 81));
    // 如果第二个 new 抛异常，第一个 new 分配的对象会泄漏
    // （此问题在 C++17 已修复，但代码语义仍不佳）
}

// ? 错误4：类型重复且容易出错
class Server {
public:
    Server()
        : m_conn(std::shared_ptr<Connection>(new Connection("localhost", 0)))
        // ? 写了两次 Connection
    {
    }

private:
    std::shared_ptr<Connection> m_conn;
};

// ? 正确做法对比：
// class Server {
// public:
//     Server()
//         : m_conn(std::make_shared<Connection>("localhost", 0))
//     {
//     }
// private:
//     std::shared_ptr<Connection> m_conn;
// };

int main()
{
    auto bad = createBad1("tcp://example.com");
    return 0;
}
```

## 检查方法

1. **静态模式匹配**：搜索正则 `(std::shared_ptr|std::unique_ptr)<[^>]+>\(new\s+`，匹配到的每一处均为违规
2. 搜索所有 `new` 表达式，跟踪其结果的使用位置：若直接作为 `std::shared_ptr` 或 `std::unique_ptr` 构造函数的参数，判定为违规
3. 检查第三方/旧代码中的 `new` + 智能指针构造，提交修改 PR
4. 对已排除的合理例外（如自定义删除器）进行标注和审查确认

## 修复指南

1. **直接替换**：将 `std::shared_ptr<T>(new T(args...))` 改为 `std::make_shared<T>(args...)`；将 `std::unique_ptr<T>(new T(args...))` 改为 `std::make_unique<T>(args...)`
2. **成员初始化列表**：同样替换，`make_*` 返回的智能指针可直接用于初始化
3. **自定义删除器（需保留 new 的例外）**：`std::shared_ptr` 有自定义删除器时仍需用 `new`，但应评估能否改用 `std::unique_ptr` + 自定义删除器；或使用 `std::make_shared` + `.release()` 再包装自定义删除器（不推荐）。此类例外需显式注释 `// NOLINT(C-20)` 并标注原因
4. **C++11 项目**：若项目需要兼容 C++11 且没有 `std::make_unique`，应在项目基础设施中提供一个内联的 `make_unique` 实现（如下），并在升级到 C++14 后移除此实现

```cpp
// 仅在 C++11 项目中使用；升级到 C++14 后应删除
#if __cplusplus < 201402L
namespace detail {
template <typename T>
struct make_unique_helper {
    template <typename... Args>
    static std::unique_ptr<T> make(Args&&... args) {
        return std::unique_ptr<T>(new T(std::forward<Args>(args)...));
    }
};
} // namespace detail

template <typename T, typename... Args>
std::unique_ptr<T> make_unique(Args&&... args) {
    return detail::make_unique_helper<T>::make(std::forward<Args>(args)...);
}
#endif
```

5. **批量修复工具**：可使用 `clang-tidy` 的 `modernize-make-unique` 和 `modernize-make-shared` 检查自动修复

## 审查清单

- [ ] 代码中是否存在 `std::shared_ptr<T>(new T(...))` 模式？
- [ ] 代码中是否存在 `std::unique_ptr<T>(new T(...))` 模式？
- [ ] 所有可以替换的地方是否已改为 `std::make_shared` / `std::make_unique`？
- [ ] 保留 `new` + 自定义删除器的例外是否有明确的注释说明？
- [ ] C++11 项目中是否有 `make_unique` 的兼容实现？
- [ ] 是否在 CI 中配置了 clang-tidy `modernize-make-*` 检查？

## 关联页面

- [[cpp-unique-ptr]] — unique_ptr 的正确使用
- [[cpp-shared-ptr]] — shared_ptr 的正确使用
- [[cpp-std-move-usage]] — 移动语义与智能指针的配合
