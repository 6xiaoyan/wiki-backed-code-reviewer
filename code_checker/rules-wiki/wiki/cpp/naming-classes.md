---
domain: cpp
rule_id: cpp-naming-classes
title: 类/结构体/枚举命名规范
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
  - [[cpp-naming-functions]]
  - [[cpp-naming-variables]]
  - [[cpp-naming-constants]]
  - [[cpp-naming-private-members]]
  - [[cpp-naming-namespaces]]
---

# 类/结构体/枚举命名规范

## 规则条款

类、结构体、枚举必须使用 **PascalCase**（首字母大写，后续每个单词的首字母也大写），无空格或符号分隔。命名应清晰表达类型的用途。
- 类名示例：`UserInfo`、`OrderStatus`、`DataProcessor`
- 结构体示例：`Point3D`、`RenderContext`
- 枚举类型示例：`ColorMode`、`ConnectionState`

## 正确示例

```cpp
// 类名 - PascalCase，清晰表达用途
class DataProcessor {
    // ...
};

class HttpClient {
    // ...
};

// 结构体
struct RenderContext {
    int width;
    int height;
};

// 枚举
enum class ConnectionState {
    Disconnected,
    Connecting,
    Connected,
    Disconnecting
};
```

## 错误示例

```cpp
// 错误：snake_case
class data_processor {  // 应为 DataProcessor
    // ...
};

// 错误：全小写无分隔
class dataprocessor {  // 应为 DataProcessor
    // ...
};

// 错误：前缀或匈牙利命名
class CDataProcessor {  // 应为 DataProcessor
    // ...
};

class TDataProcessor {  // 应为 DataProcessor
    // ...
};

// 错误：枚举名不清晰
enum class state {  // 应为 ConnectionState 等有意义名称
    A, B, C
};
```

## 检查方法
1. 扫描所有 `class`、`struct`、`enum` 声明
2. 验证名称首字母是否大写
3. 验证名称中无下划线或连字符
4. 验证名称是否由有意义的完整单词组成（非单字符或模糊缩写）
5. 正则模式：`(class|struct|enum(\s+class)?)\s+[A-Z][a-zA-Z0-9]*`

## 修复指南

1. 将 snake_case 转换为 PascalCase：`data_processor` → `DataProcessor`
2. 去掉无意义的前缀（如 `C`、`T`）：`CMyClass` → `MyClass`
3. 补充语义不清晰的名称：`Proc` → `DataProcessor` 或 `RequestProcessor`
4. 注意：修改类名时需要同步修改文件名（如果项目要求文件名与类名一致）和所有 `#include` 引用

## 审查清单

- [ ] 所有类名使用 PascalCase
- [ ] 所有结构体名使用 PascalCase
- [ ] 所有枚举类型名使用 PascalCase
- [ ] 名称清晰表达了类型的用途
- [ ] 无匈牙利命名法前缀（C、T、I 等）
- [ ] 无 snake_case 或全小写命名
- [ ] 无单字符或过度缩写名称

## 关联页面

- [[cpp-naming-functions]] — 函数命名（camelCase，注意与 PascalCase 的区别）
- [[cpp-naming-variables]] — 变量命名（camelCase）
- [[cpp-naming-constants]] — 常量命名（UPPER_CASE，注意区分）
- [[cpp-naming-private-members]] — 私有成员命名（m_ 前缀）
- [[cpp-naming-namespaces]] — 命名空间命名（全小写点分隔）
