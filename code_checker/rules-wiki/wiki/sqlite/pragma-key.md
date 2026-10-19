---
domain: sqlite
rule_id: sqlite-pragma-key
title: PRAGMA key 初始化
priority: main
source_file: rules/SQLite加密.md
source_section: "加密原理/启用加密的关键指令"
status: active
check_method: regex
deterministic_check: true
checkability: deterministic
conflicts_with: []
overrides: []
related_pages:
  - [[sqlite-must-use-sqlcipher]]
  - [[sqlite-kdf-iterations]]
---

# PRAGMA key 初始化

## 规则条款
数据库连接初始化时必须执行 `PRAGMA key = 'your_password';` 设置加密密钥。此 PRAGMA 指令必须在连接打开后、执行任何其他数据库操作（包括读取 schema、创建表、查询数据）之前立即执行，否则 SQLCipher 无法正确加解密数据库。

密钥应当从安全的配置源（如环境变量、密钥管理服务、加密配置文件）获取，不得在源代码中硬编码明文密码。

## 正确示例
```csharp
// C#: 连接后立即设置 PRAGMA key
private SqliteConnection CreateEncryptedConnection()
{
    SqliteConnection connection = new($"Data Source={_dbPath};");
    connection.Open();

    // 第一步：设置加密密钥
    using SqliteCommand keyCmd = new(
        $"PRAGMA key = '{EscapeSqlString(_dbPassword)}';", connection);
    keyCmd.ExecuteNonQuery();

    // 第二步：强化 KDF 参数
    using SqliteCommand kdfCmd = new(
        "PRAGMA cipher_default_kdf_iter = 256000;", connection);
    kdfCmd.ExecuteNonQuery();

    return connection;
}
```

```cpp
// C++: sqlcipher 连接初始化
#include <sqlcipher/sqlite3.h>

int openEncryptedDb(const char* path, const char* password) {
    sqlite3* db = nullptr;
    int rc = sqlite3_open(path, &db);
    if (rc != SQLITE_OK) return rc;

    // 立即设置密钥
    rc = sqlite3_exec(db, 
        "PRAGMA key = 'secure_password';", nullptr, nullptr, nullptr);
    if (rc != SQLITE_OK) {
        sqlite3_close(db);
        return rc;
    }

    // 设置 KDF 迭代次数
    sqlite3_exec(db, 
        "PRAGMA cipher_default_kdf_iter = 256000;", 
        nullptr, nullptr, nullptr);

    return SQLITE_OK;
}
```

```sql
-- SQL: 连接后的第一条指令
PRAGMA key = 'your_secure_password';
-- 之后才能执行其他操作
SELECT name FROM sqlite_master WHERE type = 'table';
```

## 错误示例
```csharp
// 连接打开后未设置 PRAGMA key
SqliteConnection connection = new($"Data Source={_dbPath};");
connection.Open();
// 直接查询 — 数据库未解密，操作失败或读到正确数据仅因未加密
var cmd = new SqliteCommand("SELECT * FROM users;", connection);
cmd.ExecuteReader();
```

```csharp
// 在源代码中硬编码明文密钥
const string DbPassword = "MySecretPassword123";  // 硬编码，不安全
using SqliteCommand keyCmd = new(
    $"PRAGMA key = '{DbPassword}';", connection);
```

```cpp
// 密钥硬编码
sqlite3_exec(db, "PRAGMA key = 'hardcoded123';", ...);  // 禁止

// PRAGMA key 执行顺序错误 — 先建表再设密钥
sqlite3_exec(db, "CREATE TABLE users (...);", ...);  // 在未设密钥前操作
sqlite3_exec(db, "PRAGMA key = 'password';", ...);  // 已太迟
```

## 检查方法
1. 正则检测：搜索 `PRAGMA\s+key\s*=` 确认代码中存在密钥设置语句
2. 检查 `PRAGMA key` 语句是否在数据库连接打开后、任何其他 SQL 操作之前执行
3. 扫描密钥来源：检查密钥是否来自变量、配置文件、环境变量等外部源
4. 硬编码检测：搜索 `PRAGMA key = '` 后是否直接跟随字面量字符串（非变量名），标记为违规
5. 对于 C# 项目，搜索 `SqliteConnection.Open()` 调用点，检查紧随其后的代码是否立即设置了 PRAGMA key

## 修复指南
1. 确保每次 `connection.Open()` 后立即执行 `PRAGMA key`
2. 将密钥从源代码中移除，改为从环境变量或安全配置文件读取
3. C#：使用 `EscapeSqlString()` 转义密钥中的特殊字符，防止 SQL 注入
4. C++：使用参数化方式或预编译语句传递密钥
5. 在 `PRAGMA key` 之后立即执行 `PRAGMA cipher_default_kdf_iter = 256000`
6. 考虑使用 `sqlcipher_export()` 函数在更改密码时安全地重新加密数据库

## 审查清单
- [ ] 每次数据库连接打开后都执行了 `PRAGMA key`
- [ ] `PRAGMA key` 在所有其他 SQL 操作之前执行
- [ ] 密钥不在源代码中硬编码
- [ ] 密钥从安全的外部源获取（环境变量、密钥管理服务等）
- [ ] 密钥字符串已正确转义，防止注入
- [ ] `PRAGMA cipher_default_kdf_iter` 也已设置

## 关联页面
- [[sqlite-must-use-sqlcipher]] — 必须使用 SQLCipher
- [[sqlite-kdf-iterations]] — KDF 迭代次数
- [[sqlite-no-manual-salt]] — 禁止手动管理 Salt/PBKDF2
