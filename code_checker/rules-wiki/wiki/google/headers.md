---
domain: google
rule_id: google-headers
title: 头文件规范（Google C++ Style Guide 对照）
priority: sub
source_file: rules/Google_C++_Style_Guide.md
source_section: "第 1 章"
status: active
check_method: regex
deterministic_check: true
checkability: deterministic
conflicts_with:
  - "cpp/forward-declarations"
overrides: []
related_pages:
  - [[cpp/include-order]]
  - [[cpp/header-guards]]
  - [[cpp/inline-functions]]
  - [[cpp/forward-declarations]]
---

# 头文件规范（Google C++ Style Guide 对照）

> 来源：Google C++ Style Guide 第 1 章 | 部分与公司规则冲突，**公司规则为准**

## 与公司规则的对照

| Google 条款 | 公司规则 | 一致性 |
|------------|---------|--------|
| 头文件应自给自足（能独立编译） | — | 公司规则未明确，可作为补充 |
| `#define` 防护符命名 `PROJECT_PATH_FILE_H_` | [[cpp/header-guards]] `PROJECT_MODULE_FILE_H_` | ⚠️ 格式细微差异，**公司规则为准** |
| 直接导入依赖，不依赖间接导入 | — | 公司规则未明确，可作为补充 |
| **避免前向声明**，直接导入头文件 | [[cpp/forward-declarations]] **优先使用前向声明** | ❌ **冲突！公司规则优先：用前向声明** |
| 内联函数 ≤10 行 | [[cpp/inline-functions]] | ✅ 一致 |
| include 顺序：配套头 → C系统 → C++标准 → 其他库 → 本项目 | [[cpp/include-order]] 系统→第三方→项目 | ⚠️ 公司更宽松，**公司规则为准** |

## ❌ 关键冲突：前向声明

| 方面 | Google | 公司 |
|------|--------|------|
| 前向声明 | **避免使用**，直接 `#include` | [[cpp/forward-declarations]] **优先使用** |
| 裁决 | **以公司规则为准** | |

## 补充条款（公司规则未覆盖）

1. **禁止 `-inl.h` 文件**：过去将实现放到 `-inl.h` 文件的做法已被禁止
2. **`.inc` 文件**：少数用于特殊位置的文件可以不自给自足，使用 `.inc` 扩展名，尽量少用
3. **直接导入依赖**：`foo.cc` 使用了 `bar.h` 的符号，即使 `foo.h` 已导入 `bar.h`，`foo.cc` 也必须直接导入 `bar.h`
