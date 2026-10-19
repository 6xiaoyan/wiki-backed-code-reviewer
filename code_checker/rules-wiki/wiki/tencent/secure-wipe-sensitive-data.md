---
domain: tencent
rule_id: tencent-secure-wipe
title: 内存中的用户密码等敏感数据应该安全抹除
priority: sub
source_file: rules/Tencent_C++_Security_Guide.md
source_section: "§4.2"
status: active
check_method: llm
deterministic_check: false
checkability: llm_checkable
conflicts_with: []
overrides: []
related_pages: []
---

# 内存中的用户密码等敏感数据应该安全抹除

> 来源：腾讯 C/C++ 安全指南 §4.2 | 风险：敏感信息泄露（高）

## 规则条款

临时密码缓冲区必须在内存释放或离开作用域前显式清除（归零）。编译器优化可能丢弃朴素的 `memset` 调用——优化器看到 `memset` 后变量不再使用，会直接删除 `memset`。必须使用安全擦除函数如 `OPENSSL_cleanse` 或 `explicit_bzero`。

## 正确示例

```c++
{
    std::string user_password(100, '\0');
    snprintf(&user_password[0], user_password.size(), "password: %s", password_from_input);
    // ... 使用密码 ...
    OPENSSL_cleanse(&user_password[0], user_password.size());
}
```

## 错误示例

```c++
{
    std::string user_password(100, '\0');
    snprintf(&user_password[0], user_password.size(), "password: %s", password_from_input);
    // 作用域结束后 user_password 仍包含密码在已释放的内存中
    // 朴素的 memset 可能被编译器优化掉
}
```

## 检查方法

1. 搜索密码/密钥缓冲区的 `memset(ptr, 0, size)` 调用——可能被编译器优化掉
2. 检查是否使用了 `OPENSSL_cleanse`、`explicit_bzero`、`SecureZeroMemory` 或 `sodium_memzero`
3. LLM 审查

## 修复指南

1. 使用 `OPENSSL_cleanse()`（OpenSSL）或 `sodium_memzero()`（libsodium）
2. Windows: `SecureZeroMemory()`
3. C11: `memset_s()`（带优化屏障保证）
