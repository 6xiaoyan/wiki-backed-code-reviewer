---
domain: tencent
rule_id: tencent-no-pointer-leak
title: 防止泄露指针（包括 %p）的值
priority: sub
source_file: rules/Tencent_C++_Security_Guide.md
source_section: "§1.5"
status: active
check_method: llm
deterministic_check: false
checkability: llm_checkable
conflicts_with: []
overrides: []
related_pages: []
---

# 防止泄露指针（包括 %p）的值

> 来源：腾讯 C/C++ 安全指南 §1.5 | 风险：信息泄露（中）

## 规则条款

包含 `%p` 或原始指针值的格式化输出不应到达不受信任的接收者。泄露地址有助于攻击者绕过 ASLR。不得将原始指针值用作唯一标识符或返回给用户。

## 正确示例

```c++
uint64_t g_object_id = 0;

void Foo::Foo() {
    this->object_id_ = g_object_id++;
}

uint64_t GetUniqueObjectId(const Foo* object) {
    if (object)
        return object->object_id_;
    else
        error(...);
}
```

## 错误示例

```c++
// 将指针值暴露为对象 ID
uint64_t GetUniqueObjectId(const Foo* pobject) {
    return (uint64_t)pobject;  // 暴露地址
}
```

## 检查方法

1. 搜索将指针转换为整数类型的代码：`(uint64_t)ptr`、`reinterpret_cast<uint64_t>(ptr)`
2. 搜索 `%p` 格式说明符的 printf 调用
3. 检查是否有指针值通过日志/网络/UI 输出
4. LLM 审查：判断指针值是否会到达用户可见输出

## 修复指南

1. 使用自增 ID 或 UUID 替代原始指针值作为对象标识符
2. 移除生产代码中的 `%p` 格式说明符
3. 如果调试必须输出指针，使用 `#ifdef DEBUG` 条件编译包裹
