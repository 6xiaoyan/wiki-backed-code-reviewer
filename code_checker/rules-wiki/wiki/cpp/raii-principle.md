---
domain: cpp
rule_id: cpp-raii-principle
title: RAII 原则
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
  - [[cpp-raii-ctor-dtor]]
  - [[cpp-raii-copy-semantics]]
  - [[cpp-raii-std-wrappers]]
---

# RAII 原则

## 规则条款
所有资源管理必须基于 RAII（Resource Acquisition Is Initialization）原则。即：资源的生命周期
必须绑定到某个对象的生命周期——资源在对象构造时获取，在对象析构时自动释放。禁止手动调用
资源获取/释放函数（如 `malloc`/`free`、`open`/`close`、`lock`/`unlock`），除非是在 RAII
包装器的实现内部。

RAII 是 C++ 最核心的资源管理范式，它保证了：
- **异常安全**：即使发生异常，栈展开也会调用析构函数释放资源
- **无资源泄漏**：资源生命周期由编译器自动管理
- **代码简洁**：无需手动编写清理代码

## 正确示例
```cpp
#include <fstream>
#include <memory>
#include <mutex>
#include <string>
#include <vector>

// 文件资源由 fstream 对象管理——自动关闭
void readConfig(const std::string& path) {
    std::ifstream file(path);
    if (!file.is_open()) {
        throw std::runtime_error("Cannot open config file");
    }
    std::string line;
    while (std::getline(file, line)) {
        processLine(line);
    }
    // 无需手动 file.close()——析构函数自动处理
}

// 动态内存由 unique_ptr 管理——自动释放
std::unique_ptr<Database> createDatabase(const std::string& connStr) {
    auto db = std::make_unique<Database>(connStr);
    db->initialize();
    return db;  // 所有权转移，无泄漏风险
}

// 互斥锁由 lock_guard 管理——自动解锁
class ThreadSafeCounter {
    std::mutex mutex_;
    int value_ = 0;
public:
    int increment() {
        std::lock_guard<std::mutex> lock(mutex_);
        return ++value_;
        // lock 析构时自动 unlock，即使 ++value_ 抛出异常
    }
};

// 自定义 RAII 包装器
class SocketGuard {
    int socketFd_;
public:
    explicit SocketGuard(int fd) : socketFd_(fd) {}
    ~SocketGuard() {
        if (socketFd_ >= 0) {
            close(socketFd_);
        }
    }
    SocketGuard(const SocketGuard&) = delete;
    SocketGuard& operator=(const SocketGuard&) = delete;
    SocketGuard(SocketGuard&& other) noexcept
        : socketFd_(other.socketFd_) {
        other.socketFd_ = -1;
    }
    int get() const { return socketFd_; }
};
```

## 错误示例
```cpp
#include <cstdio>
#include <mutex>
#include <string>

// 手动管理文件资源——违规
std::string readFileRaw(const char* path) {
    FILE* fp = fopen(path, "r");
    if (!fp) {
        return {};
    }
    char buffer[256];
    std::string result;
    while (fgets(buffer, sizeof(buffer), fp)) {
        result += buffer;
        if (someCondition(buffer)) {
            return result;  // 泄漏！提前返回未关闭 fp
        }
    }
    fclose(fp);  // 仅在正常路径关闭——异常路径泄漏
    return result;
}

// 手动管理动态内存——违规
void processData(int size) {
    int* data = new int[size];
    fillData(data, size);
    if (data[0] < 0) {
        return;  // 内存泄漏！data 未释放
    }
    computeResult(data, size);
    delete[] data;  // 仅在正常路径释放
}

// 手动加锁/解锁——违规
class UnsafeCounter {
    std::mutex mtx_;
    int value_ = 0;
public:
    int increment() {
        mtx_.lock();
        int result = ++value_;
        mtx_.unlock();  // 如果 ++value_ 抛出（虽然 int 不会），锁永不释放
        return result;
    }
};

// 混合使用 new 和智能指针——违规
void mixedOwnership() {
    auto ptr = std::unique_ptr<Widget>(new Widget());  // 应使用 make_unique
    Widget* raw = new Widget();
    // ... 多个退出路径容易遗漏 delete raw
    delete raw;
}
```

## 检查方法
由 LLM 进行语义级审查：
1. 检测裸 `new` 和 `delete`——应替换为 `std::make_unique`/`std::make_shared`
2. 检测裸 `malloc`/`free`——应替换为 `std::vector` 或智能指针
3. 检测手动 `lock()`/`unlock()` 调用——应替换为 `std::lock_guard`/`std::unique_lock`
4. 检测 C 风格文件 API（`fopen`/`fclose`）——应替换为 `std::fstream`
5. 检测其他成对出现的资源获取/释放函数（如 POSIX `open`/`close`、`socket`/`close`）

## 修复指南
1. **裸指针**：`new` + `delete` → `std::make_unique<T>()` 或 `std::make_shared<T>()`
2. **C 文件操作**：`fopen`/`fclose` → `std::ifstream`/`std::ofstream`/`std::fstream`
3. **互斥锁**：`lock()`/`unlock()` → `std::lock_guard`、`std::unique_lock` 或 `std::scoped_lock`
4. **自定义资源**：编写 RAII 包装类，构造函数获取资源，析构函数释放资源
5. **POSIX 资源**：使用 RAII 包装器或标准库替代方案

## 审查清单
- [ ] 无裸 `new`/`delete` 出现在 RAII 包装器外部
- [ ] 无裸 `malloc`/`free` 调用
- [ ] 无手动 `lock()`/`unlock()` 调用
- [ ] C 风格文件 API 已替换为 `std::fstream`
- [ ] 所有自定义资源有对应的 RAII 包装类
- [ ] 异常安全：所有执行路径上资源均能正确释放

## 关联页面
- [[cpp-raii-ctor-dtor]] — RAII 构造/析构实现
- [[cpp-raii-copy-semantics]] — RAII 拷贝语义
- [[cpp-raii-std-wrappers]] — 标准库 RAII 包装器
