---
domain: cpp
rule_id: cpp-naming-constants
title: 常量命名规范
priority: main
source_file: rules/C++代码规范.md
source_section: "### 1.1 命名约定"
status: active
check_method: regex
deterministic_check: true
checkability: deterministic
conflicts_with: []
overrides: []
related_pages:
  - [[cpp-naming-classes]]
  - [[cpp-naming-functions]]
  - [[cpp-naming-variables]]
  - [[cpp-naming-private-members]]
  - [[cpp-naming-namespaces]]
---

# 常量命名规范

## 规则条款

常量必须使用 **UPPER_CASE**（全大写字母，单词之间用下划线 `_` 分隔）。常量是程序运行中不会被修改的值（如配置参数、固定阈值），命名需体现"不可变"的属性和具体含义。
按用途分类：

- **配置类常量**：如 `DB_CONNECTION_TIMEOUT`（数据库连接超时时间）、`API_BASE_URL`（接口请求的基础地址）
- **阈值类常量**：如 `MAX_UPLOAD_SIZE`（最大上传文件大小）、`MIN_PASSWORD_LENGTH`（密码最小长度）
- **数学/物理常量**：如 `PI`、`GRAVITY_ACCELERATION`（定义时使用 `constexpr`）

常量应使用 `const` 或 `constexpr` 声明。`#define` 宏定义常量已被禁止（见 C-09），应使用 `constexpr` 替代。
## 正确示例

```cpp
// 配置类常量
const int DB_CONNECTION_TIMEOUT = 30;       // 数据库连接超时（秒）
const std::string API_BASE_URL = "https://api.example.com/v1";

// 阈值类常量
const size_t MAX_UPLOAD_SIZE = 10 * 1024 * 1024;  // 最大上传 10MB
const int MIN_PASSWORD_LENGTH = 8;                 // 密码最小长度

// 数学/物理常量（使用 constexpr）
constexpr double PI = 3.1415926535;
constexpr double GRAVITY_ACCELERATION = 9.80665;

// 枚举常量（enum class 内部的枚举值使用 PascalCase）
enum class ErrorCode {
    Success = 0,
    InvalidParameter,
    ConnectionFailed,
    Timeout
};

// 命名空间内的常量
namespace config {
    const int MAX_RETRY_COUNT = 5;
    const int DEFAULT_TIMEOUT_MS = 3000;
}
```

## 错误示例

```cpp
// 错误：camelCase（应为 UPPER_CASE）
const int maxRetryCount = 5;             // 应为 MAX_RETRY_COUNT
constexpr double pi = 3.14159;           // 应为 PI

// 错误：PascalCase
const int MaxRetryCount = 5;             // 应为 MAX_RETRY_COUNT

// 错误：snake_case（全小写）
const int max_retry_count = 5;           // 应为 MAX_RETRY_COUNT

// 错误：混合大小写
const int Max_Retry_Count = 5;           // 应为 MAX_RETRY_COUNT

// 错误：无意义名称
const int N = 100;                        // 应为具体含义，如 MAX_ITEMS_PER_PAGE
constexpr double X = 2.71828;            // 应为 EULER_NUMBER

// 错误：#define 宏常量（已禁止，应使用 const/constexpr）
#define MAX_SIZE 1024                     // 应使用 constexpr int MAX_SIZE = 1024;
```

## 检查方法
1. 扫描所有 `const` / `constexpr` 变量声明
2. 验证常量名是否全部大写
3. 验证单词之间是否以下划线分隔（非驼峰或连字符）
4. 排除 `enum class` 内部的枚举值（枚举值使用 PascalCase，不属于本条规则检查范围）
5. 排除函数参数或函数内部的 `const` 局部变量（需根据上下文判断是否为"常量"语义）
6. 正则模式：`(?:const|constexpr)\s+\w+(?:\s*[*&])?\s+([A-Z][A-Z0-9_]*)\s*=`
7. 反向检查：扫描是否有 `#define [A-Z_]+` 形式的宏常量定义，如有则违反 C-09 规则

## 修复指南

1. 将 camelCase 转换为 UPPER_CASE：`maxRetryCount` → `MAX_RETRY_COUNT`
2. 将 PascalCase 转换为 UPPER_CASE：`MaxRetryCount` → `MAX_RETRY_COUNT`
3. 将全小写 snake_case 转为大写：`max_retry_count` → `MAX_RETRY_COUNT`
4. 补充无意义名称的语义：`N` → `MAX_ITEMS_PER_PAGE`
5. 将 `#define` 宏常量替换为 `const` / `constexpr`：`#define MAX_SIZE 1024` → `constexpr int MAX_SIZE = 1024;`
6. 注意：修改变量类型（添加 `const`/`constexpr`）时需确认该值确实在运行时不会被修改

## 审查清单

- [ ] 所有常量使用 UPPER_CASE 命名
- [ ] 单词之间以下划线分隔
- [ ] 常量名体现了"不可变"属性和具体含义
- [ ] 无 camelCase 或 PascalCase 的常量名
- [ ] 无 `#define` 宏常量（应使用 const/constexpr）
- [ ] 常量声明使用了 `const` 或 `constexpr`
- [ ] 无无意义名称（如 N、X、VAL）

## 关联页面

- [[cpp-naming-classes]] — 类命名（PascalCase，与常量 UPPER_CASE 有明显区别）
- [[cpp-naming-functions]] — 函数命名（camelCase，与常量完全不同）
- [[cpp-naming-variables]] — 变量命名（camelCase，与常量 UPPER_CASE 完全不同）
- [[cpp-naming-private-members]] — 私有成员命名（m_ 前缀 + camelCase，非 UPPER_CASE）
- [[cpp-naming-namespaces]] — 命名空间命名（全小写点分隔）
