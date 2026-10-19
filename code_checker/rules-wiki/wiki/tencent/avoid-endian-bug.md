---
domain: tencent
rule_id: tencent-avoid-endian-bug
title: 避免大小端错误
priority: sub
source_file: rules/Tencent_C++_Security_Guide.md
source_section: "§7.3"
status: active
check_method: llm
deterministic_check: false
checkability: llm_checkable
conflicts_with: []
overrides: []
related_pages: []
---

# 避免大小端错误

> 来源：腾讯 C/C++ 安全指南 §7.3 | 风险：逻辑漏洞（中）

## 规则条款

大端和小端系统之间交换的数据必须使用显式的字节序转换处理。例如，从小端主机读取大端网络协议的值时应使用 `ntohl`/`ntohs` 转换。直接逐字节复制多字节整数在网络通信、文件格式中可能导致字节序错误。

## 正确示例

```c++
// 网络字节序（大端）→ 主机字节序
uint32_t value = ntohl(*(uint32_t*)network_buffer);
uint16_t port = ntohs(*(uint16_t*)network_buffer);

// 主机 → 网络
*(uint32_t*)network_buffer = htonl(host_value);
```

## 错误示例

```c++
// 未进行字节序转换 — 在大小端不同的平台上产生不同结果
uint32_t value = *(uint32_t*)network_buffer;
*(uint16_t*)network_buffer = host_port;
```

## 检查方法

1. 搜索网络代码中的 `ntohl`、`ntohs`、`htonl`、`htons` 的使用——验证是否一致
2. 搜索网络 payload 或文件数据中直接的多字节赋值/读取
3. LLM 审查

## 修复指南

1. 网络数据：始终使用 `ntohl`/`ntohs`（接收）和 `htonl`/`htons`（发送）
2. 文件格式：定义明确的字节序并用序列化/反序列化函数
3. 考虑使用 Protocol Buffers、FlatBuffers 等框架避免手动处理
