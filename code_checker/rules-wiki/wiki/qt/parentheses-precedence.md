---
domain: qt
rule_id: qt-parentheses-precedence
title: 复杂表达式用圆括号分组以明确运算优先级
priority: main
source_file: rules/QT代码开发规范.md
source_section: "§2.5"
status: active
check_method: llm
deterministic_check: false
checkability: llm_checkable
conflicts_with: []
overrides: []
related_pages:
  - [[qt-binary-op-spacing]]
---

# 复杂表达式用圆括号分组以明确运算优先级
## 规则条款

在复杂表达式中**使用圆括号 `()` 明确分组**，使运算优先级一目了然，避免因记错优先级导致的 bug。即使运算符优先级本身正确，也推荐加括号提高可读性。重点场景：
- 混合位运算和逻辑运算（`&`、`|` 和 `&&`、`||`）- 混合算术运算和位移运算（`+`、`-` 和 `<<`、`>>`）- 多个逻辑运算符连接- 三元运算符 `?:` 的嵌套使用- 涉及指针解引用和成员访问的组合
## 正确示例

```cpp
// 位运算与逻辑运算混合 —— 加括号明确if ((flags & MaskA) || (flags & MaskB)) {
    applyCombinedMask();
}

// 位移与算术混合 —— 加括号int offset = (base << 4) + (index & 0x0F);

// 多个逻辑条件组合 —— 分组清晰
if ((a > 0 && b > 0) || (c > 0 && d > 0)) {
    processPositive();
}

// 三元运算符 —— 加括号清晰int result = (value > threshold) ? (value * factor) : (defaultValue);

// 成员访问与指针解引用
bool ready = (m_worker != nullptr) && (m_worker->isReady());
```

## 错误示例

```cpp
// 错误：位运算和逻辑运算混合，优先级易混淆if (flags & MaskA || flags & MaskB) {  // & 优先级低于 ||？实际 & 高于 ||
    applyCombinedMask();
}

// 错误：多条件组合无括号，阅读困难
if (a > 0 && b > 0 || c > 0 && d > 0) {
    processPositive();
}

// 错误：位移与加法混合，实际位移优先级低于加法
int offset = base << 4 + index & 0x0F;  // 实际含义可能是 (base << (4 + index)) & 0x0F
```

## 检查方法
1. 使用 LLM 分析表达式的复杂度。2. 检测以下模式：
   - 同一表达式混合 3 种以上不同优先级的操作符
   - 位操作符（`&` `|` `^` `~`）与逻辑操作符（`&&` `||` `!`）混合   - 位移操作符与算术操作符混合   - 赋值操作符出现在条件判断中（如 `if (a = b)`）。3. 标记缺少分组括号的复杂表达式。4. 建议添加括号以明确分组。
## 修复指南

1. 分析表达式的运算符优先级关系。2. 在低优先级操作符周围添加括号以明确分组。3. 不需要对极简单的表达式（如 `a + b * c`）过度加括号。4. 示例修复：   ```cpp
   // 修改前：   if (flags & MaskA || flags & MaskB)
   
   // 修改后：   if ((flags & MaskA) || (flags & MaskB))
   ```

## 审查清单

- [ ] 混合不同优先级操作符的表达式使用括号分组
- [ ] 位运算与逻辑运算混合时，每组位运算有独立括号
- [ ] 三元运算符嵌套时使用括号明确优先级- [ ] 不做无意义的过度括号（如 `return (x);`）
## 关联页面

- [[qt-binary-op-spacing]] —— 二元操作符前后加空白字符
