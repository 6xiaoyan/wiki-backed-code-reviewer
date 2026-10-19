---
domain: tencent
rule_id: tencent-no-hardcoded-key
title: 不应该在客户端代码中硬编码对称加密秘钥
priority: sub
source_file: rules/Tencent_C++_Security_Guide.md
source_section: "§2.3"
status: active
check_method: llm
deterministic_check: false
checkability: llm_checkable
conflicts_with: []
overrides: []
related_pages:
  - [[sqlite/must-use-sqlcipher]]
---

# 不应该在客户端代码中硬编码对称加密秘钥

> 来源：腾讯 C/C++ 安全指南 §2.3 | 风险：信息泄露（中）

## 规则条款

客户端二进制中的硬编码 AES/ChaCha20/SM1 密钥提供可忽略的安全性——密钥可通过静态分析（IDA Pro、Ghidra、strings 命令）恢复。优先使用 HTTPS 进行认证加密传输。必须自定义加密时，通过 HTTPS 从服务器获取密钥，通过 HKDF 从会话上下文派生，或通过 RSA/ECDSA + ECDHE 协商。

## 正确示例

```c++
char* g_aes_key;

void Init() {
    g_aes_key = get_key_from_https(user_id, ...);
}
```

## 错误示例

```c++
char g_aes_key[] = { ... };  // 可通过反汇编/strings 恢复

void Foo() {
    AES_func(g_aes_key, input_data, output_data);
}
```

## 检查方法

1. 搜索对称加密函数调用：`AES_*`、`ChaCha20_*`、`EVP_Encrypt*`
2. 搜索字符串常量中可能的密钥模式（Base64、hex 长字符串）
3. LLM 审查：判断密钥是否通过安全渠道获取

## 修复指南

1. 移除所有硬编码的对称密钥
2. 密钥通过 HTTPS 从服务端获取，或通过 ECDHE 密钥协商动态生成
3. 参见 [[sqlite/must-use-sqlcipher]] — 数据库加密场景使用 SQLCipher
