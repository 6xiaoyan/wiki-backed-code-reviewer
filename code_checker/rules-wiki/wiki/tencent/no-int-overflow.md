---
domain: tencent
rule_id: tencent-no-int-overflow
title: 防止整数溢出
priority: sub
source_file: rules/Tencent_C++_Security_Guide.md
source_section: "§7.1"
status: active
check_method: llm
deterministic_check: false
checkability: llm_checkable
conflicts_with: []
overrides: []
related_pages: []
---

# 防止整数溢出

> 来源：腾讯 C/C++ 安全指南 §7.1 | 风险：内存损坏（高）

## 规则条款

大小计算中的整数溢出可能导致分配不足的缓冲区大小和随后的缓冲区溢出。减法、乘法和加法操作前必须检查溢出条件，特别是在计算分配大小时。

## 正确示例

```c++
void Foo() {
    int size = len - kMicLen;
    if (size > 0 && size < 10) {  // 检查溢出（size > 0）和上限
        memcpy(dst, payload, size);
    }
}
```

## 错误示例

```c++
const int kMicLen = 4;

void Foo() {
    int len = 1;
    char payload[10] = {0};
    char dst[10] = {0};
    memcpy(dst, payload, len - kMicLen);  // 1 - 4 = 0xFFFFFFFD — 大量复制
}
```

## 检查方法

1. 搜索内存分配相关的算术运算：`malloc(a * b)`、`new T[n * m]`
2. 检查运算前是否有溢出验证
3. 编译器：`-ftrapv`（捕获有符号溢出）
4. UBSan（UndefinedBehaviorSanitizer）检测运行时整数溢出

## 修复指南

1. 乘法前检查 `a > SIZE_MAX / b`
2. 加法前检查 `a > SIZE_MAX - b`
3. 使用安全的整数运算库或编译器内置（GCC `__builtin_mul_overflow`）
