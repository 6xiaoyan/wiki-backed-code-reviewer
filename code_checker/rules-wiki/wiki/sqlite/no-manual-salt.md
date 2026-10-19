---
domain: sqlite
rule_id: sqlite-no-manual-salt
title: 禁止手动管理 Salt/PBKDF2
priority: main
source_file: rules/SQLite加密.md
source_section: "Salt机制说明"
status: active
check_method: regex
deterministic_check: true
checkability: deterministic
conflicts_with: []
overrides: []
related_pages:
  - [[sqlite-no-self-aes]]
  - [[sqlite-must-use-sqlcipher]]
  - [[sqlite-kdf-iterations]]
---

# 禁止手动管理 Salt/PBKDF2

## 规则条款
禁止在应用层手动管理 salt 值或自行实现 PBKDF2 密钥派生过程。SQLCipher 内部已完整实现 PBKDF2-HMAC-SHA1 密钥派生，会自动生成随机 salt 并存储在数据库文件头部（数据库前 16 字节之后的位置）。salt 对用户完全不可见，无需手动生成、存储或管理。

错误做法包括：手动生成随机 salt、每次运行时使用不同的 salt、在数据库外部单独存储 salt、或绕过 SQLCipher 的 KDF 自行通过 PBKDF2 派生密钥再传给 SQLCipher。

## 正确示例
```csharp
// C#: 直接使用密码，SQLCipher 自行管理 salt 和 PBKDF2
SqliteConnection connection = new($"Data Source={_dbPath};");
connection.Open();

// 直接将密码交给 SQLCipher，无需手动处理 salt
using SqliteCommand keyCmd = new(
    $"PRAGMA key = '{EscapeSqlString(_dbPassword)}';", connection);
keyCmd.ExecuteNonQuery();

// SQLCipher 内部会自动：
// 1. 生成随机 salt
// 2. 执行 PBKDF2 迭代（cipher_default_kdf_iter 次）
// 3. 派生 256-bit AES 密钥
// 4. 将 salt 嵌入数据库文件头部
```

```cpp
// C++: 信任 SQLCipher 内部 KDF
sqlite3_open("data.db", &db);
sqlite3_exec(db, "PRAGMA key = 'user_password';", ...);

// SQLCipher 自动：
// - 生成 salt
// - 执行 PBKDF2-HMAC-SHA1
// - 将 salt 存储在数据库头部
// 用户无需任何手动操作
```

```sql
-- 仅需设置密钥和迭代次数，其他由 SQLCipher 自动处理
PRAGMA key = 'secure_password';
PRAGMA cipher_default_kdf_iter = 256000;
```

## 错误示例
```cpp
// 手动生成 salt 并自行执行 PBKDF2（禁止）
unsigned char salt[16];
RAND_bytes(salt, sizeof(salt));  // 手动生成 salt

unsigned char derivedKey[32];
PKCS5_PBKDF2_HMAC_SHA1(
    password, strlen(password),
    salt, sizeof(salt),          // 手动管理 salt
    256000,
    sizeof(derivedKey), derivedKey
);

// 然后用派生密钥作为 PRAGMA key 的值 — 错误
char hexKey[65];
for (int i = 0; i < 32; i++)
    sprintf(hexKey + i * 2, "%02x", derivedKey[i]);
char sql[256];
snprintf(sql, sizeof(sql), "PRAGMA key = \"x'%s'\";", hexKey);
sqlite3_exec(db, sql, ...);
// SQLCipher 会对传入的 key 再次执行 KDF，造成双重派生
```

```csharp
// 每次运行时随机生成 salt — 无法重复打开同一数据库
byte[] salt = RandomNumberGenerator.GetBytes(16);  // 每次不同
byte[] derivedKey = Pbkdf2.Derive(password, salt, 256000, 32);

// 将 salt 单独存储在外部文件 — 引入新攻击面
File.WriteAllBytes("salt.bin", salt);
```

```cpp
// 外部存储和管理 salt
struct DatabaseInfo {
    std::string dbPath;
    std::vector<unsigned char> salt;  // 不应该外部管理
};
DatabaseInfo dbInfo;
dbInfo.salt = loadSaltFromFile("db.salt");  // 来自外部文件
```

## 检查方法
1. 正则检测：搜索 PBKDF2 相关调用（`PKCS5_PBKDF2_HMAC`、`PBKDF2`、`Rfc2898DeriveBytes` 等）
2. 正则检测：搜索 `salt` 变量声明，检查是否有手动 salt 生成逻辑（`RAND_bytes`、`RandomNumberGenerator` 等）
3. 上下文分析：检查数据库相关代码中是否存在自定义的密钥派生流程
4. 检查是否有将派生后的二进制密钥作为 `PRAGMA key` 的值——这会导致 SQLCipher 对密钥再次执行 KDF
5. 检查是否有将 salt 写入外部文件或数据库外存储的逻辑

## 修复指南
1. 删除所有手动 salt 生成代码（`RAND_bytes`、`RandomNumberGenerator.GetBytes` 等）
2. 删除所有手动 PBKDF2 派生代码
3. 直接将原始密码（字符串形式）传递给 `PRAGMA key`，让 SQLCipher 内部处理 salt 和 KDF
4. 删除外部 salt 存储文件和相关读取逻辑
5. 仅通过 `PRAGMA cipher_default_kdf_iter` 控制 KDF 迭代次数
6. 如果需要生成原始密钥（raw key），使用 `PRAGMA key = "x'<hex-encoded-key>';"` 并设置 `PRAGMA cipher_default_use_hmac = OFF`，但一般场景不推荐

## 审查清单
- [ ] 不存在手动 salt 生成代码
- [ ] 不存在手动 PBKDF2 调用
- [ ] PRAGMA key 使用原始密码字符串，非派生密钥
- [ ] 不存在外部 salt 存储文件或逻辑
- [ ] KDF 迭代次数仅通过 `cipher_default_kdf_iter` 设置

## 关联页面
- [[sqlite-no-self-aes]] — 禁止自实现 AES 加密
- [[sqlite-must-use-sqlcipher]] — 必须使用 SQLCipher
- [[sqlite-kdf-iterations]] — KDF 迭代次数
- [[sqlite-pragma-key]] — PRAGMA key 初始化
