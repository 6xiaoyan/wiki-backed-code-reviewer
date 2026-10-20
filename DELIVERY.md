# 交付说明（第一阶段）

日期：2026-10-19
对应需求：[`docs/PR_REVIEW_PHASE1_PRD.md`](docs/PR_REVIEW_PHASE1_PRD.md)

## 1. 交付结论（先看这里）

**本地实现与自动化测试已完成；GitHub 端验收未完成。**

已完成：

- 独立的可公开目录已整理完毕（不含真实凭据、个人材料、旧 trace、缓存、构建产物）；
- PR diff 入口、固定 SHA 只读快照、范围与预算、确定性检查过滤、领域 Agent、
  证据核验、确定性合并、JSON/Markdown/评论渲染、发布门禁、CLI 与 LangGraph 图；
- 可信 Actions 工作流（`pull_request_target`、权限分离、同 PR 并发取消、artifact）；
- C++/Qt 示例与可复现的离线演示；
- 162 个新增测试全部通过（见 §3）。

本轮按审查意见修复了 4 类问题：

1. 领域 Agent 现在收到本领域可信 Wiki 的**规则正文**（受可信预算限制），
   模型必须逐字引用正文；证据核验先确认发现所属 Agent 领域，再只允许该领域
   本轮实际注入的 `rule_id` 与正文，最后核验引用确实出现在注入正文中；
2. 无效模型响应（空、畸形 JSON、类型错误）不再被当作“没有发现问题”，
   按重试策略处理，耗尽后标为 `incomplete`；
3. 超过单文件大小上限的适用代码文件改为**未覆盖 + `incomplete`**，
   不再当作普通排除项或降级为 `skipped`；
4. 关联头文件改为从固定 `head_sha` 的仓库树查找，未修改的同名
   `.h/.hpp/.hxx` 也会在上下文预算内读取。

未完成（需要用户侧权限/凭据，不能由本地代码替代）：

| 未完成项 | 精确缺口 |
|---|---|
| 在 `6xiaoyan` 下创建公开仓库并推送 | 当前环境没有 GitHub 登录态、`gh` CLI 或 `GITHUB_TOKEN`；未创建远端仓库 |
| Actions 真实运行证据 | 没有远端仓库，无法触发 `pull_request_target` |
| 演示 PR | 无法创建 PR / 保持 PR 打开 |
| 真实模型审查 | 没有 `DEEPSEEK_API_KEY`；LLM 路径只用测试替身验证 |
| Linux 干净环境安装验证 | 仅在 Windows + Python 3.14 上执行；依赖已固定，但未在 `ubuntu-24.04` 实跑 |
| Actions 固定到提交 SHA | 网络无法访问 `api.github.com` 校验 SHA；当前使用第一方 action 的版本标签（见 §6） |
| 截图 / 运行链接 / artifact 链接 | 不伪造；未产生 |

因此：**“GitHub 端已验收”不成立**，只能声明本地实现与测试完成。

## 2. 交付物

推荐仓库名：`wiki-backed-code-reviewer`（所有者 `6xiaoyan`，Public，默认分支 `main`）。

```text
.github/workflows/pr-review.yml     可信运行、权限分离、并发取消、artifact
code_checker/pr_review/             PR 模式实现（约 21 个模块）
code_checker/nodes/                 复用/适配的确定性检查与领域规则
code_checker/pr_review/rules.py     领域规则正文注入、来源与引用核验
code_checker/config.py              凭据改为环境变量；规则目录可配置
code_checker/tools.py               PR 模式工具权限硬约束
code_checker/state.py               PR 模式状态字段
code_checker/graph.py               新增 build_pr_review_graph()
code_checker/main.py                保留旧入口，新增 `pr` 子命令转发
code_checker/rules-wiki/            可信规则 Wiki（只读）
code_checker/agent-skills/live/     可信审查经验（只读）
examples/review-target/             C++/Qt/SQLite 示例（含一条故意的历史违规）
rules/                              审查所需规范文本（见 rules/SOURCES.md）
tests/                              新增 PR 接入测试（162 个）
scripts/demo_local.py               无需凭据的离线演示
docs/PR_REVIEW_PHASE1_PRD.md        需求原文
README.md / .env.example / .gitignore / requirements*.txt / pyproject.toml
```

关键模块职责：

| 模块 | 职责 |
|---|---|
| `pr_review/diff_parser.py` | 统一 diff 解析，新增/修改/删除/改名/二进制与行号映射 |
| `pr_review/snapshot.py` | Git 对象 / GitHub API 只读快照，截断与超大文件显式报错 |
| `pr_review/scope.py` | 适用性判断、排除项、文件数/变更行/单文件大小预算与未覆盖记录 |
| `pr_review/rules.py` | 按领域加载可信 Wiki 规则正文，执行单页/领域上限，保存本轮实际注入的 rule_id→正文 |
| `pr_review/deterministic_pr.py` | 复用现有正则规则，按改动关联性过滤历史问题，附带 Wiki 条款原文 |
| `pr_review/agents.py` | C++/Qt/SQLite 领域审查（注入本领域规则正文）、严格响应解析 + Git 确定性检查 |
| `pr_review/evidence.py` | 文件/行号/代码/领域与注入范围/规则正文引用/改动关联核验 |
| `pr_review/pipeline.py`、`stages.py`、`graph_pr.py` | 六阶段流水线与 LangGraph 图 |
| `pr_review/report.py`、`publisher.py` | 完整报告、汇总评论、发布门禁与消毒 |
| `pr_review/cli.py` | `analyze` / `publish` / `local`，状态与退出码 |
| `pr_review/models.py` | 状态机、预算、ReviewRequest/Result、review_key |

## 3. 本地验证证据

执行环境：Windows，Python 3.14.7，Git 2.55.0，LangGraph 1.2.16。
命令与结果均来自实际执行，可复现。

### 3.1 新增测试（默认测试集）

```text
$ python -m pytest
162 passed in 292.72s
```

覆盖：diff 解析（增/删/改名/二进制/多 hunk）、范围与预算、历史问题过滤、
模型证据核验、状态机、发布门禁（含伪造标记、head 变化、关闭 PR、评论消毒、
长度上限）、review_key、Git 客户端分页/429/鉴权、只读快照、工具权限、
工作流安全边界、端到端离线与多次提交、结构化请求文件、LangGraph 与顺序路径一致性，
以及本轮新增的规则正文注入/领域隔离/规则超限、无效模型响应与重试、
超大文件未覆盖语义、固定 SHA 关联头文件读取。

### 3.2 离线演示

```text
$ python scripts/demo_local.py
[配置] 降级模式: NORMAL
...
PR 审查: local/repository#0 head=15d318a6
状态: incomplete — 离线模式：只执行确定性检查，未执行完整 LLM 审查
已确认问题: 1；不确定候选: 0；已审查文件: 2/2
  - [critical] src/main.cpp:26 deterministic/check_tab_indentation — 第 26 行包含 Tab 字符
...
状态: incomplete
已确认问题:
  - [critical] src/main.cpp:26 deterministic/check_tab_indentation
已过滤（历史/无关）:
  - src/legacy.cpp:6 — 同一问题在改动前的版本中已存在（历史问题，不计为本次新增）
演示断言通过：新增 Tab 违规被报告，legacy.cpp 历史违规被过滤。
（退出码 0；内部 CLI 退出码为 2，符合 incomplete 语义）
```

### 3.3 旧入口离线兼容性

```text
$ python -m code_checker.main --offline examples/review-target
repo_scanner: 6 files
deterministic_checker: 1 violations, coverage OK
fix_agent / review_agent: offline 模式，跳过
report_exporter: 写出 compliance_report.md 与 fix_guide.md
总耗时: 72ms
退出码: 0
```

观察到的既有行为（本次未改变）：`--offline` 会跳过 `report_merger`，因此旧入口的
摘要显示“违规 0”，尽管确定性检查器已发现 1 条（示例中故意保留的历史 Tab）。
这是改动前就存在的离线路径行为；PR 模式不依赖该路径，已单独实现确定性结果合并。

### 3.4 原有测试基线

```text
$ python -m pytest code_checker/tests -q
8 failed, 93 passed
```

8 个失败在本次改动开始前的基线运行中即存在，与 PR 审查功能无关：

- `test_hardcoded_idx_guard.py`：6 个（`_check_idx_allowed` 相关夹具/全局状态）
- `test_l3_persistence.py`：2 个（大输出落盘路径）

### 3.5 本轮修复的专项验证

```text
$ python -m pytest tests/test_rules.py tests/test_evidence.py \
    tests/test_rules_injection.py tests/test_invalid_responses.py tests/test_status.py
66 passed in 187.81s

$ python -m pytest
162 passed in 292.72s
```

专项覆盖：

- `test_rules.py`：C++/Qt/SQLite 规则正文分离、单页/领域上限、未注入规则记录、
  本轮注入正文集合、引用只允许落在注入正文内；
- `test_evidence.py`：模型发现缺少 Agent 领域标记、引用其他领域规则、引用被预算
  排除的规则、引用页面中未注入段落均被拒绝；合法注入规则+正文可确认；
- `test_rules_injection.py`：模型提示词包含本领域规则正文、不含其他领域正文、
  超限后标 `incomplete` 且报告列出未注入规则、无规则正文时不调用模型；
  服务端覆盖模型伪造的 `_agent_domain`，其他领域/预算外规则不能进入正式报告；
- `test_invalid_responses.py`：空响应、畸形 JSON、顶层类型错误、合法 `[]`、
  合法发现数组、重试成功与重试耗尽后的整体状态；
- `test_scope.py`：大文件单独出现、与普通文件同时出现、恰好等于上限，
  以及唯一改动文件超限时整体状态必须是 `incomplete` 而非 `skipped`；
- `test_headers.py`：只改 `.cpp` 时读取未修改的同名头文件，路径/SHA 来自固定快照，
  预算失败/项目头文件缺失标 `incomplete`，角括号外部头文件缺失仅记录。

## 4. PRD §13 验收对照

| 场景 | 状态 | 证据 / 缺口 |
|---|---|---|
| 仓库公开发布 | ❌ 未完成 | 无 GitHub 凭据；目录已整理但未建仓/推送 |
| 干净 Linux 环境 | ⚠️ 部分 | 依赖已固定；仅在 Windows 验证，未在 Ubuntu 实跑 |
| PR 新建自动触发 | ❌ 未验证 | 工作流配置与发布逻辑有测试；无真实 Actions 运行 |
| 修改小 C++ 文件的输入范围 | ✅ 本地 | `test_scope.py`、`test_end_to_end.py`：只读改动文件，不预读全仓 |
| 引入稳定规则违规 | ✅ 本地 | 离线演示与端到端测试报告真实行号/代码/规则 |
| 保留无关历史违规 | ✅ 本地 | 演示与测试均验证过滤原因，不计入已确认问题 |
| 新增/删除/改名/多次提交 | ✅ 本地 | `test_diff_parser.py`、`test_end_to_end.py`（第二次 push 覆盖整个 PR） |
| 连续推送 A、B 两版 | ⚠️ 部分 | 并发组配置已测试；`superseded` 有单元测试；无真实取消运行 |
| 重跑同一 PR 更新评论 | ✅ 本地 | `test_publish.py`：更新同一条机器人评论，忽略用户伪造标记 |
| 无适用文件/草稿跳过 | ✅ 本地 | `test_status.py`、`test_scope.py`：不调用模型，不宣称通过 |
| API 超时/429/缺凭据 | ✅ 本地 | Git 客户端重试测试；缺凭据 → `failed`；模型失败 → `incomplete` |
| 模型返回空/畸形/类型错误 | ✅ 本地 | `test_invalid_responses.py`：重试耗尽后 `incomplete`，合法 `[]` 才可 `completed` |
| 规则正文注入与领域隔离 | ✅ 本地 | 每条发现带服务端领域标记；只接受该领域本轮实际注入的 `rule_id` 与正文，其他领域/预算外规则不进入正式报告（`test_rules.py`、`test_evidence.py`、`test_rules_injection.py`） |
| 规则正文超出注入预算 | ✅ 本地 | 记录未注入规则、报告列出、结果标 `incomplete`，未注入规则不可被引用确认 |
| 超预算/差异不完整 | ✅ 本地 | 文件数、变更行、单文件大小（含恰好等于上限）、compare/tree 截断均有测试 |
| 只改 `.cpp` 时读取关联头文件 | ✅ 本地 | `test_headers.py`：从固定 `head_sha` 树查找并记录路径/范围/SHA |
| fork PR 改脚本/依赖/工作流 | ⚠️ 部分 | 信任边界与工作流测试；无真实 fork 运行 |
| fork PR 诱导执行命令 | ✅ 本地 | `test_tool_guard.py`：PR 模式无 shell/发布工具，调用被拒绝 |
| PR 关闭/发布前新 head | ✅ 本地 | `test_publish.py`：`superseded`，不写评论 |
| 规则/skill/提示词修改 | ✅ 本地 | 配置类改动标为 `skipped`/配置候选；摘要写入 ReviewRequest |
| analyze/publish 隔离 | ✅ 本地 | `test_workflow.py`：analyze 无写权限、publish 无模型 Secret |
| 本地旧入口兼容 | ⚠️ 部分 | 离线入口实跑成功；8 个历史基线失败与本次无关 |

## 5. 安全整改（必须由有权限者完成）

1. **撤销并轮换旧 Key。** 原 `code_checker/config.py` 曾硬编码一个真实的
   DeepSeek API Key。本次已把它改为只从 `DEEPSEEK_API_KEY` / `OPENAI_API_KEY`
   环境变量读取，并且没有把该值复制到本目录、文档、测试或提交中。
   但该 Key 曾在本地源码中存在，应按已泄露处理：登录模型服务商控制台撤销旧 Key，
   生成新 Key，只配置到 GitHub Secrets（不要写入文件）。
2. **创建仓库并推送**（见 §7），确认仓库历史中没有 `.env`、缓存、个人材料。
3. **配置 Secret** `DEEPSEEK_API_KEY`，不要把 Key 写进 workflow、README 或 PR。
4. 如需调整仓库名/所有者，修改 README 与工作流中的仓库引用即可（工作流使用
   `GITHUB_REPOSITORY`，无需硬编码）。

本目录已检查：`config.py`、`pr_review/*`、工作流、`.env.example`、示例中
未发现 `sk-` / `ghp_` / `github_pat_` / `AKIA` 形式的凭据；机器相关绝对路径仅在
测试的临时目录中使用，不在运行代码中。

## 6. 未完成项与精确缺口

1. **远端仓库 / Actions / 演示 PR**：执行环境无 GitHub 登录态、`gh` 未安装、
   无 `GITHUB_TOKEN`。因此没有仓库 URL、实现提交链接、Actions 运行链接、artifact 链接，
   也没有保持打开的演示 PR。不得用本地结果冒充线上验收。
2. **真实模型调用**：无 `DEEPSEEK_API_KEY`。所有模型路径使用测试替身验证了
   规则正文注入、严格响应解析、计数、重试、失败状态与证据核验；真实模型
   是否稳定逐字引用 `rule_quote`、规则正文体积对时延/token 的实际影响，
   仍需线上试跑确认。
3. **Action 版本固定**：PRD 要求第三方 Actions 固定到已核实提交 SHA。当前工作流只使用
   第一方 action（`actions/checkout@v4`、`actions/setup-python@v5`、
   `actions/upload-artifact@v4`、`actions/download-artifact@v4`），没有引入第三方
   action；但版本标签尚未替换成提交 SHA，因为执行环境无法访问 GitHub API 校验 SHA。
   完成方式：
   ```bash
   gh api repos/actions/checkout/git/ref/tags/v4.2.2 --jq .object.sha
   gh api repos/actions/setup-python/git/ref/tags/v5.3.0 --jq .object.sha
   gh api repos/actions/upload-artifact/git/ref/tags/v4.4.3 --jq .object.sha
   gh api repos/actions/download-artifact/git/ref/tags/v4.1.8 --jq .object.sha
   # 校验后把 uses: actions/xxx@vN 改为 uses: actions/xxx@<40位SHA>  # vX.Y.Z
   ```
4. **Linux 干净环境**：`requirements.txt` 已固定本地验证过的版本；建议在
   `ubuntu-24.04` + Python 3.12 上先跑 `python -m pytest` 再触发工作流。
5. **真实 PR 演示**：按 §7 完成后，修改 `examples/review-target/src/main.cpp`
   （加入 Tab 缩进）创建 PR；再推送一次修复或新改动，确认评论被更新而不是重复创建。

## 7. 下一步操作清单（用户侧）

```bash
# 1) 在本地目录初始化并推送（目录已预置 .gitignore）
cd wiki-backed-code-reviewer
git init -b main
git add -A
git commit -m "feat: phase 1 PR reviewer"
gh repo create 6xiaoyan/wiki-backed-code-reviewer --public --source=. --push
#    若 gh 未登录：gh auth login

# 2) 配置模型 Secret（值只在本地输入，不写入文件）
gh secret set DEEPSEEK_API_KEY --repo 6xiaoyan/wiki-backed-code-reviewer

# 3) 创建演示 PR（示例仓库内的最小改动）
git checkout -b demo/tab-violation
# 编辑 examples/review-target/src/main.cpp，加入一个 Tab 缩进的函数
git commit -am "feat: add demo helper"
git push -u origin demo/tab-violation
gh pr create --fill --base main

# 4) 观察
gh run list --repo 6xiaoyan/wiki-backed-code-reviewer
gh pr view --web
```

验收时请保留演示 PR 打开状态，不自动合并。

## 8. 已知限制

- 只审查 PR diff 覆盖的改动，不做完整跨文件数据流分析。
- 文档、二进制、生成文件、第三方目录与不支持类型会被排除并列出原因。
- 超过单文件大小上限的适用代码文件属于“未覆盖”：结果标 `incomplete`，
  不会退化成 `skipped`，也不会在有其他已审文件时假装完成。
- 领域 Agent 只注入本领域规则正文；默认上限为单领域 64 KiB、单页 4 KiB。
  超限规则会列在运行记录与完整报告中，结果标 `incomplete`。
- 模型发现必须给出可核验的 `rule_quote`，且引用必须落在该领域本轮实际注入的
  规则正文中；缺失、跨领域、预算外或页面其他章节的文字都会进入
  `uncertain_findings`，因此真实模型可能比旧实现产生更多“不确定候选”。
- 规则正文注入会增加单次提示词体积；模型请求总数仍受 40 次统一预算限制。
- 修复建议均为建议，未执行验证；不会自动修改、提交或合并代码。
- 模型语义结果可能波动；稳定性由确定性规则、证据核验与状态区分保障。
- `code_checker/tests` 的 8 个历史失败未修复（不属于本阶段范围）。
- 原工作区中的其他项目、个人文档、简历、旧报告与缓存均未复制到本目录。
