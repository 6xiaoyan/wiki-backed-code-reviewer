---
title: §7 明确禁止项 — 禁止未验证输入（SQL注入）
rule_id: fix-pattern/7-明确禁止项-禁止未验证输入
priority: pattern
related_pages: []
---

# §7 明确禁止项 — 禁止未验证输入（SQL注入）

## 关联规则
- §7 明确禁止项 — 禁止未验证输入

## 代码特征
以下代码模式会导致此违规，fix_agent 可通过识别以下特征定位同类问题：

1. **直接字符串拼接构建 SQL 语句**：使用 `<<` 运算符或 `+` 运算符将用户输入（如函数参数、类的成员变量、外部传入的字符串）直接嵌入 SQL 字符串中。典型模式类似：
   ```
   sql << "UPDATE ... SET col = '" << userInput1 << "' ... WHERE ..."
   ```
   或
   ```
   "INSERT INTO ... VALUES ('" + userInput + "')"
   ```

2. **涉及多条 SQL 操作函数均使用拼接方式**：如 `addEntry`（INSERT）、`updateEntry`（UPDATE）、`deleteEntry`（DELETE）、`getPassword`（SELECT）等方法中全部使用字符串拼接，而非参数化查询。

3. **调用旧式 `exec(const std::string& sql)` 函数**：数据库操作函数直接调用 `exec(sql)` 或 `query(sql)` 这类只接受完整 SQL 字符串的接口，缺少参数化绑定机制。

4. **包含头文件仅提供基础类型**：代码中包含 `<sstream>` 或 `<string>` 但未包含用于参数化查询的 `<vector>` 等相关头文件。

## 修复步骤
按照以下顺序执行可修复此违规。每一步都是具体的代码改写指令。

### 步骤 1：在数据库接口头文件中添加参数化查询函数声明
- **文件**: `database.h`（或相应数据库封装类的头文件）
- **操作**: 在类的公开或私有接口部分，添加两个新的函数声明：
  ```cpp
  bool exec(const std::string& sql, const std::vector<std::string>& params);
  std::vector<PasswordEntry> query(const std::string& sql, const std::vector<std::string>& params);
  ```
  （如果已有同名函数但无参数，保持原有函数存在，新增重载版本）
- **说明**: 新函数接受 SQL 模板和参数列表，用于参数化执行。

### 步骤 2：在数据库实现文件中实现参数化查询函数
- **文件**: `database.cpp`（或相应数据库封装类的实现文件）
- **操作**: 实现 `exec` 和 `query` 函数，使用 `sqlite3_prepare_v2` + `sqlite3_bind_text` 进行参数化绑定，并在执行后调用 `sqlite3_finalize` 释放语句句柄。示例实现骨架如下：
  ```cpp
  bool Database::exec(const std::string& sql, const std::vector<std::string>& params) {
      sqlite3_stmt* stmt = nullptr;
      if (sqlite3_prepare_v2(m_db, sql.c_str(), -1, &stmt, nullptr) != SQLITE_OK) {
          return false;
      }
      for (size_t i = 0; i < params.size(); ++i) {
          sqlite3_bind_text(stmt, i + 1, params[i].c_str(), -1, SQLITE_TRANSIENT);
      }
      int rc = sqlite3_step(stmt);
      sqlite3_finalize(stmt);
      return rc == SQLITE_DONE;
  }
  ```
  `query` 函数类似，但要处理 `sqlite3_step` 返回的行数据并返回结果集。

### 步骤 3：改造所有使用字符串拼接的 SQL 操作函数
- **文件**: 包含违规代码的文件（如 `passwordmanager.cpp`）
- **操作**: 对以下每类函数，将字符串拼接替换为调用步骤 1 新增的 `exec(params)` 或 `query(params)`：

  - **`addEntry`**（INSERT 语句）
    - **替换前**:
      ```cpp
      sql << "INSERT INTO passwords (siteName, username, password, notes) VALUES ('"
          << siteName << "', '" << username << "', '"
          << password.toBase64().toStdString() << "', '" << notes << "');";
      return m_db->exec(sql.str());
      ```
    - **替换后**:
      ```cpp
      std::vector<std::string> params = {siteName, username, password.toBase64().toStdString(), notes};
      return m_db->exec("INSERT INTO passwords (siteName, username, password, notes) VALUES (?, ?, ?, ?)", params);
      ```

  - **`updateEntry`**（UPDATE 语句）
    - **替换前**:
      ```cpp
      sql << "UPDATE passwords SET siteName = '" << siteName << "', username = '" << username
           << "', password = '" << password.toBase64().toStdString()
           << "', notes = '" << notes << "' WHERE id = " << id << ";";
      return m_db->exec(sql.str());
      ```
    - **替换后**:
      ```cpp
      std::vector<std::string> params = {siteName, username, password.toBase64().toStdString(), notes, std::to_string(id)};
      return m_db->exec("UPDATE passwords SET siteName = ?, username = ?, password = ?, notes = ? WHERE id = ?", params);
      ```

  - **`deleteEntry`**（DELETE 语句）
    - **替换前**:
      ```cpp
      sql << "DELETE FROM passwords WHERE id = " << id << ";";
      return m_db->exec(sql.str());
      ```
    - **替换后**:
      ```cpp
      std::vector<std::string> params = {std::to_string(id)};
      return m_db->exec("DELETE FROM passwords WHERE id = ?", params);
      ```

  - **`getPassword`**（SELECT 语句）
    - **替换前**:
      ```cpp
      sql << "SELECT * FROM passwords WHERE id = " << id << ";";
      auto results = m_db->query(sql.str());
      ```
    - **替换后**:
      ```cpp
      std::vector<std::string> params = {std::to_string(id)};
      auto results = m_db->query("SELECT * FROM passwords WHERE id = ?", params);
      ```

- **重要**: 确保所有用户输入都用 `?` 占位符替代，并放入 `params` 向量，包括数字类型（如 `id`）需转为字符串。

### 步骤 4：调整包含文件（仅在编译报错时处理）
- **文件**: 如 `passwordmanager.cpp`
- **操作**:
  1. 如果原文件中包含 `<sstream>` 且在其他地方仍使用（如 `addEntry` 改用参数化后不再需要 `std::ostringstream`），可保留 `<sstream>` 或移除。若不确认保留即可。
  2. 确保新增 `<string>` 和 `<vector>` 头文件可用。如果原文件中缺少 `#include <string>` 或 `#include <vector>`，则添加它们。
- **示例**:
  - 保留 `#include <sstream>`（以防其他函数使用）
  - 追加 `#include <string>`（如果原来没有）
  - 确保有 `#include <vector>`（用于参数列表）

### 步骤 5：验证无用户输入的纯 SQL 操作无需改造
- **文件**: 包含违规代码的文件（如 `passwordmanager.cpp`）
- **操作**:
  - 检查 `getCount()` 和 `getAllEntries()` 等方法是否使用了用户输入（函数参数或外部变量）。如果没有用户输入（例如：`SELECT COUNT(*) FROM passwords`），则这些函数可以继续使用原有的 `exec(sql)` 或 `query(sql)`（不传参版本），无需改造。
  - 仅对接受外部参数的方法进行前述替换。

### 步骤 6：编译验证
- 对整个项目执行一次完整编译，确保没有因头文件缺失或函数签名变化导致的编译错误。常见错误包括：
  - 未包含 `<vector>` 导致 `std::vector` 未定义
  - 忘记在实现文件中添加 `sqlite3_finalize(stmt)` 导致链接警告或内存泄漏
  - 占位符数量与参数数量不匹配（务必逐个核对）

## 来源
run: 20260728-104017-f51e3114, 迭代 3 轮, 最终 9/10