# PyGoat baseline 材料

本目录记录材料版本与 token 统计，不包含模型审查结果，也没有修改审查器主流程。

## 本地文件

第三方材料保存在项目 checkout 之外：

```text
D:/ai_share/langgraph/benchmark-data/pygoat-baseline/
├── targets/pygoat/       # 保留上游原貌的目标代码仓库
├── judge/realvuln/       # RealVuln 自动判分器、配置、标准答案及配套文档
├── rules/
│   ├── core/            # 腾讯 Python 安全、Django 4.2 安全/部署、OWASP Django 安全
│   ├── supplemental/    # OWASP SQL 注入、XSS、SSRF、反序列化、授权
│   └── optional-style/  # Google Python Style Guide、PEP 8；不纳入安全组默认输入
└── metadata/            # 材料来源、提交与 SHA-256
```

目标版本：`2fb0c600245f50670e8b9233c784afe61e8b340b`。
判分器版本：`90c3221a83e44242b7b67555094349107c21283f`。
标准答案包含 78 条漏洞和 10 条容易误报的合规案例。
PyGoat 的 `requirements.txt` 固定了 Django 4.2，故 Django 文档下载自对应版本的官方仓库。

RealVuln 使用稀疏 checkout，已下载判分入口、`scorer/`、`parsers/`、`config/`、PyGoat 标准答案、测试与配套文档；没有下载其他目标应用或所有扫描器历史结果。判分器按文件、CWE 漏洞类别及行号容差匹配，源码位于 `judge/realvuln/score.py` 和 `judge/realvuln/scorer/`。

## 统计结果

- [分类与组合统计](token-report.md)
- [完整统计 JSON](token-report.json)
- [逐文件计数、分类和内容哈希](token-inventory.csv)
- [来源与版本清单](assets.lock.json)

统计使用 `tiktoken` 的 `o200k_base` 和 `cl100k_base`，逐文件编码后求和；它们是比较口径，并非已经核实的全部待测模型专用 tokenizer。不计 Git 内部文件、二进制文件、对话封装、提示词、工具定义、模型输出或图像 token。

`Python + HTML 模板 + 核心安全规范` 为 **126,000 o200k_base token**；即使包含全部目标文本和 11 份规范，也只有 **293,358 token**。判分代码和答案的 token 不应计入审查模型输入。

## 正式实验前尚需处理的输入边界

原仓库包含 `Solutions/solution.md`、教学说明模板和讨论页面，可能提示漏洞或解法。当前下载保持原貌，没有声称这些材料是无答案泄漏的输入。后续需固定两组一致的文件范围和访问限制；不能仅靠提示词假定 Agent 无法读取答案。目标源码中的固有教学特征也需要在结论中说明。

标准答案与判分器虽然保存在目标 checkout 之外，但目录分离不等于已实施权限隔离。当前未创建沙箱、未运行 PyGoat、未安装其依赖，也未调用模型。

腾讯和 OWASP 的原始条款含有版本或场景限定。下载完成不表示已经将所有条款确认为本轮有效判分要求；新增规范要求也不会自动获得 RealVuln 的标签覆盖。

## 重新统计

在本项目根目录运行，依赖 `requests`、`tiktoken` 和 Git：

```powershell
python scripts/prepare_pygoat_materials.py --count-only
```

不加 `--count-only` 会校验/准备固定的代码仓库，并重新下载规范；规范来源分支会重新解析为提交，产生新的来源快照。已有实验应保留原 `assets.lock.json`，避免将不同规范快照的结果混用。

所有原始文档保留来源及 SHA-256，见清单中的 `documents`。上游代码、文档及标准答案继续适用各自许可证。
