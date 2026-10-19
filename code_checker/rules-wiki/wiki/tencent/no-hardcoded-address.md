---
domain: tencent
rule_id: tencent-no-hardcoded-address
title: 不应当向指针赋予写死的地址
priority: sub
source_file: rules/Tencent_C++_Security_Guide.md
source_section: "§8.3"
status: active
check_method: regex
deterministic_check: true
checkability: deterministic
conflicts_with: []
overrides: []
related_pages: []
---

# 不应当向指针赋予写死的地址

> 来源：腾讯 C/C++ 安全指南 §8.3 | 风险：内存损坏（高）

## 规则条款

在嵌入式/固件上下文之外，向指针分配硬编码地址是危险的，因为内存布局在系统和版本之间各不相同。硬编码地址可能在当前平台上恰好有效，但在其他版本或平台上会导致崩溃或内存损坏。

## 正确示例

```c++
// 通过正常分配获取指针
int* ptr = new int;
*ptr = 42;

// 或嵌入式场景中通过文档明确标注
// #define DEVICE_REG_BASE 0x40000000  // SoC datasheet §3.2
```

## 错误示例

```c++
int* ptr = (int*)0x12345678;  // 硬编码地址 — 可能在任何位置
*ptr = 42;                    // 未定义行为
```

## 检查方法

1. 搜索将整数字面量转换为指针的代码
2. 正则表达式：`= *\(?\w+\*\)? *0x[0-9a-fA-F]+`（非零十六进制转换为指针）
3. 排除嵌入式平台的寄存器映射（需要有明确的 SoC 文档支持）

## 修复指南

1. 通过标准分配获取指针（`new`、`malloc`、栈分配）
2. 如果在嵌入式平台确实需要硬编码 MMIO 地址，添加文档注释并封装为 `constexpr` 常量
