---
domain: tencent
rule_id: tencent-no-alloca-vla
title: 尽量减少使用 _alloca 和可变长度数组
priority: sub
source_file: rules/Tencent_C++_Security_Guide.md
source_section: "§1.3"
status: active
check_method: regex
deterministic_check: true
checkability: deterministic
conflicts_with: []
overrides: []
related_pages:
  - [[cpp/no-cstyle-strings-arrays]]
---

# 尽量减少使用 `_alloca` 和可变长度数组

> 来源：腾讯 C/C++ 安全指南 §1.3 | 风险：内存损坏（高）、拒绝服务（低）

## 规则条款

`_alloca` 和可变长度数组（VLA）分配编译时未知大小的内存。在循环内可能导致栈溢出（拒绝服务）或内存损坏。VLA 是 C++ 中的非标准扩展，禁止使用。

## 正确示例

```c++
// 用堆分配替代
for (int i = 0; i < 100000; i++) {
    char* foo = (char*)malloc(0x10000);
    // ... 使用 foo ...
    free(foo);
    foo = NULL;
}

// C++ 中用 std::string 替代 VLA
void Foo(int size) {
    std::string msg(size, '\0');
}
```

## 错误示例

```c++
// 循环中使用 _alloca — 栈溢出风险
for (int i = 0; i < 100000; i++) {
    char* foo = (char*)_alloca(0x10000);
}

// VLA — C++ 非标准扩展
void Foo(int size) {
    char msg[size];  // 不可控的栈溢出风险
}
```

## 检查方法

1. 搜索 `_alloca(` 调用
2. 搜索可变长度数组声明（函数内的 `type name[non_const_expr]`）
3. 正则表达式：`\b_alloca\s*\(` 和 `\w+\s+\w+\s*\[[^\]\d][^\]]*\]`（排除常量大小）

## 修复指南

1. 将 `_alloca` 替换为 `malloc`/`new` + `free`/`delete`（堆分配）
2. 将 VLA 替换为 `std::vector` 或 `std::string`（C++）
3. 确保堆分配有对应的释放

## 审查清单

- [ ] 无 `_alloca` 调用
- [ ] 无可变长度数组（VLA）
- [ ] 循环内无栈分配可变大小内存
