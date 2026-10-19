# Fix Patterns 操作日志

> 记录所有 fix-pattern 的生成、审核、修改历史。

| 时间 | 操作 | 文件 | 说明 |
|------|------|------|------|
| 2026-07-28 | 初始化 | - | 创建 fix-patterns 目录结构 |
| 2026-07-28 10:38 | 自动生成 | raw/sqlite-必须使用-sqlcipher-加密.md | 来源 run, idx=0, 规则: SQLite 必须使用 SQLCipher 加密 |
| 2026-07-28 | 人工审核 | sqlite-必须使用-sqlcipher-加密.md | 审核通过，移至正式目录 |
| 2026-07-28 10:56 | 自动生成 | raw/sql-injection-parameterization.md | SQL 注入参数化修复模式 |
| 2026-07-28 10:56 | 自动生成 | raw/no-hardcoded-keys.md | 硬编码密钥消除模式 |
| 2026-07-28 10:57 | 自动生成 | raw/no-password-in-logs.md | 密码不应输出到日志 |
| 2026-07-28 10:57 | 自动生成 | raw/no-short-variable-names.md | 短变量名消除模式 |
| 2026-07-28 10:57 | 自动生成 | raw/constant-naming-uppercase.md | 常量 UPPER_CASE 命名 |
| 2026-07-28 | 批量审核 | 上述 5 条 raw 草稿 | 全部审核通过，移至正式目录 |
| 2026-07-28 12:09 | 自动生成 | raw/4-2-头文件包含顺序规则-q-39.md | 来源 run, idx=1, 规则: §4.2 头文件包含顺序规则 [Q-39] |
| 2026-08-04 13:53 | 自动生成 | raw/s-03-tencent-no-plaintext-sensitive-data-密码仅-base64-编码后明文存储.md | 来源 run, idx=18, 规则: S-03/tencent/no-plaintext-sensitive-data — 密码仅 Base64 编码后明文存储 |
| 2026-08-12 11:36 | 自动生成 | raw/sqlite-必须使用-sqlcipher-加密.md | 来源 run, idx=2, 规则: SQLite 必须使用 SQLCipher 加密 |
| 2026-08-12 11:37 | 自动生成 | raw/2-3-腾讯安全-不应在客户端代码中硬编码对称加密密钥-tencent-no-hardcoded-key-sqlite-.md | 来源 run, idx=12, 规则: §2.3 腾讯安全 — 不应在客户端代码中硬编码对称加密密钥 / tencent/no-hardcoded-key / sqlite/pragma-key |
| 2026-08-12 11:37 | 自动生成 | raw/1-1-命名约定-常量应使用-upper_case.md | 来源 run, idx=13, 规则: §1.1 命名约定 — 常量应使用 UPPER_CASE |
| 2026-08-12 11:37 | 自动生成 | raw/4-1-腾讯安全-不得明文存储用户密码等敏感数据-tencent-no-plaintext-sensitive-data.md | 来源 run, idx=15, 规则: §4.1 腾讯安全 — 不得明文存储用户密码等敏感数据 / tencent/no-plaintext-sensitive-data |
| 2026-08-12 13:08 | 自动生成 | raw/sqlite-必须使用-sqlcipher-加密-1.md | 来源 run, idx=2, 规则: SQLite 必须使用 SQLCipher 加密 |
| 2026-08-12 13:09 | 自动生成 | raw/1-2-头文件规范-include-分组之间应用空行分隔.md | 来源 run, idx=6, 规则: §1.2 头文件规范 — #include 分组之间应用空行分隔 |
| 2026-08-12 13:09 | 自动生成 | raw/2-2-变量声明-避免短变量名.md | 来源 run, idx=34, 规则: §2.2 变量声明 — 避免短变量名 |
| 2026-08-12 13:10 | 自动生成 | raw/1-1-命名约定-函数-方法命名规范-c-02.md | 来源 run, idx=37, 规则: §1.1 命名约定 — 函数/方法命名规范 [C-02] |
