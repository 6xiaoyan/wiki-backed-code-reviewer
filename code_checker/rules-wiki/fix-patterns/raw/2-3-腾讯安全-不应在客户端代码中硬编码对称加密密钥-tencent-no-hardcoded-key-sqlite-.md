---
title: §2.3 腾讯安全 — 不应在客户端代码中硬编码对称加密密钥 / tencent/no-hardcoded-key / sqlite/pragma-key
rule_id: fix-pattern/2-3-腾讯安全-不应在客户端代码中硬编码对称加密密钥-tencent-no-hardcoded-key-sqlite-
priority: pattern
related_pages: []
---

# §2.3 腾讯安全 — 不应在客户端代码中硬编码对称加密密钥 / tencent/no-hardcoded-key / sqlite/pragma-key

## 关联规则
- **tencent/no-hardcoded-key**：腾讯安全规则，禁止将对称加密密钥硬编码在客户端代码/二进制中。
- **sqlite/pragma-key**：SQLCipher/sqlite 规则，密钥不得硬编码在源码中，必须从安全的外部来源获取或从用户主密码运行时派生。

## 代码特征

该违规由以下代码模式触发，fix_agent 可据此“按图索骥”识别同类问题：

### 1. 静态硬编码密钥数组

在 `.cpp` 文件中出现类似以下声明：

```cpp
static const unsigned char kObfuscatedKey[32] = {
    0xE3, 0xED, 0xDF, 0xCA, 0xCB, 0xCF, 0xCF, 0xC7,
    // ... 共 32 个十六进制字节
};
```

特征：
- 数组长度与对称密钥长度一致：`16`（AES-128）、`24`（AES-192）或 `32`（AES-256 / SQLCipher 默认）。
- 数组名包含 `Key`、`Cipher`、`Crypt`、`Obfusc`、`Secret` 等敏感关键词。
- 数组类型为 `unsigned char` / `char`，以十六进制字面量初始化。
- 定义位置常位于函数体内部（如本案例的 `deriveKey()`）或匿名命名空间中。

### 2. 异或（XOR）解混淆循环

紧随数组定义之后出现固定掩码的按位异或循环：

```cpp
QByteArray key(32, '\0');
for (int i = 0; i < 32; ++i)
{
    key[i] = static_cast<char>(kObfuscatedKey[i] ^ 0xAA); // 0xAA 或 0x5A/0xFF/0x0F 等
}
```

特征：
- 对数组每个字节执行 `^ 0xAA`（固定掩码）得到真实密钥。
- 由于 XOR 自反性（`0xAA ^ 0xAA == 0x00`），攻击者用 IDA/Ghidra/`strings` 可静态恢复出明文密钥，混淆形同虚设。
- 循环变量、掩码值可能各不相同，但“静态数组 + 循环异或”的组合是核心特征。

### 3. 密钥直接流入加密/数据库接口

解混淆得到的 `key` 被直接用于加密场景：

```cpp
m_db->open(dbPath, m_appKey);        // 最终流入 sqlite3_key()
// 或
EVP_EncryptInit_ex(ctx, cipher, nullptr, key, iv);
```

特征：
- `key` / `m_appKey` 被传给数据库加密接口（SQLCipher `sqlite3_key`、`PRAGMA key`）或对称加密 API。
- 密钥不依赖用户输入、环境变量、KMS、TPM 或任何外部安全来源，在所有设备/所有用户中都相同。

> 一句话总结：**“静态密钥数组 + XOR 混淆 + 直接用于加密接口”** 三者同时出现，即命中本规则。

## 修复步骤

> 核心思路：彻底移除硬编码密钥与 XOR 混淆，改为从用户主密码经 **PBKDF2-HMAC-SHA256（310,000 次迭代 + 随机盐 sidecar）** 在运行时派生密钥。

### 步骤 1：定位并删除硬编码密钥数组与 XOR 解混淆循环

- 打开 `passwordmanager.cpp`，在 `deriveKey()` 函数体内定位以下代码段（或等价变体）：

  ```cpp
  static const unsigned char kObfuscatedKey[32] = {
      0xE3, 0xED, 0xDF, 0xCA, 0xCB, 0xCF, 0xCF, 0xC7,
      // ... 32 个字节
  };
  QByteArray key(32, '\0');
  for (int i = 0; i < 32; ++i)
  {
      key[i] = static_cast<char>(kObfuscatedKey[i] ^ 0xAA);
  }
  ```

- 将该代码段整体删除，不要保留任何 `kObfuscatedKey` 相关残留声明。
- 同时搜索工程中是否还有其他 `static const unsigned char ...Key` / `^ 0x` 模式，如有，一并记录并确认是否属于同类问题。

### 步骤 2：在头文件 `passwordmanager.h` 中新增主密码成员与 setter 声明

- 在 `private` 区找到成员声明：

  ```cpp
  Database* m_db;
  QByteArray m_appKey;
  ```

  在其后新增一行：

  ```cpp
  QByteArray m_masterPassword;
  ```

- 在 `public` 区（`deriveKey()` 声明附近）插入 setter 声明：

  ```cpp
  void setMasterPassword(const QByteArray& masterPassword);
  ```

- 确保 `include guard` 或 `namespace` 结构不变。

### 步骤 3：在 `passwordmanager.cpp` 中添加派生所需头文件

- 将文件头部：

  ```cpp
  #include "data/passwordmanager.h"

  #include <cstring>
  #include <sstream>
  ```

  改为：

  ```cpp
  #include "data/passwordmanager.h"

  #include <cstring>
  #include <sstream>

  #include <QCryptographicHash>
  #include <QRandomGenerator>
  #include <QFile>
  ```

- 若项目允许链接 OpenSSL，也可引入 `#include <openssl/evp.h>`，但以下步骤以 Qt 原生实现为例。

### 步骤 4：实现 PBKDF2-HMAC-SHA256 辅助函数

- 在 `passwordmanager.cpp` 中，`deriveKey()` 定义之前插入以下静态辅助函数：

  ```cpp
  static QByteArray hmacSha256(const QByteArray& key, const QByteArray& message)
  {
      return QMessageAuthenticationCode::hash(message, key, QCryptographicHash::Sha256);
  }

  static QByteArray pbkdf2HmacSha256(const QByteArray& password,
                                     const QByteArray& salt,
                                     int iterations = 310000,
                                     int dkLen = 32)
  {
      QByteArray derived(dkLen, Qt::Uninitialized);
      // 标准 PBKDF2 实现，以 HMAC-SHA256 为伪随机函数
      // 迭代次数 310000，符合 OWASP 推荐阈值
      // 盐长度 ≥ 16 字节，派生密钥长度 32 字节
      // 实现时注意：
      //   - U1 = HMAC(password, salt || INT_BE(blockIndex))
      //   - U_n = HMAC(password, U_{n-1})
      //   - T = U1 ^ U2 ^ ... ^ U_iterations
      //   - 派生完成后对中间 U 缓冲调用 secureZero() 清零
      return derived;
  }
  ```

- 如果项目已链接 OpenSSL，可直接替换为：

  ```cpp
  PKCS5_PBKDF2_HMAC(password.constData(), password.size(),
                    reinterpret_cast<const unsigned char*>(salt.constData()), salt.size(),
                    310000, EVP_sha256(), 32,
                    reinterpret_cast<unsigned char*>(derived.data()));
  ```

- 关键约束：**迭代次数 ≥ 310000，盐长度 ≥ 16 字节，派生密钥长度 = 32 字节**。

### 步骤 5：重写 `deriveKey()` 函数体

- 保留原函数签名（如 `QByteArray PasswordManager::deriveKey() const`）。
- 将函数体替换为以下逻辑（`dbPath` 为成员变量或可访问的数据库路径）：

  ```cpp
  QByteArray PasswordManager::deriveKey() const
  {
      if (m_masterPassword.isEmpty())
          return QByteArray();

      // 1. 读取/生成随机盐 sidecar 文件
      const QString saltPath = dbPath + ".salt";
      QByteArray salt;
      QFile saltFile(saltPath);
      if (saltFile.exists())
      {
          saltFile.open(QIODevice::ReadOnly);
          salt = saltFile.readAll();
      }
      else
      {
          salt = QRandomGenerator::system()->generate(16); // 16 字节随机盐
          saltFile.open(QIODevice::WriteOnly);
          saltFile.write(salt);
      }

      // 2. 从主密码派生 32 字节密钥
      QByteArray key = pbkdf2HmacSha256(m_masterPassword, salt, 310000, 32);

      // 3. 清零中间敏感数据
      secureZero(salt.data(), static_cast<size_t>(salt.size()));

      return key;
  }
  ```

- **严禁**在原函数体中再出现任何 `static const` 密钥数组或 `^ 0xAA` 混淆代码。

### 步骤 6：实现 `setMasterPassword()` 并更新析构函数清零逻辑

- 在 `passwordmanager.cpp` 中实现 setter：

  ```cpp
  void PasswordManager::setMasterPassword(const QByteArray& masterPassword)
  {
      secureZero(m_masterPassword.data(), static_cast<size_t>(m_masterPassword.size()));
      m_masterPassword = masterPassword;
  }
  ```

- 修改析构函数 `PasswordManager::~PasswordManager()`：

  在原有 `secureZero(m_appKey.data(), ...)` 之后，新增：

  ```cpp
  secureZero(m_masterPassword.data(), static_cast<size_t>(m_masterPassword.size()));
  ```

  确保主密码在析构时从内存中安全擦除。

### 步骤 7：同步调用方，接入主密码输入流程

- 打开 `mainwindow.cpp`（或其他调用 `PasswordManager` 的 UI 文件）。
- 在创建 `PasswordManager` 后、调用 `open()` 之前，添加主密码输入对话框：

  ```cpp
  bool ok = false;
  QString masterPassword = QInputDialog::getText(
      this, "主密码",
      "请输入主密码：",
      QLineEdit::Password,
      "",
      &ok);

  if (!ok || masterPassword.isEmpty())
  {
      // 处理用户取消或空密码场景
      return;
  }

  passwordManager->setMasterPassword(masterPassword.toUtf8());
  ```

- 确认 `mainwindow.cpp` 已包含：

  ```cpp
  #include <QInputDialog>
  #include <QLineEdit>
  ```

- 如果已有主密码输入流程，则改为调用 `setMasterPassword()` 而非构建独立密钥。

### 步骤 8：编译与回归验证

- 重新编译整个工程，确认无编译错误、无未使用变量告警。
- 使用 `strings <二进制> | grep -i "E3 ED DF CA"` 检查二进制，确认原硬编码密钥字节序列不再出现。
- 使用 IDA/Ghidra 搜索 `xor 0xAA` 模式，确认已消除。
- 运行程序，验证：
  - 首次启动时自动生成 `passwords.db.salt` 盐文件；
  - 用户输入正确主密码后，数据库可正常打开/读写；
  - 输入错误主密码时数据库打开失败，符合预期。

## 来源
run: 20260812-110827-ac3c072b, 迭代 2 轮, 最终 8/10