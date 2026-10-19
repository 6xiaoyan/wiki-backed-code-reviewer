---
domain: git
rule_id: git-commit-desc-style
title: 提交描述风格
priority: main
source_file: rules/git规范.md
source_section: "### 一、提交信息格式"
status: active
check_method: regex
deterministic_check: true
checkability: deterministic
conflicts_with: []
overrides: []
related_pages:
  - [[git-commit-format]]
  - [[git-commit-type-enum]]
  - [[git-commit-desc-length]]
---

# 提交描述风格

## 规则条款

提交描述（`<类型>: <描述>` 中冒号空格之后的部分）必须满足以下风格要求：

1. **结尾不加句号**（中文句号`。` 和英文句号`.` 均禁止出现在描述末尾）。2. **使用祈使句**：用"添加"而非"添加了"，用"修复"而非"修复了"，用"更新"而非"更新了"——即用动词原形描述变更，而非过去时或完成时。3. **首字母小写**（英文描述）：若描述以英文开头，首字母必须小写，如`fix: fix login crash` 而非 `fix: Fix login crash`。中文描述不适用此条（中文无大小写概念）。

简而言之，提交描述应该像一条命令：告诉代码库做什么，而非"做了什么"。

## 正确示例

中文描述（祈使句，无语号）：

```
feat: 添加用户注册功能
fix: 修复登录页面崩溃的问题
docs: 更新 API 认证文档
refactor: 提取公共验证逻辑
perf: 优化数据库查询性能
test: 添加登录模块单元测试
chore: 升级依赖库版本
build: 配置 webpack 打包优化
ci: 添加 GitHub Actions 流水线
revert: 回滚用户模块重构
```

英文描述（祈使句、首字母小写、无语号）：

```
feat: add user registration
fix: fix login page crash
docs: update API authentication docs
refactor: extract common validation logic
perf: optimize database query performance
test: add unit tests for login module
chore: upgrade lodash to 4.17.21
build: configure webpack optimization
ci: add GitHub Actions pipeline
revert: revert user module refactor
```

## 错误示例

### 结尾加句号
```
feat: 添加用户注册功能。
```
错误原因：描述以中文句号 `。` 结尾。
```
feat: add user registration.
```
错误原因：描述以英文句号 `.` 结尾。
### 使用了过去时/完成时
```
feat: 添加了用户注册功能
```
错误原因：`添加了` 是完成时/过去时，应使用祈使句 `添加`。
```
fix: 修复了登录页面崩溃
```
错误原因：`修复了` 是完成时，应使用祈使句`修复`。
```
feat: added user registration
```
错误原因：`added` 是过去时，应使用祈使句`add`。
```
fix: fixed login crash
```
错误原因：`fixed` 是过去时，应使用祈使句`fix`。
### 英文首字母大写
```
feat: Add user registration
```
错误原因：英文描述首字母 `A` 大写，应使用小写 `add`。
```
fix: Fix login page crash
```
错误原因：英文描述首字母 `F` 大写，应使用小写 `fix`。
### 组合错误

```
feat: 添加了用户注册功能。
```
错误原因：同时使用了完成时`添加了` 和结尾句号`。`。
```
fix: Fixed login crash.
```
错误原因：同时使用了首字母大写`Fixed`、过去时 `ed` 和结尾句号`.`。
## 检查方法
1. 从提交信息中提取描述部分（`<类型>: ` 之后的所有内容）。2. **结尾句号检查**：检查描述最后一个字符是否为 `。` 或 `.`。若是，报告违规。3. **祈使句检查（中文）**：检查描述中是否包含常见完成时助词`了`。若包含（如 `添加了`、`修复了`、`更新了`），提示可能使用了完成时而非祈使句。4. **首字母检查（英文）**：若描述以ASCII 字母开头（A-Z 或 a-z），检查首字符是否为大写（A-Z）。若是大写，报告违规。

注意：描述可能为中英混合（如 `更新 README 文档`），此时中文部分检查祈使句，英文部分检查大小写即可，不必过度约束。

自动化检查建议逻辑：
```
function checkDescStyle(description):
    errors = []
    
    // 1. 结尾句号
    if description ends with "。" or ".":
        errors.append("描述结尾不得加句号")
    
    // 2. 中文完成时助词
    if "了" in description:
        errors.append("描述疑似使用完成时（"了"），建议使用祈使句")
    
    // 3. 英文首字母大写
    if description[0] is ASCII uppercase letter (A-Z):
        errors.append("英文描述首字母应小写")
    
    return errors
```

## 修复指南

1. **移除结尾句号**：删除描述末尾的 `。` 或 `.`。2. **转换为祈使句**：
   - 中文：去掉动词后的`了`（`添加了` -> `添加`，`修复了` -> `修复`）。
   - 英文：将过去时动词改为原形（`added` -> `add`，`fixed` -> `fix`，`updated` -> `update`，`removed` -> `remove`）。3. **修正英文首字母**：将描述首字母改为小写（仅限ASCII 开头的情况）。4. 若已提交，使用`git commit --amend -m "<修正后的信息>"` 修正最近一次提交。
## 审查清单

- [ ] 描述末尾是否没有句号（`。` 或 `.`）？
- [ ] 中文描述是否使用了祈使句（无 `了` 等完成时助词）？
- [ ] 英文描述首字母是否为小写？
- [ ] 英文描述是否使用了动词原形（非过去时）？
- [ ] 描述是否像一条命令——告诉代码库"做什么"。
## 关联页面

- [[git-commit-format]] ：提交信息格式（类型与描述的冒号空格规则）
- [[git-commit-type-enum]] ：提交类型枚举（11 种允许值）
- [[git-commit-desc-length]] ：提交描述长度限制（50 字符）。
