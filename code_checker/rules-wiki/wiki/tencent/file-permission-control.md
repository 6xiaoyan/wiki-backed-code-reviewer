---
domain: tencent
rule_id: tencent-file-permissions
title: 文件权限控制
priority: sub
source_file: rules/Tencent_C++_Security_Guide.md
source_section: "§5.3"
status: active
check_method: regex
deterministic_check: true
checkability: deterministic
conflicts_with: []
overrides: []
related_pages: []
---

# 文件权限控制

> 来源：腾讯 C/C++ 安全指南 §5.3 | 风险：逻辑漏洞（中）

## 规则条款

创建的文件必须具有限制性权限。使用过于宽松的权限（如 `0777`）允许任何用户读写甚至执行该文件，可能导致敏感信息泄露或文件被篡改。

## 正确示例

```c++
// Unix: 仅所有者可读写
int fd = creat("file.txt", 0600);

// 或使用 open 指定权限
int fd = open("file.txt", O_WRONLY | O_CREAT | O_TRUNC, 0600);

// Windows: 使用安全描述符限制访问
```

## 错误示例

```c++
if (creat("file.txt", 0777) < 0) {  // 任何人都可以 读/写/执行
    printf("File creation failed\n");
}
```

## 检查方法

1. 搜索 `creat`、`open(..., O_CREAT)`、`fopen`、`CreateFile` 调用
2. 检查文件创建权限参数是否过于宽松（Unix: `0777`、`0666`；Windows: `GENERIC_ALL`）
3. 正则表达式：`\bcreat\s*\([^,]+,\s*0?7\d7\b`

## 修复指南

1. Unix: 使用 `0600`（仅所有者读写）或 `0640`（所有者+组）
2. Windows: 为 `CreateFile` 配置合适的安全属性
3. 使用 `umask` 限制默认权限
