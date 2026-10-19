---
domain: qt
rule_id: qt-include-no-dot-h
title: Qt 头文件引用格式
priority: main
source_file: rules/QT代码开发规则.md
source_section: "§4.3 Qt 库引用"
status: active
check_method: regex
deterministic_check: true
checkability: deterministic
conflicts_with: []
overrides: []
related_pages:
  - [[qt-include-order]]
---

# Qt 头文件引用格式
## 规则条款

引用 Qt 库头文件时，必须使用不带 `.h` 后缀的格式，这是 Qt 官方标准风格。例如使用 `#include <QPushButton>` 而非 `#include <QPushButton.h>` 或 `#include <qpushbutton.h>`。
此规则适用于所有 Qt 模块头文件，包括 QtWidgets、QtCore、QtGui、QtNetwork、QtSql、QtXml 等。
## 正确示例

```cpp
// Qt Widgets 模块
#include <QPushButton>
#include <QLabel>
#include <QLineEdit>
#include <QCheckBox>
#include <QSpinBox>
#include <QComboBox>
#include <QGroupBox>
#include <QTableWidget>
#include <QWidget>
#include <QDialog>
#include <QMainWindow>
#include <QApplication>

// Qt Core 模块
#include <QString>
#include <QList>
#include <QMap>
#include <QVector>
#include <QFile>
#include <QDir>
#include <QTimer>
#include <QObject>
#include <QThread>
#include <QDebug>

// Qt Gui 模块
#include <QPainter>
#include <QPixmap>
#include <QFont>
#include <QColor>
#include <QKeyEvent>
#include <QMouseEvent>

// Qt Network 模块
#include <QTcpSocket>
#include <QNetworkAccessManager>

// Qt Sql 模块
#include <QSqlDatabase>
#include <QSqlQuery>
```

## 错误示例

```cpp
// 错误：多余 .h 后缀
#include <QPushButton.h>      // 应为 #include <QPushButton>
#include <QWidget.h>          // 应为 #include <QWidget>
#include <QString.h>          // 应为 #include <QString>
#include <QDebug.h>           // 应为 #include <QDebug>

// 错误：全部小写 + .h 后缀
#include <qpushbutton.h>      // 应为 #include <QPushButton>
#include <qwidget.h>          // 应为 #include <QWidget>
#include <qstring.h>          // 应为 #include <QString>

// 错误：即使省略 .h 也不能全小写
#include <qpushbutton>        // 应为 #include <QPushButton>（注意大小写）
```

## 检查方法
使用正则表达式匹配 `#include` 指令中的 Qt 头文件引用：

1. 匹配模式：`#include\s*[<"]Q\w+\.h[>"]`
   - 检测任何 `#include <Q...h>` 或 `#include "Q...h"` 形式的语句。2. 同时匹配全小写形式：`#include\s*[<"]q\w+\.h[>"]`
   - 如 `#include <qpushbutton.h>`
3. 检查范围：
   - `.h` / `.hpp` / `.cpp` / `.cxx` 源文件。   - 排除第三方库和系统头文件目录
4. 所有匹配到的 `#include` 指令标记为违规
## 修复指南

1. 对于 `#include <Qxxx.h>` —— 直接去掉 `.h` 后缀：   - `#include <QPushButton.h>` → `#include <QPushButton>`
   - `#include <QWidget.h>` → `#include <QWidget>`
2. 对于 `#include <qxxx.h>` —— 去掉 `.h` 后缀并修正大小写：   - `#include <qpushbutton.h>` → `#include <QPushButton>`
   - `#include <qwidget.h>` → `#include <QWidget>`
3. Qt 类名通常以 `Q` 开头，每个单词首字母大写，无下划线
4. 查找替换时注意保持引号/尖括号风格不变
## 审查清单

- [ ] 所有 `#include` 中引用 Qt 头文件无 `.h` 后缀
- [ ] Qt 类名大小写正确（`QPushButton` 而非 `qpushbutton`）
- [ ] 尖括号引用 Qt 库头文件（`<QtClass>`），双引号仅用于项目内部头文件
- [ ] 无遗漏的旧式 Qt 头文件（如 `<QtGui>` 全模块引用，应细化为具体类）

## 关联页面

- [[qt-include-order]]：Qt 头文件包含顺序规则