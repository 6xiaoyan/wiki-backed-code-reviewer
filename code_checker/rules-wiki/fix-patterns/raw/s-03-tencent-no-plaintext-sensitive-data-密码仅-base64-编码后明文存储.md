---
title: S-03/tencent/no-plaintext-sensitive-data — 密码仅 Base64 编码后明文存储
rule_id: fix-pattern/s-03-tencent-no-plaintext-sensitive-data-密码仅-base64-编码后明文存储
priority: pattern
related_pages: []
---

# S-03/tencent/no-plaintext-sensitive-data — 密码仅 Base64 编码后明文存储

## 关联规则

- `S-03/tencent/no-plaintext-sensitive-data`（qt-0019）：敏感数据不得明文或可逆编码存储。
- `S-07`（qt-0051）：与 S-03 为同一问题，已合并处理。

## 代码特征

以下代码模式会导致违规：

1. **写入路径对密码做 Base64 可逆编码后拼入 SQL**：
   ```cpp
   << password.toBase64().toStdString() << "', '"
   ```
   或
   ```cpp
   << "password = '" << password.toBase64().toStdString() << "', "
   ```
   Base64 是编码而非加密，任何拿到数据库文件的人都能直接解码还原明文密码。

2. **读取路径对存储的密码做 Base64 解码**：
   ```cpp
   entry.password = QByteArray::fromBase64(QByteArray(argv[3]));
   ```
   此代码与写入路径的 Base64 编码对称，进一步证明存储的是可逆编码后的密码。

3. **伴随特征（高风险）**：SQLCipher 主密钥硬编码在代码中（如 `sqlite3_key(m_appKey)` 且 `m_appKey` 为固定字符串），此时即使依赖数据库文件级加密，硬编码密钥被攻破后全部密码仍会泄露。

4. **特征关键词**：`toBase64`、`fromBase64`、`password.toStdString()`、`QByteArray(argv[3])`、`sqlite3_key`。

## 修复步骤

> 提示：密码管理器场景要求密码可检索（用户需要取回密码），因此**不要**使用不可逆哈希；应在移除显式 Base64 编码后，依赖 SQLCipher 文件级加密保护静态数据。

1. **移除 `addEntry` 中密码的 Base64 编码**，直接写入原始密码字节：
   ```cpp
   // 修改前
   << password.toBase64().toStdString() << "', '"
   // 修改后
   << password.toStdString() << "', '"
   ```

2. **移除 `updateEntry` 中密码的 Base64 编码**，直接写入原始密码字节：
   ```cpp
   // 修改前
   << "password = '" << password.toBase64().toStdString() << "', "
   // 修改后
   << "password = '" << password.toStdString() << "', "
   ```

3. **移除读取回调中的 Base64 解码**，保持读写路径对称：
   ```cpp
   // 修改前（database.cpp）
   entry.password = QByteArray::fromBase64(QByteArray(argv[3]));
   // 修改后
   entry.password = QByteArray(argv[3]);
   ```

4. **确认数据库连接已启用 SQLCipher 文件级加密**（如 `database.cpp` 中调用了 `sqlite3_key`），并**将主密钥改为用户输入/系统密钥链获取**，删除硬编码密钥（如当前代码第 40-49 行的硬编码 `m_appKey`）。这是保证静态存储安全的必要条件。

5. **（强制加固）使用参数化查询消除注入风险**：将 `addEntry`/`updateEntry` 中的字符串拼接 SQL 改为 `sqlite3_prepare_v2` + `sqlite3_bind_text` 绑定 `password`（以及 `siteName`/`username`/`notes`）。若无法参数化，至少将密码中的单引号替换为两个单引号（`'` → `''`）后再拼入 SQL。

## 来源

run: 20260804-132308-386ed1c1, 迭代 3 轮, 最终 6/10