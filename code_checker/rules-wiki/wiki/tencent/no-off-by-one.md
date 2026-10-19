---
domain: tencent
rule_id: tencent-no-off-by-one
title: 防止 Off-By-One
priority: sub
source_file: rules/Tencent_C++_Security_Guide.md
source_section: "§7.2"
status: active
check_method: llm
deterministic_check: false
checkability: llm_checkable
conflicts_with: []
overrides: []
related_pages:
  - [[tencent/no-oob-write]]
---

# 防止 Off-By-One

> 来源：腾讯 C/C++ 安全指南 §7.2 | 风险：内存损坏（高）

## 规则条款

Off-by-one 错误发生在最大值差 1 时，例如没有为 null 终止符留出空间。使用 `strncat` 时必须从剩余空间减去 1（给 `\0` 留位置）。C++ 代码应使用 `std::string`/`std::vector` 而不是原始 C 字符串函数。

## 正确示例

```c++
// 始终为 \0 留出 1 字节
strncat(fullname, firstname, sizeof(fullname) - strlen(fullname) - 1);
strncat(fullname, lastname, sizeof(fullname) - strlen(fullname) - 1);
```

## 错误示例

```c++
char buf[64] = {0};
strncat(buf, long_string, sizeof(buf) - strlen(buf));
// 最后 1 字节被占用 — 没有为 \0 留空间
```

## 检查方法

1. 搜索 `strncat`、`strncpy` 调用，验证第三个参数是否留有 `\0` 空间
2. 搜索循环中比较 `<` vs `<=` 的边界条件
3. LLM 审查

## 修复指南

1. `strncat` 第三个参数始终 `sizeof(buf) - strlen(buf) - 1`
2. C++ 代码中用 `std::string` 完全避免这个问题
3. 数组索引循环使用 `<` 而非 `<=`（除非意图包含最后位置）
