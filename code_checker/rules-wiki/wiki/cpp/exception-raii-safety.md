---
domain: cpp
rule_id: cpp-exception-raii-safety
title: 异常安全的 RAII
priority: main
source_file: rules/C++代码规范.md
source_section: "§4.2 异常安全"
status: active
check_method: llm
deterministic_check: false
checkability: llm_checkable
conflicts_with: []
overrides: []
related_pages:
  - [[cpp-exception-safety-guarantees]]
  - [[cpp-exception-prefer-strong]]
---

# 异常安全的 RAII

## 规则条款
使用 RAII（Resource Acquisition Is Initialization）确保资源泄漏安全：即使在发生异常时，所有资源（内存、文件句柄、锁、套接字等）都必须被正确释放。资源的管理生命周期应绑定到对象的生命周期，由构造函数获取资源，析构函数释放资源。C++ 的栈展开机制会确保在异常发生时，所有局部对象的析构函数被自动调用。

## 正确示例
```cpp
// 文件资源：RAII 包装
class FileGuard {
public:
    explicit FileGuard(const char* path, const char* mode)
        : m_file(std::fopen(path, mode)) {
        if (!m_file) {
            throw std::runtime_error("Failed to open file");
        }
    }

    ~FileGuard() {
        if (m_file) {
            std::fclose(m_file);
        }
    }

    FileGuard(const FileGuard&) = delete;
    FileGuard& operator=(const FileGuard&) = delete;

    FileGuard(FileGuard&& other) noexcept
        : m_file(other.m_file) {
        other.m_file = nullptr;
    }

    std::FILE* get() const noexcept { return m_file; }

private:
    std::FILE* m_file = nullptr;
};

// 使用 RAII — 异常安全
void processFile(const std::string& path) {
    FileGuard file(path.c_str(), "r");   // 资源获取即初始化
    auto header = readHeader(file.get()); // 可能抛异常
    auto body = readBody(file.get());     // 可能抛异常
    // 即使抛异常，file 析构函数自动关闭文件
}

// 互斥锁：RAII 包装
void threadSafeUpdate(SharedData& data, const Update& update) {
    std::lock_guard<std::mutex> lock(data.mutex);  // 获取锁
    data.apply(update);                             // 可能抛异常
    // 即使抛异常，lock_guard 析构自动释放锁
}

// 智能指针：RAII 管理内存
std::unique_ptr<Widget> createWidget(const Config& cfg) {
    auto w = std::make_unique<Widget>(cfg);  // 即使后续抛异常，w 被自动释放
    w->initialize();                          // 可能抛异常
    return w;                                 // 转移所有权，无泄漏
}
```

## 错误示例
```cpp
// 裸资源管理：抛异常导致文件泄漏
void badProcessFile(const char* path) {
    FILE* f = std::fopen(path, "r");
    if (!f) return;
    auto data = parseData(f);     // 抛异常 → f 永远不被 fclose
    processData(data);
    std::fclose(f);               // 永远执行不到
}

// 裸锁管理：抛异常导致死锁
void badThreadSafeUpdate(SharedData& data, const Update& update) {
    data.mutex.lock();            // 手动加锁
    data.apply(update);           // 抛异常 → 锁永远不释放
    data.mutex.unlock();          // 永远执行不到
}

// 裸指针管理：抛异常导致内存泄漏
Widget* badCreateWidget(const Config& cfg) {
    Widget* w = new Widget(cfg);  // 裸 new
    w->initialize();              // 抛异常 → w 泄漏
    return w;
}

// 两个资源，第二个获取失败时第一个泄漏
void badTwoResources() {
    auto* a = new ResourceA();    // 获取资源 A
    auto* b = new ResourceB();    // 抛异常 → 资源 A 泄漏
    // ...
    delete a;
    delete b;
}
```

## 检查方法
1. 扫描代码中的裸 `new`、裸 `delete`、`malloc`/`free`、`fopen`/`fclose`——这些是 RAII 违规的典型标志。
2. 检查锁操作是否使用 `std::lock_guard`、`std::unique_lock` 或 `std::scoped_lock` 等 RAII 包装器。
3. 审查可能在堆资源分配和使用之间抛出异常的函数调用路径。
4. 用 LLM 分析函数：是否存在"获取资源 A → 获取资源 B → ..."的链式获取，中间任一失败导致前面资源泄漏。

## 修复指南
- **内存**：用 `std::unique_ptr`/`std::shared_ptr` 替代裸 `new`/`delete`；用 `std::make_unique`/`std::make_shared` 直接构造。
- **文件**：用 `std::fstream`（自动关闭）或自定义 RAII 包装类替代 C 风格 `FILE*`。
- **锁**：用 `std::lock_guard`/`std::scoped_lock` 替代手动 `lock()`/`unlock()`。
- **其他资源**：对套接字、数据库连接、OS 句柄等，编写专用 RAII 包装类。
- **多资源获取**：在单个表达式内获取所有资源（利用求值顺序），或先获取再逐一用 RAII 接管。

## 审查清单
- [ ] 代码中是否没有裸 `new` 和裸 `delete`？
- [ ] 文件操作是否使用 `std::fstream` 或 RAII 包装类？
- [ ] 互斥锁是否使用 `std::lock_guard` 或 `std::scoped_lock`？
- [ ] 是否存在 C 风格资源管理（`malloc`/`free`、`fopen`/`fclose`）？
- [ ] 多资源获取路径上是否存在中间失败导致前序资源泄漏的风险？
- [ ] 自定义 RAII 类的析构函数是否标记为 `noexcept`？

## 关联页面
- [[cpp-exception-safety-guarantees]] — 异常安全保证等级的完整定义
- [[cpp-exception-prefer-strong]] — 异常安全保证的优先级选择
