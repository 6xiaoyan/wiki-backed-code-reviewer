---
domain: cpp
rule_id: cpp-raii-copy-semantics
title: RAII 拷贝语义
priority: main
source_file: rules/C++代码规范.md
source_section: "§3.1 RAII"
status: active
check_method: llm
deterministic_check: false
checkability: llm_checkable
conflicts_with: []
overrides: []
related_pages:
  - [[cpp-raii-principle]]
  - [[cpp-raii-ctor-dtor]]
  - [[cpp-raii-std-wrappers]]
---

# RAII 拷贝语义

## 规则条款
对于管理独占资源的 RAII 类，必须明确处理拷贝语义：要么通过 `= delete` 禁止拷贝，要么正确
实现深拷贝以产生独立管理的资源副本。永远不要依赖编译器生成的默认拷贝构造函数和拷贝赋值
运算符来管理资源——这会导致双重释放（double-free）或资源所有权混乱。

选择指南：
- **独占资源**（文件句柄、socket、互斥锁）：禁止拷贝，仅允许移动
- **可共享资源**（引用计数数据、共享内存块）：实现深拷贝或引用计数
- **值语义数据**：如果成员均为值类型且自动管理资源，默认拷贝即可

## 正确示例
```cpp
#include <memory>
#include <mutex>
#include <cstdio>
#include <string>
#include <stdexcept>

// 独占资源：禁止拷贝，仅支持移动
class SocketGuard {
    int fd_;
public:
    explicit SocketGuard(int fd) : fd_(fd) {}
    ~SocketGuard() {
        if (fd_ >= 0) {
            close(fd_);
        }
    }

    // 禁止拷贝
    SocketGuard(const SocketGuard&) = delete;
    SocketGuard& operator=(const SocketGuard&) = delete;

    // 支持移动
    SocketGuard(SocketGuard&& other) noexcept : fd_(other.fd_) {
        other.fd_ = -1;
    }
    SocketGuard& operator=(SocketGuard&& other) noexcept {
        if (this != &other) {
            if (fd_ >= 0) {
                close(fd_);
            }
            fd_ = other.fd_;
            other.fd_ = -1;
        }
        return *this;
    }

    int get() const noexcept { return fd_; }
};

// 可共享资源：实现深拷贝
class Buffer {
    std::unique_ptr<char[]> data_;
    size_t size_;
public:
    Buffer(size_t size)
        : data_(std::make_unique<char[]>(size))
        , size_(size) {}

    // 深拷贝：新对象拥有独立的内存副本
    Buffer(const Buffer& other)
        : data_(std::make_unique<char[]>(other.size_))
        , size_(other.size_) {
        std::copy(other.data_.get(),
                  other.data_.get() + size_,
                  data_.get());
    }

    Buffer& operator=(const Buffer& other) {
        if (this != &other) {
            auto newData = std::make_unique<char[]>(other.size_);
            std::copy(other.data_.get(),
                      other.data_.get() + other.size_,
                      newData.get());
            data_ = std::move(newData);
            size_ = other.size_;
        }
        return *this;
    }

    Buffer(Buffer&&) noexcept = default;
    Buffer& operator=(Buffer&&) noexcept = default;

    char* data() noexcept { return data_.get(); }
    const char* data() const noexcept { return data_.get(); }
    size_t size() const noexcept { return size_; }
};

// 互斥锁：语义上不可拷贝
class ThreadSafeValue {
    std::mutex mutex_;
    int value_ = 0;
public:
    ThreadSafeValue() = default;

    // 互斥锁不可拷贝，因此包含它的类也必须禁止拷贝
    ThreadSafeValue(const ThreadSafeValue&) = delete;
    ThreadSafeValue& operator=(const ThreadSafeValue&) = delete;

    // 移动：需要特别处理——移动时不能拷贝 mutex
    ThreadSafeValue(ThreadSafeValue&& other) noexcept
        : value_(other.value_) {
        // mutex_ 默认构造，不拷贝自 other
    }

    int get() const {
        // 注意：const 方法中需要 mutable mutex
        return value_;
    }
};

// 使用 shared_ptr 实现引用计数共享
class SharedResource {
    struct Impl {
        int data;
        explicit Impl(int d) : data(d) {}
    };
    std::shared_ptr<Impl> impl_;
public:
    explicit SharedResource(int value)
        : impl_(std::make_shared<Impl>(value)) {}

    // 默认拷贝使用 shared_ptr 的引用计数——正确
    SharedResource(const SharedResource&) = default;
    SharedResource& operator=(const SharedResource&) = default;

    int getData() const { return impl_->data; }
    int useCount() const { return static_cast<int>(impl_.use_count()); }
};
```

## 错误示例
```cpp
#include <cstdio>
#include <cstring>

// 管理资源的类未定义拷贝语义——依赖编译器生成（违规）
class BadFileWrapper {
    FILE* fp_;
public:
    explicit BadFileWrapper(const char* path) {
        fp_ = std::fopen(path, "w");
    }
    ~BadFileWrapper() {
        if (fp_) {
            std::fclose(fp_);
        }
    }

    // 未定义拷贝构造和拷贝赋值！
    // 编译器生成的默认版本会逐成员拷贝 fp_
    // 导致两个对象持有同一个 FILE*——double free!
};

void doubleFreeBug() {
    BadFileWrapper f1("test.txt");
    BadFileWrapper f2 = f1;  // 浅拷贝！f1.fp_ == f2.fp_
}  // f2 析构 → fclose(fp_); f1 析构 → fclose(fp_) again → 未定义行为！

// 管理资源的类定义了拷贝但实现错误——违规
class BrokenBuffer {
    char* data_;
    size_t size_;
public:
    explicit BrokenBuffer(size_t sz)
        : data_(new char[sz]), size_(sz) {}
    ~BrokenBuffer() { delete[] data_; }

    // 拷贝构造函数：浅拷贝指针——错误！
    BrokenBuffer(const BrokenBuffer& other)
        : data_(other.data_)   // 两个对象指向同一内存！
        , size_(other.size_) {}

    // 拷贝赋值：先 delete 再浅拷贝——更糟！
    BrokenBuffer& operator=(const BrokenBuffer& other) {
        if (this != &other) {
            delete[] data_;         // 如果 other 就是 *this，灾难
            data_ = other.data_;    // 仍然浅拷贝
            size_ = other.size_;
        }
        return *this;
    }
};

// 仅用注释说明不可拷贝——不足以防止误用
class CommentOnlyNonCopyable {
    int* ptr_;
public:
    // 注意：此类不可拷贝
    explicit CommentOnlyNonCopyable(int val) : ptr_(new int(val)) {}
    ~CommentOnlyNonCopyable() { delete ptr_; }
    // 没有 = delete——编译器仍然生成默认拷贝操作！
};
```

## 检查方法
由 LLM 进行审查：
1. 检测管理裸资源（指针、文件句柄、socket 等）的类是否显式处理了拷贝操作
2. 若类有自定义析构函数但无自定义拷贝/移动操作 → 违反"五法则" → 标记
3. 检测拷贝构造函数是否执行深拷贝（为新对象分配独立资源）
4. 检测 `= delete` 是否用于禁止拷贝的独占资源类
5. 检测拷贝赋值运算符是否处理自赋值（`if (this != &other)`）以及异常安全

## 修复指南
1. **禁止拷贝**：对于独占资源类，添加 `= delete` 同时提供移动构造函数
2. **深拷贝**：对于值语义类，实现深拷贝确保两个对象拥有独立资源
3. **引用计数**：对于可共享资源，使用 `std::shared_ptr` 实现共享所有权
4. **五法则**：如果定义（或删除）了析构函数、拷贝构造、拷贝赋值、移动构造、移动赋值中的任一个，通常需要定义或删除全部五个
5. **自赋值安全**：拷贝赋值运算符必须能正确处理 `*this == other` 的情况

## 审查清单
- [ ] 管理独占资源的类已禁止拷贝（`= delete`）
- [ ] 支持拷贝的资源类已正确实现深拷贝
- [ ] 拷贝赋值运算符可安全处理自赋值
- [ ] 拷贝赋值运算符提供强异常安全保证（或至少基本保证）
- [ ] 遵守五法则：特殊成员函数全定义或全删除
- [ ] 无编译器生成的拷贝操作用于管理资源的类

## 关联页面
- [[cpp-raii-principle]] — RAII 原则
- [[cpp-raii-ctor-dtor]] — RAII 构造/析构实现
- [[cpp-raii-std-wrappers]] — 标准库 RAII 包装器
