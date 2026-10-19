---
domain: cpp
rule_id: cpp-perfect-forwarding
title: 在适当场合使用完美转发（std::forward）
priority: main
source_file: rules/C++代码规范.md
source_section: "§2.2 Move Semantics — 在适当场合使用完美转发(std::forward)"
status: active
check_method: llm
deterministic_check: false
checkability: llm_checkable
conflicts_with: []
overrides: []
related_pages:
  - [[cpp-std-move-usage]]
  - [[cpp-move-ctors]]
  - [[cpp-make-smart-ptr]]
---

# 在适当场合使用完美转发（std::forward）

## 规则条款

在泛型代码（模板函数）中，当需要将参数原封不动地（保留其左值/右值属性）传递给另一个函数时，必须使用 `std::forward<T>(arg)` 实现完美转发。典型场景包括：工厂函数、包装器/代理函数、以及将参数传递给基类或底层实现的转发层。注意不要混淆 `std::move`（无条件转右值）和 `std::forward`（有条件转发）：`std::move` 用于明确放弃所有权，`std::forward` 用于转发时保留值类别。

## 正确示例

```cpp
#include <memory>
#include <string>
#include <utility>
#include <vector>
#include <iostream>

// ? 示例1：make_unique 是完美转发的典范
template <typename T, typename... Args>
std::unique_ptr<T> makeUnique(Args&&... args)
{
    return std::unique_ptr<T>(new T(std::forward<Args>(args)...));
    // 如果传入左值 → T 被拷贝构造
    // 如果传入右值 → T 被移动构造
}

// ? 示例2：日志包装器 — 保留参数的值类别
class Logger {
public:
    template <typename Func, typename... Args>
    decltype(auto) logAndCall(const std::string& tag,
                              Func&& func,
                              Args&&... args)
    {
        std::cout << "[LOG] " << tag << std::endl;

        // ? 完美转发：保留 func 和 args 的原始类别
        return std::forward<Func>(func)(
            std::forward<Args>(args)...
        );
    }
};

// ? 示例3：emplace 风格的工厂方法
class EventBus {
public:
    template <typename Event, typename... Args>
    void dispatch(Args&&... args)
    {
        // ? 完美转发构造参数给 Event 的构造函数
        auto event = std::make_unique<Event>(
            std::forward<Args>(args)...
        );
        m_events.push_back(std::move(event));
    }

private:
    std::vector<std::unique_ptr<EventBase>> m_events;
};

// ? 示例4：通用的 setter 包装
template <typename T>
class Property {
public:
    template <typename U>
    void set(U&& value)
    {
        // ? 转发 value：左值 → 拷贝，右值 → 移动
        m_value = std::forward<U>(value);
    }

    const T& get() const { return m_value; }

private:
    T m_value;
};

// ? 示例5：lambda 中的完美转发
template <typename Func>
auto wrapCallback(Func&& callback)
{
    return [callback = std::forward<Func>(callback)](auto&&... args) mutable {
        // ? 在 lambda 内部再次完美转发
        return std::invoke(callback,
                           std::forward<decltype(args)>(args)...);
    };
}

class Connection {
public:
    explicit Connection(const std::string& host) {}
    explicit Connection(std::string&& host) {}
};

int main()
{
    // 左值调用
    std::string localHost = "localhost";
    auto conn1 = makeUnique<Connection>(localHost);  // 拷贝构造

    // 右值调用
    auto conn2 = makeUnique<Connection>("remote");   // 移动构造

    // 使用 setter
    Property<std::string> prop;
    std::string name = "alice";
    prop.set(name);               // 左值 → 拷贝赋值
    prop.set(std::string("bob")); // 右值 → 移动赋值

    // 使用 emplace 接口
    EventBus bus;
    std::string host = "event-server";
    bus.dispatch<Connection>(host);               // 拷贝构造
    bus.dispatch<Connection>(std::move(host));    // 移动构造

    return 0;
}
```

## 错误示例

```cpp
#include <memory>
#include <string>
#include <utility>
#include <iostream>

// ? 错误1：模板函数中用 std::move 代替 std::forward
template <typename T>
void badStore(T&& value)
{
    // ? std::move 总是将 value 转为右值
    // 当传入左值时，value 本应是拷贝，却被意外移走
    m_global = std::move(value);
    // 如果用左值调用 badStore，则左值被意外移走 → 危险
}

static std::string m_global;

// ? 错误2：按值传参后还用 forward
template <typename T>
void badForwardByValue(T value)  // 已经是按值传参
{
    // ? value 是局部对象，不应用 std::forward
    // std::forward 用于转发引用参数（T&& / auto&&）
    // 这里 value 是值类型，直接使用或 std::move 即可
    m_global = std::move(value);  // ? 这种情况下用 move 是对的
}

// ? 错误3：忘记 forward，直接传递 T&& 参数
template <typename T, typename... Args>
std::unique_ptr<T> makeUniqueBad(Args&&... args)
{
    // ? args... 现在是左值表达式了（有名字的变量），会走拷贝构造
    return std::unique_ptr<T>(new T(args...));
    // 应该写 new T(std::forward<Args>(args)...)
}

// ? 错误4：混淆 move 和 forward — 无条件移动转发参数
template <typename T>
void process(T&& value)
{
    if (std::is_rvalue_reference_v<decltype(value)>) {
        // ? 不需要 if — std::forward 本来就能在编译期区分
        takeOwnership(std::move(value));
    } else {
        makeCopy(value);
    }
    // ? 正确做法：takeOwnership(std::forward<T>(value));
}

// ? 错误5：forward 后继续使用原参数
template <typename T>
void badForwardUsage(T&& value)
{
    auto copy = std::forward<T>(value);  // 如果 T 是右值引用，value 被移走
    std::cout << value;  // ? value 可能已被移走
}

int main()
{
    std::string myName = "hello";
    badStore(std::move(myName));  // 明确移动是可以的
    // 但 badStore(myName);  // ? myName 会被意外移走！

    return 0;
}
```

## 检查方法

1. **模板函数的 T&& 参数**：搜索 `template<typename T> ... f(T&& arg)` 模式的函数，检查内部传递给其他函数时是否使用了 `std::forward<T>(arg)` 而非直接传递 `arg`
2. **auto&& 参数**：搜索 lambda 或函数中的 `auto&&` 参数，检查转发时是否使用了 `std::forward<decltype(param)>(param)`
3. **模板中误用 std::move**：搜索模板函数中 `std::move(T&& param)` 的模式（应该用 `std::forward`），`move` 会无条件移走左值
4. **可变参数模板中忘记 forward**：搜索 `Args&&... args` 参数，检查展开时是否用了 `std::forward<Args>(args)...`
5. **按值传参后误用 forward**：搜索按值传参的泛型参数后面使用了 `std::forward` 的模式

## 修复指南

1. **模板函数中将 move 改为 forward**：将 `std::move(universalRef)` 改为 `std::forward<T>(universalRef)`，其中 `T` 是模板推导出的类型（不是具体类型）
2. **补充遗漏的 forward**：在模板函数中，`T&&` 类型的变量 `x` 是一个有名字的左值，传递给其他函数时必须写 `std::forward<T>(x)` 或 `std::move(x)` 才能保持右值性。保留值类别用 `forward`，无条件移动用 `move`
3. **lambda 中的转发**：`auto&&... args` 的 lambda 参数中使用 `std::forward<decltype(args)>(args)...`；同理，捕获的泛型 lambda 也可以使用 `std::forward`
4. **按值传参的模板无需 forward**：如果函数参数是 `T value`（按值），那么 `value` 就是局部变量，直接用 `std::move(value)` 或直接传递即可
5. **添加 type_traits 检查**：在转发前可以用 `static_assert` 确保类型正确，例如 `static_assert(std::is_constructible_v<Target, Args...>)`

## 审查清单

- [ ] 模板函数中的 `T&&`（万能引用）参数转发时是否使用了 `std::forward<T>`？
- [ ] lambda 中的 `auto&&` 参数转发时是否使用了 `std::forward<decltype(arg)>`？
- [ ] 可变参数模板 `Args&&...` 是否通过 `std::forward<Args>(args)...` 展开？
- [ ] 是否避免了模板函数中对 `T&&` 参数使用 `std::move`（应使用 `std::forward`）？
- [ ] 按值传参的函数中是否误用了 `std::forward`（应用 `std::move` 或直接使用）？
- [ ] `std::forward` 调用后是否避免了对参数的进一步访问（右值已被移走的情况）？
- [ ] 类型约束是否完整（如使用 SFINAE 或 concepts 限定 Args）？

## 关联页面

- [[cpp-std-move-usage]] — std::move 的正确使用以及与 forward 的区别
- [[cpp-move-ctors]] — 与完美转发配合的移动构造
- [[cpp-make-smart-ptr]] — make_unique/make_shared 的完美转发实现
