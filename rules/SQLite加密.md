# SQLite加密

# 概述

使用 SQLCipher 作为 SQLite 的加密扩展，实现数据库文件级透明加密（Transparent Database Encryption）。

数据库文件在磁盘上以加密形式存在，未提供正确密钥时无法读取任何内容。

# 技术组成

### 1. 核心组件

*   SQLite（数据库引擎）
    
*   SQLCipher（加密扩展）
    
*   Microsoft.Data.Sqlite（c# .NET 数据访问驱动,其他语言自行查找对应库）
    

### 2. 加密算法

*   AES-256-CBC（数据加密）
    
*   HMAC-SHA512（完整性校验）
    
*   PBKDF2（密钥派生）
    

# 加密原理

### 1. 文件级加密模型

数据库以“页”为单位进行加密：

明文数据 → 分页 → AES-256 加密 → 加密数据库文件

---

### 2. 解密流程

Password → KDF(PBKDF2) → 256-bit Key → 解密数据库

---

### 3. 启用加密的关键指令

```sql
PRAGMA key = 'your_password';
```

# KDF 密钥派生机制

### 1. SQLCipher 默认行为

SQLCipher 自动执行：

*   PBKDF2-HMAC-SHA1
    
*   多轮迭代
    
*   内部 salt 自动生成与存储
    

---

### 2. 强化 KDF 参数

```sql
PRAGMA cipher_default_kdf_iter = 256000;
```

作用：

*   增加暴力破解成本
    
*   提高密钥推导时间
    
*   增强整体安全性
    

# Salt机制说明

### SQLCipher 行为

*   自动生成 salt
    
*   salt 存储在数据库头部
    
*   用户不可见
    
*   不需要手动维护
    

---

### 错误做法

*   手动随机 salt
    
*   每次运行 salt 不一致
    
*   外部管理 salt
    

# C# 数据库连接方式

```c#
  /// <summary>
  /// 创建已加密的数据库连接
  /// </summary>
  private SqliteConnection CreateEncryptedConnection()
  {
      SqliteConnection connection = new($"Data Source={_dbPath};");
      connection.Open();
      
      using SqliteCommand keyCmd = new($"PRAGMA key = '{EscapeSqlString(_dbPassword)}';", connection);
      keyCmd.ExecuteNonQuery();
      using SqliteCommand kdfCmd = new("PRAGMA cipher_default_kdf_iter = 256000;", connection);
      kdfCmd.ExecuteNonQuery();

      return connection;
  }
```

# 验证方案

## 使用  NavicaPremiumLite  [https://www.navicat.com.cn/products/navicat-premium-lite](https://www.navicat.com.cn/products/navicat-premium-lite)

1.  连接->新建连接->SQLite
    
    ![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/mxPOG5zag9Nr5nKa/img/17c93087-97de-42df-aa61-900a66c25db9.png)
    
    ![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/mxPOG5zag9Nr5nKa/img/8f02de3d-dbbb-43ae-80c3-d5457ef6bb54.png)
    
2.  选择数据库文件路径
    
    ![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/mxPOG5zag9Nr5nKa/img/1c56d699-6471-4d49-8bc6-1b7b7862f4f9.png)
    
3.  点击高级选项->勾选已加密->输入密码->密码名称选择**sqlcipher**
    
    ![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/mxPOG5zag9Nr5nKa/img/5e59bfde-c68a-456f-90ff-40a2d6cbe428.png)
    
4.  点击测试连接
    
    ![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/mxPOG5zag9Nr5nKa/img/d2536e08-c2d1-45cc-8550-fd5d0d1f81de.png)
    
5.  测试连接成功之后点击确定即可打开数据库
    

![image.png](https://alidocs.oss-cn-zhangjiakou.aliyuncs.com/res/mxPOG5zag9Nr5nKa/img/7fba4556-38f1-4fac-a186-82bb5e0d9df4.png)
