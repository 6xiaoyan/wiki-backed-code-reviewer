---
title: §7 明确禁止项 / 腾讯安全 §2.3 — 禁止硬编码密钥
rule_id: fix-pattern/7-明确禁止项-腾讯安全-2-3-禁止硬编码密钥
priority: pattern
related_pages: []
---

# §7 明确禁止项 / 腾讯安全 §2.3 — 禁止硬编码密钥

## 关联规则
- §7 明确禁止项 / 腾讯安全 §2.3 — 禁止硬编码密钥

## 代码特征
以下代码模式会导致此违规，fix_agent 应通过关键词/模式匹配识别：

1. **硬编码密钥/密码字面量**：
   - 直接使用 `QByteArrayLiteral("明文密码")` 或 `QByteArray("明文密码")` 初始化密码变量。
   - 使用 `static const unsigned char kObfuscatedKey[32] = {...}` 或类似静态数组存储硬编码密钥。
   - 在类方法（如 `deriveKey()`）中直接返回一个硬编码的密钥或密码。

2. **典型变量或方法命名**：
   - 方法名包含 `deriveKey`、`getHardcodedKey`、`kObfuscatedKey` 等暗示硬编码的标识符。
   - 变量名如 `pwd`、`password`、`key`、`appKey` 直接接收硬编码字面量。

3. **静态或全局密码/密钥定义**：
   - 在 `.h` 或 `.cpp` 文件中定义 `static const unsigned char` 数组作为密钥。
   - 在类的私有成员中定义 `QByteArray m_appKey` 或类似变量，并通过硬编码方式赋值。

4. **修复目标**：所有此类硬编码模式应改为从用户输入、安全凭据管理器或环境变量获取密码，并通过安全哈希派生密钥。

## 修复步骤
按顺序执行以下步骤，每一步均为精确的代码改写指令：

### 步骤 1: 删除硬编码密钥方法，添加从用户输入派生密钥的方法

- **操作**: 修改头文件（如 `passwordmanager.h`）
- **替换前**（私有部分）:
```
private:
    QByteArray deriveKey();

    Database* m_db;
    QByteArray m_appKey;
```
- **替换后**:
```
private:
    Database* m_db;
    QByteArray m_appKey;

public:
    bool setMasterPassword(const QByteArray& masterPwd);
```
- **说明**: 移除 `deriveKey()` 方法声明，添加 `setMasterPassword()` 公共方法，接受用户输入的密码。

### 步骤 2: 实现从用户密码派生密钥的逻辑

- **操作**: 修改源文件（如 `passwordmanager.cpp`）
- **替换前**（方法 `PasswordManager::deriveKey()` 的实现）:
```
QByteArray PasswordManager::deriveKey()
{
    static const unsigned char kObfuscatedKey[32] = {
        // ... 硬编码的字节序列
    };
    // ...
}
```
- **替换后**:
```
bool PasswordManager::setMasterPassword(const QByteArray& masterPwd)
{
    m_appKey = QCryptographicHash::hash(masterPwd, QCryptographicHash::Sha256);
    // 可选：对 masterPwd 进行安全清零
    // secureZero(masterPwd.data(), masterPwd.size());
    return true;
}
```
- **说明**: 用 `QCryptographicHash::hash` 从 `masterPwd` 派生密钥，覆盖旧硬编码逻辑。同时，在文件中添加必要的头文件：`#include <QCryptographicHash>`。

### 步骤 3: 修改构造函数以接收用户密码并调用派生方法

- **操作**: 修改 `mainwindow.h` 构造函数声明
- **替换前**:
```
explicit MainWindow(QWidget* parent = nullptr);
```
- **替换后**:
```
explicit MainWindow(QByteArray masterPwd, QWidget* parent = nullptr);
```

### 步骤 4: 更新构造函数实现，移除初始化时的数据库操作

- **操作**: 修改 `mainwindow.cpp` 构造函数实现
- **替换前**:
```
MainWindow::MainWindow(QWidget* parent)
    : QWidget(parent)
    , m_tblWgt(nullptr)
    , m_lblCou(...)
    // ... 其他初始化
    refreshTable();      // 在数据库初始化前调用，导致崩溃
```
- **替换后**:
```
MainWindow::MainWindow(QByteArray masterPwd, QWidget* parent)
    : QWidget(parent)
    , m_tblWgt(nullptr)
    , m_lblCou(...)
    // ... 其他初始化，移除 refreshTable()
```
- **说明**: 确保构造函数中不包含任何对数据库的依赖操作（如 `refreshTable()`），这些操作应推迟到 `setMasterPassword()` 调用成功后执行。

### 步骤 5: 在调用方（如 `main.cpp`）接收用户输入密码并传递

- **操作**: 在 `main.cpp` 中，构造 `MainWindow` 前从用户输入获取密码，然后传递。
- **示例代码**:
```
QByteArray masterPwd;
// 从控制台或 GUI 输入获取密码，例如：
// masterPwd = getPasswordFromUser("Enter master password:");
// 或通过 std::getline(std::cin, input) 读取，但注意安全清零。
MainWindow mainWindow(masterPwd);
mainWindow.show();
```
- **说明**: 确保密码来源是用户输入，而非硬编码。

### 步骤 6: 时序修正 — 确保初始化在正确时机执行

- **操作**: 在 `setMasterPassword()` 方法中，调用 `initialize()` 等数据库初始化逻辑。
- **说明**: 将数据库初始化（如 `m_db->open()`）从构造函数移到 `setMasterPassword()` 内部，并在 `initialize()` 成功后，再调用 `refreshTable()`。同时，对 `masterPwd` 进行安全清零（如使用 `secureZero` 或 `memset_s`）以防止内存泄漏。

## 来源
run: 20260728-104017-f51e3114, 迭代 2 轮, 最终 9/10