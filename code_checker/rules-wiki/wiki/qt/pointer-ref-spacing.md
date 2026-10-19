---
domain: qt
rule_id: qt-pointer-ref-spacing
title: 指针与引用符号紧跟类型
priority: main
source_file: rules/QT代码开发规范.md
source_section: "§2.3"
status: active
check_method: regex
deterministic_check: true
checkability: deterministic
conflicts_with: []
overrides: []
related_pages:
  - [[cpp-operator-spacing]]
---

# 指针与引用符号紧跟类型
## 规则条款

指针符号 * 和引用符号 & **紧跟类型名**，而非变量名。这与 Qt 源码的约定一致。原因：
- 强调「类型是指针/引用」，而非变量名附属符号- 与 Qt 官方代码风格保持一致- C++ 语义上 */& 是类型的一部分（char* 是一个「指向 char 的指针」类型）

注意：一行声明多个指针变量时，仍需每行仅声明一个（参见 [[qt-one-var-per-line]]），从而避免 char* p, q 的歧义。
## 正确示例

`cpp
char* text;
const QString& myString;
QWidget* parentWidget;
int* const immutablePtr = &value;

void setData(const QByteArray& data, int* outputSize);
SignalMapper<QObject*>* mapper;
`

## 错误示例

`cpp
char *text;                 // 错误：紧贴变量名
const QString &myString;    // 错误：紧贴变量名
QWidget *parentWidget;      // 错误：紧贴变量名
// 错误：混合风格
char* a, *b;                // 错误：一行多变量（另见 qt-one-var-per-line）
`

## 检查方法
1. 使用正则表达式匹配变量声明中的指针和引用符号位置。2. 检查 * 和 & 之前有空格且紧跟变量名的模式。3. 验证 */& 左侧为类型名（无空格或仅 1 空格），右侧为变量名。
正则表达式：
- 违规模式：\w\s+[*&]\s*\w+\s*[=;,\)] —— */& 之前有多余空格（紧贴变量名）- 正确模式：\w[*&]\s+\w+ —— */& 紧贴类型

## 修复指南

1. 将*/& 从变量名前移动到类型名后：char *text → char* text。2. 将& 从变量名前移动到类型名后：const QString &str → const QString& str。3. 使用 clang-format 配置：DerivePointerAlignment: false，PointerAlignment: Left。4. 在 Qt Creator 中：Options > C++ > Edit > Format > Pointer and reference alignment 选择 Left。

## 审查清单

- [ ] 所有* 紧跟类型名，右侧有空格再接变量名
- [ ] 所有& 紧跟类型名，右侧有空格再接变量名
- [ ] 每行仅声明一个指针引用变量
- [ ] 无Type* 与Type * 混用的不一致风格

## 关联页面

- [[cpp-operator-spacing]]：C++ 操作符间距规范
- [[qt-one-var-per-line]]：每行仅声明一个变量
