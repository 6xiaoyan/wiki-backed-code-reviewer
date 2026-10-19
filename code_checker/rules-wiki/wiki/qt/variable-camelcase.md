---
domain: qt
rule_id: qt-variable-camelcase
title: 变量名采用驼峰命名法
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
  - [[qt-class-naming-pascal]]
  - [[qt-no-abbreviations]]
---

# 变量名采用驼峰命名法

## 规则条款

变量名采用**小驼峰命名法（lowerCamelCase）**：首字母小写，后续每个单词的首字母大写，其余字母小写。不包含下划线分隔（snake_case 仅用于 C++ 标准库风格或宏名）。具体规则：
- 普通变量：`tableName`、`maxItemCount`
- 布尔变量：`isVisible`、`hasChildren` 或 `canExecute` 开头
- 私有成员变量：Qt 项目统一使用 `m_` 前缀（如 `m_tableName`），参见 Qt 源码风格
- 静态变量：使用 `s_` 前缀（如 `s_instanceCount`）

## 正确示例

```cpp
// 局部变量
int itemCount = 0;
QString userName;
double averageTemperature;

// 布尔变量
bool isEnabled;
bool hasUnsavedChanges;
bool canUndo;

// 成员变量
class MyWidget : public QWidget {
private:
    QLabel *m_lblTitle;
    QLineEdit *m_edtName;
    int m_currentIndex;
    bool m_isModified;
};

// 静态变量
static int s_instanceCount = 0;
```

## 错误示例

```cpp
// 错误：snake_case
int item_count = 0;            // 应改为 itemCount
QString user_name;             // 应改为 userName

// 错误：PascalCase（应仅用于类名）
int ItemCount;                 // 应改为 itemCount
bool IsEnabled;                // 应改为 isEnabled

// 错误：全小写
int itemcount;                 // 应改为 itemCount

// 错误：匈牙利前缀（非 Qt 控件前缀）
int iRowCount;                 // 应改为 rowCount
QString strName;               // 应改为 name
```

## 检查方法
1. 使用正则表达式提取变量声明中的标识符。
2. 验证标识符是否匹配小驼峰命名规则：
   - 首字符为小写字母
   - 单词边界使用大写字母分隔
   - 无不必要的下划线
3. 排除预定义的允许例外（`m_` 前缀成员变量、`s_` 前缀静态变量、`g_` 前缀全局变量）。

正则表达式：`^[a-z][a-zA-Z0-9]*$` 用于普通变量；`^m_[a-z][a-zA-Z0-9]*$` 用于成员变量。

## 修复指南

1. 将 snake_case 变量名转换为 camelCase（例如 `item_count` → `itemCount`）。
2. 将 PascalCase 变量名转换（首字母改为小写）：`ItemCount` → `itemCount`。
3. 移除匈牙利前缀：`iRow` → `row`，`strName` → `name`。
4. 使用 IDE 的「重命名」功能（如 Qt Creator 中 `Ctrl+Shift+R`）批量重构。

## 审查清单

- [ ] 所有普通变量和函数参数使用 lowerCamelCase
- [ ] 成员变量使用 `m_` 前缀 + lowerCamelCase
- [ ] 静态变量使用 `s_` 前缀 + lowerCamelCase
- [ ] 布尔变量以 `is`/`has`/`can` 开头
- [ ] 无 snake_case 变量名
- [ ] 无匈牙利前缀（除 `m_`、`s_` 外）

## 关联页面

- [[qt-class-naming-pascal]]：类名 PascalCase 命名规则
- [[qt-no-abbreviations]]：避免使用缩写
