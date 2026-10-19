---
domain: tencent
rule_id: tencent-null-after-free
title: 释放完后置空指针
priority: sub
source_file: rules/Tencent_C++_Security_Guide.md
source_section: "§8.5"
status: active
check_method: llm
deterministic_check: false
checkability: llm_checkable
conflicts_with: []
overrides: []
related_pages:
  - [[cpp/no-bare-new-delete]]
  - [[cpp/unique-ptr]]
---

# 释放完后置空指针

> 来源：腾讯 C/C++ 安全指南 §8.5 | 风险：内存损坏（高）

## 规则条款

`free()` 或 `delete` 后，指针仍持有旧地址（悬空指针）。将其设置为 `NULL`/`nullptr` 以防止 double-free 和 use-after-free。后续对该指针的空检查会正确判断"没有指向有效内存"。

C++ 优先使用智能指针（参见 [[cpp/unique-ptr]]）——它们自动管理生命周期，消除手动释放和悬空指针。

## 正确示例

```c++
void foo() {
    char* p = (char*)malloc(100);
    memcpy(p, "hello", 6);
    free(p);
    p = NULL;                // 置空 — 防止悬空
    if (p != NULL) {         // 正确跳过
        printf("%s\n", p);
    }
}
```

## 错误示例

```c++
void foo() {
    char* p = (char*)malloc(100);
    memcpy(p, "hello", 6);
    free(p);
    // p 现在是悬空的 — 持有无效地址但非 NULL
    if (p != NULL) {         // 这个检查无用 — p 非 NULL 但无效
        printf("%s\n", p);   // use-after-free
    }
}
```

## 检查方法

1. 搜索 `free(` 和 `delete `，检查之后是否有置空操作
2. 搜索释放后继续使用同一指针的代码
3. 动态分析：ASan 检测 use-after-free

## 修复指南

1. 每次 `free(p)` 后添加 `p = NULL;`
2. 每次 `delete p` 后添加 `p = nullptr;`
3. C++ 首选方案：使用 `std::unique_ptr` 和 `std::shared_ptr`，参见 [[cpp/no-bare-new-delete]]
