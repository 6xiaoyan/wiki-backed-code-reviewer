---
domain: tencent
rule_id: tencent-safe-process-creation
title: 创建进程类函数的安全规范
priority: sub
source_file: rules/Tencent_C++_Security_Guide.md
source_section: "§1.2"
status: active
check_method: llm
deterministic_check: false
checkability: llm_checkable
conflicts_with: []
overrides: []
related_pages: []
---

# 创建进程类函数的安全规范

> 来源：腾讯 C/C++ 安全指南 §1.2 | 风险：代码执行（高）、权限提升（高）

## 规则条款

`system`、`WinExec`、`CreateProcess`、`ShellExecute` 等函数需要仔细验证参数。可执行文件路径必须加双引号。

从用户输入或环境变量构建命令行时，必须校验用户提供的内容后再传递给 shell，防止命令注入。

## 正确示例

```c++
// 路径加双引号
WinExec("\"D:\\program files\\my folder\\foobar.exe\"", SW_SHOW);

// 用户输入校验后再传 shell
std::string cmdline = "ls ";
cmdline += user_input;
if (cmdline.find_first_not_of("1234567890.+-*/e ") == std::string::npos)
    system(cmdline.c_str());
else
    warning(...);
```

## 错误示例

```c++
// 路径未加引号 — 空格路径被误解析
WinExec("D:\\program files\\my folder\\foobar.exe", SW_SHOW);
// 如果 D:\program files\my.exe 存在，会先运行它

// 命令注入 — user_input 可以注入额外命令
std::string cmdline = "calc ";
cmdline += user_input;
system(cmdline.c_str());
// 例如 user_input = "1+1 && ls" 会运行两个命令
```

## 检查方法

1. 搜索进程创建函数调用：`system`、`WinExec`、`CreateProcess`、`ShellExecute`、`exec*`、`popen`
2. 检查可执行文件路径是否用双引号包裹
3. 检查命令行参数是否包含未校验的用户输入
4. LLM 审查：判断用户输入是否经过充分校验

## 修复指南

1. 可执行文件路径始终加双引号包裹
2. 用户输入在传给 shell 前进行白名单校验
3. 优先使用不经过 shell 的 API（如 `CreateProcess` 的直接参数形式而非 `system`）
4. 考虑使用 `execve` 等不经过 shell 的替代方案

## 审查清单

- [ ] 进程创建函数的路径参数加双引号
- [ ] 用户输入在传给 shell 前经过白名单校验
- [ ] 优先使用不经过 shell 的 API
