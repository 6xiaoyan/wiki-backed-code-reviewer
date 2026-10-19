---
domain: cpp
rule_id: cpp-std-move-usage
title: 使用 std::move 明确标识可移动的左值
priority: main
source_file: rules/C++代码规范.md
source_section: "§2.2 Move Semantics — 使用 std::move 明确标识可移动的左值；对不再需要的资源使用 std::move 避免不必要的拷贝"
status: active
check_method: llm
deterministic_check: false
checkability: llm_checkable
conflicts_with: []
overrides: []
related_pages:
  - [[cpp-move-ctors]]
  - [[cpp-moved-from-state]]
  - [[cpp-perfect-forwarding]]
  - [[cpp-unique-ptr]]
---

# 使用 std::move 明确标识可移动的左值

## 规则条款

当一个左值（有名字的变量）不再被需要、且其资源可以安全移走时，必须使用 `std::move` 显式将其转换为右值引用，以触发移动构造/移动赋值而非拷贝。这可以避免昂贵的不必要拷贝（如大容器、字符串、unique_ptr）。但必须遵守一个重要例外：**不对函数返回的局部变量使用 `std::move`**，因为这会阻止编译器的 NRVO（Named Return Value Optimization）优化。

## 正确示例

```cpp
#include <memory>
#include <string>
#include <vector>
#include <utility>

class DataBuffer {
public:
    explicit DataBuffer(std::vector<int> data)
        : m_data(std::move(data))  // ? data 是参数，不再被使用
    {
    }

    void append(std::string value)
    {
        // ? value 是按值传参的副本，移动它比拷贝更高效
        m_chunks.push_back(std::move(value));
    }

    // ? 需要转移 unique_ptr 所有权时
    void setProcessor(std::unique_ptr<Processor> processor)
    {
        m_processor = std::move(processor);
    }

    // ? 从容器中移动出元素（元素不再属于容器）
    std::string takeLast()
    {
        auto result = std::move(m_chunks.back());
        m_chunks.pop_back();
        return result;  // ? 不对 result 使用 std::move，依赖 NRVO
    }

private:
    std::vector<int> m_data;
    std::vector<std::string> m_chunks;
    std::unique_ptr<Processor> m_processor;
};

// ? 正确：不阻止 NRVO
std::vector<int> generateData(size_t n)
{
    std::vector<int> result;
    result.reserve(n);
    for (size_t i = 0; i < n; ++i) {
        result.push_back(static_cast<int>(i));
    }
    return result;  // ? 不写 std::move(result)，编译器自动 NRVO
}

// ? 返回表达式（非变量名）时可以用 move
std::unique_ptr<Processor> createProcessor(int mode)
{
    auto p = std::make_unique<Processor>(mode);
    if (mode == 0) {
        return std::make_unique<Processor>(0);  // 临时对象，本身就是右值
    }
    return p;  // ? 局部变量，NRVO 适用，不用 move
}

// ? 将元素移入容器避免拷贝
void populateConnections(std::vector<std::string>& targets)
{
    std::vector<std::unique_ptr<Connection>> conns;
    for (auto& target : targets) {
        auto conn = std::make_unique<Connection>(target);
        conns.push_back(std::move(conn));  // ? conn 不再使用
    }
    // 处理 conns...
}

int main()
{
    std::vector<int> v = {1, 2, 3, 4, 5};
    DataBuffer buf(std::move(v));  // ? v 不再使用
    // v 处于"有效但未指定"状态，不应再访问

    std::string name = "hello world";
    buf.append(std::move(name));   // ? name 的内容被移走，不再使用

    auto proc = std::make_unique<Processor>(42);
    buf.setProcessor(std::move(proc));  // ? proc 所有权转移

    return 0;
}
```

## 错误示例

```cpp
#include <memory>
#include <string>
#include <vector>
#include <utility>

// ? 错误1：对 return 局部变量使用 std::move（阻止 NRVO）
std::vector<int> generateDataBad(size_t n)
{
    std::vector<int> result;
    result.reserve(n);
    for (size_t i = 0; i < n; ++i) {
        result.push_back(static_cast<int>(i));
    }
    return std::move(result);  // ? 阻止 NRVO！
    // NRVO 直接将 result 构造在调用方的位置（零开销）
    // std::move 强制使用移动构造（至少有一次移动开销）
}

// ? 错误2：遗漏 std::move 导致不必要的深拷贝
class Processor {
public:
    explicit Processor(std::string name)
        : m_name(name)  // ? 拷贝了 name，应用 std::move(name)
    {
    }

private:
    std::string m_name;
};

// ? 错误3：移动后继续使用对象
void badMoveUsage()
{
    std::string s = "important data";
    std::string dest = std::move(s);  // s 的内容被移走
    std::cout << s.length();  // ? s 处于"有效但未指定"状态，不确定输出
}

// ? 错误4：对 const 对象使用 std::move
void badConstMove(const std::string& input)
{
    std::string copy = std::move(input);  // ? std::move(const T&) 不会真正移动
    // input 是 const 引用，std::move 返回 const T&&
    // 移动构造无法绑定到 const T&&（除非移动构造接受 const T&&，通常不）
    // 实际上还是会调用拷贝构造
}

// ? 错误5：条件分支中对同一变量多次 move
void badConditionalMove(bool useA, std::string a, std::string b)
{
    std::string chosen;
    if (useA) {
        chosen = std::move(a);
    } else {
        chosen = std::move(b);
    }
    // a 或 b 之一被移走了，但编译器不保证在编译期知道是哪个
    // 后续不能再安全地访问 a 或 b，除非通过检查 useA
    // 更好的做法是将选择逻辑封装
}

int main()
{
    auto data = generateDataBad(100);
    return 0;
}
```

## 检查方法

1. **return std::move 检测**：搜索正则 `return\s+std::move\(`，检查其参数是否为局部变量名（非表达式/非成员访问）——绝大多数情况下应移除 `std::move`
2. **遗漏 std::move 检测（构造函数参数）**：搜索构造函数初始化列表中按值接收的 `std::string`、`std::vector` 等参数是否缺少 `std::move`
3. **移动后使用检测**：在 `std::move(x)` 调用后，检查同一作用域内是否存在对 `x` 的后续读操作（除了赋值/析构）
4. **const 对象 std::move 检测**：搜索对 `const` 限定的变量或参数使用 `std::move` 的情况——移除 `std::move`，因为无法真正移动
5. **容器中的 move**：检查 `push_back`/`insert` 等操作是否对不再使用的左值使用了 `std::move`

## 修复指南

1. **移除错误的 return std::move**：将 `return std::move(localVar);` 改为 `return localVar;` 以启用 NRVO
2. **补充遗漏的 std::move**：在构造函数初始化列表、赋值语句、容器插入操作中，对按值传递的即将销毁的左值参数添加 `std::move`
3. **修复移动后使用**：若对象被 `std::move` 后逻辑上仍需要访问，说明不应在此处移动——考虑重新组织代码或使用拷贝。若只是重新赋值是可以的（如 `s = std::move(t); s = "new value";` 合法）
4. **修复 const 上的无用 move**：移除 `std::move(constObj)`，因为这些调用无法触发移动语义
5. **编译器警告**：启用 `-Wpessimizing-move`（GCC 9+/Clang 12+）在编译时检测阻止 NRVO 的 `std::move`；启用 `-Wredundant-move`（GCC 9+/Clang 12+）检测冗余的 `std::move`

## 审查清单

- [ ] 是否存在 `return std::move(localVariable)`（阻止 NRVO）？
- [ ] 构造函数/赋值中按值传递的参数是否使用了 `std::move`？
- [ ] `std::move` 后是否存在对原对象的后续访问（赋值/析构除外）？
- [ ] 是否有对 `const` 限定变量使用 `std::move` 的无意义调用？
- [ ] 容器插入不再使用的元素时是否使用了 `std::move`？
- [ ] `std::unique_ptr` 的所有权转移是否使用了 `std::move`？
- [ ] 编译器是否启用了 `-Wpessimizing-move` 和 `-Wredundant-move` 警告？

## 关联页面

- [[cpp-move-ctors]] — 为类实现移动操作
- [[cpp-moved-from-state]] — 移动后对象的状态保证
- [[cpp-perfect-forwarding]] — std::forward 与完美转发
- [[cpp-unique-ptr]] — unique_ptr 的移动
