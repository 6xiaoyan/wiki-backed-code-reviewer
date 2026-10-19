---
domain: qt
rule_id: qt-one-var-per-line
title: 每行仅声明一个变量
priority: main
source_file: rules/QT代码开发规范.md
source_section: "§2.2"
status: active
check_method: regex
deterministic_check: true
checkability: deterministic
conflicts_with: []
overrides: []
related_pages:
  - [[qt-variable-camelcase]]
  - [[qt-no-short-names]]
---

# 每行仅声明一个变量
## 规则条款

每个变量声明独占一行。禁止在同一行中使用逗号声明多个变量。这有利于：
- 为每个变量添加独立的注释
- 减少 merge 冲突
- 提高 diff 可读性- 便于在调试器中观察变量
## 正确示例

```cpp
int width = 0;
int height = 0;
int depth = 0;

QString userName;
QString userEmail;
```

## 错误示例

```cpp
int width = 0, height = 0, depth = 0;  // 错误：一行声明多个变量
QString userName, userEmail;            // 错误：一行声明多个变量```

## 检查方法
1. 使用正则表达式匹配包含逗号的变量声明行。2. 排除非声明上下文（如函数参数列表、模板参数列表、初始化列表）。3. 匹配模式：同一行中在类型名后出现 `,` 且用于分隔变量名。
正则表达式（简化）：匹配形如 `(int|long|short|float|double|char|bool|auto|Q[A-Z]\w*|QString|QByteArray|QList|QVector|QMap|QHash|QSet|std::\w+)\s+\w+\s*,\s*\w+` 的模式。
实际检测应解析 C++ 语法以区分变量声明与函数调用、模板参数等逗号用法。
## 修复指南

1. 将逗号分隔的多个变量拆为独立的声明行。2. 若多个变量类型相同，每行重复写类型名：   ```cpp
   // 修改前：   int x, y, z;
   // 修改后：   int x;
   int y;
   int z;
   ```

## 审查清单

- [ ] 无一行包含多个变量声明（逗号分隔）- [ ] 每个变量独占一行，便于添加行内注释
- [ ] 指针/引用符号紧贴变量名而非类型（例外场景遵循 qt-pointer-ref-spacing 规则）
## 关联页面

- [[qt-variable-camelcase]] —— 变量名采用驼峰命名法
- [[qt-no-short-names]] —— 避免使用短变量名
