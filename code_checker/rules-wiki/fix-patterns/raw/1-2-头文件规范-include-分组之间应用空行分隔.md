---
title: §1.2 头文件规范 — #include 分组之间应用空行分隔
rule_id: fix-pattern/1-2-头文件规范-include-分组之间应用空行分隔
priority: pattern
related_pages: []
---

# §1.2 头文件规范 — #include 分组之间应用空行分隔

## 关联规则

- §1.2 头文件规范 — #include 分组之间应用空行分隔
- Qt 头文件（第三方库分组）与工程内头文件（工程内分组）之间未用空行分隔

## 代码特征

此类违规出现在源文件头文件包含区，典型特征为：

- 存在连续两行 `#include`，且属于不同 include 分组：
  - 上一行属于第三方库/框架头文件，例如 `#include <QApplication>`、`#include <QtWidgets/QMainWindow>`；
  - 下一行属于工程内头文件，例如 `#include "ui/mainwindow.h"`、`#include "core/foo.h"`。
- 两行之间**没有空行**，即上一行 include 换行后紧跟着下一行 include。
- 可识别为违规的代码模式：

```cpp
#include <QApplication>
#include "ui/mainwindow.h"
```

这里 `#include <QApplication>` 与 `#include "ui/mainwindow.h"` 紧邻，缺少规范要求的空行，导致第三方库分组和工程内分组边界不清晰。

## 修复步骤

1. **定位违规位置**：找到相邻的两行 include，形式为：

   ```cpp
   #include <QApplication>
   #include "ui/mainwindow.h"
   ```

   确认这两行之间没有空行。

2. **确认目标 include 行唯一**：全文搜索 `#include "ui/mainwindow.h"`，确认该行在整个文件中只出现一次；若出现多次，只处理 include 区中紧跟在 `#include <QApplication>` 后面的这一处，不要影响其他位置的同名 include。

3. **执行修复**，可采用以下任一方式：

   - **方式 A：整体替换**  
     将连续两行：

     ```cpp
     #include <QApplication>
     #include "ui/mainwindow.h"
     ```

     整体替换为：

     ```cpp
     #include <QApplication>

     #include "ui/mainwindow.h"
     ```

     注意：两个 include 行之间必须插入**一个空行**；不要额外保留原来的 `#include "ui/mainwindow.h"`，避免产生重复 include。

   - **方式 B：delete + insert_after**  
     1. 删除 `#include "ui/mainwindow.h"` 这一整行；
     2. 以 `#include <QApplication>` 为 anchor，在它之后插入文本：

        ```
        
        #include "ui/mainwindow.h"
        ```

        该文本以一个空行开头，再写入原来的 include 行。

4. **验证修复结果**：

   - 最终代码应为：

     ```cpp
     #include <QApplication>

     #include "ui/mainwindow.h"
     ```

   - `#include <QApplication>` 与 `#include "ui/mainwindow.h"` 之间恰好有一个空行；
   - `#include "ui/mainwindow.h"` 没有重复出现；
   - `main()` 等其余代码保持不变。

## 来源

run: 20260812-124714-b67d2525, 迭代 2 轮, 最终 8/10