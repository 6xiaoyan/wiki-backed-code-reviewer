---
domain: tencent
rule_id: tencent-no-user-format-string
title: 不应当把用户可修改的字符串作为 printf 系列函数的 format 参数
priority: sub
source_file: rules/Tencent_C++_Security_Guide.md
source_section: "§1.6"
status: active
check_method: regex
deterministic_check: true
checkability: deterministic
conflicts_with: []
overrides: []
related_pages: []
---

# 不应当把用户可修改的字符串作为 printf 系列函数的 format 参数

> 来源：腾讯 C/C++ 安全指南 §1.6 | 风险：代码执行（高）、内存损坏（高）、信息泄露（中）、拒绝服务（低）

## 规则条款

如果用户控制格式字符串，可以使用 `%n`、`%p` 等写入任意内存或泄露数据。对于 Wi-Fi 名称、设备名称和类似用户可控字符串尤其关键。格式字符串参数必须始终是字符串字面量（或受信任的常量），绝不能来自用户输入。

## 正确示例

```c++
snprintf(buf, sizeof(buf), "%s", wifi_name);
```

## 错误示例

```c++
snprintf(buf, sizeof(buf), wifi_name);  // wifi_name 是攻击者可控的
// 如果 wifi_name = "%p%p%p%p%n"，攻击者可写任意内存
```

## 检查方法

1. 搜索 `printf`、`sprintf`、`snprintf`、`vprintf`、`fprintf` 调用
2. 检查第一个参数（格式字符串）是否来自用户输入或非字面量
3. 正则表达式：`\b(?:printf|sprintf|snprintf|fprintf)\s*\([^"]` 匹配非字面量格式字符串
4. 排除使用 `"%s"` 等字面量常量的合法调用

## 修复指南

1. 格式字符串必须始终为字符串字面量
2. 用户输入通过 `%s` 等占位符传入，而非作为格式字符串
3. 如需动态格式，构建时确保格式字符串不受用户控制

## 审查清单

- [ ] 所有 printf 系列函数的格式参数为字符串字面量
- [ ] 用户输入通过 `%s` 占位符传参，不作为格式字符串
