---
domain: qt
rule_id: qt-var-qclass-lowercase
title: Qt 类变量命名（下划线风格）
priority: main
source_file: rules/QT代码开发规范.md
source_section: "§3.4 变量命名"
status: active
check_method: llm
deterministic_check: false
checkability: advisory_only
conflicts_with:
  - cpp-naming-variables
overrides: []
related_pages:
  - [[cpp-naming-variables]]
  - [[qt-var-last-word-type]]
  - [[qt-ui-control-prefix]]
---

# Qt 类变量命名（下划线风格）

## 规则条款

普通变量使用 Qt 类名去掉 "Q" 后的小写形式，以下划线分隔单词。例如 `QString` 类型的变量命名为 `user_name`，`QPushButton` 类型的变量命名为 `submit_button`。

**重要说明**：本规则已被 C++ 主规范 `cpp-naming-variables` 覆盖。Qt 官方编码规范推荐 camelCase 风格。本条款仅适用于明确声明采用 Qt 下划线风格的历史项目。新项目应遵循 `cpp-naming-variables`（camelCase），不应使用本规则。

## 正确示例

```cpp
// 仅当项目明确采用 Qt 下划线风格时适用
// QString 类型变量
QString user_name;
QString first_name;
QString last_name;

// QPushButton 类型变量
QPushButton *submit_button;
QPushButton *cancel_button;

// QLineEdit 类型变量
QLineEdit *password_edit;
QLineEdit *search_box;

// QCheckBox 类型变量
QCheckBox *remember_me;
QCheckBox *auto_login;

// QComboBox 类型变量
QComboBox *country_list;
QComboBox *language_select;

// QSpinBox 类型变量
QSpinBox *age_spin;
QSpinBox *count_spin;
```

## 错误示例

```cpp
// 以下为新项目 cpp-naming-variables 下的正确写法（camelCase），
// 对采用下划线风格的历史项目则为不符合本条款：

// QString 类型——应使用 camelCase
QString userName;         // 历史项目下划线风格应为 user_name
QString firstName;        // 历史项目下划线风格应为 first_name

// QPushButton 类型——应使用 camelCase
QPushButton *submitButton;  // 历史项目下划线风格应为 submit_button

// QLineEdit 类型——应使用 camelCase
QLineEdit *passwordEdit;    // 历史项目下划线风格应为 password_edit
```

## 检查方法
1. 确认项目是否明确声明采用 Qt 下划线风格命名规范。
2. 扫描代码中 Qt 类型（`QString`、`QPushButton`、`QLineEdit` 等）的变量声明。
3. 检查变量名是否为 Qt 类名去掉 "Q" 后的下划线形式。
4. 对于新项目（默认 camelCase），**不触发**此规则——由 `cpp-naming-variables` 负责检查。
5. LLM 辅助判断变量名是否符合命名模式。

## 修复指南

1. 确定项目命名风格：新项目默认使用 `cpp-naming-variables`（camelCase）。
2. 如为历史项目且需保持 Qt 下划线风格，将变量名改为 Qt 类名小写下划线形式：
   - 取 Qt 类名（如 `QPushButton`），去掉前缀 "Q"（`PushButton`），转为全小写（`pushbutton`）
   - 在单词边界插入下划线（`push_button`）
3. 示例修复：
   - `submitBtn` → `submit_button`（或按新规范保留 `submitBtn`）
   - `passWord` → `password_edit`（或按新规范改为 `passwordEdit`）

## 审查清单

- [ ] 确认项目命名规范声明（下划线风格 vs camelCase）
- [ ] 若为 camelCase 新项目，此规则不适用，由 `cpp-naming-variables` 覆盖
- [ ] 若为下划线风格历史项目，检查 Qt 类型变量名是否为 Qt 类名去掉 "Q" 后的下划线形式
- [ ] 变量名单词分隔符为下划线，非驼峰

## 关联页面

- [[cpp-naming-variables]]：C++ 变量命名规范（camelCase），覆盖本规则
- [[qt-var-last-word-type]]：变量名末尾类型标识
- [[qt-ui-control-prefix]]：UI 控件变量命名前缀
