---
domain: qt
rule_id: qt-braces-empty-body
title: 空语句体使用空大括号，禁止仅写分号
priority: main
source_file: rules/QT代码开发规则.md
source_section: "§2.4"
status: active
check_method: regex
deterministic_check: true
checkability: deterministic
conflicts_with: []
overrides: []
related_pages:
  - [[qt-braces-knr]]
---

# 空语句体使用空大括号，禁止仅写分号
## 规则条款

当控制流语句的语句体为空时（即不需要执行任何操作），必须使用**空大括号 `{}`** 明确表示，**禁止仅写分号 `;`**。`;` 容易被忽视或误解为笔误，而`{}` 明确传达「此处有意为空」的意图。推荐在 `{}` 内部添加简短注释说明为何为空。
## 正确示例

```cpp
// 显式空体，注释说明原因while (m_timer->isActive()) {
    // 等待定时器完成，由信号驱动继续}

// 空循环体
for (int i = 0; i < size && data[i] != sentinel; ++i) {
    // 仅递增指针，找到sentinel 即停止}

// 空函数体（纯虚接口的默认实现）void BasePlugin::initialize()
{
    // 默认无操作，子类可重写}
```

## 错误示例

```cpp
// 错误：仅用分号，意图不明
while (m_timer->isActive());  // 危险：容易被误读为while 循环体是空语句
// 错误：分号空体，极易被忽略for (int i = 0; i < size && data[i] != sentinel; ++i);  // 分号容易被忽略
// 错误：仅写分号if (condition);  // 意图不明确，是故意为空还是忘记写语句体？
else doSomething();
```

## 检查方法
1. 搜索控制流语句（`if`、`for`、`while`）头部的 `)` 后紧跟`;` 的模式。2. 验证该`;` 是否为空语句体。3. 排除 `do-while` 结构中`while (...) ;` 语法（`;` 是语法要求）。
正则表达式：
- 违规：`\b(?:if|for|while)\s*\([^)]*\)\s*;`：控制语句后直接跟分号
- 例外（do-while）：`}\s*while\s*\([^)]*\)\s*;`：不标记
## 修复指南

1. 将`;` 替换为`{ }` 或`{}`。2. 推荐在`{}` 内添加`// intentionally empty` 或说明为何为空的注释。3. 示例修复：   ```cpp
   // 修改前   while (m_timer->isActive());
   
   // 修改后   while (m_timer->isActive()) {
       // 等待定时器完成   }
   ```

## 审查清单

- [ ] 无控制流语句后仅有`;` 作为空体
- [ ] 空语句体使用 `{}` 包裹
- [ ] 空体内部有注释说明为空的原因
- [ ] `do-while` 语句中`while(cond);` 不受此规则约束
## 关联页面

- [[qt-braces-knr]]：控制流K&R 风格
