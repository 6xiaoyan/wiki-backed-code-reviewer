---
domain: tencent
rule_id: tencent-use-csprng
title: 在需要高强度安全加密时不应使用弱 PRNG 函数
priority: sub
source_file: rules/Tencent_C++_Security_Guide.md
source_section: "§4.4"
status: active
check_method: regex
deterministic_check: true
checkability: deterministic
conflicts_with: []
overrides: []
related_pages: []
---

# 在需要高强度安全加密时不应使用弱 PRNG 函数

> 来源：腾讯 C/C++ 安全指南 §4.4 | 风险：敏感数据泄露（高）

## 规则条款

生成 AES/ChaCha20/SM1 密钥/IV/nonce，或 RSA/ECDSA/ECDH 私钥时，必须使用密码学安全的伪随机数生成器（CSPRNG）——绝不用 `rand()`、`random()` 或自定义 LCG。

## 正确示例（按平台）

| 平台 | 推荐函数 |
|------|---------|
| OpenSSL | `RAND_bytes()` |
| libsodium | `randombytes_buf()` |
| Linux | `getrandom()` 或 `/dev/urandom` |
| Apple iOS | `SecRandomCopyBytes()` |
| Windows | `BCryptGenRandom()`、`CryptGenRandom()` |

## 错误示例

```c++
// 绝不用于密钥生成！
int key[8];
for (int i = 0; i < 8; i++)
    key[i] = rand();  // rand() 输出可预测
```

## 检查方法

1. 搜索加密上下文（AES、RSA、ECDSA 等密钥/IV 生成）中的 `rand()` 和 `random()` 调用
2. 搜索自定义 PRNG 实现（线性同余、梅森旋转用于安全用途）
3. 正则表达式：`\b(?:rand|random)\s*\(\)` 出现在加密相关代码中

## 修复指南

1. 将 `rand()` / `random()` 替换为平台 CSPRNG
2. 统一封装：在项目中创建一个 `GenerateRandomBytes()` 函数，内部使用适当平台 API
3. 永远不要自己实现加密随机数生成器
