---
domain: sqlite
rule_id: sqlite-no-self-aes
title: 禁止自实现 AES 加密
priority: main
source_file: rules/SQLite加密.md
source_section: "技术组成/加密算法"
status: active
check_method: regex
deterministic_check: true
checkability: deterministic
conflicts_with: []
overrides: []
related_pages:
  - [[sqlite-must-use-sqlcipher]]
  - [[sqlite-no-manual-salt]]
---

# 禁止自实现 AES 加密

## 规则条款
禁止自行调用 `AES_encrypt` / `EVP_*` / `QAESEncryption` 等加密 API 来实现数据库加密方案以替代 SQLCipher。SQLCipher 内部使用 AES-256-CBC 进行数据库页级加密、HMAC-SHA512 进行完整性校验、PBKDF2 进行密钥派生，已提供完整的透明数据库加密方案。

自行实现数据库加密存在以下风险：未正确处理页边界和页内偏移、缺少完整性校验导致数据篡改不可检测、密钥管理漏洞、未正确实现 CBC 模式的 IV 生成策略、并发访问时加密状态错误等。

## 正确示例
```csharp
// C#: 使用 SQLCipher，不自行调用任何加密 API
SqliteConnection connection = new($"Data Source={_dbPath};");
connection.Open();

// SQLCipher 内部自动完成 AES-256-CBC 加密
using SqliteCommand keyCmd = new(
    $"PRAGMA key = '{EscapeSqlString(_dbPassword)}';", connection);
keyCmd.ExecuteNonQuery();
using SqliteCommand kdfCmd = new(
    "PRAGMA cipher_default_kdf_iter = 256000;", connection);
kdfCmd.ExecuteNonQuery();

// 之后所有读写操作自动透明加解密
using SqliteCommand cmd = new("CREATE TABLE IF NOT EXISTS users (...);", connection);
cmd.ExecuteNonQuery();
```

```cpp
// C++: 直接使用 SQLCipher，无手动加密代码
#include <sqlcipher/sqlite3.h>

sqlite3* db;
sqlite3_open("encrypted.db", &db);
sqlite3_exec(db, "PRAGMA key = 'secure_pwd';", nullptr, nullptr, nullptr);
sqlite3_exec(db, "PRAGMA cipher_default_kdf_iter = 256000;", nullptr, nullptr, nullptr);

// 正常操作 — 加密对应用层完全透明
sqlite3_exec(db, "INSERT INTO users VALUES (1, 'Alice');", ...);
```

```sql
-- SQLCipher 提供完整加密，无需手动加密任何数据
PRAGMA key = 'secure_password';
PRAGMA cipher_default_kdf_iter = 256000;
-- 所有表和数据的读写均由 SQLCipher 透明加密
```

## 错误示例
```cpp
// 使用 OpenSSL EVP API 自行加密数据库文件（禁止）
#include <openssl/evp.h>

void selfEncryptDatabase(const std::string& dbPath, const std::string& key) {
    std::ifstream in(dbPath, std::ios::binary);
    std::ofstream out(dbPath + ".enc", std::ios::binary);

    EVP_CIPHER_CTX* ctx = EVP_CIPHER_CTX_new();
    EVP_EncryptInit_ex(ctx, EVP_aes_256_cbc(), nullptr, 
                       key.data(), iv);
    // ... 手动加密每个数据块
    // 问题：SQLite 内部页结构被破坏，无法正常读写
}
```

```cpp
// 直接调用 OpenSSL AES 加密函数（禁止）
#include <openssl/aes.h>

void encryptPage(char* pageData, int pageSize, const unsigned char* key) {
    AES_KEY aesKey;
    AES_set_encrypt_key(key, 256, &aesKey);
    for (int i = 0; i < pageSize; i += AES_BLOCK_SIZE) {
        AES_encrypt(pageData + i, pageData + i, &aesKey);
    }
    // 问题：无完整性校验，无 IV 管理，无并发支持
}
```

```cpp
// Qt: 使用 QAESEncryption 自行加密数据库（禁止）
#include <QAESEncryption>

QByteArray encryptedData = QAESEncryption::encrypt(
    plainData, key, QAESEncryption::AES_256, QAESEncryption::CBC);
// 问题：绕过了 SQLCipher 的页级加密和完整性校验机制
```

```csharp
// 自实现加密包装层，绕过了 SQLCipher（禁止）
public class SelfEncryptedDb
{
    private readonly byte[] _key;

    public void Write(string table, byte[] data)
    {
        // 自行 AES 加密数据
        byte[] encrypted = Aes.Encrypt(data, _key);
        // 写入纯 SQLite 数据库
        _plainSqlite.Insert(table, encrypted);
        // 问题：仅加密了数据内容，数据库 schema 和内部分配结构仍明文
    }
}
```

## 检查方法
1. 正则检测：搜索 `AES_encrypt`、`AES_set_encrypt_key`（OpenSSL AES API）
2. 正则检测：搜索 `EVP_EncryptInit`、`EVP_DecryptInit`、`EVP_CIPHER_CTX`（OpenSSL EVP API）
3. 正则检测：搜索 `QAESEncryption`（Qt 加密 API）
4. 正则检测：搜索 `Aes.`、`AesManaged`、`Aes.Create`（C# AES API）
5. 上下文分析：检查以上 API 调用是否出现在数据库相关代码路径中
6. 如果 AES 调用出现在非数据库上下文中（如网络通信加密），可通过上下文排除

## 修复指南
1. 删除所有自行调用 AES 加密 API 来加密数据库数据的代码
2. 删除自实现的"打开数据库 → 解密文件 → 操作 → 关闭前加密写回"的包装层
3. 改为直接使用 SQLCipher，将数据库路径指向 SQLCipher 加密的文件
4. 在连接初始化时设置 `PRAGMA key`，让 SQLCipher 透明处理所有加解密
5. 如果已有自加密的数据库数据，需要写迁移脚本：使用自实现代码解密 → 导入 SQLCipher 加密的数据库
6. 对于非数据库用途的 AES 调用（如网络通信、配置文件加密等），保留但添加 `// NOLINT` 注释说明用途

## 审查清单
- [ ] 不存在 `AES_encrypt` / `EVP_EncryptInit` 在数据库代码路径中
- [ ] 不存在 `QAESEncryption` 用于数据库加密
- [ ] 不存在 C# `Aes.Create` / `AesManaged` 在数据库操作代码中
- [ ] 不存在自实现的数据库文件加密/解密包装层
- [ ] 非数据库用途的 AES 调用已标注 NOLINT 并说明用途

## 关联页面
- [[sqlite-must-use-sqlcipher]] — 必须使用 SQLCipher
- [[sqlite-no-manual-salt]] — 禁止手动管理 Salt/PBKDF2
- [[sqlite-pragma-key]] — PRAGMA key 初始化
