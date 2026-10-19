---
domain: qt
rule_id: qt-file-naming
title: 文件名使用类名全小写且无下划线分隔
priority: main
source_file: rules/QT代码开发规则.md
source_section: "§3.1 文件命名"
status: active
check_method: regex
deterministic_check: true
checkability: deterministic
conflicts_with: []
overrides: []
related_pages:
  - [[qt-class-semantic-noun]]
  - [[qt-ui-class-parent-suffix]]
---

# 文件名使用类名全小写且无下划线分隔
## 规则条款

采用 Qt Creator 默认命名风格：文件名由类名直接转为全小写，不加下划线等分隔符。例如类名 `InsWidget` 对应文件名为 `inswidget.h` 和 `inswidget.cpp`。
## 正确示例

```
类名                  文件名
--------------------------------------------------
InsWidget            → inswidget.h / inswidget.cpp
LoginDialog          → logindialog.h / logindialog.cpp
UserTableWidget      → usertablewidget.h / usertablewidget.cpp
QMotionAdvWgt        → qmotionadvwgt.h / qmotionadvwgt.cpp
HttpRequestHandler   → httprequesthandler.h / httprequesthandler.cpp
```

```cpp
// inswidget.h：文件名与类名 InsWidget 对应，全小写无分隔
#pragma once
#include <QWidget>

class InsWidget : public QWidget
{
    Q_OBJECT
public:
    explicit InsWidget(QWidget *parent = nullptr);
};
```

## 错误示例

```
// 错误：使用了下划线分隔
ins_widget.h        // 类名 InsWidget，不应有下划线

// 错误：保留了原始大小写
InsWidget.h         // 应全小写 inswidget.h

// 错误：混合大小写和下划线
Ins_Widget.h        // 应全小写 inswidget.h
User_Table_Widget.h // 应全小写 usertablewidget.h

// 错误：驼峰文件名
loginDialog.h       // 应全小写 logindialog.h
```

## 检查方法
使用正则表达式检查头文件和源文件名：

1. 遍历项目中所有 `.h`、`.hpp`、`.cpp`、`.cxx` 文件。2. 提取文件名（不含扩展名），检查是否全为小写字母和数字。3. 正则：文件名应匹配 `^[a-z0-9]+$`（不含扩展名）。4. 若文件名包含大写字母或下划线，标记为违规。5. 进一步验证：文件名应为对应类名的全小写形式。提取头文件中的类定义，计算期望的文件名，与实际文件名对比。
接口文件（`_p.h` 私有实现）和 Qt MOC 生成的 `moc_*.cpp` 文件不受此规则约束。
## 修复指南

1. 确定文件对应的主类名。2. 将类名转为全小写，得到正确的文件名。3. 重命名文件（使用 `git mv` 保留版本历史）。4. 更新所有 `#include` 引用该文件的地方。5. 更新 `.pro` / `CMakeLists.txt` 中的文件列表（如有）。6. 重新编译确保无遗漏。
## 审查清单

- [ ] `.h` 文件名全小写，无下划线
- [ ] `.cpp` 文件名全小写，无下划线
- [ ] 文件名与内部主类名对应（类名转小写）
- [ ] 所有 `#include` 引用已更新
- [ ] 项目文件（pro/CMakeLists.txt）已同步更新

## 关联页面

- [[qt-class-semantic-noun]]：类名需为意思明确的名词短语
- [[qt-ui-class-parent-suffix]]：界面类命名最后一个单词体现父类属性