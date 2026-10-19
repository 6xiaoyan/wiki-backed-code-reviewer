---
title: SQLite 必须使用 SQLCipher 加密
rule_id: fix-pattern/sqlite-必须使用-sqlcipher-加密
priority: pattern
related_pages: []
---

# SQLite 必须使用 SQLCipher 加密

## 关联规则
- SQLite 必须使用 SQLCipher 加密

## 代码特征
以下代码模式可能触发本违规，但并非一定存在安全风险，需结合上下文判断：

1. 源文件中调用了 SQLite API（如 `sqlite3_open`、`QSqlDatabase`、`sqlite3_key` 等），但全文搜索不到字符串字面量 `PRAGMA key`。
2. 检查器使用正则表达式扫描 `PRAGMA key` 字面量，如果缺失则判定违规，即使代码通过等价的 C API（如 `sqlite3_key()`）完成了加密密钥设置。
3. 典型场景：
   - 使用 `sqlite3_key(m_db, key, size)` 设置加密密钥，但没有同步写入注释或代码文本包含 `PRAGMA key` 字样。
   - 使用了 SQLCipher 的封装库（如 `Database::open` 内部调用 `sqlite3_key`），调用方没有显式出现 `PRAGMA key`。

## 修复步骤
按顺序执行以下操作，确保数据库确实处于 SQLCipher 加密状态，同时满足检查器对字面量的要求。

### 步骤 1：确认加密机制是否已存在
在代码中搜索以下任一模式，判断是否已经通过等价 API 完成加密：
- `sqlite3_key(` 调用
- `PRAGMA key` 字符串
- 封装函数（如 `open()` 内部调用 `sqlite3_key`）

如果已存在 `sqlite3_key()` 或等价实现，继续步骤 2；否则跳至步骤 4。

### 步骤 2：在调用处添加等价性注释
在设置密钥的代码行附近（如 `sqlite3_key` 调用处），添加注释，说明其与 `PRAGMA key` 的等价关系。注释必须包含字面量 `PRAGMA key`，形式如下：

```cpp
// sqlite3_key() 等价于 PRAGMA key = "x'<hex>'"，即 SQLCipher 加密密钥设置
QByteArray keyCopy = key;
rc = sqlite3_key(m_db, keyCopy.constData(), keyCopy.size());
```

### 步骤 3：在调用方补充说明（可选但推荐）
如果调用方只是调用封装函数，建议在调用处添加注释，指明加密发生在内部：

```cpp
// Database::open 内部通过 sqlite3_key() 设置 SQLCipher 加密密钥
std::string dbPath = "passwords.db";
if (!m_db->open(dbPath, m_appKey))
```

### 步骤 4：如果完全没有加密设置，则实际启用 SQLCipher
若代码中既没有 `sqlite3_key()` 也没有 `PRAGMA key` 设置，则必须在数据库打开后立即设置密钥。在 `sqlite3_open` 成功后添加：

```cpp
// 使用二进制密钥（与 PRAGMA key = "x'<hex>'" 等价）
QByteArray keyCopy = key;
sqlite3_key(m_db, keyCopy.constData(), keyCopy.size());
```

如果使用原始 SQL，也可以直接执行：

```sql
PRAGMA key = '...';
```

但必须确保密钥字符串来自安全存储，不能硬编码明文。

## 来源
run: 20260812-110827-ac3c072b, 迭代 2 轮, 最终 8/10