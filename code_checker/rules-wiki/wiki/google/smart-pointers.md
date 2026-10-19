---
domain: google
rule_id: google-smart-pointers
title: 所有权与智能指针（Google C++ Style Guide 对照）
priority: sub
source_file: rules/Google_C++_Style_Guide.md
source_section: "§5.1"
status: active
check_method: llm
deterministic_check: false
checkability: llm_checkable
conflicts_with: []
overrides: []
related_pages:
  - [[cpp/unique-ptr]]
  - [[cpp/shared-ptr]]
  - [[cpp/weak-ptr]]
  - [[cpp/make-smart-ptr]]
---

# 所有权与智能指针（Google C++ Style Guide 对照）

> 来源：Google C++ Style Guide §5.1 | 与公司规则基本一致

## 与公司规则的对照

| Google 条款 | 公司规则 | 一致性 |
|------------|---------|--------|
| 优先使用 `std::unique_ptr` 进行明确的所有权转移 | [[cpp/unique-ptr]] | ✅ 一致 |
| 避免共享所有权，`shared_ptr` 仅用于真正需要的场景 | [[cpp/shared-ptr]] | ✅ 一致 |
| 使用 `std::make_unique` 和 `std::make_shared` | [[cpp/make-smart-ptr]] | ✅ 一致 |
| 禁止使用 `std::auto_ptr` | — | ✅（C++17 已移除） |

## Google 补充

```cpp
// 所有权转移的清晰接口
std::unique_ptr<Foo> FooFactory();
void FooConsumer(std::unique_ptr<Foo> ptr);
```

- 动态分配的对象应有单一、固定的所有者
- 通过智能指针转移所有权
- 使用 `std::shared_ptr<const Foo>` 强调共享但不修改
- `std::weak_ptr` 用于打破循环引用（参见 [[cpp/weak-ptr]]、[[cpp/weak-ptr-cycles]]）
