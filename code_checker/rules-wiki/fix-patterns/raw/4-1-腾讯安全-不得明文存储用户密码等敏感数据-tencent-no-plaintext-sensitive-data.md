---
title: §4.1 腾讯安全 — 不得明文存储用户密码等敏感数据 / tencent/no-plaintext-sensitive-data
rule_id: fix-pattern/4-1-腾讯安全-不得明文存储用户密码等敏感数据-tencent-no-plaintext-sensitive-data
priority: pattern
related_pages: []
---

# §4.1 腾讯安全 — 不得明文存储用户密码等敏感数据 / tencent/no-plaintext-sensitive-data

## 关联规则
- tencent/no-plaintext-sensitive-data

## 代码特征
以下代码模式会导致本违规，fix_agent 应通过关键词/模式识别同类问题：

- 密码字段在写入数据库前仅通过 `QByteArray::toBase64()` / `toBase64()` 进行编码，如：
  ```cpp
  sql << "INSERT INTO passwords ... VALUES ('" << password.toBase64().toStdString() << "', ...)"
  ```
- 读取数据库时使用 `QByteArray::fromBase64()` 还原密码，如：
  ```cpp
  entry.password = QByteArray::fromBase64(QByteArray(argv[3]));
  ```
- 对密码使用任何**可逆编码**（Base64、Hex、URL 编码等）而非**不可逆哈希**（PBKDF2、Argon2id、scrypt、bcrypt）。
- 硬编码数据库加密密钥或使用弱密钥，导致“编码后存储”等价于明文存储。
- 存在 `getPassword()` 之类的函数返回哈希值，并将其直接用于 UI 回填或再次哈希，造成双重哈希或语义混乱。

## 修复步骤
请按以下顺序执行修复：

1. **引入密码哈希工具函数**  
   在 `passwordmanager.cpp` 的匿名命名空间或合适的工具类中，新增基于 PBKDF2-HMAC-SHA256 的哈希函数（迭代次数至少 256000，盐长度至少 16 字节），返回格式为 `salt:hash`（Base64 编码）。示例结构：
   ```cpp
   static QByteArray hmacSha256(const QByteArray &key, const QByteArray &data) { /* ... */ }
   static QByteArray pbkdf2Sha256(const QByteArray &password, const QByteArray &salt, int iterations) { /* ... */ }
   static QByteArray hashPassword(const QString &password) {
       QByteArray salt = ...; // 使用 QRandomGenerator::system() 生成 16 字节随机盐
       QByteArray hash = pbkdf2Sha256(password.toUtf8(), salt, 256000);
       return salt.toBase64() + ":" + hash.toBase64();
   }
   ```
   确保生成的字符串不包含单引号（`'`），或后续 SQL 拼接时进行转义。

2. **修改写入逻辑（addEntry）**  
   将原代码：
   ```cpp
   << password.toBase64().toStdString() << "', '"
   ```
   改为：
   ```cpp
   << hashPassword(password).toStdString() << "', '"
   ```

3. **修改更新逻辑（updateEntry）**  
   找到 `updateEntry` 中的 SQL 拼接，同样将 `password.toBase64()` 替换为 `password.isEmpty() ? <保留原哈希> : hashPassword(password)`。即：当密码输入为空时，跳过密码字段更新，避免对已有哈希再次哈希；不为空时写入新哈希。

4. **修改数据库读取逻辑（database.cpp）**  
   将读取密码时使用的：
   ```cpp
   entry.password = QByteArray::fromBase64(QByteArray(argv[3]));
   ```
   改为直接存储原始哈希字符串：
   ```cpp
   entry.password = QByteArray(argv[3]);
   ```
   注意：此时 `entry.password` 保存的是 `salt:hash` 格式的哈希值，不是明文密码。

5. **调整 UI 交互，避免哈希值回填编辑框**  
   在 `mainwindow.cpp::editEntry()` 中，删除类似 `dlg.setPassword(pwd)` 的调用（因为 `pwd` 此时是哈希值）。改为留空密码框，并添加占位提示“留空则不修改密码”。同时确保 `updateEntry` 在密码为空时保留原哈希。

6. **清理未使用的解码/取回接口**  
   若 `PasswordManager` 中已无调用方，删除 `getPassword()` 的声明和定义（或改为不返回哈希值、仅供内部校验使用）。同步检查 `passwordmanager.h` 和 `passwordmanager.cpp`，移除所有不再使用的 `fromBase64` / `toBase64` 对密码的处理。

7. **验证 SQL 语句合法性**  
   检查所有涉及密码的 INSERT/UPDATE SQL 拼接，确保在空密码分支下 SQL 语法仍然正确（例如不要出现多余逗号或引号），并核对哈希字符串中没有会破坏 SQL 结构的字符。

## 来源
run: 20260812-110827-ac3c072b, 迭代 2 轮, 最终 8/10