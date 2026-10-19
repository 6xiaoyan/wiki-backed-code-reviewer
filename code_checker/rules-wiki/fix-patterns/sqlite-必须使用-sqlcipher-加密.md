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
以下代码模式会导致此违规，修复者应通过关键词/结构化模式匹配到同类问题：

1. **调用 `sqlite3_key()` C API 设置密钥**（这是最常见的不合规模式）  
   - 关键词匹配：`sqlite3_key(`  
   - 示例代码：
     ```cpp
     rc = sqlite3_key(m_db, keyCopy.constData(), keyCopy.size());
     ```
2. **使用 `PRAGMA key` 但格式错误**（如外层使用双引号或非标准十六进制语法）  
   - 关键词匹配：`PRAGMA key = "` 或 `PRAGMA key = 'x'`（非标准字面量）  
   - 示例错误格式：
     ```cpp
     exec("PRAGMA key = \"x'" + hexKey + "'\";");
     ```
3. **调用 `PRAGMA key` 之前未设置 KDF 参数**（`cipher_default_kdf_iter` 等）  
   - 关键词匹配：`PRAGMA key` 前没有 `PRAGMA cipher_default_kdf_iter` 或 `PRAGMA kdf_iter`
4. **缺少对 `exec()` 返回值的错误检查**（设置 KDF 或 key 后未判断是否成功）
5. **未对敏感内存（`hexKey`、`keyCopy`）执行 `secureZero` 清理**

## 修复步骤
请严格按以下顺序执行修复（每一步均为可执行的代码改写指令）：

### 步骤 1：删除原有的 `sqlite3_key()` 调用及相关变量声明
- **操作**：找到以下模式并整体删除：
  ```cpp
  int rc = sqlite3_key(m_db, keyCopy.constData(), keyCopy.size());
  secureZero(keyCopy.data(), static_cast<size_t>(keyCopy.size()));
  if (rc != SQLITE_OK)
  {
      sqlite3_close(m_db);
      m_db = nullptr;
      return false;
  }
  ```
  （如果使用 `QByteArray keyCopy` 变量，保留该变量供后续步骤使用；否则需从外部获取密钥字节数组。）

### 步骤 2：在 `PRAGMA key` 之前添加 KDF 参数设置（必须在 key 之前执行）
- **操作**：在调用 `exec("PRAGMA key ...")` 语句的**上方**插入：
  ```cpp
  if (!exec("PRAGMA cipher_default_kdf_iter = 256000;"))
  {
      secureZero(keyCopy.data(), static_cast<size_t>(keyCopy.size()));
      sqlite3_close(m_db);
      m_db = nullptr;
      return false;
  }
  ```
  如果数据库需要自定义其他 KDF 参数（如 `cipher_page_size`），可在此处一并设置。

### 步骤 3：生成十六进制密钥字符串
- **操作**：在 KDF 参数设置之后、`PRAGMA key` 之前，添加：
  ```cpp
  QByteArray hexKey = keyCopy.toHex();
  ```

### 步骤 4：使用标准 SQL 十六进制字面量设置加密密钥
- **操作**：将原 `exec("PRAGMA key ...")` 替换为以下代码（注意使用标准 SQL 十六进制字面量 `x'...'`，不带双引号）：
  ```cpp
  if (!exec("PRAGMA key = x'" + hexKey.toStdString() + "';"))
  {
      secureZero(keyCopy.data(), static_cast<size_t>(keyCopy.size()));
      secureZero(hexKey.data(), static_cast<size_t>(hexKey.size()));
      sqlite3_close(m_db);
      m_db = nullptr;
      return false;
  }
  ```

### 步骤 5：清理敏感内存（如果之前未清理）
- **操作**：在 `PRAGMA key` 执行成功后，仍需清理 `keyCopy` 和 `hexKey`：
  ```cpp
  secureZero(keyCopy.data(), static_cast<size_t>(keyCopy.size()));
  secureZero(hexKey.data(), static_cast<size_t>(hexKey.size()));
  ```

### 步骤 6：检查 `exec()` 返回值（可选但推荐）
- 若前述步骤已对 KDF 和 key 的 `exec()` 返回值做了错误处理，则无需重复；若未做，则需将 `exec()` 返回值判断为 `!exec(...)` 并执行关闭数据库、清理内存、返回 `false`。

### 完整修复示例（最终通过审查的代码结构）
```cpp
QByteArray keyCopy = key; // 假设 key 是 QByteArray 类型
QByteArray hexKey = keyCopy.toHex();

// KDF 参数必须在 PRAGMA key 之前设置
if (!exec("PRAGMA cipher_default_kdf_iter = 256000;"))
{
    secureZero(keyCopy.data(), static_cast<size_t>(keyCopy.size()));
    sqlite3_close(m_db);
    m_db = nullptr;
    return false;
}

// 使用标准 SQL 十六进制字面量设置加密密钥
if (!exec("PRAGMA key = x'" + hexKey.toStdString() + "';"))
{
    secureZero(keyCopy.data(), static_cast<size_t>(keyCopy.size()));
    secureZero(hexKey.data(), static_cast<size_t>(hexKey.size()));
    sqlite3_close(m_db);
    m_db = nullptr;
    return false;
}

secureZero(keyCopy.data(), static_cast<size_t>(keyCopy.size()));
secureZero(hexKey.data(), static_cast<size_t>(hexKey.size()));
```

## 来源
run: 20260728-102230-c1310d23, 迭代 2 轮, 最终 8/10