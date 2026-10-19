---
domain: cpp
rule_id: cpp-raii-std-wrappers
title: 标准库 RAII 包装器
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
  - [[cpp-raii-copy-semantics]]
---

# 标准库 RAII 包装器

## 规则条款
在管理资源时，优先使用 C++ 标准库提供的 RAII 包装器，而不是手写资源管理类。标准库包装器
经过广泛测试、优化良好、语义清晰，并且与语言和库生态系统无缝集成。

常用标准库 RAII 包装器：
| 资源类型           | 标准库包装器                              |
|-------------------|------------------------------------------|
| 动态内存（独占）    | `std::unique_ptr<T>`                     |
| 动态内存（共享）    | `std::shared_ptr<T>`                     |
| 动态内存（弱引用）  | `std::weak_ptr<T>`                       |
| 互斥锁（简单）      | `std::lock_guard<std::mutex>`            |
| 互斥锁（灵活）      | `std::unique_lock<std::mutex>`           |
| 多互斥锁           | `std::scoped_lock<Mutexes...>`           |
| 文件 I/O           | `std::fstream` / `std::ifstream` / `std::ofstream` |
| 动态数组           | `std::vector<T>`                         |
| 字符串             | `std::string`                            |
| 共享锁             | `std::shared_lock<std::shared_mutex>`    |
| 条件变量等待       | `std::condition_variable` + `std::unique_lock` |
| 一次性执行         | `std::call_once` + `std::once_flag`      |

## 正确示例
```cpp
#include <memory>
#include <mutex>
#include <shared_mutex>
#include <fstream>
#include <vector>
#include <string>
#include <iostream>

// 独占所有权：unique_ptr
class DataManager {
    std::unique_ptr<Database> db_;
public:
    explicit DataManager(const std::string& connStr)
        : db_(std::make_unique<Database>(connStr)) {}

    // 转移所有权
    std::unique_ptr<Database> releaseDb() {
        return std::move(db_);
    }

    Database* get() const { return db_.get(); }
};

// 共享所有权：shared_ptr / weak_ptr
class Cache {
    std::shared_ptr<Config> config_;
    std::weak_ptr<Logger> logger_;  // 弱引用，避免循环
public:
    explicit Cache(std::shared_ptr<Config> cfg,
                   std::shared_ptr<Logger> log)
        : config_(std::move(cfg))
        , logger_(log) {}

    void write(const std::string& msg) {
        if (auto log = logger_.lock()) {  // 升级为 shared_ptr
            log->info(msg);
        }
    }
};

// 互斥锁 RAII
class ThreadSafeMap {
    mutable std::shared_mutex mutex_;
    std::map<std::string, int> data_;
public:
    void set(const std::string& key, int value) {
        std::unique_lock lock(mutex_);  // 独占锁
        data_[key] = value;
    }

    int get(const std::string& key) const {
        std::shared_lock lock(mutex_);  // 共享锁，多读并发
        auto it = data_.find(key);
        return (it != data_.end()) ? it->second : 0;
    }
};

// 多锁同时获取，避免死锁
class AccountTransfer {
    std::mutex fromMutex_;
    std::mutex toMutex_;
    int fromBalance_ = 0;
    int toBalance_ = 0;
public:
    void transfer(int amount) {
        // scoped_lock 原子性地获取多个锁，防止死锁
        std::scoped_lock lock(fromMutex_, toMutex_);
        fromBalance_ -= amount;
        toBalance_   += amount;
    }
};

// 文件 RAII
std::vector<std::string> readLines(const std::string& path) {
    std::ifstream file(path);
    if (!file.is_open()) {
        throw std::runtime_error("Cannot open: " + path);
    }
    std::vector<std::string> lines;
    std::string line;
    while (std::getline(file, line)) {
        lines.push_back(std::move(line));
    }
    return lines;  // file 自动关闭
}

// unique_ptr 自定义删除器（用于 C 库资源）
struct FreeDeleter {
    void operator()(void* p) const noexcept {
        std::free(p);
    }
};

void useCLibrary() {
    // 使用 unique_ptr + 自定义删除器包装 C 库资源
    std::unique_ptr<char, FreeDeleter> buffer(
        static_cast<char*>(std::malloc(1024)));
    // buffer 析构时自动调用 std::free
}

// FILE* 也可以这样包装
struct FileCloser {
    void operator()(std::FILE* fp) const noexcept {
        if (fp) {
            std::fclose(fp);
        }
    }
};

std::string readWithUniquePtr(const char* path) {
    std::unique_ptr<std::FILE, FileCloser> fp(std::fopen(path, "r"));
    if (!fp) {
        throw std::runtime_error("Cannot open file");
    }
    char buffer[256];
    std::string result;
    while (std::fgets(buffer, sizeof(buffer), fp.get())) {
        result += buffer;
    }
    return result;
}
```

## 错误示例
```cpp
#include <cstdlib>
#include <cstdio>
#include <mutex>
#include <string>
#include <vector>

// 手写资源管理替代标准库包装器——违规
template<typename T>
class MyUniquePtr {  // 完全不需要——标准库已有 std::unique_ptr
    T* ptr_;
public:
    explicit MyUniquePtr(T* p) : ptr_(p) {}
    ~MyUniquePtr() { delete ptr_; }
    T* get() const { return ptr_; }
    T* release() { T* p = ptr_; ptr_ = nullptr; return p; }
    // ... 缺少移动语义、缺少数组特化、缺少自定义删除器 ...
};

// 手动加锁/解锁替代 std::lock_guard——违规
class ManualLocking {
    std::mutex mtx_;
    int data_ = 0;
public:
    void update() {
        mtx_.lock();          // 应使用 std::lock_guard
        data_ += 1;
        // 可能提前返回的路径...
        mtx_.unlock();
    }

    int read() {
        mtx_.lock();          // 应使用 std::lock_guard
        int result = data_;
        mtx_.unlock();
        return result;
    }
};

// 裸 new/delete 替代 unique_ptr / shared_ptr——违规
class WidgetFactory {
public:
    Widget* create() {
        return new Widget();  // 应返回 std::unique_ptr<Widget>
    }

    void destroy(Widget* w) {
        delete w;             // 应让 unique_ptr 析构处理
    }
};

// 手动管理动态数组替代 std::vector——违规
class IntList {
    int* data_;
    size_t size_;
    size_t capacity_;
public:
    IntList() : data_(new int[16]), size_(0), capacity_(16) {}
    ~IntList() { delete[] data_; }

    void push_back(int value) {
        if (size_ >= capacity_) {
            // 手写扩容逻辑——完全可以用 std::vector
            size_t newCap = capacity_ * 2;
            int* newData = new int[newCap];
            for (size_t i = 0; i < size_; ++i) {
                newData[i] = data_[i];
            }
            delete[] data_;
            data_ = newData;
            capacity_ = newCap;
        }
        data_[size_++] = value;
    }
    // 缺少拷贝/移动语义、迭代器、erase、reserve...
};

// 用 C FILE* 替代 fstream——违规
std::string readFile(const std::string& path) {
    FILE* fp = std::fopen(path.c_str(), "r");
    if (!fp) return {};
    char buf[1024];
    std::string result;
    while (std::fgets(buf, sizeof(buf), fp)) {
        result += buf;
    }
    std::fclose(fp);
    return result;
}
```

## 检查方法
由 LLM 进行审查：
1. 检测手写资源管理类，与标准库同类功能对比（如自定义 smart pointer vs `std::unique_ptr`）
2. 检测手动 `lock()`/`unlock()` vs `std::lock_guard`/`std::unique_lock`/`std::scoped_lock`
3. 检测 C 风格文件 API vs `std::fstream`
4. 检测手动动态数组管理 vs `std::vector`
5. 检测 `new`/`delete` vs `std::make_unique`/`std::make_shared`
6. 识别手写的 RAII 包装器，评估是否有标准库替代方案

只有在标准库包装器无法满足特殊需求时（如需要特定平台的资源句柄语义），手写 RAII 包装器才被接受。

## 修复指南
1. **动态内存**：`new`/`delete` → `std::make_unique<T>()` 或 `std::make_shared<T>()`
2. **动态数组**：手写的 `new[]`/`delete[]` + 扩容逻辑 → `std::vector<T>`
3. **互斥锁**：`mtx.lock()`/`mtx.unlock()` → `std::lock_guard`（简单场景）或 `std::unique_lock`（需要延迟锁定/提前解锁）
4. **多锁**：多个 `lock()` 调用 → `std::scoped_lock`（原子锁定避免死锁）
5. **文件 I/O**：`fopen`/`fclose`/`fread`/`fwrite` → `std::ifstream`/`std::ofstream`/`std::fstream`
6. **C 库资源**：如无法使用标准库替代，使用 `std::unique_ptr` + 自定义删除器包装

## 审查清单
- [ ] 动态内存管理使用 `std::unique_ptr`/`std::shared_ptr`，无裸 `new`/`delete`
- [ ] 动态数组使用 `std::vector`，无手写扩容逻辑
- [ ] 互斥锁使用 `std::lock_guard`/`std::unique_lock`/`std::scoped_lock`
- [ ] 文件操作使用 `std::fstream`，无 C FILE* API
- [ ] 无不必要的标准库 RAII 包装器的手写仿制品
- [ ] C 库资源通过 `std::unique_ptr` + 自定义删除器安全包装
- [ ] 字符串使用 `std::string`，无手动字符数组管理

## 关联页面
- [[cpp-raii-principle]] — RAII 原则
- [[cpp-raii-ctor-dtor]] — RAII 构造/析构实现
- [[cpp-raii-copy-semantics]] — RAII 拷贝语义
