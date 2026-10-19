# git提交规范

建议使用业内广泛使用的 Git 提交规范（基于 Angular 提交规范扩展），包含格式说明和示例，便于团队协作和版本管理：

### 一、提交信息格式

业内广泛使用下方模板

```plaintext
<类型>[可选作用域]: <描述>

[可选正文]

[可选脚注]

```

考虑到实际使用，我们精简为下方模板：

```plaintext
<类型>: <描述>
```

示例：fix:修复通讯无法正常使用的bug

#### 1. 类型（Type）

用于说明提交的性质，必须为以下值之一：

1.  **feat**：新功能（feature）
    
    *   用于提交新功能。
        
    *   示例：`feat: 增加用户注册功能`
        
2.  **fix**：修复 bug
    
    *   用于提交 bug 修复。
        
    *   示例：`fix: 修复登录页面崩溃的问题`
        
3.  **docs**：文档变更
    
    *   用于提交仅文档相关的修改。
        
    *   示例：`docs: 更新 README 文件`
        
4.  **style**：代码风格变动（不影响代码逻辑）
    
    *   用于提交仅格式化、标点符号、空白等不影响代码运行的变更。
        
    *   示例：`style: 删除多余的空行`
        
5.  **refactor**：代码重构（既不是新增功能也不是修复 bug 的代码更改）
    
    *   用于提交代码重构。
        
    *   示例：`refactor: 重构用户验证逻辑`
        
6.  **perf**：性能优化
    
    *   用于提交提升性能的代码修改。
        
    *   示例：`perf: 优化图片加载速度`
        
7.  **test**：添加或修改测试
    
    *   用于提交测试相关的内容。
        
    *   示例：`test: 增加用户模块的单元测试`
        
8.  **chore**：杂项（构建过程或辅助工具的变动）
    
    *   用于提交构建过程、辅助工具等相关的内容修改。
        
    *   示例：`chore: 更新依赖库`
        
9.  **build**：构建系统或外部依赖项的变更
    
    *   用于提交影响构建系统的更改。
        
    *   示例：`build: 升级 webpack 到版本 5`
        
10.  **ci**：持续集成配置的变更
    
    *   用于提交 CI 配置文件和脚本的修改。
        
    *   示例：`ci: 修改 GitHub Actions 配置文件`
        
11.  **revert**：回滚
    
    *   用于提交回滚之前的提交。
        
    *   示例：`revert: 回滚 feat: 增加用户注册功能`
        

#### 2. 作用域（Scope，可选）

说明提交影响的范围，如模块、组件、文件名等，示例：`user`（用户模块）、`login`（登录功能）、`redis`（Redis 相关）。

#### 3. 描述（Description）

*   简短描述提交内容（不超过 50 字符）
    
*   首字母小写，结尾不加句号
    
*   使用祈使句（如“添加”而非“添加了”，“修复”而非“修复了”）
    

#### 4. 正文（Body，可选）

*   详细描述提交原因、实现方式、解决的问题等
    
*   每行不超过 72 字符
    
*   可分多行，使用空行分隔段落
    

#### 5. 脚注（Footer，可选）

*   **关闭 Issue**：如 `Closes #123`（关闭 Issue 123）
    
*   **不兼容变更**：以 `BREAKING CHANGE:` 开头，说明变更内容和迁移方法
    

### 二、示例

#### 1. 新功能提交

```c++
feat(login): 添加验证码登录功能

- 新增图形验证码生成接口
- 登录时验证验证码有效性
- 验证码过期时间设置为 5 分钟

Closes #456

```

#### 2. 修复 Bug 提交

```c++
fix(order): 修复订单金额计算错误

当商品数量为 0 时，总价计算逻辑异常，导致负数金额。
现已添加数量校验，确保数量 ≥ 1 时才计算总价。

Fixes #789

```

#### 3. 文档更新提交

```c++
docs: 更新 API 文档中的参数说明

补充了 /user/list 接口的分页参数描述，
明确 pageSize 最大值为 100。

```

#### 4. 重构提交

```c++
refactor(utils): 重构日期工具类

- 移除冗余的日期转换方法
- 统一使用 LocalDateTime 替代 Date
- 优化时区处理逻辑

```

#### 5. 不兼容变更提交

```c++
feat(api): 重构用户信息接口

将 /v1/user 接口迁移至 /v2/user，
返回格式从 JSON 改为 Protocol Buffer。

BREAKING CHANGE: 接口路径和返回格式变更，
请更新客户端请求地址并适配 PB 格式解析。
Closes #101

```

### 三、规范优势

1.  **自动化支持**：可通过工具（如 `commitlint`）校验提交信息格式
    
2.  **生成日志**：自动生成清晰的 CHANGELOG（如 `standard-version` 工具）
    
3.  **便于回溯**：快速定位某类变更（如筛选所有 `fix` 类型的提交）
    
4.  **团队协作**：统一提交风格，减少沟通成本
    

### 四、推荐Git管理软件

##### [**sourcetree**](https://www.sourcetreeapp.com/)

[Sourcetree 使用教程 | 菜鸟教程](https://www.runoob.com/git/source-tree-intro.html)

##### [**小乌龟**](https://tortoisegit.org/download/)

[git可视化工具小乌龟安装&使用\_git小乌龟-CSDN博客](https://blog.csdn.net/xwnxwn/article/details/108694863)

参考文档：

[git commit 代码提交规范 - zetaiota - 博客园](https://www.cnblogs.com/anly95/p/13163384.html)

[git 代码提交规范，feat，fix，chore都是什么意思?\_git fix-CSDN博客](https://blog.csdn.net/chenyajundd/article/details/139322838)

# 附录

可以用下面小工具理解如何使用

[https://mp.weixin.qq.com/s/0SEX\_Sv7Ns3nxO7UBBB4Bw: https://mp.weixin.qq.com/s/0SEX\_Sv7Ns3nxO7UBBB4Bw](https://mp.weixin.qq.com/s/0SEX_Sv7Ns3nxO7UBBB4Bw)