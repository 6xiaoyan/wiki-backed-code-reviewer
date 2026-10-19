---
domain: tencent
rule_id: tencent-no-type-confusion
title: 防止错误的类型转换（type confusion）
priority: sub
source_file: rules/Tencent_C++_Security_Guide.md
source_section: "§8.6"
status: active
check_method: llm
deterministic_check: false
checkability: llm_checkable
conflicts_with: []
overrides: []
related_pages:
  - [[cpp/no-reinterpret-c-cast]]
---

# 防止错误的类型转换（type confusion）

> 来源：腾讯 C/C++ 安全指南 §8.6 | 风险：内存损坏（高）

## 规则条款

通过错误的成员/类型访问联合体或多态对象会导致类型混淆——将内存当作不同类型读取或写入。使用联合体时，必须通过类型标签字段检查当前活跃成员后再访问。

## 正确示例

```c++
void Foo() {
    struct MessageBuffer buf;
    buf.msg_type = NAME_TYPE;
    buf.name = "Hello World";

    if (buf.msg_type == ID_TYPE)        // 先检查类型
        buf.name_id = user_controlled_value;  // 仅在类型匹配时写入
}
```

## 错误示例

```c++
struct MessageBuffer {
    int msg_type;
    union {
        const char* name;
        int name_id;
    };
};

void Foo() {
    struct MessageBuffer buf;
    buf.msg_type = NAME_TYPE;
    buf.name = "Hello World";

    buf.name_id = user_controlled_value;  // 类型混淆 — 覆盖名称指针！如果 user_controlled_value 可控，则 buf.name 现在指向攻击者控制的地址
    if (buf.msg_type == NAME_TYPE) {
        printf("Message: %s\n", buf.name);  // 从攻击者控制的地址读取
    }
}
```

## 检查方法

1. 搜索联合体（`union`）的使用
2. 验证每个联合体成员的访问前是否有类型标签检查
3. LLM 审查：联合体的活跃成员与类型标签是否一致

## 修复指南

1. C++17+ 优先使用 `std::variant` 替代联合体（类型安全）
2. 如果必须使用联合体，确保类型标签在联合体之前声明，且所有路径都检查标签
3. 禁止将 `reinterpret_cast` 用于类型双关（参见 [[cpp/no-reinterpret-c-cast]]）
