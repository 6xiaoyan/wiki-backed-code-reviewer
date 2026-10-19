---
domain: qt
rule_id: qt-ui-class-parent-suffix
title: 界面类命名最后一个单词体现父类属性
priority: main
source_file: rules/QT代码开发规范.md
source_section: "§3.2 类命名"
status: active
check_method: regex
deterministic_check: true
checkability: deterministic
conflicts_with: []
overrides: []
related_pages:
  - [[qt-class-semantic-noun]]
  - [[qt-no-single-q-prefix]]
---

# 界面类命名最后一个单词体现父类属性

## 规则条款

界面类（UI 类）的类名最后一个单词应体现其继承的父类属性。例如继承 `QDialog` 的类以 `Dialog` 结尾，继承 `QWidget` 的类以 `Widget` 结尾。全新概念的子类（非直接映射到现有 Qt 控件概念）可以自主命名，无需强制包含父类信息。

## 正确示例

```cpp
// 对话框类 —— 以 Dialog 结尾
class LoginDialog : public QDialog { };
class SettingsDialog : public QDialog { };
class AboutDialog : public QDialog { };

// 表格控件 —— 以 TableWidget 结尾
class UserTableWidget : public QTableWidget { };
class DataTableWidget : public QTableWidget { };

// 列表控件 —— 以 ListWidget 结尾
class FileListWidget : public QListWidget { };
class LogListWidget : public QListWidget { };

// 树形控件 —— 以 TreeWidget 结尾
class FolderTreeWidget : public QTreeWidget { };

// 按钮控件 —— 以 Button 结尾
class IconButton : public QPushButton { };
class MenuButton : public QToolButton { };

// 通用 Widget —— 以 Widget 结尾
class HeaderWidget : public QWidget { };
class StatusBarWidget : public QWidget { };

// 组合框 —— 以 ComboBox 结尾
class CountryComboBox : public QComboBox { };

// 全新概念子类 —— 可自主命名
class TimelineView : public QAbstractItemView { };
class HeatmapChart : public QWidget { };
class WaveformDisplay : public QWidget { };
```

## 错误示例

```cpp
// 错误：登录对话框不以 Dialog 结尾
class LoginWindow : public QDialog { };       // 应为 LoginDialog

// 错误：用户表格不以 TableWidget 结尾
class UserTable : public QTableWidget { };    // 应为 UserTableWidget

// 错误：文件列表不以 ListWidget 结尾
class FilePanel : public QListWidget { };     // 应为 FileListWidget

// 错误：继承 QWidget 却以 Panel 结尾（无对应 Qt 控件 Panel）
// 若 Panel 是自定义概念则允许，但直接继承 QWidget 建议用 Widget
class InfoPanel : public QWidget { };         // 建议 HeaderWidget / InfoWidget

// 错误：父类属性不一致——继承 QDialog 却叫 LoginWidget
class LoginWidget : public QDialog { };       // 应为 LoginDialog
```

## 检查方法
使用正则表达式结合类继承关系检测：

1. 提取每个类定义，解析其父类名称。
2. 根据父类确定期望的后缀：

| 父类 | 期望后缀 |
|------|---------|
| `QDialog` | `Dialog` |
| `QWidget` | `Widget` |
| `QFrame` | `Frame` |
| `QMainWindow` | `MainWindow` |
| `QTableWidget` | `TableWidget` |
| `QListWidget` | `ListWidget` |
| `QTreeWidget` | `TreeWidget` |
| `QPushButton` | `Button` |
| `QToolButton` | `Button` 或 `ToolButton` |
| `QComboBox` | `ComboBox` |
| `QSpinBox` | `SpinBox` |
| `QScrollArea` | `ScrollArea` |
| `QGroupBox` | `GroupBox` |
| `QStackedWidget` | `StackedWidget` |
| `QMenu` | `Menu` |
| `QAction` | `Action` |

3. 检查类名最后一个单词是否匹配期望后缀。
4. 若类名不匹配且类不是全新概念的自定义控件，标记为违规。

## 修复指南

1. 确定类的父类类型。
2. 参照上表确定正确的后缀。
3. 重命名类：`<功能描述> + <父类后缀>`，如 `LoginDialog`。
4. 同步更新文件名（遵循 Q-25 的 `logindialog.h` 格式）。
5. 更新所有 `#include` 和引用。
6. 若该类确实是全新概念的自定义控件（如上面 `TimelineView`），添加注释说明为何不使用父类后缀。

## 审查清单

- [ ] 界面类类名最后一个单词与父类一致
- [ ] 全新概念子类的自主命名有理有据
- [ ] 无类名后缀与实际父类不匹配的情况（如继承 QDialog 却叫 XXXWidget）
- [ ] 重命名后文件引用已全部更新

## 关联页面

- [[qt-class-semantic-noun]]：类名需为名词短语
- [[qt-no-single-q-prefix]]：自建类禁止以 Q 开头
