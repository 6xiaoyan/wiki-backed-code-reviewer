---
domain: cpp
rule_id: cpp-moved-from-state
title: 移动后对象必须处于有效但未指定的状态
priority: main
source_file: rules/C++代码规范.md
source_section: "§2.2 Move Semantics — 移动后对象必须处于有效但未指定的状态"
status: active
check_method: llm
deterministic_check: false
checkability: llm_checkable
conflicts_with: []
overrides: []
related_pages:
  - [[cpp-move-ctors]]
  - [[cpp-std-move-usage]]
  - [[cpp-unique-ptr]]
---

# 移动后对象必须处于有效但未指定的状态

## 规则条款

移动操作（移动构造或移动赋值）完成后，被移动的源对象（moved-from object）必须保持在一个"有效但未指定"的状态。这意味着：
- **有效**：对象仍然可以被安全地析构
- **未指定**：对象的具体内容不确定（可能是空的、默认构造的状态，也可能是部分资源残留）
- **安全操作**：对象可以重新被赋值（赋予一个新的有效状态）
- **不依赖**：不应依赖被移动对象的具体值（如大小、内容等）

这条规则同时约束移动操作的实现者和调用者：实现者必须确保源对象可被安全析构和重新赋值；调用者在移动后不应读取源对象的具体值。

## 正确示例

```cpp
#include <memory>
#include <string>
#include <vector>
#include <cassert>
#include <utility>

// ? 示例1：移动构造后源对象状态安全的类
class Buffer {
public:
    explicit Buffer(size_t size)
        : m_data(new char[size])
        , m_size(size)
    {
    }

    ~Buffer() { delete[] m_data; }

    // 移动构造：将源置为安全状态
    Buffer(Buffer&& other) noexcept
        : m_data(std::exchange(other.m_data, nullptr))
        , m_size(std::exchange(other.m_size, 0))
    {
        // ? other 仍有效：m_data == nullptr, m_size == 0
        // other 可以安全析构（delete[] nullptr 是安全的）
        // other 可以重新赋值
    }

    Buffer& operator=(Buffer&& other) noexcept
    {
        if (this != &other) {
            delete[] m_data;
            m_data = std::exchange(other.m_data, nullptr);
            m_size = std::exchange(other.m_size, 0);
        }
        return *this;
        // ? other 处于安全状态
    }

    Buffer(const Buffer&) = delete;
    Buffer& operator=(const Buffer&) = delete;

private:
    char* m_data;
    size_t m_size;
};

// ? 示例2：调用者正确使用 moved-from 对象
void useMovedFromObject()
{
    std::vector<int> v1 = {1, 2, 3, 4, 5};
    std::vector<int> v2 = std::move(v1);

    // ? v1 现在处于"有效但未指定"状态

    // ? 安全操作1：检查是否为空（STL 保证移动后为空）
    assert(v1.empty());

    // ? 安全操作2：重新赋值，赋予有效状态
    v1 = {6, 7, 8};
    assert(v1.size() == 3);

    // ? 安全操作3：调用 clear()
    v1.clear();

    // ? 安全操作4：调用 size()（值未指定，但调用安全）
    auto s = v1.size();  // s == 0

    // ? v1 离开作用域，安全析构
}

// ? 示例3：重新利用 moved-from 对象
std::string processName(std::string input)
{
    std::string result = std::move(input);

    // ? input 处于有效但未指定状态
    // ? 可以直接重新赋值，无需先调用 clear()
    input = "default value";

    // 利用 input 做其他事情
    if (result.empty()) {
        return input;  // NRVO
    }
    return result;
}

// ? 示例4：unique_ptr 的 moved-from 状态
void manageConnection()
{
    auto conn = std::make_unique<Connection>("tcp://localhost");

    // 转移所有权
    std::unique_ptr<Connection> other = std::move(conn);

    // ? conn 现在为 nullptr（unique_ptr 保证 moved-from 为 nullptr）
    assert(conn == nullptr);

    // ? 可以重新分配
    conn = std::make_unique<Connection>("tcp://backup");
    assert(conn != nullptr);

    // ? 可以重置
    conn.reset();
}

int main()
{
    useMovedFromObject();
    return 0;
}
```

## 错误示例

```cpp
#include <memory>
#include <string>
#include <vector>
#include <cassert>
#include <cstring>
#include <iostream>

// ? 错误1：移动操作未将源对象置为安全状态
class BadBuffer {
public:
    explicit BadBuffer(size_t size)
        : m_data(new char[size])
        , m_size(size)
    {
    }

    ~BadBuffer()
    {
        delete[] m_data;  // 析构时调用 delete[]
    }

    BadBuffer(BadBuffer&& other) noexcept
        : m_data(other.m_data)   // 窃取指针
        , m_size(other.m_size)
    {
        // ? 忘记置空 other.m_data
        // other 析构时会 delete 同一块内存 → double-free!
    }

private:
    char* m_data;
    size_t m_size;
};

// ? 错误2：移动后依赖 moved-from 对象的具体值
void badMovedFromUsage()
{
    std::string s = "hello world";
    std::string dest = std::move(s);

    // ? 不规范：依赖 moved-from 对象的具体值
    // STL 保证 moved-from std::string 处于"有效但未指定"状态
    // 具体内容可能为空、也可能残留部分字符串
    std::cout << "After move, s = '" << s << "'" << std::endl;  // ? 不可预测
    if (s == "hello") {  // ? 比较移动后的值无意义
        std::cout << "still hello\n";
    }
}

// ? 错误3：移动后不重新赋值就读取
void badReuse(std::vector<int>& target)
{
    std::vector<int> data = {1, 2, 3};
    target = std::move(data);

    // ? 依赖 data 的旧值
    int first = data[0];  // ? data 已被移走，下标访问是未定义行为
    //   即使 STL 通常会将移动后的 vector 置为空，
    //   但规范不保证 data[0] 有效访问（空 vector 下标访问是 UB）
}

// ? 错误4：移动操作实现不正确 — 未释放当前资源
class BadAssignment {
public:
    explicit BadAssignment(int* ptr) : m_ptr(ptr) {}
    ~BadAssignment() { delete m_ptr; }

    BadAssignment& operator=(BadAssignment&& other) noexcept
    {
        // ? 忘记释放当前 m_ptr → 内存泄漏
        // ? 忘记将 other.m_ptr 置空 → double-free
        m_ptr = other.m_ptr;
        return *this;
    }

private:
    int* m_ptr;
};

// ? 错误5：移动到自身
void badSelfMove()
{
    std::vector<int> v = {1, 2, 3};
    v = std::move(v);  // ? 自赋值移动，行为未定义
    // 正确的移动赋值会检查 if (this != &other)
}

int main()
{
    badMovedFromUsage();
    return 0;
}
```

## 检查方法

1. **移动构造/赋值实现检查**：检查自定义移动操作是否将源对象的资源指针置为有效状态（如 `nullptr` 表示"无资源"），并确保源对象的析构不会引发 double-free 或资源泄漏
2. **源对象析构安全性检查**：检查源对象被移动后，其析构函数是否可以安全执行（不释放已转移的资源、不访问已被拿走的指针）
3. **移动后使用检查**：在代码中搜索 `std::move(x)` 或 `std::forward<T>(x)` 之后对 `x` 的非赋值/非析构访问——依赖 moved-from 对象的具体值是未定义行为的危险信号
4. **自赋值检查**：搜索自定义移动赋值运算符，确认包含 `if (this != &other)` 检查
5. **STL 容器 moved-from 检查**：检查是否对 moved-from 的 STL 容器进行了下标访问（在未确认非空的情况下）

## 修复指南

1. **修复移动操作的实现**：使用 `std::exchange(member, safe_value)` 确保源对象的成员同时完成"窃取"和"置为安全值"；安全的默认值包括 `nullptr`（指针）、`0`/`-1`（句柄）、空容器（STL 容器移动后自动为空）
2. **修复移动后读取**：如果逻辑上需要保留原对象的值，则不使用 `std::move`，改用拷贝；如果只需要 eventually 重新赋值，则仅在重新赋值后才访问 moved-from 对象
3. **添加自赋值保护**：在所有移动赋值运算符开头添加 `if (this != &other)` 检查
4. **文档标注**：在函数文档中明确标注哪些参数会被 move、move 后对象的状态保证
5. **使用 sanitizer**：在开发构建中启用 AddressSanitizer（`-fsanitize=address`）检测 use-after-move 和 double-free

## 审查清单

- [ ] 自定义移动操作是否将源对象的资源指针/句柄置为安全状态？
- [ ] 被移动对象的析构函数是否能安全执行（不引发 double-free）？
- [ ] 代码中是否存在对 moved-from 对象的非赋值、非析构访问？
- [ ] 移动赋值运算符是否包含自赋值检查？
- [ ] STL 容器被 move 后是否在重新赋值/`clear()` 之后才进行下标访问？
- [ ] 是否对 moved-from 对象进行了有意义的比较或条件判断？
- [ ] 是否启用了 AddressSanitizer 检测 use-after-move？

## 关联页面

- [[cpp-move-ctors]] — 实现正确的移动操作
- [[cpp-std-move-usage]] — std::move 的正确调用方式
- [[cpp-unique-ptr]] — unique_ptr 的 moved-from 状态（nullptr 保证）
