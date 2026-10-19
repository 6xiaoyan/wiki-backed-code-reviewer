---
domain: tencent
rule_id: tencent-no-arbitrary-write
title: 防止任意地址写
priority: sub
source_file: rules/Tencent_C++_Security_Guide.md
source_section: "§6.2"
status: active
check_method: llm
deterministic_check: false
checkability: llm_checkable
conflicts_with: []
overrides: []
related_pages:
  - [[cpp/no-unvalidated-input]]
---

# 防止任意地址写

> 来源：腾讯 C/C++ 安全指南 §6.2 | 风险：内存损坏（高）

## 规则条款

允许用户控制的值成为写入目标可实现任意内存损坏和代码执行。写入目标地址绝不能由用户输入直接或间接控制。

## 正确示例

```c++
void Write(MyStruct& dst_struct) {
    // dst_struct.buf 由程序内部控制，非用户可控
    char payload[10] = {0};
    memcpy(dst_struct.buf, payload, sizeof(payload));
}
```

## 错误示例

```c++
void Write(MyStruct dst_struct) {
    char payload[10] = {0};
    memcpy(dst_struct.buf, payload, sizeof(payload));
}

int main() {
    MyStruct dst_struct;
    dst_struct.buf = (char*)user_controlled_value;  // 攻击者控制写入地址
    Write(dst_struct);
    return 0;
}
```

## 检查方法

1. 搜索 `memcpy`、`memmove`、`strcpy`、`sprintf` 的目标地址参数
2. 确认目标地址不来自用户输入或外部数据
3. LLM 审查：目标指针是否可能被用户控制

## 修复指南

1. 目标缓冲区地址由程序内部静态或栈分配，不经用户输入决定
2. 如果目标必须动态选择，使用白名单限制可选地址范围
3. 禁止将用户输入直接转换为指针
