---
domain: tencent
rule_id: tencent-no-path-traversal
title: 避免路径穿越问题
priority: sub
source_file: rules/Tencent_C++_Security_Guide.md
source_section: "§5.1"
status: active
check_method: regex
deterministic_check: true
checkability: deterministic
conflicts_with: []
overrides: []
related_pages:
  - [[cpp/no-unvalidated-input]]
---

# 避免路径穿越问题

> 来源：腾讯 C/C++ 安全指南 §5.1 | 风险：逻辑漏洞（高）

## 规则条款

从外部输入构建的文件路径必须进行清理，防止 `../` 穿越。攻击者可以通过 `../../etc/passwd` 等路径遍历技术读取或写入预期目录之外的任意文件。

## 正确示例

```c++
char file_path[PATH_MAX] = "/home/user/code/";
char name[20] = "../file.txt";
if (strstr(name, "..") != NULL) {
    return;  // 拒绝穿越尝试
}
int fd = open(file_path, O_RDONLY);
```

## 错误示例

```c++
char file_path[PATH_MAX] = "/home/user/code/";
char name[20] = "../file.txt";  // 路径穿越
memcpy(file_path + strlen(file_path), name, sizeof(name));
int fd = open(file_path, O_RDONLY);  // 读取预期目录之外的任意文件
```

## 检查方法

1. 搜索包含 `..` 的字符串拼接路径操作
2. 搜索 `open`、`fopen`、`CreateFile` 等使用的路径是否包含用户可控组件
3. 正则表达式：检查文件路径参数是否来自外部输入

## 修复指南

1. 过滤或拒绝包含 `..`、`/`、`\`、`~` 的用户输入
2. 使用白名单而非黑名单验证路径
3. 拼接前调用规范化函数：`realpath()`、`GetFullPathName()`
4. 使用 `chroot` 或 jail 限制文件访问范围
