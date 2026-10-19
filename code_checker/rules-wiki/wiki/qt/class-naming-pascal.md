---
domain: qt
rule_id: qt-class-naming-pascal
title: 类名 PascalCase 命名规则（Qt 公有类以 Q 开头）
priority: main
source_file: rules/QT代码开发规则.md
source_section: "§2.2"
status: active
check_method: regex
deterministic_check: true
checkability: deterministic
conflicts_with: []
overrides: []
related_pages:
  - [[qt-variable-camelcase]]
---

# 类名 PascalCase 命名规则（Qt 公有类以 Q 开头）

## 规则条款

类名采用 **PascalCase（大驼峰命名法）**：每个单词首字母大写，其余字母小写，无下划线分隔。Qt 相关命名约定：- **Qt 公有类**应以大写字母 `Q` 开头（如 `QWidget`、`QRgb`、`QString`）。- **Qt 公有函数**通常以小写字母 `q` 开头（如 `qRgb`、`qAlpha`、`qBound`）。- **自定义类**使用 PascalCase，不使用 `Q` 前缀（避免与 Qt 官方类混淆）

## 正确示例

```cpp
// Qt 官方类 — 以 Q 开头
class QPushButton;
class QNetworkAccessManager;
class QXmlStreamReader;

// Qt 公有函数 — 以 q 开头
int gray = qGray(rgb);
QRgb color = qRgb(255, 128, 64);
int bounded = qBound(0, value, 100);

// 自定义类 — PascalCase，不用 Q 前缀
class UserProfileManager;
class DataImportService;
class ReportGenerator;
```

## 错误示例

```cpp
// 错误：类名使用 snake_case
class user_profile_manager { };     // 应改为 UserProfileManager

// 错误：自定义类不应使用 Q 前缀（与 Qt 官方类混淆）
class QDataImportService { };       // 应改为 DataImportService
class QMyCustomWidget { };          // 应改为 MyCustomWidget

// 错误：类名首字母小写
class dataImporter { };             // 应改为 DataImporter

// 错误：全大写
class DATABASECONNECTION { };       // 应改为 DatabaseConnection
```

## 检查方法
1. 使用正则表达式匹配类声明（`class\s+(\w+)`）。2. 验证类名：首字母大写，匹配 `[A-Z][a-zA-Z0-9]*` 格式
   - 若非 Qt 官方类/子类，不以前缀 `Q` 开头。3. 标记不符合 PascalCase 或自定义类误用 `Q` 前缀的情况。
正则表达式：`class\s+[A-Z][a-zA-Z0-9]*` 用于验证类名格式；`class\s+Q[A-Z][a-zA-Z0-9]*` 用于检测自定义类是否误用 Qt 前缀（需结合上下文判断）。
## 修复指南

1. 将 snake_case 类名转换为 PascalCase：`data_importer` → `DataImporter`。2. 移除自定义类的 `Q` 前缀：`QDataImporter` → `DataImporter`。3. 使用 Qt Creator 或 VS Code 的重命名功能进行全局替换。4. 同步更新对应的头文件保护宏名称。
## 审查清单

- [ ] 所有类名使用 PascalCase（首字母大写）
- [ ] 自定义类不使用 `Q` 前缀
- [ ] Qt 继承类命名清晰表达其扩展功能
- [ ] 头文件保护宏与类名一致
## 关联页面

- [[qt-variable-camelcase]]：变量名采用驼峰命名法
