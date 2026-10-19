# API 降级兜底策略

> **设计哲学**：这是一个**内部工具**，不是面向外部用户的 SaaS 产品。
> 内部工具的兜底策略与 SaaS 有本质区别——我们不需要"静默降级以保证用户体验不中断"，
> 我们需要"大声报告什么没跑到，让开发者自己决定下一步"。
>
> 参考：llm-code-review `--offline` 模式、PRSense 六边形架构、
> Revet "不是 GPT 包装器"宣言、IntelliJ IDEA Code Review Plugin 双模式设计。

---

## 0 内部工具 vs SaaS：设计哲学的根差异

### 0.1 为什么内部工具的兜底策略不同

| 维度 | 对外 SaaS | 内部工具（我们） |
|------|-----------|-----------------|
| **失败代价** | 用户流失、SLA 赔钱 | 同事多等一会儿，重跑一次 |
| **静默降级** | 可接受（用户体验不中断） | **危险**——漏报比报错更糟糕 |
| **复杂度容忍度** | 愿意为可用性买单（多 region、消息队列） | 越简单越好，出问题好排查 |
| **恢复手段** | 自动自愈 | 手动重跑就行 |
| **用户期待** | "服务永远在线" | "挂了告诉我就行，我自己重跑" |

核心矛盾：**对外服务需要"尽量别挂"，内部工具需要"挂了就大声说，别偷偷降级"。**

### 0.2 行业内部工具的实践

搜索了多个 2024-2025 年的内部代码审查工具，发现一个清晰的共性模式：

**1. llm-code-review（radetsky）——显式 `--offline` 标志**

不做自动降级。API 挂了就报错，用户看到后自己决定：
```bash
llm-code-review --repo ./myproject           # 正常模式：LLM + 静态分析
llm-code-review --repo ./myproject --offline  # 离线模式：纯静态分析
```

设计哲学：**给用户控制权，而不是替用户做决定。**

**2. PRSense（navxio）——六边形架构，核心零网络依赖**

```
Core（纯逻辑，零网络访问，零文件系统假设）
  ↑ 实现端口
Adapters（LLM provider、文件系统等）
  ↑ 可插拔，可替换
```

核心 review 逻辑与 LLM 完全解耦。Ollama 本地模型、Anthropic、OpenAI 随意换——核心一行不动。

**3. Revet——"不是 GPT 包装器"**

> "80% of checks are deterministic, fast, free, and reproducible. Offline-first."

刻意把定位写成"确定性工具 + AI 可选增强"，而不是"AI 工具 + 确定性兜底"。

**4. IntelliJ IDEA Code Review Plugin——显式双模式**

- **Network Mode**：连服务器，实时同步，完整功能
- **Local Mode**：存本地 `.idea` 文件，零网络依赖

没有"半在线"状态。要么在线要么离线，清晰明确。

### 0.3 我们已有的架构优势

我们的 `code_checker` 实际上已经踩在了行业主线上：

```
deterministic_checker（确定性正则，21 规则，零 API）
    ↓
四路 LLM agent（语义增强，可选）
    ↓
format_fixer（确定性修复，零 API）
    ↓
fix_agent / review_agent（LLM 增强，可选）
    ↓
report_exporter（纯本地，零 API）
```

**我们不需要"加降级层"——我们需要的是把已有的确定性底座正式化，让 LLM 变成明确可跳过的增强层。**

### 0.4 核心设计原则

1. **报告一定产出**——即使所有 LLM 都挂了，deterministic_checker + format_fixer + report_exporter 三条纯本地路径保证有结果
2. **大声降级，不静默吞错**——API 失败的 stage 产出显式标记（`degraded`/`skipped`/`failed`），不在底层偷偷换方案
3. **给用户控制权**——`--offline` 跳过所有 LLM，`--force` 忽略 API 错误继续。不替用户做降级决策
4. **不做自动级联降级**——API 挂了不会自动从 pro 切 flash 再切正则。挂了就标记，让用户知道
5. **状态显式，来源透明**——报告中每个 stage 标注运行状态，每条违规标注 `source_kind`

---

## 1 逐阶段降级行为

### 1.1 永不降级的阶段（纯本地，零 API）

| 阶段 | 说明 |
|------|------|
| `repo_scanner` | 扫描本地文件系统 |
| `deterministic_checker` | 21 条正则规则，Python 强制执行 |
| `format_fixer` | include 排序、Tab→空格等确定性修复 |
| `report_exporter` | 写 Markdown 文件到磁盘 |

### 1.2 LLM 阶段降级行为

#### cpp_agent / qt_agent / sqlite_agent

| 场景 | 行为 |
|------|------|
| 正常 | `create_react_agent(model=llm)` 分 chunk 并行 |
| 单个 chunk API 异常 | 该 chunk 返回空（`[]`），其他 chunk 不受影响 |
| 全部 chunk 失败 | 返回 `{"xxx_violations": []}`，pipeline 继续 |
| offline 模式 | 跳过整个 agent，返回空列表 |

**降级报告质量**：
- ✅ 仍有 `deterministic_checker` 的正则违规（Tab、行宽、保护宏等）
- ❌ 缺失 LLM 语义违规（命名、设计问题等）
- 报告中标注 `cpp_agent: degraded (N/M chunks failed)`

#### git_agent

| 场景 | 行为 |
|------|------|
| 正常 | LLM agent 通过 `run_git_log` 工具获取提交记录 |
| API 不可用 / offline | 纯 Python 正则检查 commit 格式：`<type>: <desc>` 格式、type 枚举、长度 ≤ 50 |
| git 未安装 | 返回 `[]`，报告标注 "Git 审查跳过（git 未安装）" |

**本地降级能力**：Git 的 4 条规则全部是正则可检查的（格式、类型枚举、长度、风格），完全不需要 LLM。

#### report_merger

| 场景 | 行为 |
|------|------|
| 正常 | LLM agent 语义去重 |
| LLM 抛异常 | 触发 `_fallback_dedup()`：按 `(file, line)` 确定性去重 |
| LLM 返回空 | 同上（已有逻辑） |

#### fix_agent

| 场景 | 行为 |
|------|------|
| 正常 | per-violation 并行，3 轮补跑 |
| 单条 API 异常 | 该条标记 `fix_status: "degraded"`，其他条不受影响 |
| 全部 API 异常 | 所有未修复的标记 `degraded`，报告列出 "需手动修复" |
| offline 模式 | 跳过，所有方案标记 `degraded`，不做修复尝试 |

**注意**：fix_agent 不做模板降级（template fixers）。之前考虑的模板修复（include 排序等）已由 `format_fixer` 确定性完成，fix_agent 处理的都是需要语义理解的修复。LLM 不可用时强行模板修复可能产生错误 diff，不如标记 `degraded` 让人工处理。

#### review_agent

| 场景 | 行为 |
|------|------|
| 正常 | LLM agent 评分 + 反幻觉 gate |
| 单个 chunk API 异常 | 该 chunk 的所有 plan 标记 `fix_status: "unreviewed"` |
| 全部 chunk 失败 | 所有 plan 标记 `unreviewed`，报告警告 "修复方案未经审查" |

**安全门禁**：review_agent 是拦截幻觉的最后防线。它挂了 = 防线失守。**绝不**在防线失守时默认放行。标记 `unreviewed` = 告诉用户"这些修复没人审过，你自己看"。

#### wiki_arbitration / fix_patterns（离线后处理）

| 场景 | 行为 |
|------|------|
| API 不可用 | 静默跳过，不阻塞 pipeline |
| 多次跳过 | 将未仲裁结果写入 `.cache/pending-arbitration/`，下次可用时批量处理（Phase 2） |

---

## 2 全局降级模式

```python
# DEGRADATION_MODE 环境变量
#   strict  — 不降级，API 故障即 crash（CI 门禁用）
#   normal  — LLM 阶段降级但继续，始终产出报告（默认）
#   offline — 零 API 调用，只跑确定性检查 + format_fixer
DEGRADATION_MODE = os.environ.get("DEGRADATION_MODE", "normal").lower()
```

| 阶段 | strict | normal | offline |
|------|--------|--------|---------|
| deterministic_checker | ✅ 运行 | ✅ 运行 | ✅ 运行 |
| format_fixer | ✅ 运行 | ✅ 运行 | ✅ 运行 |
| cpp/qt/sqlite agent | crash on fail | degrade → skip | 跳过 |
| git_agent | crash on fail | degrade → 本地正则 | 本地正则 |
| report_merger | crash on fail | degrade → 确定性去重 | 确定性去重 |
| fix_agent | crash on fail | degrade → 标记 degraded | 跳过 → degraded |
| review_agent | crash on fail | degrade → unreviewed | 跳过 → unreviewed |
| wiki_arbitration | 跳过 | 跳过 | 跳过 |
| fix_patterns | 跳过 | 跳过 | 跳过 |
| **最终产出** | 完整或 crash | ✅ 始终有报告 | ✅ 始终有报告 |

### CLI 标志

```bash
# 正常模式（默认）
python -m code_checker.main ./myproject

# 离线模式：零 API 调用
python -m code_checker.main ./myproject --offline

# strict 模式：API 故障即 crash（CI 门禁）
python -m code_checker.main ./myproject --strict
```

---

## 3 State 字段

```python
# state.py 新增
class DegradationEvent(TypedDict):
    stage: str           # 阶段名
    status: str          # "ok" | "degraded" | "skipped" | "failed"
    reason: str          # 降级原因
    impact: str          # 对报告质量的影响

# AgentState 新增字段
degradation_log: list[dict]   # 逐阶段降级事件
offline_mode: bool            # 是否为离线模式
```

---

## 4 报告降级可见性

### 4.1 报告顶部横幅

当有阶段降级时，报告最顶部出现可信度横幅：

```markdown
## ⚠️ 运行状态

| 阶段 | 状态 | 说明 |
|------|------|------|
| deterministic_checker | ✅ 正常 | 21/21 规则已运行 |
| cpp_agent | ⚠️ 部分降级 | 3/4 chunks 成功，1 chunk API timeout |
| qt_agent | ✅ 正常 | 5/5 chunks 成功 |
| git_agent | ✅ 本地模式 | API 不可用，使用本地正则检查 |
| sqlite_agent | ⏭️ 跳过 | 无 SQLite 文件 |
| report_merger | ✅ 正常 | LLM 去重 |
| format_fixer | ✅ 正常 | 2 条自动修复 |
| fix_agent | ❌ 降级 | API 不可用，6 条修复标记为 degraded |
| review_agent | ❌ 降级 | API 不可用，所有修复标记为 unreviewed |

**综合可信度**: ⚠️ MEDIUM — 确定性检查完整，LLM 语义审查和修复方案审查不可用。
             请人工审查标记为 unreviewed 的条目。
```

### 4.2 每条违规的 source_kind

```markdown
- **来源**: cpp|qt
- **source_kind**: deterministic  ← 确定性检查，可信度最高
```

或：

```markdown
- **来源**: cpp
- **source_kind**: llm_pro  ← LLM 语义审查，可信度高
```

---

## 5 与之前方案的对比（为什么不做）

| 之前考虑的 | 为什么不做 |
|-----------|-----------|
| Circuit Breaker 熔断器 | 内部工具一次运行几十次调用，熔断器省不了资源但增加有状态组件 |
| 自动级联降级（pro→flash→正则） | 静默降级——用户不知道报告里哪些是 pro 出的哪些是正则出的 |
| 多 provider failover | 只有 DeepSeek 一个供应商，且 prompt 已针对调优 |
| 模板修复器（TEMPLATE_FIXERS） | format_fixer 已做确定性修复，语义修复用模板可能产生错误 diff |
| LangGraph RetryPolicy | SDK 内置 `max_retries` 已够用，框架级容错不需要 |

---

## 6 实施计划

### Phase 1：基础韧性（当前）

| # | 改动 | 文件 |
|---|------|------|
| 1 | `ChatOpenAI` 加 `max_retries=2` + `timeout=180/120` | `config.py` |
| 2 | 添加 `DEGRADATION_MODE` 环境变量 + `offline_mode` | `config.py`, `state.py` |
| 3 | `_degradable()` wrapper：catch 异常 + 记录降级事件 | `graph.py` |
| 4 | Per-chunk 故障隔离（cpp/qt/sqlite agent） | 3 个 agent 文件 |
| 5 | git_agent 纯正则本地 fallback | `agent_git.py` |
| 6 | report_merger 异常触发 `_fallback_dedup` | `report_merger.py` |
| 7 | review_agent 安全门禁（失败→unreviewed） | `agent_review.py` |
| 8 | fix_agent 添加 `degraded` 状态 | `agent_fix.py` |
| 9 | 报告降级可见性横幅 | `report_exporter.py` |
| 10 | `--offline` / `--strict` CLI 标志 | `main.py` |

### Phase 2：延迟恢复（后续）

| # | 改动 | 说明 |
|---|------|------|
| 11 | wiki_arbitration 延迟批处理 | `.cache/pending-arbitration/` 积压 → 批量处理 |
| 12 | 降级日志持久化 | JSONL 格式记录每次降级事件 |

---

*最后更新：2026-07-28*
