---
domain: qt
rule_id: qt-switch-break
title: case 分支需包含 break 或 return 语句
priority: main
source_file: rules/QT代码开发规范.md
source_section: "§2.6 Switch"
status: active
check_method: regex
deterministic_check: true
checkability: deterministic
conflicts_with: []
overrides: []
related_pages:
  - [[qt-switch-case-alignment]]
---

# case 分支需包含 break 或 return 语句

## 规则条款

每个 `case` 分支必须包含 `break` 或 `return` 语句以终止执行。若故意使用穿透（fall through）逻辑，必须用注释明确说明。

## 正确示例

```cpp
// 每个分支都有 break，清晰明了
void handleAction(int action)
{
    switch (action) {
    case ACTION_OPEN:
        openFile();
        break;
    case ACTION_SAVE:
        saveFile();
        break;
    case ACTION_CLOSE:
        closeFile();
        break;
    default:
        break;
    }
}

// 使用 return 终止分支
QString getErrorMessage(int code)
{
    switch (code) {
    case 0:
        return QStringLiteral("成功");
    case 1:
        return QStringLiteral("文件未找到");
    case 2:
        return QStringLiteral("权限不足");
    default:
        return QStringLiteral("未知错误");
    }
}

// 故意穿透，用注释说明
void processChar(QChar ch)
{
    switch (ch.unicode()) {
    case 'a':
    case 'A':
        // fall through — 大小写统一处理
        handleAlpha();
        break;
    case '0':
        // fall through — 数字统一处理
    case '1':
    case '2':
        handleDigit();
        break;
    }
}
```

## 错误示例

```cpp
// 错误：case 分支缺少 break，导致意外穿透
void handleAction(int action)
{
    switch (action) {
    case ACTION_OPEN:
        openFile();
        // 缺少 break，会继续执行 SAVE 逻辑
    case ACTION_SAVE:
        saveFile();
    case ACTION_CLOSE:
        closeFile();
    }
}

// 错误：穿透没有注释说明意图
void processLevel(int level)
{
    switch (level) {
    case 1:
        initBasicMode();
    case 2:
        initAdvancedMode();
    case 3:
        initExpertMode();
    }
}
```

## 检查方法
使用正则表达式对 `case` 分支检测：

1. 定位每个 `case <值>:` 或 `default:` 标签。
2. 从该标签向下扫描，直到遇到下一个 `case`/`default` 标签或 `switch` 块的结束 `}`。
3. 检查该区间内是否存在 `break;` 或 `return`（含 `return <表达式>;`）语句。
4. 如果不存在，检查是否有 `// fall through` 或类似意图说明注释。
5. 既无终止语句也无穿透注释的分支视为违规。

## 修复指南

1. 为每个缺失终止语句的 `case` 分支末尾添加 `break;`。
2. 若该分支本意就是穿透到下一个 `case`，添加 `// fall through` 注释说明。
3. 对于连续多个值共享同一处理逻辑的空 `case`（如 `case 'a': case 'A':`），只需在最后的处理逻辑后加 `break;`。
4. 考虑使用 `[[qt-switch-case-alignment]]` 属性（C++17）替代注释，增强编译器检查。

## 审查清单

- [ ] 每个非空的 `case` 分支都有 `break` 或 `return` 语句
- [ ] 故意穿透的分支有明确注释（`// fall through` 或 `[[qt-switch-case-alignment]]`）
- [ ] 连续的 `case` 标签共享的处理逻辑后正确终止
- [ ] `default` 分支也有适当的终止语句

## 关联页面

- [[qt-switch-case-alignment]]：case 标签与 switch 关键字对齐
