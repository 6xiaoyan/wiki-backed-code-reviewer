---
domain: tencent
rule_id: tencent-no-oob-write
title: 防止各种越界写（向前/向后）
priority: sub
source_file: rules/Tencent_C++_Security_Guide.md
source_section: "§6.1"
status: active
check_method: llm
deterministic_check: false
checkability: llm_checkable
conflicts_with: []
overrides: []
related_pages: []
---

# 防止各种越界写（向前/向后）

> 来源：腾讯 C/C++ 安全指南 §6.1 | 风险：内存损坏（高）

## 规则条款

超出数组边界写入——无论是超出末尾（向前）还是超出开头（通过负索引向后）——都会损坏内存。所有数组索引必须验证上界和下界（参见 §7.6）。

## 正确示例

```c++
int a[5];
int b = user_controlled_value;
if (b >= 0 && b < 5) {
    a[b] = 3;  // 边界已验证
}
```

## 错误示例

```c++
int a[5];
a[5] = 0;  // 索引 5 超出末尾（有效索引 0..4）

int a[5];
int b = user_controlled_value;
a[b] = 3;  // 未验证 b 的边界
```

## 检查方法

1. 搜索数组索引，验证是否有边界检查
2. AddressSanitizer（ASan）在运行时检测堆/栈越界
3. 静态分析：Coverity、clang-tidy `bounds-check`

## 修复指南

1. 所有数组索引访问前添加边界检查
2. C++ 中优先使用 `std::array` + `.at()`（抛异常）或 `std::vector` + bounds checking
3. 参见 §7.6 索引上下界检查
