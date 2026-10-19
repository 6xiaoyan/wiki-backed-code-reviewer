---
domain: qt
rule_id: qt-binary-op-spacing
title: 二元操作符前后加空白字符
priority: main
source_file: rules/QT代码开发规则.md
source_section: "§2.3"
status: active
check_method: regex
deterministic_check: true
checkability: deterministic
conflicts_with: []
overrides: []
related_pages:
  - [[qt-keyword-spacing]]
---

# 二元操作符前后加空白字符

## 规则条款

所有二元操作符（`+`、`-`、`*`、`/`、`=`、`==`、`!=`、`<`、`>`、`<=`、`>=`、`&&`、`||`、`&`、`|`、`^`、`<<`、`>>`、`+=`、`-=`、`*=`、`/=` 等）均*前后各添加1 个空格*。这使表达式层次分明，操作优先级一目了然。例外：
- 一元操作符（`!`、`~`、`++`、`--`、`-`（负号））与操作数之间不加空格- 成员访问操作符（`.`、`->`）前后不加空格- 下标操作符`[]` 内部不加空格
- 函数调用符`()` 内部不加空格

## 正确示例

```cpp
int total = baseValue + additionalValue;
double ratio = (double)count / (double)total;
bool isValid = (index >= 0) && (index < maxCount);

if ((a == b) || (c != d)) {
    notifyChange();
}

for (int i = 0; i < size; ++i) {
    result += values[i] * weights[i];
}

QString fullName = firstName + " " + lastName;
int mask = flags & (OptionA | OptionB);
```

## 错误示例

```cpp
int total = baseValue+additionalValue;   // 错误：+ 号前后缺少空格double ratio=count/total;                // 错误：＝/ 号前后缺少空格bool isValid=(a==b)||(c!=d);            // 错误：所有操作符前后均缺少空格
if (x&&y) {                              // 错误：& 前后无空格    process();
}

// 一元操作符 —：正确不加空格
if (!isReady) { /* ... */ }              // 正确： 与操作数之间无空格for (int i = 0; i < n; ++i) { /* ... */ }  // 正确：+ 作为一元操作符不加空格
```

## 检查方法
1. 使用正则表达式匹配二元操作符前后缺少空格的情况。2. 排除一元操作符、成员访问、下标等上下文。3. 重点检测常见违规模式：`+`、`-`、`*`、`/`、`=`、`==`、`&&`、`||` 等操作符两侧缺少空格。
正则表达式（简化）：- `=\s*=`：`==` 操作符缺少空格（需区分）- `[a-zA-Z0-9_\)\]]\*[a-zA-Z0-9_\(]`：`*` 前后缺少空格
- `[a-zA-Z0-9_\)\]]\+[a-zA-Z0-9_\(]`：`+` 前后缺少空格

## 修复指南

1. 使用 clang-format 自动格式化：`SpaceBeforeAssignmentOperators: true`。2. Qt Creator 中`Options > C++ > Edit > Format` 使用内置 Qt 风格。3. 手动修复：在二元操作符前后各添加 1 个空格。
## 审查清单

- [ ] 所有二元操作符（`+` `-` `*` `/` `=` `==` `!=` `&&` `||` 等）前后各有 1 个空格- [ ] 一元操作符（`!` `~` `++` `--`）与操作数之间无空格
- [ ] 成员访问（`.` `->`）前后无空格
- [ ] 下标 `[]` 内部无多余空格
## 关联页面

- [[qt-keyword-spacing]]：关键字与括号之间加空格