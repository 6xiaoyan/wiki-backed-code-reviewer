---
domain: qt-wiki
rule_id: qtwiki-switch-style
title: Switch 语句风格（Qt Coding Style 对照）
priority: sub
source_file: rules/Qt_Coding_Style.md
source_section: "Switch 语句"
status: active
check_method: regex
deterministic_check: true
checkability: deterministic
conflicts_with: []
overrides: []
related_pages:
  - [[qt/switch-break]]
  - [[qt/switch-case-alignment]]
---

# Switch 语句风格（Qt Coding Style 对照）

> 来源：Qt Coding Style（[wiki.qt.io](https://wiki.qt.io/Qt_Coding_Style)）| 与公司规则一致

## 与公司规则的对照

| Qt Coding Style 条款 | 公司规则页面 | 一致性 |
|---------------------|------------|--------|
| Case 标签与 switch 对齐 | [[qt/switch-case-alignment]] | ✅ 一致 |
| 每个 case 以 break/return 结尾 | [[qt/switch-break]] | ✅ 一致 |
| 故意的穿透用 `Q_FALLTHROUGH()` 标记 | [[qt/switch-break]] | ✅ 一致 |

## Qt Coding Style 示例

```cpp
switch (myEnum) {
case Value1:
  doSomething();
  break;
case Value2:
case Value3:
  doSomethingElse();
  Q_FALLTHROUGH();
default:
  defaultHandling();
  break;
}
```

## 冲突说明

无冲突。Qt Coding Style 的 switch 风格与公司规则完全一致。
