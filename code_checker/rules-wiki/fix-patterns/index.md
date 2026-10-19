# Fix Patterns 索引

> 修复模式知识库 —— 从历史修复中沉淀的模式，供 fix_agent 在重试时查阅。
>
> **raw/** 目录为自动生成的草稿，需人工审核后移至本目录方可被检索。

## SQLite / SQLCipher

- [[sqlite-必须使用-sqlcipher-加密]] — PRAGMA 必须在 sqlite3_key 之前设置，hex key 格式，secureZero 清理

## 安全

- [[sql-injection-parameterization]] — SQL 注入修复：字符串拼接 → 参数化查询（sqlite3_prepare_v2 + bind）
- [[no-hardcoded-keys]] — 硬编码密钥消除：用户输入主密码 + SHA-256 派生
- [[no-password-in-logs]] — 敏感信息泄露：禁止 qDebug 输出密码字段

## Qt / C++ 命名规范

- [[no-short-variable-names]] — 短变量名消除：单字符参数 → 描述性名称，头文件/实现/引用三处同步
- [[constant-naming-uppercase]] — 常量命名：camelCase → UPPER_CASE，static const → constexpr

## 使用方式

fix_agent 在修复被驳回后，可通过 `search_wiki("关键词", domain="fix-patterns")` 检索历史修复模式。

## 维护说明

- 新草稿生成在 `raw/` 目录，由 run 结束后自动产出
- 审核通过后移动到本目录，同时更新本索引文件
- 每条模式包含：关联规则、代码特征、修复步骤、来源 run
