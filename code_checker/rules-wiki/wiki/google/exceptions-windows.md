---
domain: google
rule_id: google-exceptions-windows
title: 规则特例与 Windows 代码（Google 对照）
priority: sub
source_file: rules/Google_C++_Style_Guide.md
source_section: "第 10 章"
status: active
check_method: llm
deterministic_check: false
checkability: advisory_only
conflicts_with: []
overrides: []
related_pages: []
---

# 规则特例与 Windows 代码（Google C++ Style Guide 对照）

> 来源：Google C++ Style Guide 第 10 章 | 仅供参考

## 现有不合规范的代码

对于已存在且不符合当前风格规范的代码，为保持项目内部一致性可暂时不遵循本指南。但新代码必须遵循规范。

## Windows 代码补充条款

| 条款 | 说明 |
|------|------|
| 禁用匈牙利命名法 | 不使用 `iNum`、`szName` 等前缀 |
| 慎用 Windows 原生类型 | 避免 `DWORD`、`HANDLE` 等（用 `uint32_t`、`void*` 替代） |
| 编译器警告 ≥3 级 | 所有警告当作错误处理（`/WX`） |
| 不使用 `#pragma once` | 采用头文件保护宏 |
| 避免非标准扩展 | 使用标准 C++ |

## Windows 例外

以下场景允许打破部分规则：
- **COM/ATL/WTL**：允许多重继承
- **ATL/STL 异常处理**：可启用编译器异常
- **预编译头文件**（`stdafx.h`）：允许

## 与公司规则的关系

公司规则体系中未明确覆盖 Windows 特定规范。以上条款可作为 Windows 平台项目的补充参考。
