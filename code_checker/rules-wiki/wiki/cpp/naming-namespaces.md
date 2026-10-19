---
domain: cpp
rule_id: cpp-naming-namespaces
title: 命名空间命名规范
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
  - [[cpp-naming-constants]]
  - [[cpp-naming-private-members]]
---

# 命名空间命名规范

## 规则条款

命名空间必须使用**全小写字母**，层级之间用 `::` 分隔（C++17 嵌套命名空间语法 `namespace A::B::C` 或传统嵌套写法均可）。命名空间用于划分代码模块，避免不同模块的类/函数重名，用小写字母和点 `.` 体现层级关系（从大模块到小模块）。
按用途分类：

- **业务模块**：按业务域划分，从顶级到具体子模块，如 `com.company.shop.user`（`com` 为顶级域名，`company` 为公司名，`shop` 为商城模块，`user` 为用户子模块）
- **功能模块**：按功能/工具划分，如 `utils.date.format`（`utils` 为工具类模块，`date` 为日期子模块，`format` 为格式化相关功能）

推荐使用 C++17 嵌套命名空间语法：`namespace com::company::shop::user { }`

## 正确示例

```cpp
// 业务模块 — 按业务域层级划分
namespace com::company::shop::user {
    class UserService { /* ... */ };
    class UserRepository { /* ... */ };
}

namespace com::company::shop::order {
    class OrderProcessor { /* ... */ };
}

// 功能模块 — 按功能类型划分
namespace utils::date::format {
    std::string toISO8601(const DateTime& dt);
    std::string toReadable(const DateTime& dt);
}

namespace utils::crypto::hash {
    std::string sha256(const std::string& input);
    std::string md5(const std::string& input);
}

// 嵌套写法（传统兼容方式，与上述效果等价）
namespace utils {
    namespace network {
        namespace http {
            class HttpClient { /* ... */ };
        }
    }
}

// 单层命名空间
namespace core {
    class Engine { /* ... */ };
}

namespace config {
    const int MAX_CONNECTIONS = 100;
}
```

## 错误示例

```cpp
// 错误：PascalCase
namespace Utils::DateFormat {         // 应为 utils::date::format 或 utils::dateformat
    // ...
}

// 错误：camelCase
namespace utils::dateFormat {         // 应为 utils::date::format（用点分层）
    // ...
}

// 错误：snake_case
namespace utils::date_format {        // 应为 utils::date::format（用点分层）
    // ...
}

// 错误：UPPER_CASE
namespace UTILS::NETWORK {            // 应为 utils::network
    // ...
}

// 错误：混合大小写
namespace Utils::network::HTTP {      // 应为 utils::network::http
    // ...
}

// 错误：层级过浅或名称不清晰
namespace u {                          // 应使用有意义名称，如 utils
    // ...
}

namespace my_stuff {                   // 应使用正规命名，如 com::company::product
    // ...
}
```

## 检查方法
1. 扫描所有 `namespace` 声明
2. 验证命名空间名是否全部小写
3. 验证层级之间是否用 `::`（声明中）或 `.`（概念上）分隔
4. 验证每个层级段是否有明确含义
5. 验证是否避免单字符命名空间名
6. 正则模式（C++17 嵌套）：`namespace\s+[a-z][a-z0-9]*(?:::[a-z][a-z0-9]*)*\s*\{?`
7. 正则模式（传统嵌套）：`namespace\s+[a-z][a-z0-9]*\s*\{`
8. 反模式检测：`namespace\s+[A-Z]`（大写开头）

## 修复指南

1. 将 PascalCase 转为全小写：`Utils` → `utils`
2. 将 camelCase 转为点分层：`dateFormat` → `date::format`（或 `date.format` 概念上）
3. 将 snake_case 转为点分层：`date_format` → `date::format`
4. 将 UPPER_CASE 转为小写：`NETWORK` → `network`
5. 补充无意义名称的语义：`u` → `utils`，`ns` → `network::socket`
6. 将匿名或模糊命名空间改为具体含义的名称
7. 注意：修改命名空间名需要同步修改所有 `using namespace` 声明和嵌套引用
8. 建议将传统嵌套写法迁移为 C++17 嵌套语法以简化代码

## 审查清单

- [ ] 所有命名空间名使用全小写字母
- [ ] 层级之间用 :: 分隔（或概念上用 . 表示）
- [ ] 命名空间层级从大到小，体现清晰的模块结构
- [ ] 每个层级段有明确含义
- [ ] 无 PascalCase、camelCase、snake_case 或 UPPER_CASE 命名空间
- [ ] 无单字符命名空间名
- [ ] 命名空间命名与目录结构一致（推荐）

## 关联页面

- [[cpp-naming-classes]] — 类命名（PascalCase，在命名空间内部使用）
- [[cpp-naming-functions]] — 函数命名（camelCase，在命名空间内部使用）
- [[cpp-naming-variables]] — 变量命名（camelCase，在命名空间内部使用）
- [[cpp-naming-constants]] — 常量命名（UPPER_CASE，可定义在命名空间内）
- [[cpp-naming-private-members]] — 私有成员命名（m_ 前缀，与命名空间规则无直接关系）
