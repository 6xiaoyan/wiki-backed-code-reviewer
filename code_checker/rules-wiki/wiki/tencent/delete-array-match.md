---
domain: tencent
rule_id: tencent-delete-array-match
title: 对数组 delete 时需要 delete[]
priority: sub
source_file: rules/Tencent_C++_Security_Guide.md
source_section: "§1.7"
status: active
check_method: regex
deterministic_check: true
checkability: deterministic
conflicts_with: []
overrides: []
related_pages:
  - [[cpp/no-bare-new-delete]]
  - [[cpp/unique-ptr]]
---

# 对数组 delete 时需要 `delete[]`

> 来源：腾讯 C/C++ 安全指南 §1.7 | 风险：内存损坏（高）、逻辑错误（中）、内存泄漏（低）

## 规则条款

`delete[]` 和 `delete` 调用不同的释放函数（`operator delete[]` vs `operator delete`）。对 `new[]` 分配的内存使用 `delete` 是未定义行为。反之亦然。

现代 C++ 中，`string`、`vector` 和智能指针（如 `std::unique_ptr<T[]>`）消除了大多数原始 `delete[]` 的使用。公司规则已要求优先使用智能指针（参见 [[cpp/no-bare-new-delete]] 和 [[cpp/unique-ptr]]）。

## 正确示例

```c++
Foo* b = new Foo[5];
delete[] b;
```

## 错误示例

```c++
Foo* b = new Foo[5];
delete b;  // 未定义行为 — debug 构建会触发断言
```

## 检查方法

1. 搜索 `new[]` 分配：`new\s+\w+\[`
2. 搜索对应的 `delete`（不带 `[]`）
3. 工具支持：Valgrind/memcheck、AddressSanitizer（ASan）可检测运行时不匹配
4. 正则表达式：对每个 `new T[n]` 检查是否有对应的 `delete[]`

## 修复指南

1. `new[]` 必须对应 `delete[]`
2. `new` 必须对应 `delete`
3. **最佳实践：** 用 `std::vector` 替代数组 new，用 `std::unique_ptr<T[]>` 替代手动数组管理
4. 参见 [[cpp/no-bare-new-delete]] — 公司规则已禁止裸 new/delete

## 审查清单

- [ ] `new[]` 分配有对应的 `delete[]`
- [ ] 无数组/非数组 new-delete 混配
- [ ] C++ 代码优先使用 `std::vector` / `std::unique_ptr<T[]>`
