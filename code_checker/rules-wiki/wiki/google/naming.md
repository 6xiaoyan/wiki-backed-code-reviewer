---
domain: google
rule_id: google-naming
title: 命名约定（Google C++ Style Guide 对照）
priority: sub
source_file: rules/Google_C++_Style_Guide.md
source_section: "第 7 章"
status: active
check_method: regex
deterministic_check: true
checkability: deterministic
conflicts_with:
  - "cpp/naming-classes"
  - "cpp/naming-functions"
  - "cpp/naming-variables"
  - "cpp/naming-constants"
  - "cpp/naming-private-members"
overrides: []
related_pages:
  - [[cpp/naming-classes]]
  - [[cpp/naming-functions]]
  - [[cpp/naming-variables]]
  - [[cpp/naming-constants]]
  - [[cpp/naming-private-members]]
  - [[cpp/naming-namespaces]]
---

# 命名约定（Google C++ Style Guide 对照）

> 来源：Google C++ Style Guide 第 7 章 | **全面冲突，公司规则为准**

## ❌ 命名约定全面冲突

Google 的命名风格与公司规则在几乎所有方面都不同。**全部以公司规则为准。**

| 项目 | Google 风格 | 公司规则 | 裁决 |
|------|-----------|---------|------|
| **类/类型** | `PascalCase` | [[cpp/naming-classes]] `PascalCase` | ✅ 唯一一致 |
| **函数** | `PascalCase`（如 `MyExcitingFunction()`） | [[cpp/naming-functions]] **`camelCase`**（首字母小写） | ❌ **公司规则为准** |
| **变量** | `snake_case`（全小写下划线） | [[cpp/naming-variables]] **`camelCase`** | ❌ **公司规则为准** |
| **常量** | `k` + `CamelCase`（如 `kDaysInAWeek`） | [[cpp/naming-constants]] **`UPPER_CASE`** | ❌ **公司规则为准** |
| **类成员** | 尾部下划线 `table_name_` | [[cpp/naming-private-members]] **`m_camelCase`** 或 `camelCase_` | ❌ **公司规则为准** |
| **文件命名** | `snake_case.cc` / `.h` | 公司约定不同 | ❌ **公司规则为准** |
| **枚举** | `kEnumName` 或 `ENUM_NAME` | 常量风格 | ⚠️ 依具体情况 |
| **命名空间** | 全小写 | [[cpp/naming-namespaces]] 全小写 | ✅ 一致 |
| **宏** | `UPPER_CASE` | [[cpp/no-macro-constants]] 不推荐用宏 | ✅ 一致 |

## Getter/Setter 命名

Google 风格：`my_exciting_member_variable()` / `set_my_exciting_member_variable()`

公司 Qt 规则：[[qt/getter-no-get]]（getter 不加 "get" 前缀）

**以公司规则为准。**
