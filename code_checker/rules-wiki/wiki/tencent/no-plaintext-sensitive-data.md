---
domain: tencent
rule_id: tencent-no-plaintext-auth
title: 不得明文存储用户密码等敏感数据
priority: sub
source_file: rules/Tencent_C++_Security_Guide.md
source_section: "§4.1"
status: active
check_method: llm
deterministic_check: false
checkability: llm_checkable
conflicts_with: []
overrides: []
related_pages:
  - [[sqlite/must-use-sqlcipher]]
  - [[sqlite/pragma-key]]
---

# 不得明文存储用户密码等敏感数据

> 来源：腾讯 C/C++ 安全指南 §4.1 | 风险：敏感数据泄露（高）

## 规则条款

密码必须在存储前使用 Argon2、scrypt、bcrypt 或 PBKDF2 进行哈希处理。参考 [password-hashing.net](https://password-hashing.net/)。敏感数据必须在传输（HTTPS）和静态存储（如 SQLCipher）中加密。绝不能在日志、数据库、文件中以明文存储密码。

## 正确示例

```c++
// 密码哈希（使用 libsodium）
char hashed_password[crypto_pwhash_STRBYTES];
if (crypto_pwhash_str(hashed_password, password, strlen(password),
        crypto_pwhash_OPSLIMIT_INTERACTIVE,
        crypto_pwhash_MEMLIMIT_INTERACTIVE) != 0) {
    // 处理错误
}
// 存储 hashed_password，不存储原始 password
```

## 错误示例

```c++
// 绝不要这样做：明文存储密码
FILE* f = fopen("users.txt", "a");
fprintf(f, "user=%s, password=%s\n", username, password);  // 明文密码！
```

## 检查方法

1. 搜索字符串和文件输出中的 "password"、"passwd"、"pwd"、"secret"、"key" 字段
2. 检查敏感数据是否在存储前被哈希或加密
3. LLM 审查：判断敏感信息是否被正确保护

## 修复指南

1. 密码使用 Argon2id / scrypt / bcrypt / PBKDF2 哈希
2. 配置/数据库加密参见 [[sqlite/must-use-sqlcipher]]
3. 敏感数据传输使用 HTTPS/TLS
