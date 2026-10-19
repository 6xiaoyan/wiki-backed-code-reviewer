---
domain: qt
rule_id: qt-switch-case-alignment
title: case 标签与 switch 关键字对齐
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
  - [[qt-switch-break]]
---

# case 标签与 switch 关键字对齐

## 规则条款

`case` 标签必须与 `switch` 关键字保持同一缩进层级。`case` 内部的执行语句缩进一层。

## 正确示例

```cpp
void processStatus(int status)
{
    switch (status) {
    case 0:
        handleSuccess();
        break;
    case 1:
        handleWarning();
        break;
    case 2:
        handleError();
        break;
    default:
        logUnknownStatus(status);
        break;
    }
}
```

## 错误示例

```cpp
// 错误：case 比 switch 多缩进一层
void processStatus(int status)
{
    switch (status) {
        case 0:
            handleSuccess();
            break;
        case 1:
            handleWarning();
            break;
    }
}
```

```cpp
// 错误：case 与内部语句同一层级，无法区分
void processStatus(int status)
{
    switch (status) {
    case 0:
    handleSuccess();
    break;
    }
}
```

## 检查方法
使用正则表达式检查 `case` 关键字前的缩进是否与同级 `switch` 关键字一致：

1. 定位每个 `switch` 语句块的起始行，记录其缩进深度（前导空白字符数量）。
2. 检查该 `switch` 块内每个 `case` 或 `default` 标签的缩进深度。
3. `case`/`default` 标签的缩进深度必须等于 `switch` 关键字的缩进深度。
4. 标签内部的执行语句缩进深度应比 `case` 多一级（通常 4 个空格）。

正则检测思路：提取 `switch` 行前导空白长度 `N`，其后 `case`/`default` 行前导空白长度也必须为 `N`。

## 修复指南

1. 找到缩进不正确的 `case` 或 `default` 标签。
2. 调整该行的前导空白，使其与 `switch` 关键字对齐。
3. 确保 `case` 内部的语句比 `case` 多缩进一级（4 个空格）。
4. 在 IDE 中可使用自动格式化工具辅助修复。

## 审查清单

- [ ] 所有 `case` 标签与 `switch` 关键字在同一缩进层级
- [ ] 所有 `default` 标签与 `switch` 关键字在同一缩进层级
- [ ] `case` 内部语句比 `case` 标签多缩进一层
- [ ] 嵌套 `switch` 语句的各层 `case` 均正确对齐

## 关联页面

- [[qt-switch-break]]：每个 case 分支需包含 break/return 语句
