---
domain: qt
rule_id: qt-var-last-word-type
title: 变量名末尾类型标识
priority: main
source_file: rules/QT代码开发规范.md
source_section: "§3.4 变量命名"
status: active
check_method: llm
deterministic_check: false
checkability: llm_checkable
conflicts_with: []
overrides: []
related_pages:
  - [[qt-var-qclass-lowercase]]
  - [[qt-ui-control-prefix]]
  - [[cpp-naming-variables]]
---

# 变量名末尾类型标识

## 规则条款

对于无独立概念的变量（即变量本身不表达独立业务含义，仅作为某种类型的容器或集合），变量名最后一个单词应为类名，以体现变量类型。例如：`QList<QString>` 类型的传送带名称集合，命名为 `m_conveyor_name_list` 或 `m_conveyor_names`，其中 `list` 或复数形式表明其为列表容器类型。

该规则的核心意图是让阅读者在不必查看声明的情况下，通过变量名即可推断其类型。适用于成员变量和局部变量中缺乏独立业务语义的场景。

## 正确示例

```cpp
// QList 容器——最后一个单词为 list 或复数形式
QList<QString> m_conveyor_name_list;
QList<QString> m_conveyor_names;
QList<QWidget*> m_child_widget_list;
QList<int> m_id_list;

// QMap 容器——最后一个单词为 map
QMap<QString, int> m_config_map;
QMap<int, QWidget*> m_widget_map;

// QVector 容器——最后一个单词为 vec 或复数
QVector<double> m_value_vec;
QVector<QPointF> m_points;

// QSet 容器——最后一个单词为 set
QSet<QString> m_visited_set;

// 非容器但缺乏独立概念——末尾为类型标识
QTimer m_refresh_timer;
QFile m_log_file;
QDir m_work_dir;
```

## 错误示例

```cpp
// 无独立概念的变量，末尾未体现类型
QList<QString> m_conveyor_name;     // 是单数名称还是列表？→ 应为 m_conveyor_name_list 或 m_conveyor_names
QMap<QString, int> m_config;        // 是单个配置项还是映射表？→ 应为 m_config_map
QTimer m_refresh;                   // 是刷新动作还是定时器？→ 应为 m_refresh_timer

// 以下具有独立业务概念的变量不需要末尾类型标识——这些是正确的，不应触发检查：
QString m_user_name;                // 有独立概念，无需类型后缀
int m_active_count;                 // count 本身就是业务语义
bool m_is_enabled;                  // 有独立语义
```

## 检查方法
1. LLM 分析变量声明，判断变量是否具有独立业务概念。
2. 对于缺乏独立概念的变量，检查其名称末尾是否包含类型标识词（如 `list`、`map`、`vec`、`set`、`timer`、`file`、`dir` 等）
3. 若变量名末尾没有类型标识且变量本身缺乏独立语义，标记为违规。
4. 特别注意：具有明确业务含义的变量（如 `m_user_name`、`m_active_count`）不适用此规则。

## 修复指南

1. 判断变量是否有独立业务概念：
   - 有独立概念：如 `user_name`、`active_count`、`is_visible`——无需修改
   - 无独立概念：如纯容器、工具类实例——需添加类型标识
2. 对于需要修复的变量，在变量名末尾添加类型标识：
   - `QList` → 末尾加 `_list` 或使用复数形式
   - `QMap` → 末尾加 `_map`
   - `QVector` → 末尾加 `_vec` 或使用复数形式
   - `QSet` → 末尾加 `_set`
   - `QTimer` → 末尾加 `_timer`
   - `QFile` → 末尾加 `_file`
3. 同步更新所有引用该变量的位置。

## 审查清单

- [ ] 识别所有缺乏独立业务概念的变量声明
- [ ] 检查变量名末尾是否包含恰当的类型标识
- [ ] 确认有独立概念的变量未被误报
- [ ] 类型标识词需准确反映实际类型（`_list` 对应 `QList`，`_map` 对应 `QMap` 等）

## 关联页面

- [[qt-var-qclass-lowercase]]：Qt 类变量下划线命名
- [[qt-ui-control-prefix]]：UI 控件变量命名前缀
- [[cpp-naming-variables]]：C++ 变量命名总体规范
