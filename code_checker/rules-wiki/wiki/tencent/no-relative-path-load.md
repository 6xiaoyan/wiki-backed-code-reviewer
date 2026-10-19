---
domain: tencent
rule_id: tencent-no-relative-path
title: 避免相对路径导致的安全问题（DLL、EXE 劫持等问题）
priority: sub
source_file: rules/Tencent_C++_Security_Guide.md
source_section: "§5.2"
status: active
check_method: regex
deterministic_check: true
checkability: deterministic
conflicts_with: []
overrides: []
related_pages: []
---

# 避免相对路径导致的安全问题（DLL、EXE 劫持）

> 来源：腾讯 C/C++ 安全指南 §5.2 | 风险：逻辑漏洞（中）

## 规则条款

使用相对路径加载模块允许攻击者在搜索顺序中优先放置恶意 DLL/EXE。必须使用绝对路径加载动态库和可执行文件。

## 正确示例

```c++
// 安全实践
HINSTANCE hinst = ::LoadLibraryEx("C:\\Program Files\\MyApp\\dll_nolib.dll",
    NULL, LOAD_LIBRARY_SEARCH_SYSTEM32);
```

## 错误示例

```c++
HINSTANCE hinst = ::LoadLibrary("dll_nolib.dll");
// 如果当前目录存在恶意 dll_nolib.dll，会加载它
```

## 检查方法

1. 搜索 `LoadLibrary`（非 `LoadLibraryEx`）、`LoadLibraryEx`（未指定完整路径）
2. 搜索 `CreateProcess`、`ShellExecute` 中使用了相对路径
3. 正则表达式：检查路径参数是否为绝对路径

## 修复指南

1. 始终在 `LoadLibrary`、`LoadLibraryEx`、`CreateProcess`、`ShellExecute` 中使用绝对路径
2. 在启动时调用 `SetDllDirectory(TEXT(""))` 从 DLL 搜索中移除当前目录
3. 使用 `SetDefaultDllDirectories` + `AddDllDirectory`/`RemoveDllDirectory`
