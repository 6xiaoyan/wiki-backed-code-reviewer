---
domain: git
rule_id: git-commit-format
title: 提交信息格式
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
  - [[git-commit-type-enum]]
  - [[git-commit-desc-length]]
  - [[git-commit-desc-style]]
---

# 提交信息格式

## 规则条款

提交信息必须遵循精简模板：`<类型>: <描述>`，即类型与描述之间以冒号分隔，冒号后紧跟**一个**空格。
项目采用精简模板，不含scope（作用域）、body（正文）、footer（脚注）等扩展字段。每一条提交信息由两个部分构成：
| 部分 | 含义 | 要求 |
|------|------|------|
| `<类型>` | 提交类别 | 必须为11 种枚举值之一（见 [[git-commit-type-enum]]）|
| `<描述>` | 变更说明 | 不超过50 字符（见 [[git-commit-desc-length]]），风格要求见[[git-commit-desc-style]] |

格式示意：
```
<类型>: <描述>
 ^    ^^
 |    ||-- 一个空格 |    |--- 冒号
 |-------- 类型（feat/fix/docs/...）```

## 正确示例

```
feat: 添加用户注册功能
fix: 修复登录页面崩溃的问题
docs: 更新 API 文档
style: 统一代码缩进格式
refactor: 提取公共验证逻辑
perf: 优化数据库查询性能
test: 添加登录模块单元测试
chore: 升级依赖库版本
build: 配置 CMake 编译选项
ci: 添加 GitHub Actions 流水线
revert: 回滚用户模块重构
```

## 错误示例

```
feat:添加用户注册功能
```
错误原因：冒号后缺少空格。
```
feat : 添加用户注册功能
```
错误原因：冒号前多了一个空格。
```
feat  : 添加用户注册功能
```
错误原因：冒号前有多余空格。
```
添加用户注册功能
```
错误原因：缺少类型前缀和冒号分隔符。
```
feat:  添加用户注册功能
```
错误原因：冒号后多于一个空格。
```
feat：添加用户注册功能```
错误原因：使用了中文冒号（全角），必须使用英文冒号（半角）。
## 检查方法
1. 使用正则表达式`^(feat|fix|docs|style|refactor|perf|test|chore|build|ci|revert): .+$` 匹配提交信息。2. 若提交信息不匹配该模式，则判定为格式错误。3. 特别注意：冒号必须是英文半角冒号 `:`，冒号后必须有且仅有一个空格。
具体步骤：
1. 获取待检查的提交信息（`git log -1 --format=%s` 或提交时输入的信息）。2. 去除首尾空白字符。3. 用上述正则表达式进行全文匹配。4. 若匹配失败，报告具体的格式问题（缺少类型、冒号格式错误、空格数量错误等）。
## 修复指南

1. 确定本次提交的变更类型（feat/fix/docs 等，参见 [[git-commit-type-enum]]）。2. 在类型后添加英文半角冒号 `:`。3. 在冒号后添加**一个**空格。4. 在空格后写入变更描述（参见 [[git-commit-desc-style]] 和 [[git-commit-desc-length]]）。5. 若提交已经执行，可使用`git commit --amend -m "<修正后的信息>"` 修改最近一次提交信息。
## 审查清单

- [ ] 提交信息是否包含类型前缀。- [ ] 类型与描述之间是否使用了英文半角冒号 `:`。- [ ] 冒号后是否有且仅有一个空格？
- [ ] 类型是否在 11 种枚举值之一？（参见 [[git-commit-type-enum]]）- [ ] 描述是否符合长度和风格要求？（参见 [[git-commit-desc-length]]、[[git-commit-desc-style]]）
## 关联页面

- [[git-commit-type-enum]]：提交类型枚举（11 种允许值）
- [[git-commit-desc-length]] ：提交描述长度限制（0 字符。- [[git-commit-desc-style]] ：提交描述风格要求（祈使句、无语号等）
