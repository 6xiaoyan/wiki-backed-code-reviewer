---
domain: cpp
rule_id: cpp-no-unvalidated-input
title: 禁止未验证输入
priority: main
source_file: rules/C++代码规范.md
source_section: "§7 明确禁止项"
status: active
check_method: llm
deterministic_check: false
checkability: llm_checkable
conflicts_with: []
overrides: []
related_pages:
  - [[cpp-no-cstyle-strings-arrays]]
  - [[cpp-no-reinterpret-c-cast]]
---

# 禁止未验证输入

## 规则条款
禁止使用未经验证的输入和未处理的外部数据。所有来自用户、网络、文件、环境变量、命令行参数等外部来源的数据，在使用前必须经过验证和净化。这包括类型检查、范围校验、格式验证和注入攻击防护。

## 正确示例
```cpp
class InputValidator {
public:
    // 验证并限制整数范围
    static std::optional<int> validatePort(const std::string& input) {
        try {
            int port = std::stoi(input);
            if (port < 1 || port > 65535) {
                return std::nullopt;  // 拒绝无效端口
            }
            return port;
        } catch (const std::exception&) {
            return std::nullopt;  // 非数值输入
        }
    }

    // 验证字符串长度和字符集
    static bool isValidUsername(std::string_view username) {
        if (username.empty() || username.size() > 32) {
            return false;
        }
        return std::all_of(username.begin(), username.end(), [](char c) {
            return std::isalnum(static_cast<unsigned char>(c)) || c == '_';
        });
    }

    // 文件路径验证
    static bool isPathSafe(const std::filesystem::path& path) {
        // 防止路径遍历攻击
        auto canonical = std::filesystem::weakly_canonical(path);
        return canonical.string().find("..") == std::string::npos;
    }

    // SQL 参数化查询（防注入）
    void queryUser(const std::string& name) {
        // 使用预编译语句，参数绑定而非字符串拼接
        m_stmt.bind(1, name);  // 参数自动转义
        m_stmt.execute();
    }
};

// 使用验证结果
void handleRequest(const std::string& rawPort) {
    auto port = InputValidator::validatePort(rawPort);
    if (!port.has_value()) {
        throw std::invalid_argument("Invalid port number");
    }
    listenOnPort(*port);  // 安全：已验证
}
```

## 错误示例
```cpp
// 未验证的整数转换
void connectToServer(const std::string& rawPort) {
    int port = std::stoi(rawPort);    // 可能抛出异常，无范围检查
    listenOnPort(port);               // 可能使用负值或超大值
}

// 未净化的字符串用于命令执行
void executeCommand(const std::string& userInput) {
    std::string cmd = "ping " + userInput;  // 命令注入风险！
    system(cmd.c_str());                    // userInput = "8.8.8.8; rm -rf /"
}

// SQL 字符串拼接（注入漏洞）
void lookupUser(const std::string& name) {
    std::string query = "SELECT * FROM users WHERE name = '"
                      + name + "'";  // SQL 注入：name = "admin' OR '1'='1"
    executeQuery(query);
}

// 环境变量未检查
void readConfig() {
    const char* configPath = std::getenv("CONFIG_PATH");
    std::ifstream file(configPath);  // nullptr 或恶意路径
}

// 数组索引未验证
void accessData(const std::string& indexStr) {
    int index = std::stoi(indexStr);
    int value = m_data[index];  // 可能越界访问
}
```

## 检查方法
1. LLM 审查所有外部数据入口点：
   - 用户输入（`std::cin`、GUI 输入、网络套接字）
   - 文件读取（`std::ifstream`、`fopen`）
   - 环境变量（`std::getenv`）
   - 命令行参数（`argv`）
   - 网络数据（socket recv）
2. 验证数据在使用前是否经过以下处理：
   - 类型转换是否使用了安全的转换函数并检查了异常
   - 数值是否检查了上下限
   - 字符串是否检查了长度和字符集
   - 路径是否经过了规范化检查和遍历防护
3. 识别潜在注入点（SQL、命令行、HTML 等）并验证参数化/转义

## 修复指南
1. 所有外部输入设置明确的验证规则（类型、范围、格式）
2. 数值输入：使用 `std::stoi`/`std::stod` 等并捕获异常，验证范围
3. 字符串输入：限制长度、验证字符集、使用正则表达式校验格式
4. SQL 查询：使用参数化查询（预编译语句），绝不拼接字符串
5. 命令执行：避免 `system()`、`popen()`，使用平台 API；必须在 shell 中执行时，转义所有参数
6. 路径验证：使用 `std::filesystem::weakly_canonical()` 后检查路径遍历
7. 数组索引：验证索引在合法范围内，优先使用 `std::vector::at()` 而非 `operator[]`
8. 早返回策略：验证失败时尽早返回错误，不要让无效数据进入深层逻辑

## 审查清单
- [ ] 所有外部数据入口是否有对应验证逻辑
- [ ] 数值输入检查了类型、范围和边界
- [ ] 字符串输入检查了长度和字符集
- [ ] SQL 查询使用了参数化而非字符串拼接
- [ ] 命令执行避免了直接拼接用户输入
- [ ] 文件路径检查了路径遍历攻击
- [ ] 数组/容器访问验证了索引范围

## 关联页面
- [[cpp-no-cstyle-strings-arrays]] — 禁止 C 风格字符串和数组
- [[cpp-no-reinterpret-c-cast]] — 禁止 reinterpret_cast 和 C 风格转换
