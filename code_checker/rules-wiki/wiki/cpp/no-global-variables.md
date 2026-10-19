---
domain: cpp
rule_id: cpp-no-global-variables
title: 禁止全局变量
priority: main
source_file: rules/C++代码规范.md
source_section: "§7 明确禁止项"
status: active
check_method: regex
deterministic_check: true
checkability: deterministic
conflicts_with: []
overrides: []
related_pages:
  - [[cpp-no-using-namespace-in-header]]
  - [[cpp-thread-local]]
---

# 禁止全局变量

## 规则条款
禁止使用全局变量（除单例等特定模式外）。全局变量引入全局状态，使代码难以测试、推理和并行化。多线程环境下，全局变量的访问需要同步保护，增加复杂性和死锁风险。全局变量的初始化顺序在跨翻译单元间也是不确定的。

## 正确示例
```cpp
// 单例模式：封闭的全局访问点
class ConfigManager {
public:
    static ConfigManager& instance() {
        static ConfigManager mgr;  // C++11 保证线程安全的局部静态初始化
        return mgr;
    }

    void load(const std::string& configPath);
    std::string getValue(const std::string& key) const;

    // 禁止拷贝
    ConfigManager(const ConfigManager&) = delete;
    ConfigManager& operator=(const ConfigManager&) = delete;

private:
    ConfigManager() = default;
    std::unordered_map<std::string, std::string> m_config;
};

// 依赖注入替代全局变量
class DataProcessor {
public:
    explicit DataProcessor(ConfigManager& config,
                           std::shared_ptr<Logger> logger)
        : m_config(config), m_logger(std::move(logger)) {}

    void process();

private:
    ConfigManager& m_config;
    std::shared_ptr<Logger> m_logger;
};

// constexpr 编译期常量（非全局状态）
constexpr int DefaultTimeoutMs = 5000;
constexpr std::string_view AppVersion = "2.0.0";
```

## 错误示例
```cpp
// 全局变量（非 const）
int g_requestCount = 0;                    // 数据竞争风险
std::string g_currentUser;                 // 全局可变状态
std::unordered_map<int, Session> g_sessions;  // 多线程访问问题

// 全局指针
Logger* g_logger = nullptr;                // 初始化顺序不确定

// 静态类成员（本质是全局变量）
class GlobalState {
public:
    static int s_errorCount;  // 全局状态，应避免
};

// 命名空间中的变量
namespace Utils {
    bool g_debugMode = false;  // 等同于全局变量
}
```

## 检查方法
1. 正则检测：在全局/命名空间作用域搜索非 const 变量声明
   - 模式：在函数体外、类体外的变量声明（排除 `const`/`constexpr`）
2. 正则检测：搜索静态成员变量（类体内的 `static` 声明）
3. 排除项：`const`/`constexpr` 编译期常量
4. 排除项：单例模式的 `instance()` 方法内的局部静态变量
5. 排除项：日志器、配置管理器等明确的单例模式

## 修复指南
1. 全局可变状态 → 封装为单例类（Meyer's Singleton）
2. 全局配置 → 依赖注入，通过构造函数或 setter 传入
3. 全局计数器 → 封装在类中，通过接口访问
4. 跨模块共享数据 → 使用消息传递或事件系统
5. 确实需要的全局访问点 → 使用单例模式，明确标注理由
6. 常量 → 使用 `constexpr` 或 `const`（不在此规则禁止范围）

## 审查清单
- [ ] 不存在非 const 全局/命名空间变量
- [ ] 静态成员变量有明确的使用理由
- [ ] 单例模式的实现正确（线程安全、不可拷贝）
- [ ] constexpr 常量未与可变全局状态混淆

## 关联页面
- [[cpp-no-using-namespace-in-header]] — 头文件禁止 using namespace
- [[cpp-thread-local]] — 线程局部存储优先
