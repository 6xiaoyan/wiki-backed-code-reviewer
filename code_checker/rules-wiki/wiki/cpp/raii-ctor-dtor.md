---
domain: cpp
rule_id: cpp-raii-ctor-dtor
title: RAII 构造/析构实现
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
  - [[cpp-raii-copy-semantics]]
  - [[cpp-raii-std-wrappers]]
---

# RAII 构造/析构实现

## 规则条款
自定义 RAII 类必须将资源获取操作放在构造函数中完成，将资源释放操作放在析构函数中完成。
构造函数应完成资源的完整初始化，使对象在构造完成后即处于可用状态；析构函数必须是无异常
抛出的（隐式 `noexcept`），并且不得执行可能失败的复杂操作。

构造函数中获取资源失败时，应通过抛出异常来报告；析构函数中释放资源失败时，应吞下错误
并记录日志，因为析构函数本身不应抛出异常。

## 正确示例
```cpp
#include <memory>
#include <string>
#include <stdexcept>

// 文件句柄 RAII 包装器
class FileHandle {
    FILE* fp_;
public:
    // 构造函数：获取资源
    explicit FileHandle(const std::string& path, const char* mode) {
        fp_ = std::fopen(path.c_str(), mode);
        if (!fp_) {
            throw std::runtime_error("Failed to open file: " + path);
        }
    }

    // 析构函数：释放资源，不抛出异常
    ~FileHandle() {
        if (fp_) {
            std::fclose(fp_);  // fclose 不会抛出异常
        }
    }

    // 禁止拷贝
    FileHandle(const FileHandle&) = delete;
    FileHandle& operator=(const FileHandle&) = delete;

    // 支持移动
    FileHandle(FileHandle&& other) noexcept : fp_(other.fp_) {
        other.fp_ = nullptr;
    }
    FileHandle& operator=(FileHandle&& other) noexcept {
        if (this != &other) {
            if (fp_) {
                std::fclose(fp_);
            }
            fp_ = other.fp_;
            other.fp_ = nullptr;
        }
        return *this;
    }

    FILE* get() const noexcept { return fp_; }
};

// 数据库连接 RAII 包装器
class DbConnection {
    db_handle* handle_;
public:
    explicit DbConnection(const std::string& connectionString)
        : handle_(nullptr) {
        int rc = db_connect(connectionString.c_str(), &handle_);
        if (rc != DB_OK || !handle_) {
            throw std::runtime_error("Database connection failed: "
                                     + std::to_string(rc));
        }
    }

    ~DbConnection() {
        try {
            if (handle_) {
                db_disconnect(handle_);  // 假设可能因网络问题失败
            }
        } catch (...) {
            // 析构函数吞下所有异常；记录到日志
            logError("Failed to disconnect database cleanly");
        }
    }

    DbConnection(const DbConnection&) = delete;
    DbConnection& operator=(const DbConnection&) = delete;
    DbConnection(DbConnection&& other) noexcept
        : handle_(other.handle_) {
        other.handle_ = nullptr;
    }
    DbConnection& operator=(DbConnection&& other) noexcept {
        if (this != &other) {
            if (handle_) {
                db_disconnect(handle_);
            }
            handle_ = other.handle_;
            other.handle_ = nullptr;
        }
        return *this;
    }
};

// 两阶段初始化是 RAII 的反模式
// 正确做法：构造函数中完成所有初始化
class NetworkClient {
    Socket socket_;
    bool connected_;
public:
    explicit NetworkClient(const std::string& host, int port)
        : socket_()
        , connected_(false) {
        socket_.connect(host, port);
        connected_ = true;
        // 构造完成后对象立即处于可用状态
    }

    ~NetworkClient() {
        if (connected_) {
            socket_.disconnect();
        }
    }

    bool isConnected() const noexcept { return connected_; }
    void send(const std::string& data) {
        if (!connected_) {
            throw std::runtime_error("Not connected");
        }
        socket_.write(data);
    }
};
```

## 错误示例
```cpp
#include <string>
#include <cstdio>

// 两阶段初始化：构造后需要再调用 init()——反模式
class BadFileHandler {
    FILE* fp_;
public:
    BadFileHandler() : fp_(nullptr) {}  // 构造时未获取资源！

    bool open(const std::string& path) {  // 资源获取延迟到 init 方法
        fp_ = std::fopen(path.c_str(), "r");
        return fp_ != nullptr;
    }

    ~BadFileHandler() {
        if (fp_) {
            std::fclose(fp_);
        }
    }

    // 用户可能忘记调用 open()，导致对象处于半初始化状态
};

// 使用示例——易出错
void processFile() {
    BadFileHandler handler;
    // 忘记调用 handler.open()？对象语义不完整
    if (handler.open("data.txt")) {  // 每次使用前需检查
        // ... 使用 handler ...
    }
    // 如果 open 失败，handler 仍然被析构（无资源泄漏），但语义混乱
}

// 析构函数中执行可能抛出异常的操作——违规
class BadDatabaseHandle {
    db_conn* conn_;
public:
    BadDatabaseHandle(db_conn* c) : conn_(c) {}

    ~BadDatabaseHandle() {
        db_disconnect(conn_);  // 如果抛出异常 → std::terminate！
    }
};

// 构造失败时不抛出异常，而是设置错误状态——反模式
class ConfigLoader {
    bool valid_;
public:
    ConfigLoader(const std::string& path) : valid_(false) {
        // 加载失败仅设置标志，不抛出异常
        auto data = readFile(path);
        if (data.empty()) {
            return;  // 对象处于无效状态
        }
        parse(data);
        valid_ = true;
    }

    bool isValid() const { return valid_; }
    // 调用者每次使用都必须检查 isValid()——容易遗漏
};
```

## 检查方法
由 LLM 进行审查：
1. 检测类是否具有 `init()`/`open()`/`start()`/`connect()` 等两阶段初始化方法——标记为反模式
2. 检测析构函数中是否包含 `throw` 语句或调用可能抛出的函数而未包裹 try-catch
3. 检测构造函数是否仅做字段赋值而未完成资源获取
4. 检测类是否提供 `isValid()`/`isOpen()` 等状态查询方法——可能暗示两阶段初始化
5. 确认移动构造函数/赋值运算符正确转移资源所有权（将源对象置为"空"状态）

## 修复指南
1. **消除两阶段初始化**：将 `init()` 方法的内容移入构造函数，确保构造完成后对象即处于可用状态
2. **构造失败用异常**：构造函数中资源获取失败时抛出异常，而非设置错误标志
3. **析构安全**：析构函数中仅执行不会失败的操作；如确有失败可能，用 try-catch 包裹并记录日志
4. **移动语义**：实现移动构造/赋值以支持值语义和容器存储
5. **五法则**：如自定义了析构函数，通常也需要自定义或删除拷贝/移动操作

## 审查清单
- [ ] 构造函数中完成所有资源获取操作
- [ ] 无两阶段初始化模式（无 init/open/start 等延迟初始化方法）
- [ ] 析构函数中释放所有资源
- [ ] 析构函数不抛出异常（隐式 noexcept）
- [ ] 移动操作正确转移所有权并将源对象置空
- [ ] 构造失败通过异常报告，而非错误标志

## 关联页面
- [[cpp-raii-principle]] — RAII 原则
- [[cpp-raii-copy-semantics]] — RAII 拷贝语义
- [[cpp-raii-std-wrappers]] — 标准库 RAII 包装器
