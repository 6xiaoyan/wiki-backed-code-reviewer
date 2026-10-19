---
domain: qt
rule_id: qt-no-cstyle-cast
title: 避免 C 风格类型转换，优先使用 C++ 风格转换
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
  - [[qt-no-space-after-cast]]
  - [[cpp-no-reinterpret-c-cast]]
---

# 避免 C 风格类型转换，优先使用 C++ 风格转换

## 规则条款

**禁止使用 C 风格类型转换** `(Type)expr`，必须使用 C++ 命名转换：- `static_cast<Type>(expr)` → 编译期类型转换（最常见）
- `dynamic_cast<Type>(expr)` → 运行时多态类型转换（带 RTTI 检查）
- `const_cast<Type>(expr)` → 移除/添加 const 限定
- `reinterpret_cast<Type>(expr)` → 底层位重解释（仅在 C 互操作时允许，需 `// NOLINT`）
原因：- C++ 风格转换语义明确，易于搜索和审查
- 编译器可对不同类型的转换进行不同级别的检查- C 风格转换可能意外执行 `reinterpret_cast` 级别的危险操作
## 正确示例

```cpp
int intValue = static_cast<int>(doubleValue);
QWidget* widget = dynamic_cast<QWidget*>(qobject);
const char* data = static_cast<const char*>(byteArray.constData());

// 向下转型
auto* myClass = dynamic_cast<MyClass*>(basePointer);
if (myClass) {
    myClass->customMethod();
}

// Qt 专用转换（作为 C++ 转换的补充）
auto* button = qobject_cast<QPushButton*>(sender());
int rounded = qRound(3.14);
```

## 错误示例

```cpp
int intValue = (int)doubleValue;                   // 错误：C 风格转换
QWidget* widget = (QWidget*)qobject;                // 错误：C 风格转换
const char* data = (const char*)byteArray.data();   // 错误：C 风格转换

void* ptr = (void*)buffer;                          // 错误：C 风格转换

// 错误：函数风格转换也应避免（除单参数构造外）int x = int(3.14);                                  // 应改为 static_cast<int>(3.14)
```

## 检查方法
1. 搜索 `(Type)` 模式（C 风格转换）。2. 排除函数声明、构造初始化列表、强制类型转换运算符定义等非转换场景。3. 匹配正则表达式：`\([a-zA-Z_][a-zA-Z0-9_:<>*& ]*\)\s*[a-zA-Z_\(]` 用于检测可疑的 C 风格转换。
正则表达式（简化）：`\([a-zA-Z_]\w*(?:\s*[*&]+)?\s*\)\s*\w` 匹配 C 风格转换模式。
## 修复指南

1. 将 `(Type)expr` 替换为 `static_cast<Type>(expr)`（大多数情况）。2. 若涉及多态类型转换，使用 `dynamic_cast<Type>(expr)` 并检查 nullptr。3. 若需要移除 const，使用 `const_cast<Type>(expr)`。4. Qt 对象间转换优先使用 `qobject_cast<T>(obj)`。
转换对照表：

| C 风格 | C++ 风格 |
|--------|----------|
| `(int)3.14` | `static_cast<int>(3.14)` |
| `(QWidget*)obj` | `qobject_cast<QWidget*>(obj)` |
| `(const char*)data` | `static_cast<const char*>(data)` |

## 审查清单

- [ ] 代码中无 C 风格转换 `(Type)expr`
- [ ] 所有类型转换使用命名的 C++ 转换操作符- [ ] `reinterpret_cast` 仅在 C 库互操作中使用并添加了 `// NOLINT` 注释
- [ ] `dynamic_cast` 结果已检查 nullptr

## 关联页面

- [[qt-no-space-after-cast]] —— 类型转换后不加空白字符- [[cpp-no-reinterpret-c-cast]] —— C++ 中禁止 `reinterpret_cast`（C 库互操作除外）