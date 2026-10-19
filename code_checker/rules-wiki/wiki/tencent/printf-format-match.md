---
domain: tencent
rule_id: tencent-printf-format-match
title: printf 系列参数必须对应
priority: sub
source_file: rules/Tencent_C++_Security_Guide.md
source_section: "§1.4"
status: active
check_method: llm
deterministic_check: false
checkability: llm_checkable
conflicts_with: []
overrides: []
related_pages: []
---

# printf 系列参数必须对应

> 来源：腾讯 C/C++ 安全指南 §1.4 | 风险：信息泄露（中）

## 规则条款

`printf` 系列函数（`sprintf`、`snprintf`、`vprintf` 等）的格式说明符必须与参数类型精确匹配。不匹配的 `%p` 可能暴露内部指针值，破坏 ASLR。

## 正确示例

```c++
char buf[1000] = {0};
snprintf(buf, sizeof(buf), "%d: %s", id, some_string);
```

## 错误示例

```c++
char buf[1000] = {0};
snprintf(buf, sizeof(buf), "%d: %p", id, some_string);
// %p 应该是 %s — 向客户端泄露原始指针
```

## 检查方法

1. 搜索 `printf`、`sprintf`、`snprintf`、`vprintf`、`fprintf` 调用
2. 检查格式字符串中每个 `%` 说明符与对应参数的类型是否匹配
3. 特别关注 `%p` 的使用——它泄露原始指针值
4. LLM 审查：判断参数类型与格式说明符的一致性

## 修复指南

1. 确保格式说明符类型与参数类型一致：`%d`→int, `%s`→char*, `%p`→pointer（仅调试）
2. 避免在生产代码中使用 `%p`
3. 优先使用 C++ 的 `std::format`（C++20）或 `std::ostringstream` 替代 printf 系列
4. 编译时启用 `-Wformat` 警告（`-Wall` 中）

## 审查清单

- [ ] printf 系列函数的格式说明符与参数类型匹配
- [ ] 生产代码中无 `%p` 格式说明符
- [ ] 编译时 `-Wformat` 警告已启用
