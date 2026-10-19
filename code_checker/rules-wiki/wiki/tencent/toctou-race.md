---
domain: tencent
rule_id: tencent-toctou-race
title: 注意 Time-of-check Time-of-use (TOCTOU) 条件竞争
priority: sub
source_file: rules/Tencent_C++_Security_Guide.md
source_section: "§3.3"
status: active
check_method: llm
deterministic_check: false
checkability: llm_checkable
conflicts_with: []
overrides: []
related_pages: []
---

# 注意 Time-of-check Time-of-use (TOCTOU) 条件竞争

> 来源：腾讯 C/C++ 安全指南 §3.3 | 风险：内存损坏（高）、逻辑错误（中）
> 级别：【建议】

## 规则条款

资源的状态被检查，然后使用，但攻击者在此期间修改了它。常见于文件系统操作（如先检查文件是否存在再打开，攻击者在检查和使用之间替换了文件）。

## 缓解措施

1. 最小化跨进程文件操作
2. 尽可能缩短 check-use 间隔
3. 使用操作后重新检查
4. 在检查*之前*获取锁，而非之后
5. 使用原子化的系统调用（如 `openat` + `O_NOFOLLOW`、`fstat` + `open` 组合）

## 检查方法

1. 搜索 `access()` → `open()` 模式（TOCTOU 经典案例 — 用 `fstat`/`open` 替代）
2. 搜索 `stat()` → `open()` 模式
3. LLM 审查：识别检查和使用之间有可被利用的时间窗口

## 修复指南

1. 用 `open()` + `fstat()` 替代 `access()` + `open()`
2. 减少文件系统操作的次数和间隔
3. 用 `O_NOFOLLOW` 和 `O_EXCL` 标志减少符号链接攻击面
