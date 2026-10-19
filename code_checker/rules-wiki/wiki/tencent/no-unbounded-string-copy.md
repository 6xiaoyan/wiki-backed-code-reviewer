---
domain: tencent
rule_id: tencent-no-unbounded-copy
title: 不得直接使用无长度限制的字符拷贝函数
priority: sub
source_file: rules/Tencent_C++_Security_Guide.md
source_section: "§1.1"
status: active
check_method: regex
deterministic_check: true
checkability: deterministic
conflicts_with: []
overrides: []
related_pages:
  - [[cpp/no-cstyle-strings-arrays]]
---

# 不得直接使用无长度限制的字符拷贝函数

> 来源：腾讯 C/C++ 安全指南 §1.1 | 风险：缓冲区溢出（高）、信息泄露（中）、拒绝服务（低）

## 规则条款

禁止使用 `strcpy`、`strcat`、`sprintf`、`wcscpy`、`mbscpy` 等无长度限制的字符拷贝函数。应替换为 `_s` 安全版本或 `n` 版本函数（如 `snprintf`、`vsnprintf`）。

使用 `sscanf` 时通过 `%10s` 限制字符串长度，并确保 null 终止。

MSVC 的 `_snprintf`（VS 2015 之前）不保证 null 终止，需手动处理。

安全模式 — 预留一字节并显式 null 终止：

```c++
char buf[101] = {0};
snprintf(buf, sizeof(buf) - 1, "foobar ...", ...);
```

`strncpy` 在复制长度等于 `n` 时会省略 `\0`，同样不安全。

C++ 中优先使用 `string`、`vector` 和更高级的抽象（参见 [[cpp/no-cstyle-strings-arrays]]）。

## 正确示例

```c++
char a[4] = {0};
_snprintf(a, sizeof(a), "%s", "AAAA");
a[sizeof(a) - 1] = '\0';
foo = strlen(a);
```

## 错误示例

```c++
char a[4] = {0};
_snprintf(a, 4, "%s", "AAAA");  // a 是 "AAAA"——没有 \0！
size_t foo = strlen(a);         // 越界读取
```

## 检查方法

1. 搜索以下函数的调用：`strcpy`、`strcat`、`sprintf`、`wcscpy`、`mbscpy`
2. 搜索 `sscanf` 调用是否限制了字符串长度（`%Ns` 格式）
3. 搜索 `strncpy` 调用后是否显式添加了 `\0`
4. 正则表达式：`\b(strcpy|strcat|sprintf|wcscpy|mbscpy)\s*\(`

## 修复指南

1. 将 `strcpy`/`strcat` 替换为 `strncpy`/`strncat` + 显式 `\0` 或 `snprintf`
2. 将 `sprintf` 替换为 `snprintf`
3. C++ 代码中优先使用 `std::string` 替代 C 风格字符数组
4. 对所有 `_snprintf` 调用后显式添加 `buf[sizeof(buf)-1] = '\0'`

## 审查清单

- [ ] 无 `strcpy`/`strcat`/`sprintf`/`wcscpy`/`mbscpy` 直接调用
- [ ] `snprintf` 调用后有显式 null 终止
- [ ] `strncpy` 调用后正确添加了 `\0`
- [ ] C++ 代码优先使用 `std::string`

## 关联页面

- [[cpp/no-cstyle-strings-arrays]] — 公司规则：禁止 C 风格数组/字符串
