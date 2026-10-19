"""
wiki_arbitration — 跑后 Wiki 仲裁模块。

在 pipeline 完成后，用 flash 模型审视违规结果和矛盾候选，
决定 wiki 规则需要如何修改，生成人工审核报告。

设计原则：
  - 运行时 wiki 保持干净（无 conflicts_with / overrides 标注）
  - 跑完后由仲裁模型集中审视所有违规和矛盾，裁决规则变更
  - 规则冲突通过修改/删除/合并规则来解决，而非标注冲突元数据
  - 所有变更写入报告文件，人工审核后方可应用
"""

import os
import json
import datetime
import hashlib
from typing import Optional

from langchain_core.messages import HumanMessage
from code_checker.config import llm
from code_checker.wiki_search import _init_index, _WIKI_DIR

# ── 路径 ──
_ARBITRATION_REPORT_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), ".cache", "wiki-arbitration-report.md",
)
_CONTRADICTIONS_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "rules-wiki", "CONTRADICTIONS.md",
)

ARBITRATION_SYSTEM_PROMPT = """你是代码规范系统管理员。你负责维护一套公司 C++ / Qt 代码规范 wiki。

你的核心职责：审视代码审查 pipeline 跑出的违规结果和矛盾候选，决定 wiki 规则如何修改。

## 工作流程

你会收到以下输入：
1. **本轮违规清单** — checker agent 发现的所有违规（含代码、规则、行号、严重度）
2. **矛盾候选** — review_agent 标记的潜在规范冲突（[CONTRADICTION-CANDIDATE]）
3. **已知矛盾表** — CONTRADICTIONS.md 中已记录的历史矛盾
4. **当前 Wiki 规则** — 所有规则页面的完整内容

你的任务：
1. 逐条审视矛盾候选：是真实规范冲突还是 false alarm？
2. 审视违规清单：是否有规则本身有问题（过严、过宽、与另一规则冲突）？
3. 决定每个需要处理的规则采取什么行动
4. 生成具体的 wiki 修改方案

## 可选行动

对每条需要处理的规则，选择以下行动之一：

| 行动 | 含义 | 示例 |
|------|------|------|
| **MODIFY** | 修改规则条款，增加例外说明或缩小适用范围 | 禁止裸 new 规则增加 "Qt 父子模型除外" |
| **DELETE** | 删除该规则页面（规则本身错误、过时、或被其他规则覆盖） | 删除与另一规则完全矛盾的页面 |
| **MERGE** | 合并两条规则为一个，消除重叠和矛盾 | 两条规则描述同一件事，合并 |
| **SPLIT** | 将一条过大的规则拆分为多条 | 规则太宽泛，拆成具体场景 |
| **NO_CHANGE** | 规则没有问题，不需要修改 | 违规是真实代码问题，与规则无关 |

## 判断原则

1. **规则应该清晰、无歧义、不自相矛盾**
2. **当两条规则冲突时，裁决哪条真正代表最佳实践**
3. **不要通过标注冲突来回避问题——直接修改规则解决冲突**
4. **宁可规则少而精，不要多而矛盾**
5. **如果违规是真实代码问题（不是规则冲突导致的），规则不需要改**
6. **如果违规反复出现且总是被驳回（false positive），说明规则需要收窄**

## 输出格式

请按以下结构输出仲裁报告：

```markdown
# Wiki 仲裁报告

**Run**: {run_id}
**日期**: {date}
**仓库**: {repo_path}

## 摘要

- 总违规: N 条
- 矛盾候选: N 条（新 N, 已知 N）
- 需修改规则: N 条
- 无需变更: N 条

---

## 逐条分析

### 候选 #1: <描述>

- **判定**: CONFIRMED（真实冲突）/ FALSE_ALARM（非冲突）/ KNOWN（已知矛盾，已在 CONTRADICTIONS.md 中记录）
- **分析**: <为什么这样判定>
- **行动**: MODIFY / DELETE / MERGE / NO_CHANGE
- **涉及页面**: <wiki 页面 slug>

### 候选 #2: ...

---

## 建议的 Wiki 变更

### 变更 #1: MODIFY cpp/no-bare-new-delete.md

**理由**: ...

**具体修改**:
- **位置**: 「规则条款」段落末尾
- **操作**: 在段落末尾增加
- **新增文本**:
  ```
  **Qt 例外**：...
  ```

### 变更 #2: ...

---

## 已知矛盾更新

（如有需要更新 CONTRADICTIONS.md 状态的操作）
```

## 重要提示

- 不要输出虚构的违规或矛盾
- 只基于实际输入做判断
- 修改建议要具体到能在 wiki 页面中定位到段落
- 如果某条违规明显是 checker agent 幻觉（声称的代码不存在），不要基于它修改规则
- 真正的冲突需要通过修改规则来解决，而非标注 conflict_with 回避
"""


def run_wiki_arbitration(result: dict, run_id: str) -> dict:
    """运行 wiki 仲裁分析。

    在 pipeline 完成后调用。使用 flash 模型审视所有违规和矛盾候选，
    生成规则修改建议报告。

    Args:
        result: pipeline 的返回结果（包含 violations, fix_plans 等）
        run_id: 本次 run 的标识

    Returns:
        {
            "report_path": str | None,   # 报告文件路径
            "changes_proposed": int,      # 建议的 wiki 变更数
            "contradictions_confirmed": int,  # 确认为真实冲突的候选数
            "contradictions_false_alarm": int,  # 判定为非冲突的候选数
        }
    """
    from code_checker.tools import get_contradiction_candidates

    candidates = get_contradiction_candidates()
    violations = result.get("merged_violations") or []
    fix_plans = result.get("fix_plans") or []
    repo_path = result.get("repo_path", "?")

    # ── 如果没有违规也没有候选，跳过 ──
    if not violations and not candidates:
        print("[wiki_arbitration] 无违规无候选，跳过")
        return {
            "report_path": None,
            "changes_proposed": 0,
            "contradictions_confirmed": 0,
            "contradictions_false_alarm": 0,
        }

    # ── 加载已知矛盾表 ──
    known_contradictions = ""
    if os.path.exists(_CONTRADICTIONS_PATH):
        try:
            with open(_CONTRADICTIONS_PATH, "r", encoding="utf-8") as f:
                known_contradictions = f.read()
        except Exception:
            pass

    # ── 加载所有 wiki 页面（摘要，非全文——全文过长）──
    idx = _init_index()
    wiki_summaries = _build_wiki_summary(idx)

    # ── 构建违规摘要 ──
    violations_text = _build_violations_text(violations, fix_plans)

    # ── 构建矛盾候选文本 ──
    candidates_text = _build_candidates_text(candidates, fix_plans)

    # ── 如果内容为空，跳过 ──
    if not violations_text.strip() and not candidates_text.strip():
        print("[wiki_arbitration] 无有效违规和候选内容，跳过")
        return {
            "report_path": None,
            "changes_proposed": 0,
            "contradictions_confirmed": 0,
            "contradictions_false_alarm": 0,
        }

    # ── 调用 pro 模型进行仲裁 ──
    date_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    user_prompt = f"""请对以下代码审查 run 进行 wiki 规则仲裁。

**Run**: {run_id}
**日期**: {date_str}
**仓库**: {repo_path}

---

## 本轮违规清单

{violations_text if violations_text.strip() else "（本轮无违规）"}

---

## 矛盾候选

{candidates_text if candidates_text.strip() else "（本轮无矛盾候选）"}

---

## 已知矛盾表

{known_contradictions[:8000] if known_contradictions else "（无已知矛盾记录）"}

---

## 当前 Wiki 规则摘要

{wiki_summaries}

---

请按系统提示中的输出格式生成仲裁报告。"""

    print("[wiki_arbitration] 正在用 pro 模型分析 wiki 规则一致性...")
    try:
        response = llm.invoke([HumanMessage(content=user_prompt)])
        report_content = response.content.strip()
    except Exception as e:
        print(f"[wiki_arbitration] 模型调用失败: {e}")
        return {
            "report_path": None,
            "changes_proposed": 0,
            "contradictions_confirmed": 0,
            "contradictions_false_alarm": 0,
        }

    # ── 写入报告文件 ──
    os.makedirs(os.path.dirname(_ARBITRATION_REPORT_PATH), exist_ok=True)
    # 如果报告已存在，追加序号
    report_path = _ARBITRATION_REPORT_PATH
    if os.path.exists(report_path):
        base = _ARBITRATION_REPORT_PATH[:-3]  # strip .md
        counter = 1
        while os.path.exists(f"{base}-{counter}.md"):
            counter += 1
        report_path = f"{base}-{counter}.md"

    try:
        with open(report_path, "w", encoding="utf-8") as f:
            f.write(report_content)
        print(f"[wiki_arbitration] 报告已写入: {report_path}")
    except OSError as e:
        print(f"[wiki_arbitration] 写入报告失败: {e}")
        return {
            "report_path": None,
            "changes_proposed": 0,
            "contradictions_confirmed": 0,
            "contradictions_false_alarm": 0,
        }

    # ── 从报告中提取统计 ──
    changes_proposed = report_content.count("### 变更 #")
    contradictions_confirmed = report_content.count("CONFIRMED")
    contradictions_false_alarm = report_content.count("FALSE_ALARM")

    return {
        "report_path": report_path,
        "changes_proposed": changes_proposed,
        "contradictions_confirmed": contradictions_confirmed,
        "contradictions_false_alarm": contradictions_false_alarm,
    }


def _build_wiki_summary(idx: dict[str, dict]) -> str:
    """构建 wiki 页面摘要文本。

    每条规则包含：slug, title, domain, 规则条款段落（核心内容），
    检查方法，修复指南（摘要）。
    """
    lines = []
    # 按 domain 分组
    domains: dict[str, list[dict]] = {}
    for slug, page in idx.items():
        d = page["domain"]
        if d not in domains:
            domains[d] = []
        domains[d].append(page)

    for domain in sorted(domains):
        lines.append(f"### {domain} ({len(domains[domain])} 页)")
        lines.append("")
        for page in domains[domain]:
            slug = page["slug"]
            title = page["title"]
            content = page["content"]

            # 提取规则条款段落（## 规则条款 之后的内容，到下一个 ## 之前）
            rule_clause = _extract_section(content, "规则条款", max_chars=800)
            check_method = _extract_section(content, "检查方法", max_chars=400)
            fix_guide = _extract_section(content, "修复指南", max_chars=300)

            lines.append(f"#### [{slug}] {title}")
            lines.append("")
            if rule_clause:
                lines.append(f"**规则条款**: {rule_clause}")
            if check_method:
                lines.append(f"**检查方法**: {check_method}")
            if fix_guide:
                lines.append(f"**修复指南**: {fix_guide}")
            lines.append("")
        lines.append("")

    total = sum(len(pages) for pages in domains.values())
    header = f"共 {total} 条规则，{len(domains)} 个域\n\n"
    return header + "\n".join(lines)


def _extract_section(content: str, section_name: str, max_chars: int = 800) -> str:
    """从 markdown 内容中提取指定章节的文本。

    匹配 `## 章节名` 或 `## 章节名\n` 之后的段落，到下一个 `## ` 或文件末尾。
    """
    import re

    # 匹配 "## 章节名" 标题（可能有额外的空格或标点）
    pattern = re.compile(rf"^##\s+{re.escape(section_name)}.*$", re.MULTILINE | re.IGNORECASE)
    m = pattern.search(content)
    if not m:
        return ""

    start = m.end()
    # 找到下一个 ## 标题
    next_section = re.search(r"^##\s+", content[start:], re.MULTILINE)
    if next_section:
        end = start + next_section.start()
    else:
        end = len(content)

    text = content[start:end].strip()
    # 去掉 frontmatter 残留和多余空行
    text = re.sub(r"\n{3,}", "\n\n", text)
    if len(text) > max_chars:
        text = text[:max_chars] + "…"
    return text


def _build_violations_text(violations: list[dict], fix_plans: list[dict]) -> str:
    """构建违规清单的文本摘要。"""
    if not violations:
        return ""

    lines = []
    for i, v in enumerate(violations):
        if v is None:
            continue
        rule = v.get("rule", "未知规则")
        severity = v.get("severity", "?")
        file_path = v.get("file", "?")
        line = v.get("line", 0)
        current = (v.get("current") or "")[:300]
        expected = (v.get("expected") or "")[:300]
        reason = (v.get("reason") or "")[:300]

        # 获取对应 fix_plan 的审查结果
        review_info = ""
        if i < len(fix_plans) and fix_plans[i] is not None:
            fp = fix_plans[i]
            status = fp.get("fix_status", "?")
            feedback = (fp.get("feedback") or "")[:200]
            review_info = f"  - **审查结果**: {status}"
            if feedback:
                review_info += f" — {feedback}"

        lines.append(f"### 违规 #{i}: [{severity}] {rule}")
        lines.append(f"- **文件**: {file_path}:{line}")
        lines.append(f"- **当前代码**: `{current}`")
        lines.append(f"- **期望代码**: `{expected}`")
        lines.append(f"- **原因**: {reason}")
        if review_info:
            lines.append(review_info)
        lines.append("")

    return "\n".join(lines)


def _build_candidates_text(candidates: list[dict], fix_plans: list[dict]) -> str:
    """构建矛盾候选文本摘要。"""
    if not candidates:
        return ""

    lines = []
    for i, c in enumerate(candidates):
        desc = c.get("description", "?")
        idx = c.get("idx", -1)
        file_path = c.get("file", "?")
        line = c.get("line", 0)
        feedback = (c.get("feedback") or "")[:300]
        v = c.get("violation", {})

        lines.append(f"### 候选 #{i+1}")
        lines.append(f"- **描述**: {desc}")
        lines.append(f"- **位置**: {file_path}:{line} (fix_plan idx={idx})")
        lines.append(f"- **关联规则**: {v.get('rule', '?')}")
        lines.append(f"- **违规代码**: `{v.get('current', '?')[:200]}`")
        lines.append(f"- **修复后代码**: `{c.get('fix_after', '?')[:200]}`")
        lines.append(f"- **审查意见**: {feedback}")
        lines.append("")

    return "\n".join(lines)
