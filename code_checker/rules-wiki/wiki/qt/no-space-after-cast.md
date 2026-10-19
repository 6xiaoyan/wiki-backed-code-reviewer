---
domain: qt
rule_id: qt-no-space-after-cast
title: 类型转换后不加空白字符
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
  - [[qt-no-cstyle-cast]]
---

# 类型转换后不加空白字符
## 规则条款

C++ 风格类型转换（`static_cast<>`、`dynamic_cast<>`、`const_cast<>`、`reinterpret_cast<>`）的**尖括号后不加空白字符**。转换表达式应写为 `static_cast<Type>(expr)`，而非 `static_cast<Type> (expr)`。这与函数调用的空格规则一致——函数名后不跟空格。
## 正确示例

```cpp
int value = static_cast<int>(doubleValue);
QWidget* widget = dynamic_cast<QWidget*>(object);
const QString& ref = const_cast<const QString&>(mutableRef);

void* ptr = static_cast<void*>(buffer);
auto* button = dynamic_cast<QPushButton*>(sender());
```

## 错误示例

```cpp
int value = static_cast<int> (doubleValue);       // 错误：> 和 ( 之间有多余空格QWidget* w = dynamic_cast<QWidget*> (object);      // 错误：> 和 ( 之间有多余空格
// Qt 风格的 qobject_cast 同理
QPushButton* btn = qobject_cast<QPushButton*> (obj); // 错误：> 和 ( 之间有多余空格```

## 检查方法
1. 搜索 C++ 风格转换表达式。2. 检查 `_cast<...>` 与紧跟的 `(` 之间是否存在空白字符。3. 同样检查 `qobject_cast<...>` 的格式。
正则表达式：`(_cast|qobject_cast)<[^>]*>\s+\(` → 匹配类型转换后有空格的模式。
## 修复指南

1. 删除 `>` 和 `(` 之间的所有空白字符。2. 使用 clang-format：`SpaceAfterCStyleCast: false` 处理 C 风格转换；C++ 风格转换的空格由 `SpaceBeforeParens` 控制，设为 `ControlStatements` 以仅在控制流关键字后加空格。3. 全局搜索替换：`static_cast<` 后确保直接跟 `(`。
## 审查清单

- [ ] `static_cast<T>(expr)` 的 `>` 和 `(` 之间无空格- [ ] `dynamic_cast<T>(expr)` 的 `>` 和 `(` 之间无空格- [ ] `const_cast<T>(expr)` 的 `>` 和 `(` 之间无空格- [ ] `reinterpret_cast<T>(expr)` 的 `>` 和 `(` 之间无空格- [ ] `qobject_cast<T>(expr)` 的 `>` 和 `(` 之间无空格
## 关联页面

- [[qt-no-cstyle-cast]] —— 避免 C 风格类型转换，优先使用 C++ 风格转换
