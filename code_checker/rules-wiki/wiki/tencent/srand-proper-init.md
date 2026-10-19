---
domain: tencent
rule_id: tencent-srand-init
title: rand() 类函数应正确初始化
priority: sub
source_file: rules/Tencent_C++_Security_Guide.md
source_section: "§4.3"
status: active
check_method: llm
deterministic_check: false
checkability: llm_checkable
conflicts_with: []
overrides: []
related_pages: []
---

# rand() 类函数应正确初始化

> 来源：腾讯 C/C++ 安全指南 §4.3 | 风险：逻辑漏洞（高）

## 规则条款

`rand()` 必须用 `srand()` 种子化；否则序列是确定性的（等效于 `srand(1)`）。每次程序运行都会生成相同的"随机"数序列，破坏了依赖随机性的安全逻辑。

注意：对于安全敏感的用途（如密钥生成、令牌生成），`rand()` 本身也不够安全——应使用 CSPRNG（参见 §4.4）。

## 正确示例

```c++
int main() {
    srand(time(0));           // 用当前时间种子化
    int foo = rand();         // 每次运行不同
    return 0;
}
```

## 错误示例

```c++
int main() {
    int foo = rand();         // 未种子化 — 每次运行相同值
    return 0;
}
```

## 检查方法

1. 搜索 `rand()` 调用，检查之前是否有 `srand()` 调用
2. LLM 审查：判断随机序列是否需要种子化
3. 提醒：安全敏感场景应使用 CSPRNG 而非 `rand()`

## 修复指南

1. 在 `main()` 或启动代码中调用 `srand(time(0))`
2. 安全敏感用途：使用 CSPRNG（`RAND_bytes`、`getrandom` 等）
