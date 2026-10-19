---
title: §2.2 避免使用短变量名 — [Q-03] qt/no-short-names
rule_id: fix-pattern/2-2-避免使用短变量名-q-03-qt-no-short-names
priority: pattern
related_pages: []
---

# §2.2 避免使用短变量名 — [Q-03] qt/no-short-names

## 关联规则
- `qt/no-short-names`：函数或方法参数名、局部变量名为单字符（除循环计数器 i/j/k、数学坐标 x/y/z、模板类型参数 T/U/V 等允许场景外），且该变量作用域贯穿超过 3 行代码时，应使用有意义的描述性名称。

## 代码特征
以下代码模式会触发本违规（`fix_agent` 可通过关键词/模式匹配识别）：

- **违规场景**：在头文件（`.h`）中声明函数时，参数名使用单字符（如 `n`、`s`、`a`、`b` 等），且该参数不是循环计数器、数学坐标或模板类型参数。
- **典型特征**：
  - 函数声明形如：`void setNotes(const std::string& n);`（参数名仅为 1 个字母）。
  - 对应的 `.cpp` 实现中，函数签名同样使用该短参数名，并在函数体内多处引用该参数（例如 `m_edtNotes->setText(QString::fromStdString(n));`）。
  - 参数作用域跨越整个函数体，通常超过 3 行代码，需要在多个语句中引用。
- **非违规例外**：`for (int i = 0; ...)` 中的 `i`、数学函数中的 `x/y/z`、模板声明中的 `T/U/V` 等不触发此规则。

## 修复步骤
1. **定位所有相关文件**：找到声明该函数的头文件（`.h`）以及定义该函数的实现文件（`.cpp`）。可能还涉及其他 `.cpp` 文件中对该函数的调用——但本规则仅关注参数名，调用处无需修改（调用者不关心参数名称，只关心类型）。

2. **修改头文件中的函数声明**：将参数名从短变量名改为有意义的描述性名称。  
   - 操作示例：  
     `void setNotes(const std::string& n);` → `void setNotes(const std::string& notes);`

3. **修改实现文件中的函数签名**：在 `.cpp` 文件中找到该函数的定义行，同步修改参数名，使其与头文件一致。  
   - 操作示例：  
     `void PasswordDialog::setNotes(const std::string& n)` → `void PasswordDialog::setNotes(const std::string& notes)`

4. **修改函数体内所有对该旧参数名的引用**：搜索函数体内所有使用旧参数名的地方（包括赋值、参数传递、输出等），全部替换为新名称。  
   - 操作示例：  
     `m_edtNotes->setText(QString::fromStdString(n));` → `m_edtNotes->setText(QString::fromStdString(notes));`  
   - 提示：使用文本编辑器的“查找替换”功能，限定在当前函数范围内，避免误改其他同名变量。

5. **确认无遗漏**：检查文件是否还存在旧参数名的引用。若函数体较长，建议逐行扫描或使用编译器的“未定义变量”错误检测来验证。确保所有引用均已更新，否则会导致编译错误。

## 来源
run: 20260728-104017-f51e3114, 迭代 2 轮, 最终 10/10