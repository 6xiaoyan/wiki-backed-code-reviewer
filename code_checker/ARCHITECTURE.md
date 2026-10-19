# Code Checker — 架构文档

## 概述

**Code Checker** 是一个基于 LangGraph 的自动化代码合规审查系统。它对 C++/Qt 项目进行多维度检查（代码规范、Git 提交、SQLite 安全），自动生成修复方案，并通过自我审查（self-critique）迭代优化修复质量，最终输出 Markdown 格式的合规报告。

### 核心能力

| 维度 | 检查对象 | 审查方式 |
|------|----------|----------|
| C++ 代码规范 | `.cpp` `.h` `.hpp` `.cc` | LLM（DeepSeek） |
| Qt 开发规范 | 含 Qt 标记的文件 + `.pro` `.ui` | LLM（DeepSeek），正则预筛选 |
| Git 提交规范 | 最近 50 条 commit | 纯正则规则引擎 |
| SQLite 安全 | 含 SQLite 标记的 C++ 文件 | LLM（DeepSeek），正则预筛选 |

---

## 技术栈

| 层 | 技术 |
|----|------|
| 工作流编排 | LangGraph (`StateGraph` + `Send` 扇出) |
| LLM 后端 | DeepSeek API（`langchain-openai` 兼容接口） |
| 状态管理 | TypedDict（`AgentState`） |
| Git 交互 | `subprocess`（纯规则引擎） |

---

## 项目结构

```
code_checker/
├── __init__.py              # 包入口，导出 app 和 AgentState
├── main.py                  # 启动入口（可直接运行）
├── config.py                # 全局配置（LLM、文件扩展名、正则、路径）
├── state.py                 # AgentState 类型定义
├── utils.py                 # 工具函数（JSON 解析、文件读取）
├── routing.py               # 路由逻辑（Send 扇出 + 条件路由）
├── graph.py                 # StateGraph 构建 & 编译
├── nodes/                   # 节点模块（每个节点一个文件）
│   ├── __init__.py          # 统一导出
│   ├── repo_scanner.py      # 文件扫描
│   ├── cpp_checker.py       # C++ 规范检查
│   ├── qt_checker.py        # Qt 规范检查
│   ├── git_checker.py       # Git 提交检查
│   ├── sqlite_checker.py    # SQLite 安全审查
│   ├── report_merger.py     # 违规去重合并
│   ├── fix_planner.py       # 修复方案生成
│   ├── self_critique.py     # 自我审查（反思）
│   └── report_exporter.py   # 报告导出
└── ARCHITECTURE.md          # 本文档
```

---

## 工作流拓扑

```
                        ┌──────────────────────────────┐
                        │          START               │
                        └─────────────┬────────────────┘
                                      │
                                      ▼
                        ┌──────────────────────────────┐
                        │       repo_scanner            │
                        │  · 递归遍历 repo_path         │
                        │  · 过滤源码扩展名             │
                        │  · 读取文件全文（UTF-8/GBK）  │
                        └─────────────┬────────────────┘
                                      │
                              Send 扇出 (4路并行)
                ┌─────────┬─────────┼─────────┬─────────┐
                ▼         ▼         ▼         ▼         ▼
          ┌─────────┐┌─────────┐┌─────────┐┌──────────────┐
          │  cpp    ││  qt     ││  git    ││   sqlite     │
          │ checker ││ checker ││ checker ││   checker    │
          │ (LLM)   ││ (LLM)   ││ (正则)  ││   (LLM)      │
          └────┬────┘└────┬────┘└────┬────┘└──────┬───────┘
               │          │          │             │
               └──────────┴──────────┴─────────────┘
                                      │
                                      ▼
                        ┌──────────────────────────────┐
                        │      report_merger            │
                        │  · 按 (file, line) 去重       │
                        │  · 保留最高严重度             │
                        │  · 按严重度→文件→行号排序     │
                        └─────────────┬────────────────┘
                                      │
                                      ▼
                        ┌──────────────────────────────┐
                        │       fix_planner             │
                        │  · 按文件分组                 │
                        │  · LLM 生成修复方案           │
                        │  · 首次全量 / 重试增量        │
                        └─────────────┬────────────────┘
                                      │
                                      ▼
                        ┌──────────────────────────────┐
                        │      self_critique            │
                        │  · 对每条方案评分 (0-10)      │
                        │  · 维度: 正确性/完整性/       │
                        │    无副作用/风格一致          │
                        │  · ≥6 分 → passed (status=1)  │
                        └─────────────┬────────────────┘
                                      │
                              条件路由
                      ┌───────────┴───────────┐
                      │                       │
              有未通过 & <3次            全部通过 / 达上限
                      │                       │
                      ▼                       ▼
               fix_planner             report_exporter
               (重改)                  · 生成 Markdown
                      │                · 写入 compliance_report.md
                      │                       │
                      └───────────────────────┘
                                      │
                                      ▼
                                      END
```

---

## 数据流（AgentState）

### State 字段说明

```
AgentState
├── [输入]
│   └── repo_path: str                       # 仓库路径
│
├── [repo_scanner 产出]
│   ├── file_list: list[str]                 # 文件路径列表
│   └── file_contents: dict[str, str]        # 文件路径 → 全文
│
├── [四路检查器产出]
│   ├── cpp_violations: list[dict]           # C++ 违规
│   ├── qt_violations: list[dict]            # Qt 违规
│   ├── git_violations: list[dict]           # Git 违规
│   └── sqlite_violations: list[dict]        # SQLite 违规
│
├── [流水线产出]
│   ├── merged_violations: list[dict]        # 去重合并后
│   ├── fix_plans: list[dict]                # 修复方案（含 status/score）
│   ├── fix_iteration: int                   # 迭代计数
│   └── final_report: str                    # Markdown 报告
│
└── [LangGraph 内置]
    └── messages: list[BaseMessage]          # 消息通道
```

### 违规记录结构

```python
{
    "file":     str,    # 文件路径
    "line":     int,    # 行号
    "rule":     str,    # 规范条款名
    "severity": str,    # critical | warning | suggestion
    "current":  str,    # 当前代码
    "expected": str,    # 应为
    "reason":   str,    # 原因说明
    "source":   str,    # 来源检查器（merger 添加）
}
```

### 修复方案结构

```python
{
    "file":       str,   # 文件路径
    "line":       int,   # 行号
    "fix_before": str,   # 原代码
    "fix_after":  str,   # 修复后代码
    "reason":     str,   # 修复理由
    "status":     int,   # 0 = 未通过审查, 1 = 已通过
    "score":      int,   # 自我审查评分 (0-10)
    "feedback":   str,   # 审查反馈
}
```

---

## 模块职责 & 依赖

| 模块 | 职责 | 依赖 |
|------|------|------|
| `config.py` | LLM 客户端、扩展名集合、正则模式、路径常量 | `langchain_openai` |
| `state.py` | `AgentState` TypedDict 定义 | `langgraph`, `langchain_core` |
| `utils.py` | JSON 容错解析、文件读取 | 标准库 |
| `nodes/repo_scanner.py` | 递归扫描源码文件 | `config`, `utils` |
| `nodes/cpp_checker.py` | C++ 规范 LLM 审查 | `config`, `utils` |
| `nodes/qt_checker.py` | Qt 规范 LLM 审查 + 正则预筛选 | `config`, `utils` |
| `nodes/git_checker.py` | Git commit 格式校验（纯规则） | `config` |
| `nodes/sqlite_checker.py` | SQLite 安全 LLM 审查 + 正则预筛选 | `config`, `utils` |
| `nodes/report_merger.py` | 违规去重、严重度排序 | `config` |
| `nodes/fix_planner.py` | LLM 生成修复方案（全量/增量） | `config`, `utils` |
| `nodes/self_critique.py` | LLM 自我审查修复方案 | `config` |
| `nodes/report_exporter.py` | 输出 Markdown 报告 | `config` |
| `routing.py` | Send 扇出 + 条件路由决策 | `config` |
| `graph.py` | StateGraph 构建、编译、导出 app | `nodes`, `routing`, `state` |
| `main.py` | 入口：调用 app.invoke() + 打印摘要 | `graph` |

### 依赖图（简化）

```
main.py
  └── graph.py
        ├── state.py
        ├── nodes/*.py
        │     ├── config.py
        │     └── utils.py
        └── routing.py
              ├── state.py
              └── config.py
```

---

## 关键设计决策

### 1. Send 扇出 vs 串行

使用 `langgraph.types.Send` 实现四路并行检查，而非串行逐个执行。四个 checker 互不依赖，扇出可将总耗时降低至 `max(T_cpp, T_qt, T_git, T_sqlite)`，而非四者之和。

### 2. LLM 审查 vs 规则引擎

- **Git checker** 使用纯正则规则引擎 — commit 格式校验是确定的、可穷举的，无需 LLM。
- **C++ / Qt / SQLite checker** 使用 LLM — 代码规范灵活多变，正则难以覆盖所有场景。

### 3. 正则预筛选

`qt_checker` 和 `sqlite_checker` 先用正则快速判断文件是否相关，再提交 LLM。避免对大量不相关文件浪费 API 调用。

### 4. 自我审查迭代（Self-Critique Loop）

`fix_planner → self_critique → route` 形成反思循环：

- LLM 对每个修复方案从四个维度评分（0-10）
- ≥ 6 分标记通过，否则退回 `fix_planner` 重改
- 最多迭代 **3 次**，防止无限循环

### 5. JSON 容错解析

`utils.extract_json_array()` 具备多层容错：

1. 去除 markdown 代码块包裹
2. 定位 `[...]` 或 `{...}` 边界
3. 修复末尾多余逗号
4. 整体解析失败 → 逐对象正则提取

---

## 使用方法

### 前提条件

```bash
pip install langgraph langchain-openai langchain-core
```

确保 `rules/` 目录包含以下文件：

- `C++代码规范.md`
- `QT代码开发规范.md`
- `SQLite加密.md`

### 运行

```bash
cd langgraph
python -m code_checker.main
```

或在代码中调用：

```python
from code_checker.graph import app

result = app.invoke({
    "repo_path": "./your-cpp-project",
    "file_list": None,
    "file_contents": None,
    "cpp_violations": None,
    "qt_violations": None,
    "git_violations": None,
    "sqlite_violations": None,
    "merged_violations": None,
    "fix_plans": None,
    "fix_iteration": 0,
    "final_report": None,
    "messages": [],
})

# 结果在 result["merged_violations"] 和 result["fix_plans"] 中
```

### 输出

运行后在当前目录生成 `compliance_report.md`，包含：

- 违规项详情（文件、行号、严重度、原因）
- 对应修复方案（改前/改后 diff）
- 审查结果（评分、通过状态、反馈）

---

## 扩展指南

### 添加新的检查器

1. 在 `nodes/` 下新建模块（如 `nodes/rust_checker.py`）
2. 实现函数签名为 `(AgentState) -> dict`，返回 `{"rust_violations": [...]}`
3. 在 `state.py` 的 `AgentState` 中添加 `rust_violations: Optional[list[dict]]`
4. 在 `routing.py` 的 `fanout_to_checkers()` 中添加 `Send("rust_checker", ...)`
5. 在 `graph.py` 中注册节点和边
6. 在 `report_merger.py` 的 `_CHECKER_SOURCES` 中添加来源

### 替换 LLM 后端

修改 `config.py` 中的 `llm` 初始化即可：

```python
llm = ChatOpenAI(
    model="gpt-4o",
    base_url="https://api.openai.com/v1",
    api_key=os.getenv("OPENAI_API_KEY"),
)
```

### 调整审查策略

修改 `config.py` 中的常量：

- `MAX_FIX_ITERATIONS`: 最大自我审查迭代次数
- `PASS_THRESHOLD`: `self_critique.py` 中的通过分数线
- `SEVERITY_ORDER`: 严重度排序权
