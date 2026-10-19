---
domain: tencent
rule_id: tencent-smart-ptr-get-safety
title: 智能指针使用安全
priority: sub
source_file: rules/Tencent_C++_Security_Guide.md
source_section: "§8.7"
status: active
check_method: llm
deterministic_check: false
checkability: llm_checkable
conflicts_with: []
overrides: []
related_pages:
  - [[cpp/unique-ptr]]
  - [[cpp/shared-ptr]]
  - [[cpp/no-bare-ownership]]
---

# 智能指针使用安全

> 来源：腾讯 C/C++ 安全指南 §8.7 | 风险：内存损坏（高）

## 规则条款

从智能指针（`get()`）获取的原始指针如果比智能指针的所有权更持久，可能导致 use-after-free。当智能指针被重置、重新赋值或离开作用域时，其管理的对象被销毁，但之前通过 `get()` 获取的原始指针仍指向已销毁的内存。

## 正确示例

```c++
void Safe() {
    fool_u_ptr = make_unique<Foo>(1);
    fool_u_ptr->Function();             // 通过智能指针直接访问
    fool_u_ptr = make_unique<Foo>(2);   // Foo(1) 被安全释放
    fool_u_ptr->Function();             // 访问 Foo(2)
}
```

## 错误示例

```c++
std::unique_ptr<Foo> fool_u_ptr = nullptr;
Foo* pfool_raw_ptr = nullptr;

void Risk() {
    fool_u_ptr = make_unique<Foo>(1);
    pfool_raw_ptr = fool_u_ptr.get();   // 指向 Foo(1) 的原始指针
    pfool_raw_ptr->Function();          // OK

    fool_u_ptr = make_unique<Foo>(2);   // Foo(1) 被销毁
    pfool_raw_ptr->Function();          // USE-AFTER-FREE！
}
```

## 检查方法

1. 搜索 `get()` 调用从智能指针获取原始指针
2. 检查原始指针的生命周期是否超出智能指针的所有权
3. LLM 审查：判断裸指针是否逃逸到智能指针之后

## 修复指南

1. 避免将 `get()` 的结果存储在变量中——每次需要时调用
2. 如果必须使用裸指针，使用 `shared_ptr` 确保所有权持续
3. 公司规则的补充：参见 [[cpp/no-bare-ownership]]
