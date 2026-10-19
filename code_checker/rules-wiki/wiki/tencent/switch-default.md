---
domain: tencent
rule_id: tencent-switch-default
title: switch 中应有 default
priority: sub
source_file: rules/Tencent_C++_Security_Guide.md
source_section: "§2.1"
status: active
check_method: regex
deterministic_check: true
checkability: deterministic
conflicts_with: []
overrides: []
related_pages:
  - [[qt/switch-break]]
  - [[qt/switch-case-alignment]]
---

# switch 中应有 default

> 来源：腾讯 C/C++ 安全指南 §2.1 | 风险：逻辑错误（中）、内存泄漏（中）

## 规则条款

每个 `switch` 必须包含 `default` 分支。缺少 `default` 意味着未列举的 case 值不会执行任何逻辑，可能导致资源泄漏、未初始化变量或其他未预期行为。

## 正确示例

```c++
int Foo(int bar) {
    switch (bar & 7) {
        case 0: return Foobar(bar);
        case 1: return Foobar(bar * 2);
        default: return -1;
    }
}
```

## 错误示例

```c++
int Foo(int bar) {
    switch (bar & 7) {
        case 0: return Foobar(bar);
        case 1: return Foobar(bar * 2);
        // 缺少 default — bar & 7 为 2..7 时无返回值！
    }
}
```

## 检查方法

1. 搜索 `switch` 语句，验证每个的 case 列表是否包含 `default:` 标签
2. 正则表达式：对每个 `switch` 语句体，检查是否存在 `default\s*:`

## 修复指南

1. 为每个 `switch` 添加 `default` 分支
2. `default` 中可以返回错误值、记录日志、或 `assert(false)`（标记不可达状态）

## 审查清单

- [ ] 每个 `switch` 语句包含 `default` 分支
- [ ] `default` 分支有明确的处理逻辑（而非空）
