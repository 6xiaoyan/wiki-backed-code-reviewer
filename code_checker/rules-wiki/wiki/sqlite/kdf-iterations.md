---
domain: sqlite
rule_id: sqlite-kdf-iterations
title: KDF 迭代次数
priority: main
source_file: rules/SQLite加密.md
source_section: "KDF 密钥派生机制"
status: active
check_method: regex
deterministic_check: true
checkability: deterministic
conflicts_with: []
overrides: []
related_pages:
  - [[sqlite-pragma-key]]
  - [[sqlite-must-use-sqlcipher]]
---

# KDF 迭代次数

## 规则条款
SQLCipher 的密钥派生函数（KDF）迭代次数必须不低于 256000 次。执行 `PRAGMA cipher_default_kdf_iter = 256000;` 设置此参数。

该参数控制 PBKDF2-HMAC-SHA1 的迭代次数。增加迭代次数可显著提高暴力破解成本——攻击者每尝试一个密码都需要执行同等次数的 PBKDF2 迭代，从而大幅延长破解时间，增强整体安全性。

在性能允许的前提下，可进一步提高迭代次数（如 512000 或更高），但不得低于 256000。

## 正确示例
```csharp
// C#: 连接后设置 KDF 迭代次数 ≥ 256000
using SqliteCommand kdfCmd = new(
    "PRAGMA cipher_default_kdf_iter = 256000;", connection);
kdfCmd.ExecuteNonQuery();
```

```cpp
// C++: sqlcipher KDF 设置
sqlite3_exec(db, 
    "PRAGMA cipher_default_kdf_iter = 256000;", 
    nullptr, nullptr, nullptr);

// 更高安全性：512000
sqlite3_exec(db, 
    "PRAGMA cipher_default_kdf_iter = 512000;", 
    nullptr, nullptr, nullptr);
```

```sql
-- 完整的安全初始化
PRAGMA key = 'your_secure_password';
PRAGMA cipher_default_kdf_iter = 256000;
-- 验证当前设置
PRAGMA cipher_default_kdf_iter;
-- 应返回: 256000
```

## 错误示例
```csharp
// 未设置 KDF 迭代次数 — 使用 SQLCipher 默认值（通常为 64000，不足）
SqliteConnection connection = new($"Data Source={_dbPath};");
connection.Open();
using SqliteCommand keyCmd = new(
    $"PRAGMA key = '{password}';", connection);
keyCmd.ExecuteNonQuery();
// 缺少 PRAGMA cipher_default_kdf_iter = 256000
```

```cpp
// 设置的迭代次数过低
sqlite3_exec(db, 
    "PRAGMA cipher_default_kdf_iter = 10000;",  // 远低于 256000
    nullptr, nullptr, nullptr);
```

```sql
-- 迭代次数低于最低要求
PRAGMA cipher_default_kdf_iter = 64000;  -- SQLCipher 旧版默认值，不安全
-- 应为 ≥ 256000
```

## 检查方法
1. 正则检测：搜索 `cipher_default_kdf_iter` 确认代码中存在 KDF 迭代设置
2. 提取等号右侧数值，验证是否 `≥ 256000`
3. 如果代码中不存在 `cipher_default_kdf_iter`，标记为缺失（违规）
4. 检查是否存在较低迭代次数的历史设置（如 4000、64000 等旧默认值）
5. 对于已有数据库，可通过 `PRAGMA cipher_default_kdf_iter;` 查询实际生效值

## 修复指南
1. 在 `PRAGMA key` 之后立即添加 `PRAGMA cipher_default_kdf_iter = 256000;`
2. 对于已存在的数据库，更改 KDF 迭代次数后需重新加密数据库：
   ```sql
   PRAGMA key = 'old_password';
   PRAGMA cipher_default_kdf_iter = 256000;
   PRAGMA rekey = 'new_password';  -- 或相同密码，触发重加密
   ```
3. 使用 `sqlcipher_export()` 函数安全地导出到新数据库
4. 性能调优：在低性能嵌入式设备上，256000 可能带来可感知的延迟，但安全性优先——接受此开销

## 审查清单
- [ ] `PRAGMA cipher_default_kdf_iter` 已设置在数据库初始化代码中
- [ ] 迭代次数 ≥ 256000（推荐 256000-512000）
- [ ] PRAGMA 在 PRAGMA key 之后执行
- [ ] 不存在使用旧版低迭代次数的代码（如 64000）
- [ ] 已有数据库如需升级迭代次数，已执行重加密

## 关联页面
- [[sqlite-pragma-key]] — PRAGMA key 初始化
- [[sqlite-must-use-sqlcipher]] — 必须使用 SQLCipher
- [[sqlite-no-manual-salt]] — 禁止手动管理 Salt/PBKDF2
