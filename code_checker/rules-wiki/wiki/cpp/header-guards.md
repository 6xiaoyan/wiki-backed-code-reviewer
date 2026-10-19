---
domain: cpp
rule_id: cpp-header-guards
title: 头文件保护宏
priority: main
source_file: rules/C++代码规范.md
source_section: "### 1.2 头文件规范"
status: active
check_method: regex
deterministic_check: true
checkability: deterministic
conflicts_with: []
overrides: []
related_pages:
  - [[cpp-include-order]]
  - [[cpp-forward-declarations]]
  - [[cpp-typing-conventions]]
---

# 头文件保护宏

## 规则条款

每个头文件必须具有唯一的保护宏，防止重复包含。保护宏格式要求：
- 全大写字母和下划线
- 必须以 `_H_` 结尾（注意：是 `_H_` 而非 `_H`）
- 段数不少于 2 段（即至少包含一个下划线分隔符）
- 命名格式：`PROJECT_MODULE_FILENAME_H_`

禁止使用 `#pragma once` 替代保护宏。虽然多数编译器支持 `#pragma once`，但它不是 C++ 标准的一部分，且在某些复杂包含场景下（符号链接、网络挂载等）可能失效。
## 正确示例

```cpp
#ifndef PROJECT_NETWORK_HTTP_CLIENT_H_
#define PROJECT_NETWORK_HTTP_CLIENT_H_

// header content goes here

#endif // PROJECT_NETWORK_HTTP_CLIENT_H_
```

对于嵌套模块：
```cpp
#ifndef PROJECT_DATABASE_INTERNAL_CONNECTION_POOL_H_
#define PROJECT_DATABASE_INTERNAL_CONNECTION_POOL_H_

// header content goes here

#endif // PROJECT_DATABASE_INTERNAL_CONNECTION_POOL_H_
```

## 错误示例

```cpp
// too generic — high risk of name collision
#ifndef HTTP_CLIENT_H
#define HTTP_CLIENT_H
// ...
#endif
```

```cpp
// missing trailing _ — does not end with _H_
#ifndef PROJECT_NETWORK_HTTP_CLIENT_H
#define PROJECT_NETWORK_HTTP_CLIENT_H
// ...
#endif
```

```cpp
// single segment — insufficient namespace protection
#ifndef HTTPCLIENT_H_
#define HTTPCLIENT_H_
// ...
#endif
```

```cpp
// using #pragma once — not standard, disallowed
#pragma once
```

## 检查方法
1. 对每个 `.h` / `.hpp` 文件，读取文件头部内容。
2. 验证第一行非注释非空白行为 `#ifndef` 指令。
3. 验证紧随其后的非注释非空白行为 `#define` 指令，且宏名与 `#ifndef` 中的宏名完全相同。
4. 验证文件末尾（通常在最后一行或倒数几行）存在 `#endif`，且 `#ifndef` 与 `#endif` 数量匹配。
5. 验证宏名格式，正则模式：
   ```
   ^[A-Z][A-Z0-9]*(_[A-Z][A-Z0-9]*)+_H_$
   ```
   拆解：
   - `^[A-Z][A-Z0-9]*`：首段以大写字母开头
   - `(_[A-Z][A-Z0-9]*)+`：至少一段额外的下划线分段（保证段数>=2）
   - `_H_$`：以 `_H_` 结尾
6. 验证不存在 `#pragma once` 指令。
## 修复指南

1. 如果使用 `#pragma once`：替换为标准的 `#ifndef` / `#define` / `#endif` 保护宏。
2. 如果宏名格式不正确：按 `PROJECT_MODULE_FILENAME_H_` 格式重命名。
3. 如果宏名存在冲突风险：添加更多命名空间层级（如子模块名）。
4. 确保 `#endif` 后有注释注明对应的宏名（推荐但非强制）。
## 审查清单

- [ ] 每个 `.h` 文件是否都有 `#ifndef` / `#define` 保护
- [ ] 保护宏名是否全大写
- [ ] 保护宏名是否以 `_H_` 结尾
- [ ] 保护宏段数是否 >= 2
- [ ] 保护宏是否具有足够的唯一性（包含项目和模块前缀）
- [ ] `#endif` 是否与 `#ifndef` 的宏名一致
## 关联页面

- [[cpp-include-order]]
- [[cpp-forward-declarations]]
- [[cpp-templates-in-headers]]
- [[cpp-inline-functions]]
- [[cpp-typing-conventions]]
