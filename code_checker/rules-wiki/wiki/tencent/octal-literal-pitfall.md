---
domain: tencent
rule_id: tencent-octal-literal
title: 注意八进制问题
priority: sub
source_file: rules/Tencent_C++_Security_Guide.md
source_section: "§1.9"
status: active
check_method: regex
deterministic_check: true
checkability: deterministic
conflicts_with: []
overrides: []
related_pages: []
---

# 注意八进制问题

> 来源：腾讯 C/C++ 安全指南 §1.9 | 风险：逻辑错误（中）

## 规则条款

使用前导零进行代码对齐可能意外创建八进制字面量。例如 `0020` 被解释为八进制 20（= 十进制 16），而非十进制 20。八进制字面量必须通过注释明确标注其用途。

## 正确示例

```c++
int access_mask = 0777;  // oct, rwxrwxrwx — 明确注释八进制用途
```

## 错误示例

```c++
char buf2[0020] = {0};  // 020（八进制）= 16（十进制），不是 20
memcpy(buf2, somebuf, 19);  // 越界写 — 缓冲区只有 16 字节
```

## 检查方法

1. 搜索以 `0` 开头的整数字面量（排除 `0x` 十六进制和单个 `0`）
2. 正则表达式：`\b0[0-7]+\b` 匹配八进制字面量
3. 检查是否有注释说明八进制用途；若无注释且在对齐场景中 → 可能是 bug

## 修复指南

1. 非八进制意图的 `0` 前缀 → 删除前导零
2. 八进制意图的 → 添加注释（如 `// oct`）
3. C++14+ 可用单引号分隔：`1'000'000` 代替前导零对齐
