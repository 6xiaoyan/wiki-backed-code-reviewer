---
domain: tencent
rule_id: tencent-no-div-zero
title: 检查除以零异常
priority: sub
source_file: rules/Tencent_C++_Security_Guide.md
source_section: "§7.4"
status: active
check_method: regex
deterministic_check: true
checkability: deterministic
conflicts_with: []
overrides: []
related_pages: []
---

# 检查除以零异常

> 来源：腾讯 C/C++ 安全指南 §7.4 | 风险：拒绝服务（低）

## 规则条款

除以零导致未定义行为（通常是崩溃或 SIGFPE 信号）。所有除法运算和取模运算的除数必须在运算前进行非零检查。

## 正确示例

```c++
int divide(int x, int y) {
    if (y == 0) {
        throw DivideByZero;  // 或返回错误码
    }
    return x / y;
}
```

## 错误示例

```c++
int divide(int x, int y) {
    return x / y;  // y == 0 → 未定义行为（崩溃）
}
```

## 检查方法

1. 搜索所有 `/` 和 `%` 操作符
2. 对每个操作，验证除数之前是否有零检查
3. 编译器/静态分析：Coverity `DIVIDE_BY_ZERO`

## 修复指南

1. 除法/取模前检查除数 `!= 0`
2. 返回错误码或抛异常（非零除数）
3. 使用 `assert(y != 0)` 在 Debug 构建中捕获
