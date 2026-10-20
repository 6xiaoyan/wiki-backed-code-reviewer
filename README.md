# wiki-backed-code-reviewer

基于 LangGraph 的 PR 代码审查器：以 PR diff 为入口，用确定性检查 + Wiki 规则辅助的
领域 Agent 审查 C++ / Qt / SQLite / Git 改动，并把一条汇总报告写回 Pull Request。

> 第一阶段实现。范围、验收条件与不做的内容见
> [`docs/PR_REVIEW_PHASE1_PRD.md`](docs/PR_REVIEW_PHASE1_PRD.md)。
> 当前交付状态、已验证项与未完成项见 [`DELIVERY.md`](DELIVERY.md)。

## 它做什么

```text
PR opened / synchronize / reopened / ready_for_review
        │
GitHub Actions（pull_request_target，可信基分支代码）
        │
  analyze job（只读 + 模型 Secret）
    ├─ 固定 base/head/merge-base 三个 SHA
    ├─ 只读取 merge_base → head 的 diff（不检出、不执行 PR 代码）
    ├─ 确定性正则检查（零 token）→ 过滤历史问题
    ├─ C++ / Qt / SQLite 领域 Agent（本领域 Wiki 规则正文 + 结构化 JSON + 统一预算）
    ├─ Git 提交规范（只看 PR 范围内的提交）
    ├─ 证据核验（文件/行号/代码/规则正文引用/改动关联性）
    └─ 导出 review-result.json / review-report.md / pr-comment.md
        │
  publish job（无模型凭据，仅 pull-requests: write）
    ├─ 校验 schema、大小、仓库、PR、head、run 一致性
    ├─ 重新读取 PR：head 变化或已关闭 → superseded，不写评论
    └─ 创建或更新唯一一条机器人汇总评论
```

## 安全边界（请先读）

- 工作流使用 `pull_request_target`：工作流、审查程序、依赖、Wiki、skill、预算
  全部来自**可信基分支提交**。
- PR head 只作为 Git 对象抓取，使用 `git cat-file` / `ls-tree` / `diff` 读取；
  **不创建 PR head 工作树，不执行 PR 中的安装、构建、测试、hook 或脚本**。
- `analyze` 只有 `contents: read`、`pull-requests: read`，并持有模型 Secret；
  `publish` 只有 `pull-requests: write`，**不持有模型 Secret**，只校验产物并发布。
- PR 模式工具面仅限读取固定快照、搜索代码、查询可信 Wiki、提交结构化问题；
  shell / 全仓 `git log` / 修复 / 规则写入 / GitHub 发布接口在 PR 模式被拒绝。
- 模型输出一律作为数据解析；评论中的 `@提醒`、HTML 注释、反引号会被中和，
  评论长度受限且始终写明被审查的 head SHA。

## 规则正文与证据

- 每个领域 Agent 只收到**本领域**的可信 Wiki 规则正文：C++ 含腾讯安全副规则，
  Qt / SQLite 各自独立，不会混入其他领域。
- 规则正文来自可信提交中的 `code_checker/rules-wiki/`，不是 PR 分支内容。
  注入受可信预算限制（默认单领域 64 KiB、单页 4 KiB）；超限规则不会被静默丢弃，
  而是记录到运行记录的 `rule_coverage`，并把结果标为 `incomplete`。
- 模型每条问题必须用 `rule_quote` 逐字引用注入的规则正文；引用缺失或与页面不匹配时，
  该候选进入 `uncertain_findings`，不计入已确认问题。
- 每条模型发现由服务端标记所属 Agent 领域。证据核验只接受**该领域本轮实际注入**的
  `rule_id` 和正文：其他领域的规则、被预算排除的规则、以及页面中未注入的段落
  都会被拒绝，不会进入已确认问题。
- 确定性检查发现会直接附带对应 Wiki 条款原文；报告同时展示规则 ID、标题、
  引用正文和来源（`source_file` / `source_section`）。
- 只修改 `.cpp` 时，同目录同名 `.h/.hpp/.hxx` 会从固定 `head_sha` 的仓库树中查找，
  在上下文预算内读取前 120 行并记录路径/范围/SHA；项目头文件缺失或读取失败会标为
  `incomplete`，角括号外部头文件缺失只记录在运行记录中。
- 非法模型响应（空响应、畸形 JSON、顶层类型错误、数组元素不是对象）不等同于
  “没有发现问题”：会按重试策略重试，耗尽后结果标为 `incomplete`。

## 本地快速开始

需要 Python 3.10+（CI 使用 3.12）与 Git。

```bash
python -m pip install -r requirements-dev.txt

# 不需要模型凭据：在示例上跑一次离线审查（演示 diff 范围与历史问题过滤）
python scripts/demo_local.py
```

离线演示的预期结果：

- 退出码 `2`，状态 `incomplete`（离线只跑确定性检查，不冒充完整 LLM 审查）；
- `src/main.cpp` 新增的 Tab 缩进行被报告为本次新增问题；
- `src/legacy.cpp` 未改动的历史 Tab 缩进被过滤，不计入本次新增；
- 在临时目录生成 `review-result.json`、`review-report.md`、`pr-comment.md`。

### 直接使用入口

```bash
# 新 PR 入口（analyze / publish / local）
python -m code_checker.pr_review analyze --repo owner/repo --pr 12 \
    --repo-path . --output-dir review-artifacts
python -m code_checker.pr_review publish --repo owner/repo --pr 12 \
    --result review-artifacts/review-result.json --dry-run
python -m code_checker.pr_review local --repo-path /path/to/repo \
    --base main --head feature --offline

# 也可以传入结构化请求对象（文件或 stdin），避免领域 Agent 依赖 Actions 环境变量
python -m code_checker.pr_review analyze --request-file request.json \
    --repo-path . --output-dir review-artifacts
cat request.json | python -m code_checker.pr_review analyze --request-file - \
    --repo-path . --output-dir review-artifacts

# 旧入口保留；也可通过 `main pr ...` 转发到新入口
python -m code_checker.main --offline /path/to/repo
python -m code_checker.main pr local --repo-path /path/to/repo --base main --head feature --offline
```

在线审查需要 `DEEPSEEK_API_KEY`；缺少凭据时 `analyze` 会以 `failed` 明确报错，
不会产出“零问题通过”。

## 在 GitHub 上启用

1. 在 `6xiaoyan` 账号下创建公开仓库（建议名 `wiki-backed-code-reviewer`），
   推送本目录的初始提交；
2. 仓库 **Settings → Secrets and variables → Actions** 添加
   `DEEPSEEK_API_KEY`（只放在 Secret，不写入文件）；
3. 确认 **Settings → Actions → General → Workflow permissions** 允许工作流
   使用只读默认权限（工作流内已按 job 收窄）；
4. 修改示例或任意 C++ 文件，创建非草稿 PR；
5. 在 PR 中查看机器人汇总评论；也可在 Actions 页面
   `PR Review → Run workflow` 输入 PR 号手动重审。

> 仓库首次启用前请先阅读 [`DELIVERY.md`](DELIVERY.md) 的“未完成项”：
> 由于执行环境没有 GitHub 登录态与模型凭据，远端仓库、真实 PR 运行与
> Actions 证据尚未产生。

## 触发与状态

| 事件 | 行为 |
|---|---|
| 新建非草稿 PR / 推送提交 / 重新打开 / 转为可审查 | 审查整个 `merge_base → head` 范围 |
| 草稿 PR | 跳过，不调用模型，评论说明原因 |
| 手动 `workflow_dispatch` | 读取当前 PR，使用可信基分支程序重审 |
| PR 已关闭/合并 | 新任务不调用模型；发布前再次检查 |
| 同一 PR 连续推送 | 同一 concurrency group，旧任务取消；发布前再校验 head |

状态语义：

| 状态 | 含义 | 退出码 |
|---|---|---|
| `completed` | 所有必要阶段完成（有问题也算完成） | 0 |
| `skipped` | 草稿/无适用改动等，不宣称检查通过 | 0 |
| `incomplete` | 预算耗尽、部分读取失败、必要 Agent 未完成 | 2 |
| `failed` | 缺配置、鉴权失败、无法准备 diff | 1 |
| `superseded` | 发布前发现新 head 或 PR 已关闭，不更新评论 | 0 |

## 预算（可信配置，PR 作者不可提高）

| 限制 | 默认值 |
|---|---|
| 单 PR 适用变更文件 | 50 个 |
| 适用文件新增+删除行合计 | 3,000 行 |
| 单个可读取文本文件 | 256 KiB（超限记为未覆盖并标 `incomplete`） |
| 额外上下文累计读取量 | 2 MiB（按路径/版本/范围去重计量） |
| 单领域规则正文注入量 | 64 KiB |
| 单页规则正文注入量 | 4 KiB |
| 单轮模型请求总数 | 40 次（所有 Agent 与重试共同计数） |
| 审查阶段时限 | 15 分钟 |
| Actions 工作流总时限 | 20 分钟 |
| 模型瞬时错误重试 | 每次调用最多 2 次 |
| 运行交付物保留 | 14 天 |

超限会明确标为 `incomplete` 并列出未覆盖文件，不会静默只审查前若干文件。
预算可通过可信环境变量 `CODE_REVIEW_BUDGET`（JSON）调整，见 `.env.example`。

## 目录结构

```text
.github/workflows/pr-review.yml   # 可信运行、权限分离、并发取消、artifact
code_checker/                     # 审查程序（保留原包名）
  pr_review/                      # PR 入口：diff/快照/范围/证据/报告/发布/CLI
  nodes/                          # 领域 Agent、确定性检查、合并、导出
  rules-wiki/                     # 可信规则 Wiki（只读）
  agent-skills/live/              # 可信审查经验（只读）
  tests/                          # 原有测试（历史基线）
examples/review-target/           # 小型 C++/Qt 示例（含一条故意的历史违规）
rules/                            # 审查用规范文本（见 rules/SOURCES.md）
tests/                            # 新增 PR 接入测试（默认测试集）
docs/                             # 第一阶段 PRD
scripts/demo_local.py             # 离线演示脚本
```

## 测试

```bash
python -m pytest            # 新增 PR 接入测试（默认，当前 162 个）
python -m pytest tests -q
python -m pytest code_checker/tests -q   # 原有测试；存在 8 个历史失败
```

新增测试覆盖规则正文注入与领域隔离、规则超限报告、无效模型响应与重试、
超大文件未覆盖语义、关联头文件从固定快照读取等行为。

`code_checker/tests` 中存在 8 个在本次改动之前就已失败的测试
（`test_hardcoded_idx_guard.py` 6 个、`test_l3_persistence.py` 2 个），
与 PR 审查功能无关，详见 [`DELIVERY.md`](DELIVERY.md)。

## 第一阶段不做

自动修复/提交/合并、GitHub App、常驻服务、Redis/数据库任务队列、
行内评论与跨轮问题身份、增量缓存复用、Wiki CI / RSI 改进循环、GitLab。
审查建议均为**建议，未执行验证**；报告不代表代码已修复或构建测试已通过。

## 规则与第三方来源

`code_checker/rules-wiki/` 保留原有规则页面与来源说明；`rules/` 只包含完成审查
所需的规范文本。Google / Qt / Tencent 指南的全文没有复制到本仓库。
本仓库不擅自为第三方内容附加许可证，详见 [`rules/SOURCES.md`](rules/SOURCES.md)。
