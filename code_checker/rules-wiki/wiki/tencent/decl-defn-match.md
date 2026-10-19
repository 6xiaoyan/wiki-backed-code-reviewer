---
domain: tencent
rule_id: tencent-decl-defn-match
title: 避免函数的声明和实现不同
priority: sub
source_file: rules/Tencent_C++_Security_Guide.md
source_section: "§2.6"
status: active
check_method: llm
deterministic_check: false
checkability: llm_checkable
conflicts_with: []
overrides: []
related_pages: []
---

# 避免函数的声明和实现不同

> 来源：腾讯 C/C++ 安全指南 §2.6 | 风险：逻辑错误（中）

## 规则条款

头文件声明和源文件定义必须在参数顺序、类型和名称上完全匹配。参数顺序不一致（如将 `width, height` 写成 `height, width`）是一种常见且难以发现的 bug，因为代码仍能编译通过。

## 正确示例

```c++
// foo.h
int CalcArea(int width, int height);

// foo.cc
int CalcArea(int width, int height) {  // 与头文件一致
    if (height > real_height) return 0;
    return height * width;
}
```

## 错误示例

```c++
// foo.h
int CalcArea(int width, int height);

// foo.cc
int CalcArea(int height, int width) {  // 顺序与头文件不同！
    if (height > real_height) return 0;  // 这里的 height 实际是调用者的 width
    return height * width;
}
```

## 检查方法

1. 对比头文件声明和源文件定义的函数签名
2. 编译器警告：`-Wmissing-prototypes`、`-Wstrict-prototypes`
3. LLM 审查：头文件和源文件中同名函数的参数名/类型是否一致

## 修复指南

1. 使用头文件中的声明作为权威来源，源文件从声明复制签名
2. 给参数起有意义的名称（而非 a, b, x, y）以降低顺序混淆风险
