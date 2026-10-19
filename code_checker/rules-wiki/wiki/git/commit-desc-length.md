---
domain: git
rule_id: git-commit-desc-length
title: 提交描述长度
priority: main
source_file: rules/git规范.md
source_section: "### 一、提交信息格式
status: active
check_method: regex
deterministic_check: true
checkability: deterministic
conflicts_with: []
overrides: []
related_pages:
  - [[git-commit-format]]
  - [[git-commit-type-enum]]
  - [[git-commit-desc-style]]
---

# 提交描述长度

## 规则条款

提交信息中 `<描述>` 部分的字符数**不超过 50 字符**。
"描述"指格式`<类型>: <描述>` 中冒号空格之后的所有内容。长度计算包含汉字、字母、数字、标点符号及空格在内的所有可见字符。
中文环境下一个汉字计为1 个字符（与GitHub/GitLab 等平台的显示宽度一致，与Unicode 码点数计数，而非字节数或终端渲染列宽）。
## 正确示例

```
feat: 添加用户注册功能
```
描述"添加用户注册功能"共8 个字符，不超过50。
```
fix: 修复登录页面崩溃的问题```
描述"修复登录页面崩溃的问题共11 个字符，不超过50。
```
docs: 更新 API 认证文档
```
描述"更新 API 认证文档"共10 个字符，不超过50。
```
refactor: extract common validation logic
```
描述"extract common validation logic"共33 个字符，不超过50。
## 错误示例

```
feat: 添加用户注册功能，包括邮箱验证、手机号验证、密码强度校验、验证码发送、以及注册成功后的欢迎邮件发送和初始角色分配逻辑
```
错误原因：描述共 57 个字符，超过 50 字符上限定
```
fix: 修复在特定网络条件下当用户连续快速点击提交按钮时可能导致表单重复提交并引发数据库死锁的问题```
错误原因：描述共 51 个字符，超过 50 字符上限定
## 检查方法
1. 从提交信息中提取描述部分：去掉`<类型>: ` 前缀（类型+ 冒号 + 空格），剩余内容即为描述。2. 计算描述部分的字符数（按 Unicode 码点计数，使用编程语言的标准字符串长度函数即可）：
   - Python: `len(description)`
   - JavaScript: `description.length`
   - C++: `description.length()` (std::string) 或按 UTF-8 码点计数
3. 若字符数 > 50，报告违规，给出实际字符数和超出量。
具体步骤：
1. 取得完整的提交信息字符串。2. 使用正则表达式`^(feat|fix|docs|style|refactor|perf|test|chore|build|ci|revert): (.+)$` 提取捕获组。3. 对第二个捕获组（描述部分）计算字符数。4. 比较字符数与 50 的关系
## 修复指南

1. 识别描述中的冗余词语，优先删除修饰性词汇。2. 若描述信息确实较多，考虑拆分为多次提交，每次提交聚焦单一变更。3. 压缩技巧：

   | 原描述 | 压缩后 |
   |--------|--------|
   | 添加用户注册功能包括邮箱和手机验证| 添加用户注册及验证功能|
   | 修复在特定网络条件下重复提交导致的问题| 修复重复提交导致死锁的问题|
   | 更新项目 README 文档中的安装说明部分 | 更新 README 安装说明 |

4. 若已提交，使用`git commit --amend -m "<修正后的信息>"` 修正最近一次提交。
## 审查清单

- [ ] 描述部分的字符数是否不超过50。- [ ] 描述是否足够简洁且仍能清晰表达变更意图例- [ ] 长描述是否已考虑拆分为多次提交？

## 关联页面

- [[git-commit-format]] ：提交信息格式（类型与描述的冒号空格规则）
- [[git-commit-type-enum]]：提交类型枚举（11 种允许值）
- [[git-commit-desc-style]] ：提交描述风格要求（祈使句、无语号等）
