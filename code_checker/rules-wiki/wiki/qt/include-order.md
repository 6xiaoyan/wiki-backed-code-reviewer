---
domain: qt
rule_id: qt-include-order
title: 头文件包含顺序规则
priority: main
source_file: rules/QT代码开发规则.md
source_section: "§4.2 代码顺序规范"
status: active
check_method: regex
deterministic_check: true
checkability: deterministic
conflicts_with: [cpp-include-order]
overrides: []
related_pages:
  - [[cpp-include-order]]
  - [[qt-member-declaration-order]]
  - [[qt-cpp-function-order]]
---

# 头文件包含顺序规则
## 规则条款

Qt 项目头文件包含须按以下顺序分组，各组之间用空行分隔：

1. 自动生成文件（如 `ui_xxx.h`、`moc_xxx.cpp` 对应的头文件）。2. 第三方库（包括 Qt 头文件和其他外部库）
3. 项目公共库（本项目的共享模块）。4. 工程内其他头文件（当前模块目录内的其他头文件）

注意：此顺序与通用 C++ 规则（C-07）的 system / third-party / project 有所不同。Qt 项目将自动生成文件单独放在最前面。
## 正确示例

```cpp
// mainwindow.cpp

// 1. 自动生成文件
#include "ui_mainwindow.h"

// 2. 第三方库 — Qt 头文件
#include <QApplication>
#include <QMessageBox>
#include <QVBoxLayout>
#include <QFileDialog>
#include <QCloseEvent>

// 2. 第三方库 — 其他外部库
#include <json/json.h>
#include <openssl/md5.h>

// 3. 项目公共库
#include "common/Logger.h"
#include "common/ConfigManager.h"
#include "common/NetworkUtils.h"

// 4. 工程内其他头文件
#include "dialogs/SettingsDialog.h"
#include "widgets/ToolBar.h"
#include "models/UserModel.h"
#include "MainWindow.h"
```

```cpp
// inswidget.cpp：简单场景
// 1. 自动生成文件
#include "ui_inswidget.h"

// 2. 第三方库（Qt）
#include <QLabel>
#include <QHBoxLayout>

// 3. 项目公共库
#include "common/StyleHelper.h"

// 4. 工程内其他头文件
#include "InsWidget.h"
```

## 错误示例

```cpp
// mainwindow.cpp：包含顺序混乱

#include <QApplication>
#include "MainWindow.h"              // 错误：工程内文件混在 Qt 之前
#include "ui_mainwindow.h"           // 错误：自动生成文件不在最前
#include <QMessageBox>
#include "common/Logger.h"           // 错误：公共库混在第三方库之间
#include <QFileDialog>
#include "dialogs/SettingsDialog.h"  // 错误：工程内文件混在第三方之前
// 正确顺序应为：
// 1. #include "ui_mainwindow.h"
// 2. #include <QApplication>
//    #include <QMessageBox>
//    #include <QFileDialog>
// 3. #include "common/Logger.h"
// 4. #include "MainWindow.h"
//    #include "dialogs/SettingsDialog.h"
```

```cpp
// 错误：分组之间无空行分隔，难以区分
#include "ui_mainwindow.h"
#include <QApplication>
#include <QMessageBox>
#include "common/Logger.h"
#include "MainWindow.h"
```

## 检查方法
使用正则表达式按分组检测：

1. 扫描文件中的所有 `#include` 行，记录其行号和内容。2. 按包含路径特征对每行分类：
| 分组 | 匹配特征 |
|------|---------|
| 自动生成 | `#include "ui_*.h"` |
| 第三方库 | `#include <...>` （尖括号）|
| 项目公共库 | `#include "common/..."` 或项目约定的公共路径 |
| 工程内文件 | 其他 `#include "..."` 且非自动生成非公共库 |

3. 检查分类后各组出现顺序：自动生成 → 第三方 → 公共库 → 工程内。4. 检查同组内的顺序（可选）：   - 第三方库中，标准库在前，Qt 库其次，其他外部库在后。   - 组内可按字母排序。5. 检查相邻不同组之间是否有空行分隔。
## 修复指南

1. 收集文件的所有 `#include` 语句。2. 按规则分组排序。3. 每个分组内按字母顺序排列。4. 分组之间加入一个空行。5. 使用 IDE 的 "Sort Includes" 或 `clang-format` 的 `IncludeCategories` 配置自动化。6. `.clang-format` 配置参考：

```yaml
IncludeCategories:
  - Regex: '^"ui_.*\.h"$'
    Priority: 1
  - Regex: '^<.*>$'
    Priority: 2
  - Regex: '^"common/.*"$'
    Priority: 3
  - Regex: '^".*"$'
    Priority: 4
```

## 审查清单

- [ ] 自动生成文件（ui_*.h）在最前
- [ ] 第三方库（尖括号 < >）紧随其后
- [ ] 项目公共库在第三方库之后
- [ ] 工程内头文件在最后
- [ ] 各组之间有明显分隔
- [ ] 同组内包含语句有序排列
## 关联页面

- [[cpp-include-order]]：C++ 通用 include 顺序（system / third-party / project），注意与 Qt 版本的区别
- [[qt-member-declaration-order]]：类成员声明顺序
- [[qt-cpp-function-order]]：.cpp 函数顺序与 .h 一致