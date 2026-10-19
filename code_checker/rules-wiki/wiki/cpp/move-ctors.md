---
domain: cpp
rule_id: cpp-move-ctors
title: 为资源管理类实现移动构造函数和移动赋值运算符
priority: main
source_file: rules/C++代码规范.md
source_section: "§2.2 Move Semantics — 为资源管理类实现移动构造函数和移动赋值运算符"
status: active
check_method: llm
deterministic_check: false
checkability: llm_checkable
conflicts_with: []
overrides: []
related_pages:
  - [[cpp-std-move-usage]]
  - [[cpp-moved-from-state]]
  - [[cpp-unique-ptr]]
---

# 为资源管理类实现移动构造函数和移动赋值运算符

## 规则条款

任何管理堆内存、文件句柄、网络套接字、互斥锁等独占资源的类，必须显式实现或正确默认（`= default`）移动构造函数和移动赋值运算符。移动语义使资源以极低成本（指针交换）在不同作用域间转移，避免昂贵的深拷贝。如果一个类声明了析构函数、拷贝构造或拷贝赋值，则必须遵循"五法则"（Rule of Five），同时声明移动操作。

## 正确示例

```cpp
#include <cstddef>
#include <cstring>
#include <utility>

// 示例1：管理动态内存的类
class Buffer {
public:
    explicit Buffer(size_t size)
        : m_data(new char[size])
        , m_size(size)
    {
    }

    ~Buffer()
    {
        delete[] m_data;
    }

    // 移动构造函数：窃取资源，将源对象置为安全状态
    Buffer(Buffer&& other) noexcept
        : m_data(std::exchange(other.m_data, nullptr))
        , m_size(std::exchange(other.m_size, 0))
    {
    }

    // 移动赋值运算符：释放当前资源，窃取源对象资源
    Buffer& operator=(Buffer&& other) noexcept
    {
        if (this != &other) {
            delete[] m_data;                       // 释放当前资源
            m_data = std::exchange(other.m_data, nullptr);
            m_size = std::exchange(other.m_size, 0);
        }
        return *this;
    }

    // 禁止拷贝（资源独占）
    Buffer(const Buffer&) = delete;
    Buffer& operator=(const Buffer&) = delete;

    size_t size() const { return m_size; }
    const char* data() const { return m_data; }

private:
    char* m_data;
    size_t m_size;
};

// 示例2：使用智能指针的类 — 移动操作可自动生成
class SmartResource {
public:
    explicit SmartResource(int id)
        : m_id(id)
        , m_buffer(std::make_unique<Buffer>(1024))
    {
    }

    // ? 移动操作由成员自动生成，无需手写
    SmartResource(SmartResource&&) noexcept = default;
    SmartResource& operator=(SmartResource&&) noexcept = default;

    // 禁止拷贝
    SmartResource(const SmartResource&) = delete;
    SmartResource& operator=(const SmartResource&) = delete;

private:
    int m_id;
    std::unique_ptr<Buffer> m_buffer;
};

// 示例3：文件句柄管理
class FileHandle {
public:
    explicit FileHandle(const char* path)
        : m_handle(openFile(path))
    {
    }

    ~FileHandle()
    {
        if (m_handle != kInvalidHandle) {
            closeFile(m_handle);
        }
    }

    FileHandle(FileHandle&& other) noexcept
        : m_handle(std::exchange(other.m_handle, kInvalidHandle))
    {
    }

    FileHandle& operator=(FileHandle&& other) noexcept
    {
        if (this != &other) {
            if (m_handle != kInvalidHandle) {
                closeFile(m_handle);
            }
            m_handle = std::exchange(other.m_handle, kInvalidHandle);
        }
        return *this;
    }

    FileHandle(const FileHandle&) = delete;
    FileHandle& operator=(const FileHandle&) = delete;

private:
    static constexpr int kInvalidHandle = -1;

    static int openFile(const char* path) { /* ... */ return 0; }
    static void closeFile(int handle) { /* ... */ }

    int m_handle;
};

int main()
{
    Buffer buf1(4096);
    Buffer buf2 = std::move(buf1);  // 移动构造，O(1) 开销
    // buf1 此时为空（m_data == nullptr, m_size == 0）

    Buffer buf3(1024);
    buf3 = std::move(buf2);  // 移动赋值，buf3 先释放自身资源

    return 0;
}
```

## 错误示例

```cpp
#include <cstddef>
#include <cstring>
#include <iostream>

// ? 错误1：管理动态内存但不实现移动操作
class BadBuffer {
public:
    explicit BadBuffer(size_t size)
        : m_data(new char[size])
        , m_size(size)
    {
    }

    ~BadBuffer()
    {
        delete[] m_data;
    }

    // ? 没有移动构造函数和移动赋值
    // 由于声明了析构函数，编译器不会隐式生成移动操作
    // BadBuffer buf2 = std::move(buf1); → 将调用拷贝构造（如果存在）

    size_t size() const { return m_size; }

private:
    char* m_data;
    size_t m_size;
};

// ? 错误2：移动操作未标记 noexcept
class RiskyBuffer {
public:
    explicit RiskyBuffer(size_t size)
        : m_data(new char[size])
        , m_size(size)
    {
    }

    ~RiskyBuffer() { delete[] m_data; }

    // ? 缺少 noexcept：std::vector 等容器在扩容时，
    //    如果移动操作不是 noexcept，会退化为拷贝
    RiskyBuffer(RiskyBuffer&& other)  // ? 应加 noexcept
        : m_data(std::exchange(other.m_data, nullptr))
        , m_size(std::exchange(other.m_size, 0))
    {
    }

    RiskyBuffer& operator=(RiskyBuffer&& other)  // ? 应加 noexcept
    {
        if (this != &other) {
            delete[] m_data;
            m_data = std::exchange(other.m_data, nullptr);
            m_size = std::exchange(other.m_size, 0);
        }
        return *this;
    }

    // 拷贝操作
    RiskyBuffer(const RiskyBuffer& other)
        : m_data(new char[other.m_size])
        , m_size(other.m_size)
    {
        std::memcpy(m_data, other.m_data, m_size);
    }

private:
    char* m_data;
    size_t m_size;
};

// ? 错误3：移动操作未将源对象置为有效状态
class LeakyBuffer {
public:
    // ...

    LeakyBuffer(LeakyBuffer&& other) noexcept
        : m_data(other.m_data)     // 窃取资源
        , m_size(other.m_size)
    {
        // ? 忘记将 other.m_data 置为 nullptr
        // other 析构时会 delete[] other.m_data，和 this->m_data 指向同一块内存
        // → double-free!
    }

private:
    char* m_data = nullptr;
    size_t m_size = 0;
};

int main()
{
    BadBuffer b1(100);
    // BadBuffer b2 = std::move(b1);  // 编译错误：移动操作被隐式删除

    std::cout << "done\n";
    return 0;
}
```

## 检查方法

1. **规则检测**：对每个定义了析构函数、拷贝构造或拷贝赋值的类，检查是否同时声明了移动构造和移动赋值（"五法则"）
2. 搜索管理裸资源的类（含 `new`/`delete`、`fopen`/`fclose`、操作系统句柄等），确认有移动操作
3. 检查移动操作是否标记为 `noexcept` — 缺少 `noexcept` 会导致 STL 容器退化为拷贝
4. 检查移动构造中源指针/句柄是否被置为安全状态（如 `nullptr`、`-1`），防止 double-free
5. 检查移动赋值中是否包含自赋值检查：`if (this != &other)`
6. 搜索继承了 `boost::noncopyable` 的类或删除了拷贝操作的类，确认提供了移动操作

## 修复指南

1. **为裸资源管理类添加移动操作**：实现移动构造（窃取资源 + 将源置为安全状态）和移动赋值（自赋检查 + 释放自身 + 窃取 + 置源为安全状态），均标记 `noexcept`，拷贝操作标记 `= delete`
2. **为智能指针成员类添加移动操作**：如果所有成员都是可移动类型（unique_ptr、string、vector 等），直接声明 `= default` 并标记 `noexcept`
3. **为既有拷贝又有移动的类**：按"五法则"实现全部 5 个特殊成员函数（析构、拷贝构造、拷贝赋值、移动构造、移动赋值），移动操作标记 `noexcept`
4. **使用 `std::exchange`**：统一用 `m_resource = std::exchange(other.m_resource, safe_value)` 同时完成窃取和置安全值
5. **添加 noexcept**：确认移动操作中不抛异常的操作不能有 `throw` 或可能抛异常的调用；若确定不会抛异常，标记 `noexcept`

## 审查清单

- [ ] 定义析构函数或拷贝操作的类是否也声明了移动构造和移动赋值？
- [ ] 移动构造和移动赋值是否标记为 `noexcept`？
- [ ] 移动构造是否将源对象的资源指针/句柄置为安全状态？
- [ ] 移动赋值是否包含自赋值检查（`if (this != &other)`）？
- [ ] 移动赋值是否在窃取资源前释放了当前持有的资源？
- [ ] 纯智能指针成员的类是否使用了 `= default` 的移动操作？
- [ ] 是否避免了只提供拷贝但禁止移动的反模式？

## 关联页面

- [[cpp-std-move-usage]] — std::move 的正确使用
- [[cpp-moved-from-state]] — 移动后对象的状态保证
- [[cpp-unique-ptr]] — unique_ptr 的移动语义
