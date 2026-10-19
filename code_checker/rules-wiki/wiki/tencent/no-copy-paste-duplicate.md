---
domain: tencent
rule_id: tencent-no-copy-paste-dup
title: 检查复制粘贴的重复代码
priority: sub
source_file: rules/Tencent_C++_Security_Guide.md
source_section: "§2.7"
status: active
check_method: llm
deterministic_check: false
checkability: llm_checkable
conflicts_with: []
overrides: []
related_pages: []
---

# 检查复制粘贴的重复代码

> 来源：腾讯 C/C++ 安全指南 §2.7 | 风险：逻辑错误（中）

## 规则条款

相同的连续行通常表示复制粘贴 bug——程序员复制了一行但忘记修改其中的变量名或索引。连续两行完全相同的赋值或函数调用几乎总是 bug。

## 正确示例

```c++
void Foobar(SomeStruct& foobase, SomeStruct& foo1, SomeStruct& foo2) {
    foo1.bar = (foo1.bar & 0xffff) | (foobase.base & 0xffff0000);
    foo2.bar = (foo2.bar & 0xffff) | (foobase.base & 0xffff0000);  // 正确处理两个对象
}
```

## 错误示例

```c++
void Foobar(SomeStruct& foobase, SomeStruct& foo1, SomeStruct& foo2) {
    foo1.bar = (foo1.bar & 0xffff) | (foobase.base & 0xffff0000);
    foo1.bar = (foo1.bar & 0xffff) | (foobase.base & 0xffff0000);  // 复制粘贴 bug：应为 foo2
}
```

## 检查方法

1. 搜索相邻行中重复的语句
2. 特别关注连续两行完全相同的赋值/函数调用
3. clang-tidy 和 SonarQube 有复制粘贴检测
4. LLM 审查：相邻相同行中是否应有变量名差异

## 修复指南

1. 删除重复行或修正其中被错误复制的变量名
2. 如果逻辑确实相同，提取为 `inline` 函数或 lambda
