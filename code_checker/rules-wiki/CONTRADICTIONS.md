# Specification Contradiction Registry

> 本文件记录公司规范文件之间的已知矛盾。
>
> **工作流**：
> 1. Pipeline 运行时：wiki 保持干净（无 conflict 标注），checker agent 按规则查违规
> 2. Pipeline 跑完后：`wiki_arbitration` 模块用 pro 模型审视违规 + 矛盾候选
> 3. 仲裁模型生成 `wiki-arbitration-report.md`，提出规则修改建议（MODIFY/DELETE/MERGE）
> 4. 人工审核报告后，应用 wiki 变更
> 5. 若仲裁确认了新的规范矛盾，在此文件中注册条目
>
> **本文件不写入 wiki 页面**。规则冲突通过修改规则本身来解
> 决，而非在 wiki 页面中标注 `conflicts_with` / `overrides` 元数据。

---

## CONTRADICTION-001: §1.1 camelCase vs §11.2 测试命名

| 字段 | 值 |
|------|-----|
| **状态** | RESOLVED — 测试函数豁免 camelCase |
| **发现日期** | 2026-07-28 |
| **来源实验** | caltest3 合规审查 (experiment-design.md) |

**冲突描述**:

- C++规范 §1.1 要求所有函数/方法使用 camelCase，错误示例明确将 snake_case 列为违规
- C++规范 §11.2 测试示例中展示 `TEST_F(DataProcessorTest, processData_EmptyInput_ReturnsEmpty)` 使用下划线分隔
- Google Test 官方推荐 `Method_Scenario_Expected` 格式；Qt Test 框架也普遍使用下划线分隔测试名

**影响范围**:

- 15 条 code_checker finding（#4-#17, #19）全部源于此矛盾
- 占 caltest3 实验总 finding 的 58%

**裁决规则**:

**§11.2 示例优先于 §1.1 字面条文。** 测试函数名（QtTest private slots、Google Test TEST/TEST_F/TEST_P 宏）豁免 camelCase 要求，允许使用 snake_case 的 `Method_Scenario_Expected` 格式。

**受影响 wiki 页面**:

- `cpp/naming-functions.md` — 规则条款适用于普通函数，测试函数不受限
- `cpp/naming-variables.md` — 同理，测试局部变量可能受影响

---

## CONTRADICTION-002: C++ Allman 大括号 vs Qt K&R 大括号

| 字段 | 值 |
|------|-----|
| **状态** | UNRESOLVED — 项目级裁决，无统一规则 |
| **发现日期** | 2026-07-28 |
| **来源实验** | caltest3 合规审查 |

**冲突描述**:

- C++规范 §1.3 要求 Allman 风格：左大括号 `{` 独占一行
- Qt 规范 §2.4 要求 K&R 风格：控制流左大括号与语句同行
- 两个规范同时生效时，代码无法同时满足两方要求

**影响范围**:

- 所有同时包含 C++ 和 Qt 代码的项目
- caltest3 实验：Claude Code 识别了此冲突并标记为跨规范元问题

**裁决规则**:

**无统一规则。** 需项目级决策：选择一种风格并在 `.clang-format` 中统一配置。
公司规范对大括号风格未做硬性规定（见 C++ 硬约束），属于项目级裁决冲突。

**受影响 wiki 页面**:

- `cpp/braces.md` — Allman 风格要求
- `qt/braces-knr.md` — K&R 风格要求
- `qt/braces-function-class.md` — 函数/类定义允许 Allman，与控制流 K&R 的边界

---

## CONTRADICTION-003: C++ 禁止裸 new vs Qt 父子模型

| 字段 | 值 |
|------|-----|
| **状态** | RESOLVED — Qt 父子模型是裸 new 禁令的合法例外 |
| **发现日期** | 2026-07-28 |
| **来源实验** | caltest3 合规审查 |

**冲突描述**:

- C++规范 §3.2 / §7 禁止裸 `new`/`delete`，要求使用 `std::make_unique`/`std::make_shared`
- Qt 规范 §4.4 要求通过父对象管理子对象生命周期：`new QLabel(this)` 是标准实践
- Qt 对象树的 `QObject::setParent()` 机制自动管理子对象析构，无需也不应使用智能指针
- 若用 `std::unique_ptr<QLabel>` 包裹 Qt 控件，会与 Qt 父子析构机制产生双重删除风险

**影响范围**:

- 所有 Qt Widgets 代码中的控件构造
- caltest3 实验中 3 处 `new QLineEdit(this)` 等被标记为裸 new 违规

**裁决规则**:

**Qt 父子模型优先。** 对于传入了父对象（`this` 或其他 `QObject*`）的 Qt 控件构造，
裸 `new` 是合法且推荐的做法。不传入父对象的 Qt 堆对象才应使用智能指针或转为栈对象。

**受影响 wiki 页面**:

- `cpp/no-bare-new-delete.md` — 规则条款需要 Qt 父子模型例外说明
- `qt/parent-child-memory.md` — Qt 对象内存管理
