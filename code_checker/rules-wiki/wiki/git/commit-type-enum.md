---
domain: git
rule_id: git-commit-type-enum
title: 提交类型枚举
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
  - [[git-commit-desc-length]]
  - [[git-commit-desc-style]]
---

# 提交类型枚举

## 规则条款

提交信息中的类型字段**仅限**以下 11 种值，不得使用除此之外的任何词语作为类型：

| 类型 | 含义 | 说明 |
|------|------|------|
| `feat` | 新功能| 新增一个功能或特化|
| `fix` | 修复 bug | 修复一个缺陷或错误 |
| `docs` | 文档变更 | 仅修改文档，不涉及代码逻辑变更 |
| `style` | 代码风格变动 | 不影响代码逻辑的格式调整（空格、缩进、分号等）|
| `refactor` | 代码重构 | 既不修复 bug 也不新增功能的代码结构调整|
| `perf` | 性能优化 | 提升性能的代码变更|
| `test` | 添加或修改测试| 添加缺失的测试或修正已有测试 |
| `chore` | 杂项 | 构建过程或辅助工具的变动（如依赖管理）|
| `build` | 构建系统或外部依赖项的变更| 影响构建系统或外部依赖的变更 |
| `ci` | 持续集成配置的变更| CI 配置文件和脚本的变更 |
| `revert` | 回滚 | 回滚之前的某个提交|

不允许在类型后添加scope（作用域），如`feat(auth): ...` 不符合精简模板规范。
## 正确示例

```
feat: 添加用户注册功能
fix: 修复登录页面崩溃的问题
docs: 更新 README 安装说明
style: 统一代码缩进为 4 空格
refactor: 提取公共验证逻辑到工具类
perf: 优化数据库查询索引
test: 添加用户模块单元测试
chore: 升级 lodash 到 4.17.21
build: 配置 webpack 打包优化
ci: 添加 GitHub Actions 自动部署
revert: 回滚用户模块重构
```

## 错误示例

```
feature: 添加用户注册功能
```
错误原因：`feature` 不是允许的类型，应使用`feat`。
```
bugfix: 修复登录崩溃
```
错误原因：`bugfix` 不是允许的类型，应使用`fix`。
```
update: 更新配置文件
```
错误原因：`update` 不在 11 种枚举值内。根据实际变更内容，应使用`feat`、`chore` 或 `refactor`。
```
修改: 调整页面布局
```
错误原因：类型必须为英文，中文"修改"不在枚举值内。
```
feat(auth): 添加用户注册功能
```
错误原因：精简模板不支持scope（作用域），应去掉`(auth)`。
```
merge: 合并分支
```
错误原因：`merge` 不是允许的类型。合并提交通常由 Git 自动生成，但手写提交信息不应使用此类型。
## 检查方法
1. 从提交信息中提取冒号前的内容作为类型候选值。2. 去除类型候选值首尾空白。3. 将类型候选值与 11 种允许值逐一比对（精确匹配，区分大小写）。4. 若不在允许列表中，报告具体违规值和最近的合法建议：
正则表达式（配合 [[git-commit-format]] 的格式检查使用）。
```
^(feat|fix|docs|style|refactor|perf|test|chore|build|ci|revert): .+$
```

其中 `(feat|fix|docs|style|refactor|perf|test|chore|build|ci|revert)` 部分精确枚举 11 种合法类型。
## 修复指南

1. 对照上方的类型含义表，确定本次提交最匹配的类型。2. 常见误用映射：
   | 错误写法 | 正确写法 | 适用场景 |
   |----------|----------|----------|
   | `feature` | `feat` | 新功能|
   | `bugfix` / `bug` / `hotfix` | `fix` | 缺陷修复 |
   | `update` / `change` / `modify` | `feat` / `refactor` / `chore` | 视实际变更而定 |
   | `add` / `new` | `feat` | 新增功能 |
   | `remove` / `delete` | `feat` / `refactor` | 视是否影响功能|
   | `improve` / `enhance` | `perf` / `refactor` | 视是否涉及性能 |

3. 若已提交，使用`git commit --amend -m "<修正后的信息>"` 修正确
## 审查清单

- [ ] 类型是否为英文小写？
- [ ] 类型是否在 11 种允许值之内？
- [ ] 类型后是否没有附加scope（如 `(auth)`）？
- [ ] 类型选择是否准确反映了变更性质。
## 关联页面

- [[git-commit-format]] ：提交信息格式（类型与描述的冒号空格规则）
- [[git-commit-desc-length]] ：提交描述长度限制（0 字符。- [[git-commit-desc-style]] ：提交描述风格要求（祈使句、无语号等）
