---
title: §1.1 命名约定 — 常量应使用 UPPER_CASE
rule_id: fix-pattern/1-1-命名约定-常量应使用-upper_case
priority: pattern
related_pages: []
---

# §1.1 命名约定 — 常量应使用 UPPER_CASE

## 关联规则
- C-04 常量命名规范：常量（不可变值）应使用 `UPPER_CASE`（全大写 + 下划线分隔），而非 Google 风格的 `k` 前缀 camelCase。
- tencent/no-hardcoded-key：禁止在代码中硬编码密钥、密码等敏感数据。

## 代码特征
触发本违规的代码通常具有以下可识别模式：

- 变量声明使用 `static const`、`constexpr` 或 `static constexpr`，表明该值在生命周期内不可变。
- 变量名以 `k` 开头，后跟 CamelCase（例如 `kObfuscatedKey`、`kMaxBufferSize`），或类似非 `UPPER_CASE` 命名。
- 常见于常量字节数组、魔术字符串、固定配置值等。
- 一个特殊的高风险场景：常量包含硬编码的密钥、盐、口令等敏感数据（例如 `static const unsigned char kObfuscatedKey[32] = { 0xE3, 0xED, ... }`）。此时除命名违规外，还会触发 no-hardcoded-key 安全规则。

典型代码示例（违规）：
```cpp
static const unsigned char kObfuscatedKey[32] = {
    0xE3, 0xED, 0xDF, 0xCA, 0xCB, 0xCF, 0xCF, 0xC7,
    // ...
};
```

## 修复步骤

### 场景 A：常量仅为普通不可变值，不包含敏感数据
1. 将常量名由 `kCamelCase` 改为全大写 + 下划线形式 `UPPER_CASE`。
   - 例如：`kMaxBufferSize` → `MAX_BUFFER_SIZE`，`kObfuscatedKey` → `OBFUSCATED_KEY`。
2. 更新当前文件内所有对该常量的引用。
3. 搜索整个项目，确保其他文件中的调用也被更新（可使用全局搜索 `kOldName`）。
4. 重新编译并运行相关测试。

### 场景 B：常量包含硬编码密钥 / 敏感数据（如 `kObfuscatedKey`）
> 注意：当常量值为硬编码密钥时，**不能仅重命名**，必须彻底移除并改用安全派生机制。

1. **删除硬编码常量定义**：
   - 移除整个静态数组声明及初始化字节，例如：
     ```cpp
     // 删除以下代码
     static const unsigned char kObfuscatedKey[32] = {
         0xE3, 0xED, 0xDF, 0xCA, // ...
     };
     ```

2. **引入随机盐（Salt）管理**：
   - 在类的头文件（`.h`）中声明：
     ```cpp
     private:
         bool loadOrCreateSalt();
         QByteArray m_salt;
     ```
   - 在实现文件（`.cpp`）中实现 `loadOrCreateSalt()`：
     - 尝试从固定路径（如 `sidecar` 文件）读取已存在的盐。
     - 若不存在，生成一个安全的随机盐（如 16 字节），并写入该文件。
     - 若读取或生成失败，返回 `false`。

3. **改造密钥派生函数**：
   - 将原有 `QByteArray deriveKey();` 改为：
     ```cpp
     QByteArray deriveKey(const QByteArray& masterPassword) const;
     ```
   - 函数内部使用 PBKDF2-HMAC-SHA256（或同等强度的 KDF）从 `masterPassword` 和 `m_salt` 派生密钥：
     - 推荐迭代次数：`250000`
     - 派生密钥长度：`32` 字节
     - 使用 `QCryptographicHash` 或 OpenSSL 等库实现，严禁直接使用固定字节。

4. **更新初始化接口**：
   - 将 `bool initialize();` 改为：
     ```cpp
     bool initialize(const QByteArray& masterPassword);
     ```
   - 在 `initialize` 中：
     1. 调用 `loadOrCreateSalt()`，失败则返回 `false`。
     2. 调用 `deriveKey(masterPassword)`，将结果存储到成员变量（如 `m_appKey`）。
     3. 后续使用 `m_appKey` 进行加密/解密操作。

5. **同步更新所有调用点**：
   - 搜索原 `initialize()` 的调用处（例如 `mainwindow.cpp` 构造函数），改为传入用户输入的主密码。
   - 删除所有 `deriveKey()` 的旧调用方式，改为传入同一主密码。
   - 确保头文件中的类声明、构造函数、成员变量与实现一致。

6. **验证一致性**：
   - 编译整个项目，确认无残留旧符号 `kObfuscatedKey`、`deriveKey()` 旧签名等。
   - 运行测试，确保加密、解密流程能正常工作。

> 若因历史原因必须暂时保留硬编码常量，则至少执行“场景 A”的重命名，并在代码中标注 `TODO`，但最终应迁移到安全派生方案。

## 来源
run: 20260812-110827-ac3c072b, 迭代 5 轮, 最终 8/10