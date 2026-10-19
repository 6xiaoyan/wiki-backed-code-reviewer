---
domain: sqlite
rule_id: sqlite-must-use-sqlcipher
title: 必须使用 SQLCipher
priority: main
source_file: rules/SQLite加密.md
source_section: "概述"
status: active
check_method: regex
deterministic_check: true
checkability: deterministic
conflicts_with: []
overrides: []
related_pages:
  - [[sqlite-pragma-key]]
  - [[sqlite-no-self-aes]]
---

# 必须使用 SQLCipher

## 规则条款
必须使用 SQLCipher 作为 SQLite 的加密扩展，实现数据库文件级透明加密（Transparent Database Encryption）。数据库文件在磁盘上以加密形式存在，未提供正确密钥时无法读取任何内容。SQLCipher 内部使用 AES-256-CBC 进行数据加密、HMAC-SHA512 进行完整性校验、PBKDF2 进行密钥派生。

禁止使用未经加密的纯 SQLite，也禁止在 SQLite 之外自行封装一层加密逻辑来替代 SQLCipher。

## 正确示例
```cpp
// C++: 链接 SQLCipher 库（非纯 SQLite）
// CMakeLists.txt
find_package(SQLCipher REQUIRED)
target_link_libraries(myapp PRIVATE SQLCipher::SQLCipher)

// 或通过 vcpkg
// vcpkg install sqlcipher
```

```csharp
// C#: 使用 Microsoft.Data.Sqlite + SQLCipher 扩展
// .csproj 引用
// <PackageReference Include="Microsoft.Data.Sqlite" Version="..." />

using Microsoft.Data.Sqlite;

private SqliteConnection CreateEncryptedConnection()
{
    SqliteConnection connection = new($"Data Source={_dbPath};");
    connection.Open();

    using SqliteCommand keyCmd = new(
        $"PRAGMA key = '{EscapeSqlString(_dbPassword)}';", connection);
    keyCmd.ExecuteNonQuery();
    using SqliteCommand kdfCmd = new(
        "PRAGMA cipher_default_kdf_iter = 256000;", connection);
    kdfCmd.ExecuteNonQuery();

    return connection;
}
```

```sql
-- 验证 SQLCipher 是否已加载
PRAGMA cipher_version;
-- 应返回 SQLCipher 版本号，如 "3.x.x community"
```

## 错误示例
```cpp
// 使用纯 SQLite 库，无加密
#include <sqlite3.h>  // 链接了未加密的 sqlite3 库

sqlite3* db;
sqlite3_open("data.db", &db);
// 数据库文件明文存储在磁盘，任意工具可直接读取
```

```csharp
// 使用未加密的 SQLite 连接
SqliteConnection connection = new($"Data Source={_dbPath};");
connection.Open();
// 未执行 PRAGMA key，数据库明文存储
```

```cpp
// 自实现加密包装层代替 SQLCipher
// 先加解密文件再丢给纯 SQLite 操作 — 错误做法
void encryptFile(const std::string& path, const std::string& key) {
    // 自行 AES 加密整个文件 ...
}
sqlite3_open("temp_decrypted.db", &db);  // 解密后明文操作
```

## 检查方法
1. 检查项目依赖配置（CMakeLists.txt / .csproj / package.json 等），确认引用的是 SQLCipher 库而非纯 SQLite
2. 在 C/C++ 项目中，检查链接配置是否包含 `sqlcipher`（非 `sqlite3` 或 `sqlite`）
3. 在 .NET 项目中，检查是否通过 NuGet 引入了 SQLCipher 相关包
4. 扫描源码中是否存在 `sqlite3_open`（表示可能使用纯 SQLite）
5. 扫描数据库初始化代码，确认连接打开后立即执行了 `PRAGMA key`

## 修复指南
1. 替换项目依赖：将 `sqlite3` 库替换为 `sqlcipher` 库
2. C/C++ 项目：修改 CMakeLists.txt 或构建脚本，链接 SQLCipher
3. .NET 项目：通过 NuGet 安装 SQLCipher 扩展包，或确保运行时加载了 SQLCipher 的 native 库
4. 连接初始化时加入 `PRAGMA key = '...';` 设置加密密钥
5. 同时执行 `PRAGMA cipher_default_kdf_iter = 256000;` 强化密钥派生
6. 使用 Navicat Premium Lite 等工具选择 SQLCipher 加密类型连接，验证数据库文件已加密

## 审查清单
- [ ] 项目依赖包含 SQLCipher 而非纯 SQLite
- [ ] 不存在直接链接未加密 sqlite3 库的情况
- [ ] 不存在自实现加密包装层替代 SQLCipher 的代码
- [ ] 数据库连接打开后立即执行了 PRAGMA key
- [ ] 可使用外部工具验证数据库文件确实已加密

## 关联页面
- [[sqlite-pragma-key]] — PRAGMA key 初始化
- [[sqlite-no-self-aes]] — 禁止自实现 AES 加密
- [[sqlite-kdf-iterations]] — KDF 迭代次数
