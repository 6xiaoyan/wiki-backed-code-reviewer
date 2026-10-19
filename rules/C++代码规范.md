# C++代码规范

# 引言

制定以下代码开发规范，以最小规范为主，考虑到开发人员较少，先执行基础的代码规范，注意**基础规范、现代C++特性、内存问题**即可。更加详细的C++代码开发可以参考谷歌代码规范和腾讯C/C++代码开发规范：

[C++ 风格指南 - 内容目录 — Google 开源项目风格指南](https://zh-google-styleguide.readthedocs.io/en/latest/google-cpp-styleguide/contents.html)

[secguide/C,C++安全指南.md at main · Tencent/secguide](https://github.com/Tencent/secguide/blob/main/C,C++%E5%AE%89%E5%85%A8%E6%8C%87%E5%8D%97.md)



## 1. 基础规范

### 1.1 命名约定

**规则**：

*   **类/结构体/枚举：使用 PascalCase，****首字母大写，后续每个单词的首字母也大写，无空格或符号分隔（如** `**UserInfo**`**、**`**OrderStatus**`**），****清晰表达用途；**
    
*   **函数/方法：使用 camelCase，动词开头，****首字母小写，后续每个单词的首字母大写，无空格或符号分隔（如** `**getUser**`**、**`**calculateTotal**`**）****；**
    
    *   示例 1（获取数据）：`getUserList`（获取用户列表）、`fetchOrderDetail`（获取订单详情）。
        
    *   示例 2（操作数据）：`updatePassword`（更新密码）、`deleteInvalidFile`（删除无效文件）。
        
    *   示例 3（计算 / 处理）：`calculateDiscount`（计算折扣）、`formatDateTime`（格式化日期时间）
        
*   **变量：使用 camelCase，****用 “名词” 表示变量存储的 “事物”，用 “形容词” 表示变量的 “状态 / 属性”，避免无意义的名称****；**
    
    *   示例 1（名词类变量）：`userName`（存储用户名）、`orderId`（存储订单 ID）、`productPrice`（存储商品价格）。
        
    *   示例 2（形容词类变量）：`isValid`（存储 “是否有效” 的布尔值，`true` 为有效，`false` 为无效）、`hasStock`（存储 “是否有库存” 的布尔值）。
        
*   **常量：使用 UPPER\_CASE，下划线分隔，****所有字母大写，单词之间用下划线** `**_**` **分隔（如** `**MAX_SIZE**`**、**`**DEFAULT_TIMEOUT**`**）；**
    
    *   常量是程序运行中不会被修改的值（如配置参数、固定阈值），命名需体现其 “不可变” 的属性和具体含义。
        

*   示例 1（配置类常量）：`DB_CONNECTION_TIMEOUT`（数据库连接超时时间）、`API_BASE_URL`（接口请求的基础地址）。
    
*   示例 2（阈值类常量）：`MAX_UPLOAD_SIZE`（最大上传文件大小）、`MIN_PASSWORD_LENGTH`（密码最小长度）。
    

*   **私有成员：使用 m\_camelCase 前缀或 camelCase\_ 后缀**
    
    *   方式 1（m\_ 前缀）：`m_userAge`（类的私有变量，存储用户年龄）、`m_checkPermission`（类的私有方法，内部校验权限）。
        
    *   方式 2（\_ 后缀）：`userAge_`（与 `m_userAge` 含义相同，仅后缀风格不同）、`checkPermission_`（与 `m_checkPermission` 含义相同）。
        
    *   注意：同一项目中需统一选择一种风格（要么全用前缀，要么全用后缀），避免混合使用。
        
*   **命名空间：使用小写字母，点分隔符表示层级****命名空间用于 “划分代码模块”，避免不同模块的类 / 函数重名，用小写字母和点** `**.**` **体现层级关系（从大模块到小模块）。**
    

*   示例 1（业务模块）：`com.company.shop.user`（`com` 为顶级域名，`company` 为公司名，`shop` 为 “商城” 模块，`user` 为 “用户” 子模块）。
    
*   示例 2（功能模块）：`utils.date.format`（`utils` 为 “工具类” 模块，`date` 为 “日期” 子模块，`format` 为 “格式化” 相关功能）。
    

**理由**：

*   提高代码可读性和一致性
    
*   减少命名冲突
    
*   明确标识符的作用域和用途
    
*   符合现代C++社区的主流约定
    

**正确示例**：

```cpp
// 类名 - PascalCase
class DataProcessor {
public:
    // 方法名 - camelCase，动词开头
    void processData();
    
    // 公有成员变量 - camelCase
    size_t bufferSize;
    
private:
    // 私有成员变量 - 前缀或后缀
    std::string m_internalBuffer;
    size_t processingCount_;
};

// 常量 - UPPER_CASE
const int MAX_RETRY_COUNT = 5;
constexpr double PI = 3.1415926535;

// 命名空间
namespace company::project::module {
    // ...
}

```

**错误示例**：

```cpp
// 错误：混合命名风格
class data_processor {  // 应为 DataProcessor
public:
    void ProcessData();  // 应为 processData
    int m_publicVar;     // 公有成员不应有m_前缀
    
private:
    std::string buffer;  // 应明确标识为私有成员
};

// 错误：常量命名不规范
const int maxRetryCount = 5;  // 应为 MAX_RETRY_COUNT

```

**检查方法**：

*   代码审查检查命名一致性
    
*   静态分析工具（Clang-Tidy）检查命名规范
    
*   自动化脚本验证命名约定
    

### 1.2 头文件规范

**规则**：

*   include 顺序：系统头文件 → 第三方库头文件 → 项目头文件
    
*   每个头文件必须有唯一的保护宏，格式：PROJECT\_MODULE\_FILENAME\_H\_
    
*   优先使用前置声明而非#include
    
*   模板定义必须放在头文件中
    
*   内联函数定义放在头文件中，但需谨慎使用
    

**理由**：

*   避免循环包含和重复包含
    
*   减少编译依赖，加快编译速度
    
*   确保编译器的单向依赖原则
    
*   提高代码的可移植性
    

**正确示例**：

```cpp
// File: network/http_client.h
#ifndef PROJECT_NETWORK_HTTP_CLIENT_H_
#define PROJECT_NETWORK_HTTP_CLIENT_H_

// 系统头文件
#include <string>
#include <vector>
#include <memory>

// 第三方库头文件
#include <boost/asio.hpp>
#include <gtest/gtest_prod.h>

// 项目头文件
#include "network/base_connection.h"
#include "utils/logger.h"

// 前置声明
namespace database {
class ConnectionPool;
}

namespace network {

class HttpClient {
public:
    explicit HttpClient(database::ConnectionPool& pool);
    // ...
};

} // namespace network

#endif // PROJECT_NETWORK_HTTP_CLIENT_H_

```

**错误示例**：

```cpp
// 错误：混乱的include顺序
#include "utils/logger.h"  // 项目头文件应在最后
#include <vector>
#include <boost/asio.hpp>

// 错误：弱保护宏
#ifndef HTTP_CLIENT_H  // 可能冲突，应使用唯一命名
#define HTTP_CLIENT_H

// 错误：不必要的包含
#include "database/connection_pool.h"  // 使用前置声明即可

```

**检查方法**：

*   编译时检查头文件依赖
    
*   静态分析工具检查include顺序和重复包含
    
*   定期运行include-what-you-use工具
    

### 1.3 代码格式

**规则**：

*   使用4空格缩进，禁止使用制表符
    
*   大括号使用Allman风格（独占一行）
    
*   行宽限制为100字符
    
*   函数参数和模板参数列表适当换行对齐
    
*   运算符前后有空格，但指针/引用符号紧跟类型
    

**理由**：

*   统一的格式提高代码可读性
    
*   便于版本控制系统进行diff操作
    
*   符合现代C++社区的共识
    

**检查方法**：

*   使用clang-format自动化格式化
    
*   CI流水线中集成格式检查
    
*   代码审查检查格式一致性
    

## 2. 现代C++特性

### 2.1 智能指针使用规范

**规则**：

*   优先使用std::unique\_ptr管理独占所有权资源
    
*   std::shared\_ptr仅用于真正需要共享所有权的场景
    
*   std::weak\_ptr用于打破std::shared\_ptr的循环引用
    
*   始终使用std::make\_unique和std::make\_shared创建智能指针
    
*   禁止在接口中使用裸指针表示所有权
    

**理由**：

*   明确资源所有权语义，防止内存泄漏
    
*   unique\_ptr性能优于shared\_ptr（无原子引用计数开销）
    
*   make\_unique/make\_shared提供异常安全保证
    
*   避免悬空指针和双重删除问题
    

**正确示例**：

```cpp
class ResourceManager {
public:
    // 工厂方法返回unique_ptr明确所有权转移
    std::unique_ptr<Connection> createConnection(const std::string& url)
    {
        return std::make_unique<Connection>(url);
    }

    // 共享所有权场景使用shared_ptr
    std::shared_ptr<Cache> getGlobalCache()
    {
        static std::weak_ptr<Cache> weakCache;
        
        if (auto sharedCache = weakCache.lock()) {
            return sharedCache;
        }
        
        auto newCache = std::make_shared<Cache>();
        weakCache = newCache;
        return newCache;
    }
};

void processData()
{
    auto manager = std::make_unique<ResourceManager>();
    
    // 明确所有权转移
    auto connection = manager->createConnection("tcp://example.com");
    
    // 共享缓存
    auto cache = manager->getGlobalCache();
    
    // 明确的生命周期管理
    connection->sendData("hello");
}

```

**错误示例**：

```cpp
// 错误：不必要的shared_ptr使用
std::shared_ptr<Connection> createConnection(const std::string& url)
{
    return std::shared_ptr<Connection>(new Connection(url)); // 应使用make_shared
}

// 错误：裸指针所有权不明确
Connection* createConnectionRaw(const std::string& url)
{
    return new Connection(url); // 调用者可能忘记删除
}

// 错误：循环引用导致内存泄漏
class Node {
public:
    std::shared_ptr<Node> next; // 可能导致循环引用
};

void createCycle()
{
    auto node1 = std::make_shared<Node>();
    auto node2 = std::make_shared<Node>();
    node1->next = node2;
    node2->next = node1; // 循环引用，内存泄漏
}

```

**检查方法**：

*   静态分析工具检查裸new/delete操作
    
*   代码审查检查智能指针使用合理性
    
*   运行时检测循环引用和内存泄漏
    

### 2.2 移动语义规范

**规则**：

*   为资源管理类实现移动构造函数和移动赋值运算符
    
*   使用std::move明确标识可移动的左值
    
*   在适当场合使用完美转发(std::forward)
    
*   对不需要的资源使用std::move避免不必要的拷贝
    
*   移动后对象必须处于有效但未指定的状态
    

**理由**：

*   减少不必要的拷贝，提高性能
    
*   明确资源所有权转移语义
    
*   利用现代C++的高效资源管理
    

**正确示例**：

```cpp
class Buffer {
public:
    Buffer() = default;
    
    // 移动构造函数
    Buffer(Buffer&& other) noexcept
        : m_data(std::exchange(other.m_data, nullptr))
        , m_size(std::exchange(other.m_size, 0))
    {}
    
    // 移动赋值运算符
    Buffer& operator=(Buffer&& other) noexcept
    {
        if (this != &other) {

            delete[ ] m_data;

            m_data = std::exchange(other.m_data, nullptr);
            m_size = std::exchange(other.m_size, 0);
        }
        return *this;
    }
    
    // 禁用拷贝
    Buffer(const Buffer&) = delete;
    Buffer& operator=(const Buffer&) = delete;
    

    ~Buffer() { delete[ ] m_data; }

    
    // 工厂方法
    static Buffer createFilledBuffer(size_t size, char fillValue)
    {
        Buffer buffer;
        buffer.m_data = new char[size];
        buffer.m_size = size;
        std::fill_n(buffer.m_data, size, fillValue);
        return buffer; // NRVO或移动语义
    }
    
private:
    char* m_data = nullptr;
    size_t m_size = 0;
};

void processLargeData()
{
    // 移动构造避免拷贝
    auto buffer = Buffer::createFilledBuffer(1024, 'A');
    
    // 明确移动语义

    auto processBuffer = [ ](Buffer buf) {

        // 处理缓冲区
    };
    
    processBuffer(std::move(buffer)); // 明确所有权转移
    // buffer现在处于有效但未指定状态
}

```

**错误示例**：

```cpp
// 错误：缺失移动操作导致不必要的拷贝
class Buffer {
public:
    Buffer(const Buffer& other)  // 昂贵的拷贝
        : m_data(new char[other.m_size])
        , m_size(other.m_size)
    {
        std::copy(other.m_data, other.m_data + m_size, m_data);
    }
    // 缺失移动构造函数和移动赋值运算符
};

// 错误：不必要的std::move使用
std::string getName()
{
    std::string name = "example";
    return std::move(name); // 阻止NRVO，应直接return name;
}

// 错误：移动后继续使用对象
void process()
{
    std::vector<int> data = {1, 2, 3};
    auto stolenData = std::move(data);
    
    data.push_back(4); // 未定义行为，data处于有效但未指定状态
}

```

**检查方法**：

*   代码审查检查移动语义的正确实现
    
*   性能分析识别不必要的拷贝
    
*   静态分析检查移动后使用问题
    

### 2.3 Lambda表达式规范

**规则**：

*   优先使用lambda而非std::bind
    
*   明确指定捕获模式：\[=\], \[&\], \[this\], 或显式捕获列表
    
*   对于小函数和算法参数，使用lambda提高可读性
    
*   多行lambda使用显式返回类型
    
*   避免在频繁调用的代码路径中使用大型lambda
    

**理由**：

*   lambda提供更清晰的语法和更好的性能
    
*   明确的捕获模式避免意外的引用捕获
    
*   提高代码的局部性和可读性
    

**正确示例**：

```cpp
void processUsers(const std::vector<User>& users, 
                  const std::string& filterName)
{
    // 明确值捕获需要的变量
    auto filteredUsers = filterUsers(users, [filterName](const User& user) {
        return user.name == filterName;
    });
    
    // 复杂lambda使用显式返回类型和多行格式
    auto processedUsers = transformUsers(filteredUsers, 


        [ ](const User& user) -> ProcessedUser {


            ProcessedUser result;
            result.id = user.id;
            result.displayName = user.firstName + " " + user.lastName;
            result.score = calculateScore(user);
            return result;
        });
    
    // 引用捕获明确标识
    std::vector<std::string> errors;
    validateUsers(processedUsers, [&errors](const ProcessedUser& user, 
                                            const std::string& error) {
        errors.push_back(fmt::format("User {}: {}", user.id, error));
    });
}

```

**错误示例**：

```cpp
// 错误：隐式引用捕获导致悬空引用
std::function<bool(const User&)> createFilter(const std::string& filterName)
{
    return [&](const User& user) {  // 危险：filterName可能已销毁
        return user.name == filterName;
    };
}

// 错误：过度使用lambda导致代码难以理解
void complexProcessing()
{
    auto result = std::accumulate(data.begin(), data.end(), 0, 


        [ ](int acc, const auto& item) {


            return [acc, item](const auto& modifier) {
                return modifier(acc + item.value * 
                    [&item]() { 
                        return item.valid ? 1 : 0; 
                    }());
            }(getModifier());
        });
}

```

**检查方法**：

*   代码审查检查lambda捕获的正确性
    
*   静态分析检测可能的悬空引用
    
*   性能分析识别lambda开销
    

## 3. 内存管理

### 3.1 资源获取即初始化(RAII)规范

**规则**：

*   所有资源管理必须基于RAII原则
    
*   资源获取在构造函数中完成，释放在析构函数中完成
    
*   确保资源类不可拷贝，或正确实现拷贝语义
    
*   使用标准库RAII包装器（std::unique\_ptr, std::shared\_ptr, std::lock\_guard等）
    

**理由**：

*   确保资源正确释放，即使发生异常
    
*   避免资源泄漏和状态不一致
    
*   简化资源管理代码
    

**正确示例**：

```cpp
class DatabaseConnection {
public:
    explicit DatabaseConnection(const std::string& connectionString)
        : m_handle(connect(connectionString))
    {
        if (!m_handle) {
            throw std::runtime_error("Failed to connect to database");
        }
    }
    
    ~DatabaseConnection()
    {
        if (m_handle) {
            disconnect(m_handle);
        }
    }
    
    // 禁用拷贝
    DatabaseConnection(const DatabaseConnection&) = delete;
    DatabaseConnection& operator=(const DatabaseConnection&) = delete;
    
    // 启用移动
    DatabaseConnection(DatabaseConnection&& other) noexcept
        : m_handle(std::exchange(other.m_handle, nullptr))
    {}
    
    DatabaseConnection& operator=(DatabaseConnection&& other) noexcept
    {
        if (this != &other) {
            if (m_handle) {
                disconnect(m_handle);
            }
            m_handle = std::exchange(other.m_handle, nullptr);
        }
        return *this;
    }
    
    void executeQuery(const std::string& query)
    {
        if (!m_handle) {
            throw std::logic_error("Database connection not established");
        }
        // 执行查询
    }
    
private:
    DBHandle* m_handle = nullptr;
};

void processWithDatabase()
{
    DatabaseConnection db("host=localhost;db=test");
    db.executeQuery("SELECT * FROM users");
    
    // 自动释放连接，即使抛出异常
}

```

**错误示例**：

```cpp
// 错误：手动资源管理
class ManualResource {
public:
    void openFile(const std::string& filename)
    {
        m_file = fopen(filename.c_str(), "r");
        if (!m_file) {
            throw std::runtime_error("Failed to open file");
        }
    }
    
    void closeFile()
    {
        if (m_file) {
            fclose(m_file);
            m_file = nullptr;
        }
    }
    
    ~ManualResource()
    {
        // 可能忘记调用closeFile()
    }
    
private:
    FILE* m_file = nullptr;
};

// 错误：异常不安全的资源管理
void unsafeProcess()
{
    ManualResource resource;
    resource.openFile("data.txt");
    
    processData(); // 如果抛出异常，文件不会关闭
    
    resource.closeFile();
}

```

**检查方法**：

*   代码审查检查所有资源管理是否使用RAII
    
*   静态分析检测手动资源管理
    
*   测试验证异常安全性
    

### 3.2 避免内存泄漏规范

**规则**：

*   禁止使用裸new和delete，使用智能指针
    
*   使用标准库容器而非手动数组管理
    
*   定期使用内存检测工具（Valgrind, AddressSanitizer）
    
*   循环引用必须使用std::weak\_ptr打破
    
*   避免在析构函数中抛出异常
    

**理由**：

*   防止内存泄漏和资源泄漏
    
*   提高代码可靠性和可维护性
    
*   简化内存管理逻辑
    

**正确示例**：

```cpp
class SafeResourceManager {
public:
    std::unique_ptr<Resource> acquireResource()
    {
        std::lock_guard lock(m_mutex);
        if (m_resources.empty()) {
            return std::make_unique<Resource>();
        }
        
        auto resource = std::move(m_resources.top());
        m_resources.pop();
        return resource;
    }
    
    void releaseResource(std::unique_ptr<Resource> resource)
    {
        std::lock_guard lock(m_mutex);
        m_resources.push(std::move(resource));
    }
    
private:
    std::mutex m_mutex;
    std::stack<std::unique_ptr<Resource>> m_resources;
};

// 使用标准库容器管理内存
void processLargeDataSet()
{
    std::vector<std::unique_ptr<DataProcessor>> processors;
    
    for (int i = 0; i < 10; ++i) {
        processors.push_back(std::make_unique<DataProcessor>());
    }
    
    // 自动释放所有processor
}

```

**错误示例**：

```cpp
// 错误：手动内存管理容易出错
class UnsafeManager {
public:
    Resource* getResource()
    {
        return new Resource(); // 调用者可能忘记删除
    }
};

// 错误：可能的内存泄漏
void riskyProcess()
{
    Resource* res1 = new Resource();
    Resource* res2 = new Resource();
    
    process(res1);
    
    if (condition) {
        delete res1; // 可能忘记删除res2
        return;
    }
    
    delete res1;
    delete res2;
}

// 错误：异常不安全
void exceptionUnsafe()
{
    auto* resource = new Resource();
    
    mightThrow(); // 如果抛出异常，resource泄漏
    
    delete resource;
}

```

**检查方法**：

*   使用Valgrind/AddressSanitizer进行内存检测
    
*   静态分析工具检查内存管理问题
    
*   代码审查检查所有new/delete使用
    

## 4. 异常安全

### 4.1 异常使用规范

**规则**：

*   只在表示真正异常情况时使用异常，不要用于控制流
    
*   抛出异常时使用值类型，捕获异常时使用常量引用
    
*   自定义异常类型应继承自std::exception，并提供what()方法
    
*   禁止在析构函数中抛出异常
    
*   使用noexcept正确标记不抛出异常的函数
    

**理由**：

*   异常用于错误处理，控制流应使用条件判断
    
*   值类型抛出避免切片问题，常量引用捕获避免不必要的拷贝
    
*   继承std::exception提供一致的异常接口
    
*   析构函数中的异常会导致std::terminate
    
*   noexcept提供性能优化和接口明确性
    

**正确示例**：

```cpp
// 自定义异常类型
class DatabaseException : public std::exception {
public:
    explicit DatabaseException(std::string message)
        : m_message(std::move(message))
    {}

    const char* what() const noexcept override {
        return m_message.c_str();
    }

private:
    std::string m_message;
};

// 值类型抛出，常量引用捕获
void connectToDatabase(const std::string& connectionString)
{
    if (connectionString.empty()) {
        throw DatabaseException("Connection string is empty");
    }
    
    try {
        // 尝试连接
    } catch (const NetworkException& e) {
        // 转换并抛出更具体的异常
        throw DatabaseException("Failed to connect: " + std::string(e.what()));
    }
}

// 正确使用noexcept
class ResourceHolder {
public:
    ~ResourceHolder() noexcept {  // 析构函数必须noexcept
        try {
            cleanup();  // 清理资源，但捕获所有异常
        } catch (...) {
            // 记录错误，但不允许异常传播
            logError("Cleanup failed");
        }
    }
    
    void cleanup() {
        // 清理操作，可能抛出异常，但被析构函数捕获
    }
};

```

**错误示例**：

```cpp
// 错误：使用异常控制流程
void processData() {
    try {
        while (true) {
            auto data = readData();
            if (data.empty()) {
                throw NoMoreDataException();  // 应使用条件判断
            }
            // 处理数据
        }
    } catch (const NoMoreDataException&) {
        // 正常结束
    }
}

// 错误：抛出指针类型
void faultyThrow() {
    throw new std::runtime_error("error");  // 内存泄漏，且捕获方需管理内存
}

// 错误：析构函数抛出异常
class BadDestructor {
public:
    ~BadDestructor() {
        throw std::runtime_error("error");  // 会导致std::terminate
    }
};

```

**检查方法**：

*   代码审查检查异常使用场景
    
*   静态分析工具检查析构函数中的异常抛出
    
*   测试验证异常安全保证
    

### 4.2 异常安全保证

**规则**：

*   函数应提供以下三种异常安全保证之一：
    
    1.  不抛保证（noexcept）：函数绝不抛出异常
        
    2.  强异常安全保证：操作失败时状态完全回滚，不影响程序状态
        
    3.  基本异常安全保证：操作失败时程序处于有效状态，无资源泄漏
        
*   优先提供强异常安全保证或不抛保证
    
*   使用RAII确保资源泄漏安全
    

**理由**：

*   明确的异常安全保证使代码更可靠
    
*   强异常安全保证简化错误恢复
    
*   基本异常安全保证是底线，确保无资源泄漏
    

**正确示例**：

```cpp
class Transaction {
public:
    // 强异常安全保证：要么成功，要么状态不变
    void transferFunds(Account& from, Account& to, double amount)
    {
        // 使用RAII管理锁
        std::lock_guard lock(m_mutex);
        
        // 先检查并扣除源账户，但暂不存入目标账户
        if (from.balance < amount) {
            throw InsufficientFundsException();
        }
        
        from.balance -= amount;
        
        try {
            to.balance += amount;
        } catch (...) {
            // 恢复源账户余额
            from.balance += amount;
            throw;  // 重新抛出
        }
        
        // 提交事务日志
        logTransaction(from, to, amount);
    }
    
    // 不抛保证
    void logTransaction(const Account& from, const Account& to, double amount) noexcept
    {
        // 简单日志操作，确保不抛出异常
        std::cout << "Transaction: " << amount << " from " 
                  << from.id << " to " << to.id << std::endl;
    }
};

// 使用RAII实现基本异常安全保证
class FileWriter {
public:
    explicit FileWriter(const std::string& filename)
        : m_file(fopen(filename.c_str(), "w"))
    {
        if (!m_file) {
            throw FileOpenException("Failed to open file: " + filename);
        }
    }
    
    ~FileWriter() {
        if (m_file) {
            fclose(m_file);  // 确保资源释放
        }
    }
    
    void write(const std::string& data) {
        if (fprintf(m_file, "%s", data.c_str()) < 0) {
            throw FileWriteException("Write failed");
        }
    }
    
private:
    FILE* m_file;
};

```

**错误示例**：

```cpp
// 错误：缺乏异常安全保证
class UnsafeContainer {
public:
    void addData(const Data& newData) {
        if (m_size >= m_capacity) {
            // 重新分配内存
            auto newBuffer = new Data[m_capacity * 2];
            for (size_t i = 0; i < m_size; ++i) {
                newBuffer[i] = m_buffer[i];  // 如果拷贝抛出，原数据已破坏
            }

            delete[ ] m_buffer;

            m_buffer = newBuffer;
            m_capacity *= 2;
        }
        
        m_buffer[m_size++] = newData;  // 可能抛出
    }
    
private:
    Data* m_buffer = nullptr;
    size_t m_size = 0;
    size_t m_capacity = 0;
};

// 错误：资源泄漏
void leakyFunction() {
    auto* resource = new Resource();
    
    mightThrow();  // 如果抛出，resource泄漏
    
    delete resource;
}

```

**检查方法**：

*   代码审查评估异常安全保证
    
*   测试验证异常场景下的状态一致性
    
*   静态分析检测资源泄漏
    

## 5. 模板与泛型编程

### 5.1 模板使用规范

**规则**：

*   模板参数使用有意义的名称，遵循概念约束
    
*   优先使用模板而非宏定义泛型代码
    
*   模板定义应放在头文件中
    
*   使用SFINAE或概念(Concepts)进行模板约束
    
*   避免过度使用模板元编程，保持代码可读性
    

**理由**：

*   提高模板代码的可读性和可维护性
    
*   宏缺乏类型安全且难以调试
    
*   头文件放置符合模板实例化要求
    
*   约束模板参数避免意外实例化
    
*   模板元编程复杂，应谨慎使用
    

**正确示例**：

```cpp
// 使用概念约束模板参数（C++20）
template<typename T>
concept Arithmetic = std::is_arithmetic_v<T>;

template<Arithmetic T>
T calculateAverage(const std::vector<T>& values)
{
    if (values.empty()) {
        throw std::invalid_argument("Empty container");
    }
    
    T sum = std::accumulate(values.begin(), values.end(), T{});
    return sum / values.size();
}

// 使用SFINAE（C++17之前）
template<typename T>
typename std::enable_if_t<std::is_arithmetic_v<T>, T>
calculateSum(const std::vector<T>& values)
{
    return std::accumulate(values.begin(), values.end(), T{});
}

// 可变参数模板使用
template<typename... Args>
void logMessage(const std::string& format, Args&&... args)
{
    if constexpr (sizeof...(Args) > 0) {
        fmt::print(format, std::forward<Args>(args)...);
    } else {
        fmt::print(format);
    }
}

```

**错误示例**：

```cpp
// 错误：模板参数命名不清晰
template<typename T, typename U, typename V>
auto process(T a, U b, V c) {  // 无法理解参数用途
    return a + b * c;
}

// 错误：使用宏实现泛型
#define MAX(a, b) ((a) > (b) ? (a) : (b))  // 类型不安全，多次求值

// 错误：模板定义在源文件中
// my_template.cpp
template<typename T>
void process(T value) {  // 链接错误，使用处无法实例化
    // ...
}

```

**检查方法**：

*   代码审查检查模板参数命名和约束
    
*   编译测试模板的各种实例化
    
*   静态分析检查模板使用合理性
    

### 5.2 概念(Concepts)使用

**规则**：

*   C++20及以上项目必须使用概念约束模板
    
*   概念应定义在命名空间范围内，具有描述性名称
    
*   优先使用标准概念（std::integral, std::invocable等）
    
*   概念应尽可能精确约束 requirements
    

**理由**：

*   概念提供更清晰模板接口和更好错误信息
    
*   标准化概念提高代码一致性
    
*   精确约束避免过度限制模板参数
    

**正确示例**：

```cpp
// 自定义概念
template<typename T>
concept StringLike = requires(T str) {
    { str.c_str() } -> std::convertible_to<const char*>;
    { str.size() } -> std::integral;
};

template<StringLike T>
void processString(const T& str)
{
    // 安全使用str.c_str()和str.size()
}

// 组合概念
template<typename T>
concept IndexableContainer = requires(T container) {
    requires std::ranges::range<T>;
    requires requires { container[0]; };
};

template<IndexableContainer Container>
auto getFirstElement(const Container& container)
{
    if (!container.empty()) {
        return container[0];
    }
    throw std::out_of_range("Container is empty");
}

```

**错误示例**：

```cpp
// 错误：不使用概念导致复杂SFINAE
template<typename T>
typename std::enable_if_t<
    std::is_convertible_v<decltype(std::declval<T>().c_str()), const char*> &&
    std::is_integral_v<decltype(std::declval<T>().size())>,
void>
processString(const T& str);  // 复杂难懂

// 错误：概念约束过于宽松或过于严格
template<typename T>
concept Any = true;  // 无实际约束价值

template<typename T>
concept TooStrict = requires {
    requires std::integral<T> || std::floating_point<T>;
    T::some_method();  // 不必要的限制
};

```

**检查方法**：

*   代码审查检查概念定义的合理性
    
*   编译测试概念约束的正确性
    
*   静态分析工具检查概念使用
    

## 6. 多线程与并发

### 6.1 线程安全规范

**规则**：

*   明确标识线程安全的类和函数
    
*   使用std::mutex保护共享数据，但避免过度使用
    
*   优先使用线程局部存储（thread\_local）而非静态变量
    
*   避免数据竞争和死锁，使用锁层次或std::scoped\_lock
    
*   使用原子操作进行简单的无锁编程
    

**理由**：

*   明确的线程安全标识避免误用
    
*   正确同步避免数据竞争
    
*   线程局部存储提高性能和线程安全性
    
*   预防死锁提高可靠性
    

**正确示例**：

```cpp
class ThreadSafeQueue {
public:
    void push(int value)
    {
        std::lock_guard lock(m_mutex);
        m_queue.push(value);
        m_cond.notify_one();
    }
    
    bool tryPop(int& value)
    {
        std::lock_guard lock(m_mutex);
        if (m_queue.empty()) {
            return false;
        }
        
        value = m_queue.front();
        m_queue.pop();
        return true;
    }
    
    int waitPop()
    {
        std::unique_lock lock(m_mutex);
        m_cond.wait(lock, [this] { return !m_queue.empty(); });
        
        int value = m_queue.front();
        m_queue.pop();
        return value;
    }
    
private:
    std::queue<int> m_queue;
    mutable std::mutex m_mutex;
    std::condition_variable m_cond;
};

// 使用原子操作
class AtomicCounter {
public:
    void increment() noexcept {
        m_count.fetch_add(1, std::memory_order_relaxed);
    }
    
    int get() const noexcept {
        return m_count.load(std::memory_order_acquire);
    }
    
private:
    std::atomic<int> m_count{0};
};

// 线程局部存储
thread_local int threadSpecificData = 0;

void threadFunction()
{
    threadSpecificData = getThreadId();  // 每个线程独立副本
}

```

**错误示例**：

```cpp
// 错误：非线程安全的单例
class UnsafeSingleton {
public:
    static UnsafeSingleton& instance() {
        if (!s_instance) {  // 数据竞争
            s_instance = new UnsafeSingleton();
        }
        return *s_instance;
    }
    
private:
    static UnsafeSingleton* s_instance;
};

// 错误：错误的双重检查锁定
class DoubleCheckedLocking {
public:
    static DoubleCheckedLocking& instance() {
        if (!s_instance) {  // 未同步的读
            std::lock_guard lock(s_mutex);
            if (!s_instance) {
                s_instance = new DoubleCheckedLocking();
            }
        }
        return *s_instance;
    }
    
private:
    static DoubleCheckedLocking* s_instance;
    static std::mutex s_mutex;
};

// 错误：死锁风险
void transferMoney(Account& a1, Account& a2, double amount)
{
    std::lock_guard lock1(a1.getMutex());
    std::lock_guard lock2(a2.getMutex());  // 可能死锁，如果另一个线程以相反顺序锁
    
    a1.withdraw(amount);
    a2.deposit(amount);
}

```

**检查方法**：

*   代码审查检查同步原语的使用
    
*   线程分析工具（ThreadSanitizer）检测数据竞争
    
*   死锁检测工具分析锁顺序
    

### 6.2 原子操作与锁

**规则**：

*   简单操作用原子操作，复杂操作用锁
    
*   使用适当的内存顺序（memory\_order），默认使用seq\_cst
    
*   优先使用std::lock\_guard，需要延迟锁定使用std::unique\_lock
    
*   使用std::scoped\_lock同时获取多个锁
    
*   避免在持有锁时调用用户代码或执行耗时操作
    

**理由**：

*   原子操作性能优于锁，但适用场景不同
    
*   正确内存顺序保证多线程语义
    
*   自动锁管理避免忘记释放锁
    
*   多锁同时获取避免死锁
    
*   减少锁的持有时间提高并发性
    

**正确示例**：

```cpp
class SafeAccount {
public:
    void transferTo(SafeAccount& other, double amount)
    {
        // 使用scoped_lock同时获取两个锁，避免死锁
        std::scoped_lock lock(m_mutex, other.m_mutex);
        
        if (m_balance < amount) {
            throw InsufficientFundsException();
        }
        
        m_balance -= amount;
        other.m_balance += amount;
    }
    
    double getBalance() const
    {
        std::lock_guard lock(m_mutex);
        return m_balance;
    }
    
private:
    mutable std::mutex m_mutex;
    double m_balance = 0.0;
};

// 原子操作使用适当内存顺序
class AtomicFlag {
public:
    void set() noexcept {
        m_flag.store(true, std::memory_order_release);
    }
    
    bool check() const noexcept {
        return m_flag.load(std::memory_order_acquire);
    }
    
    void reset() noexcept {
        m_flag.store(false, std::memory_order_relaxed);
    }
    
private:
    std::atomic<bool> m_flag{false};
};

```

**错误示例**：

```cpp
// 错误：不必要的锁保护原子操作
class OverlySynchronized {
public:
    void increment() {
        std::lock_guard lock(m_mutex);  // 不必要的锁
        m_counter++;
    }
    
private:
    int m_counter = 0;
    std::mutex m_mutex;
};

// 错误：错误的内存顺序
class IncorrectMemoryOrder {
public:
    void setValue(int value) {
        m_value.store(value, std::memory_order_relaxed);  // 可能看不到其他写入
    }
    
    int getValue() const {
        return m_value.load(std::memory_order_relaxed);  // 可能看到过期值
    }
    
private:
    std::atomic<int> m_value;
};

// 错误：手动锁管理容易出错
class ManualLock {
public:
    void lock() { m_mutex.lock(); }
    void unlock() { m_mutex.unlock(); }
    
private:
    std::mutex m_mutex;
};

void riskyFunction(ManualLock& lock)
{
    lock.lock();
    
    mightThrow();  // 如果抛出异常，锁不会释放
    
    lock.unlock();
}

```

**检查方法**：

*   代码审查检查锁和原子操作的使用
    
*   性能分析识别锁竞争瓶颈
    
*   静态分析检测不正确的内存顺序
    

## 7. 禁止模式

**明确禁止项**：

1.  禁止使用裸new和delete
    
2.  禁止使用宏定义常量或函数（除头文件保护外）
    
3.  禁止使用C风格字符串和数组（优先使用std::string和std::vector）
    
4.  禁止使用可变参数（除日志等特定场景外）
    
5.  禁止使用异常规范（throw()，除noexcept外）
    
6.  禁止使用默认捕获的lambda（\[=\]或\[&\]需明确捕获变量）
    
7.  禁止在头文件中使用using namespace
    
8.  禁止使用全局变量（除单例等特定模式外）
    
9.  禁止使用reinterpret\_cast和C风格类型转换
    
10.  禁止使用未经验证的输入和未处理的外部数据
    

**理由**：

*   这些模式容易导致错误、安全漏洞和维护问题
    
*   现代C++提供了更安全、更清晰的替代方案
    
*   禁止这些模式强制使用最佳实践
    

**检查方法**：

*   代码审查严格执行禁止列表
    
*   静态分析工具检测禁止模式的使用
    
*   CI流水线集成禁止模式检查
    

## 8. 示例代码

### 8.1 正确示例

```cpp
// 符合规范的完整示例
#include <memory>
#include <vector>
#include <string>
#include <algorithm>
#include <numeric>
#include <stdexcept>

namespace example::project {

class DataProcessor {
public:
    explicit DataProcessor(std::string name, std::shared_ptr<Logger> logger)
        : m_name(std::move(name))
        , m_logger(std::move(logger))
    {
        if (m_name.empty()) {
            throw std::invalid_argument("Name cannot be empty");
        }
    }
    
    std::vector<int> processData(const std::vector<int>& input) const
    {
        if (input.empty()) {
            return {};
        }
        
        std::vector<int> result;
        result.reserve(input.size());
        
        std::copy_if(input.begin(), input.end(), std::back_inserter(result),
                    [this](int value) { return filterValue(value); });
        
        if (m_logger) {
            m_logger->info("Processed {} items", result.size());
        }
        
        return result;
    }
    
    double calculateAverage(const std::vector<int>& data) const
    {
        if (data.empty()) {
            throw std::invalid_argument("Data cannot be empty");
        }
        
        double sum = std::accumulate(data.begin(), data.end(), 0.0);
        return sum / data.size();
    }
    
private:
    bool filterValue(int value) const noexcept
    {
        return value > 0 && value < 100;
    }
    
    std::string m_name;
    std::shared_ptr<Logger> m_logger;
};

} // namespace example::project

```

### 8.2 错误示例

```cpp
// 常见错误模式示例
#include <stdio.h>  // C头文件，应使用<cstdio>
#include "some_header.h"  // 头文件顺序错误

using namespace std;  // 禁止在头文件中使用

#define MAX_SIZE 100  // 应使用constexpr

class BadExample {
public:
    BadExample() : data(new int[100]) {}  // 裸new
    
    ~BadExample() {

        delete[ ] data;  // 裸delete

    }
    
    void process() {
        int* buffer = new int[100];  // 可能泄漏
        
        if (condition) {
            return;  // 泄漏buffer
        }
        

        delete[ ] buffer;

    }
    
    char* getCString() {  // 返回原始指针，所有权不明确
        return cstr;
    }
    
private:
    int* data;
    char cstr[100];
};

void riskyFunction() {
    static int counter = 0;  // 非线程安全
    
    int* dynamicArray = (int*)malloc(100 * sizeof(int));  // C风格分配
    
    // 未验证的输入使用
    char input[100];
    gets(input);  // 缓冲区溢出风险
    
    free(dynamicArray);
}

```

## 9. 静态分析工具配置

### 9.1 Clang-Tidy配置

**.clang-tidy文件**：

```yaml
Checks: >
    -*,
    bugprone-*,
    cert-*,
    cppcoreguidelines-*,
    clang-analyzer-*,
    modernize-*,
    performance-*,
    portability-*,
    readability-*,
    
WarningsAsErrors: '*'
CheckOptions:
  - key:             cppcoreguidelines-avoid-c-arrays.PreferContainer
    value:           'true'
  - key:             cppcoreguidelines-pro-type-member-init.IgnoreArrays
    value:           'false'
  - key:             modernize-use-nodiscard.Macros
    value:           'DEBUG_LOG, ASSERT'
  - key:             modernize-use-trailing-return-type.AllowedFunctions
    value:           'main'
  - key:             readability-identifier-naming.ClassCase
    value:           'PascalCase'
  - key:             readability-identifier-naming.VariableCase
    value:           'camelCase'
  - key:             readability-identifier-naming.FunctionCase
    value:           'camelCase'
  - key:             readability-identifier-naming.ConstantCase
    value:           'UPPER_CASE'
  - key:             readability-identifier-naming.MemberCase
    value:           'm_camelCase'
  
HeaderFilterRegex: '.*'
AnalyzeTemporaryDtors: true
FormatStyle: file

```

### 9.2 常用静态分析命令

```bash
# 基本检查
clang-tidy -p build/ -checks='-*,modernize-*' src/*.cpp

# 包含所有推荐检查
clang-tidy -p build/ -checks='bugprone-*,cert-*,cppcoreguidelines-*' src/*.cpp

# 自动修复
clang-tidy -p build/ -fix -checks='modernize-use-auto' src/*.cpp

# 与编译数据库一起使用
clang-tidy -p compile_commands.json src/*.cpp

```

## 10. 代码审查检查清单

### 10.1 基础规范

1.  [ ] 命名是否符合规范（PascalCase类名，camelCase变量名等）
    
2.  [ ] 头文件保护宏是否正确且唯一
    
3.  [ ] #include顺序是否正确（系统→第三方→项目）
    
4.  [ ] 是否使用了禁止的C风格特性（如malloc/free）
    
5.  [ ] 代码格式是否符合.clang-format配置
    
    ### 10.2 现代C++特性
    
6.  [ ] 是否优先使用智能指针而非裸指针
    
7.  [ ] 是否正确使用了移动语义和完美转发
    
8.  [ ] 是否避免了不必要的拷贝操作
    
9.  [ ] lambda捕获是否明确且安全
    
10.  [ ] 是否适当使用了auto关键字
    
    ### 10.3 内存管理
    
11.  [ ] 是否遵循RAII原则管理资源
    
12.  [ ] 是否存在潜在的内存泄漏风险
    
13.  [ ] 智能指针使用是否恰当（unique\_ptr vs shared\_ptr）
    
14.  [ ] 是否避免了循环引用
    
15.  [ ] 容器使用是否恰当（vector vs array vs list）
    
    ### 10.4 异常安全
    
16.  [ ] 异常使用是否合理（非控制流）
    
17.  [ ] 析构函数是否标记为noexcept
    
18.  [ ] 是否提供了适当的异常安全保证
    
19.  [ ] 自定义异常是否继承自std::exception
    
20.  [ ] 资源管理是否异常安全
    
    ### 10.5 多线程安全
    
21.  [ ] 共享数据是否正确同步
    
22.  [ ] 锁的使用是否恰当（范围、顺序）
    
23.  [ ] 是否避免了死锁可能性
    
24.  [ ] 原子操作的内存顺序是否正确
    
25.  [ ] 线程创建和管理是否合理
    

## 11. 单元测试规范

### 11.1 测试框架选择

**规则**：

*   使用Google Test作为测试框架
    
*   使用Google Mock作为模拟框架
    
*   测试代码与生产代码遵循相同规范
    
*   测试命名清晰表达测试意图
    

**理由**：

*   Google Test功能全面，社区支持良好
    
*   一致的代码规范提高可维护性
    
*   清晰的测试命名便于理解测试目的
    

### 11.2 测试结构规范

**正确示例**：

```cpp
// 测试类命名：被测试类名+Test
class DataProcessorTest : public ::testing::Test {
protected:
    void SetUp() override {
        // 创建测试依赖
        mockLogger = std::make_shared<MockLogger>();
        processor = std::make_unique<DataProcessor>("test", mockLogger);
    }
    
    void TearDown() override {
        // 清理资源
        processor.reset();
    }
    
    std::shared_ptr<MockLogger> mockLogger;
    std::unique_ptr<DataProcessor> processor;
};

// 测试用例命名：被测试方法_场景_预期结果
TEST_F(DataProcessorTest, processData_EmptyInput_ReturnsEmpty) {
    // 准备
    std::vector<int> emptyInput;
    
    // 执行
    auto result = processor->processData(emptyInput);
    
    // 验证
    EXPECT_TRUE(result.empty());
}

TEST_F(DataProcessorTest, calculateAverage_SingleElement_ReturnsElement) {
    // 准备
    std::vector<int> singleElement = {42};
    
    // 执行
    double result = processor->calculateAverage(singleElement);
    
    // 验证
    EXPECT_DOUBLE_EQ(42.0, result);
}

// 异常测试
TEST_F(DataProcessorTest, calculateAverage_EmptyInput_ThrowsException) {
    // 准备
    std::vector<int> emptyInput;
    
    // 执行和验证
    EXPECT_THROW(processor->calculateAverage(emptyInput), std::invalid_argument);
}

```

### 11.3 测试覆盖率要求

**规则**：

*   行覆盖率不低于80%
    
*   分支覆盖率不低于75%
    
*   关键核心模块覆盖率不低于90%
    
*   定期生成覆盖率报告并审查
    

**检查方法**：

*   使用gcov/lcov生成覆盖率报告
    
*   CI流水线集成覆盖率检查
    
*   代码审查检查测试用例完整性
    

### 11.4 测试性能要求

**规则**：

*   单元测试执行时间应保持简短
    
*   避免在测试中执行耗时操作
    
*   使用模拟对象替代真实外部依赖
    
*   定期清理过时或冗余测试
    

**理由**：

*   快速测试提高开发效率
    
*   避免外部依赖使测试更稳定
    
*   保持测试套件高效运行
    

## 12. CI/CD集成

### 12.1 持续集成流水线

**规则**：

*   每次提交必须通过完整的CI流水线
    
*   CI失败必须优先修复
    
*   流水线包含：编译、测试、静态分析、格式化检查
    
*   定期运行内存检测和性能测试
    

**示例流水线**：

```yaml
# .gitlab-ci.yml 示例
stages:
  - build
  - test
  - analyze
  - deploy

build:
  stage: build
  script:
    - cmake -B build -DCMAKE_BUILD_TYPE=Debug
    - cmake --build build --parallel 4

test:
  stage: test
  script:
    - cd build && ctest --output-on-failure

analyze:
  stage: analyze
  script:
    - run-clang-tidy -p build -checks='-*,modernize-*' src/
    - check-format src/ include/

memory-check:
  stage: test
  script:
    - valgrind --leak-check=full ./build/tests

```

### 12.2 代码质量门禁

**规则**：

*   静态分析零警告
    
*   测试通过率100%
    
*   代码覆盖率不低于设定阈值
    
*   格式化检查通过
    
*   无内存泄漏问题
    

**检查脚本示例**：

```bash
#!/bin/bash
set -e

# 编译检查
cmake -B build -DCMAKE_BUILD_TYPE=Debug
cmake --build build --parallel 4

# 静态分析
run-clang-tidy -p build -checks='-*,modernize-*' src/

# 格式化检查
find src/ include/ -name '*.cpp' -o -name '*.h' | xargs clang-format --dry-run --Werror

# 测试运行
cd build && ctest --output-on-failure

# 覆盖率检查
gcovr --exclude-unreachable-branches --exclude-throw-branches --print-summary

```