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
当出现以下任一模式时，触发本违规：

1. **数据库打开后未设置 PRAGMA key**：在 `Database::open()` 或任何 SQLite 连接初始化代码中，执行了 `open()` 或 `QSqlDatabase::open()` 之后，没有看到 `PRAGMA key = ...` 语句。
2. **使用 `sqlite3_key()` 而非 `PRAGMA key`**：代码中调用了 `sqlite3_key()` 设置密钥，但规则要求使用 `PRAGMA key = ...` 形式。
3. **PRAGMA key 位置错误**：`PRAGMA key` 不是连接打开后执行的第一条 SQL，前面已经执行了其他 SQL（如 `PRAGMA foreign_keys`、`CREATE TABLE` 等）。
4. **PRAGMA key 返回值未检查**：执行 `PRAGMA key` 后没有检查 SQL 执行结果，可能导致失败时静默继续。
5. **跨文件接口不一致**：`database.h` 中 `open()` 声明包含 `QByteArray key` 参数，但实现中未将 key 用于 `PRAGMA key`，只是保存在成员变量中；或调用方传入 key 但实现忽略。
6. **密钥以明文参数传递**：密钥通过函数参数传入、长期存储，而不是在初始化时立即消费并清零。

典型触发代码示例：
```cpp
// 错误：打开数据库后没有执行 PRAGMA key
bool Database::open(const std::string& dbPath) {
    m_db = QSqlDatabase::addDatabase("QSQLITE");
    m_db.setDatabaseName(QString::fromStdString(dbPath));
    if (!m_db.open()) return false;
    // 缺少 PRAGMA key
    return true;
}
```

## 修复步骤
按以下顺序执行修复，每一步都是强制要求：

1. **修改 database.h 中的 open() 声明，移除密钥参数**  
   将 `bool open(const std::string& dbPath, const QByteArray& key);`  
   改为 `bool open(const std::string& dbPath);`  
   密钥不再通过 `open()` 传入，由调用方在打开后立即通过 PRAGMA 设置。

2. **修改 database.cpp 中的 open() 实现**  

   - 删除不再需要的 `secureZero` 辅助函数（若存在），因为密钥不再通过参数传入，该函数已成为死代码。  
   - 修改 `open()` 函数体，确保在 `m_db.open()` 成功后只负责打开连接，不执行任何 SQL 语句。  
   - 如果 `open()` 中有类似 `sqlite3_key` 或 `PRAGMA key` 的调用，全部移除，并保持返回逻辑清晰。  
   - 参考最终通过的实现：
     ```cpp
     bool Database::open(const std::string& dbPath)
     {
         if (m_db)
         {
             return false;
         }
         // ... 创建并打开 QSqlDatabase，此处不设置任何 PRAGMA ...
         return m_db.open();
     }
     ```

3. **修改 passwordmanager.cpp 中的 initialize()，在 open() 后立即设置 PRAGMA key**  
   找到调用 `open()` 的位置（通常是 `passwordmanager.cpp` 的 `initialize()` 函数），在 `open()` 成功返回后、执行任何其他 SQL 之前，插入以下代码：

   ```cpp
   if (!m_db.exec("PRAGMA key = '" + m_appKey.toHex() + "';").lastError().isValid()) {
       // 可选：记录失败日志
       m_db.close();
       return false;
   }
   ```

   - 其中 `m_appKey` 是已经派生出的密钥，`toHex()` 得到 64 字符十六进制字符串（若密钥是 32 字节）。  
   - 必须使用单引号形式（passphrase 语义），或按业务需要使用官方原始密钥语法 `PRAGMA key = "x'<hex>'"`，二者不可混用。  
   - **检查返回值**：必须确认 SQL 执行成功，失败时关闭连接并返回 `false`（fail-closed）。

4. **如需满足 KDF 迭代要求，调整顺序**  
   如果项目中存在关于 KDF 迭代次数（如 256000 次）的规则，必须在 `PRAGMA key` 之前执行：

   ```cpp
   m_db.exec("PRAGMA cipher_default_kdf_iter = 256000;");
   ```

   确保该语句先于 `PRAGMA key` 执行，使迭代设置对当前连接立即生效。执行后同样检查返回值。

5. **验证跨文件一致性**  
   - 检查所有调用 `open()` 的地方，确保已移除原来的 `key` 参数。  
   - 检查 `database.cpp` 中是否残留 `secureZero` 或任何与旧密钥参数相关的代码。  
   - 在 `mainwindow.cpp` 等间接调用处，确认无参数调用仍然正确。

6. **编译并验证**  
   - 全量编译，确认无编译错误。  
   - 运行程序，确认数据库可打开，且在执行任何其他 SQL 前密钥已设置。  
   - 使用 `sqlcipher_export()` 或打开数据库文件验证是否已加密。

## 来源
run: 20260812-124714-b67d2525, 迭代 2 轮, 最终 7/10