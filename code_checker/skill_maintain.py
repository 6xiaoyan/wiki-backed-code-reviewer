"""
skill_maintain — 退役 + 收敛（见 SKILL_SELF_EVOLUTION.md 阶段 6）。

退役规则（v1 以 last_used 时间为准）：
  - last_used 距今超过 30 天 → 标 stale: true
  - （备选触发「连续 10 次评测未被引用」需要额外引用计数器，v1 先用时间维度，
    因为 bump_utility 每次「经验正确发挥作用」都会刷新 last_used，等效于活跃度。）
  - archive_stale() 把 stale 条目连同 md 移到 retired/，下轮清理调用。

收敛规则（v1 只提示不自动合并）：
  - 两个 skill 的「触发 + 判断」文本高度重叠时，返回疑似重复 id 对，
    人工确认后合并。
"""

import os
import re
import json
import datetime
import shutil

from code_checker.skill_loader import SKILL_ROOT

STALE_DAYS = 30


def mark_stale(agent_name: str) -> list[str]:
    """把 last_used 距今超过 30 天的 skill 标 stale，返回本次标记的 id 列表。

    从未被使用过的 skill（last_used 为 None）用 created 起算。
    """
    manifest_path = os.path.join(SKILL_ROOT, "live", agent_name, "manifest.json")
    if not os.path.exists(manifest_path):
        return []
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    today = datetime.date.today()
    marked: list[str] = []
    for entry in manifest.get("skills", []):
        if entry.get("stale"):
            continue
        last_used = entry.get("last_used") or entry.get("created")
        if last_used is None:
            continue
        try:
            d = datetime.date.fromisoformat(str(last_used))
        except ValueError:
            continue
        if (today - d).days > STALE_DAYS:
            entry["stale"] = True
            marked.append(entry["id"])

    if marked:
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, ensure_ascii=False, indent=2)
    return marked


def archive_stale(agent_name: str) -> list[str]:
    """把 stale 的 skill（md + manifest 条目）移到 retired/，返回归档的 id 列表。

    被归档的 skill 不再被 load_live_skills 注入（manifest 条目已移除）。
    """
    live = os.path.join(SKILL_ROOT, "live", agent_name)
    retired = os.path.join(SKILL_ROOT, "retired", agent_name)
    manifest_path = os.path.join(live, "manifest.json")
    if not os.path.exists(manifest_path):
        return []
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    os.makedirs(retired, exist_ok=True)
    archived: list[str] = []
    kept: list[dict] = []
    for entry in manifest.get("skills", []):
        if entry.get("stale"):
            src = os.path.join(live, entry["file"])
            if os.path.exists(src):
                shutil.move(src, os.path.join(retired, entry["file"]))
            archived.append(entry["id"])
        else:
            kept.append(entry)

    manifest["skills"] = kept
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    return archived


def find_duplicates(agent_name: str) -> list[tuple[str, str]]:
    """返回「疑似重复」的 skill id 对（触发 + 判断 文本高度重叠），人工确认后合并。

    第一版不做语义去重——只按整篇正文的 token Jaccard 粗筛，阈值定低，
    宁可多报让人判断，绝不自动合并。
    """
    live = os.path.join(SKILL_ROOT, "live", agent_name)
    manifest_path = os.path.join(live, "manifest.json")
    if not os.path.exists(manifest_path):
        return []
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)

    texts: dict[str, set] = {}
    for entry in manifest.get("skills", []):
        if entry.get("stale"):
            continue
        md_path = os.path.join(live, entry["file"])
        if not os.path.exists(md_path):
            continue
        with open(md_path, "r", encoding="utf-8") as f:
            texts[entry["id"]] = _tokenize(f.read())

    ids = list(texts.keys())
    dupes: list[tuple[str, str]] = []
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            a, b = texts[ids[i]], texts[ids[j]]
            if not a or not b:
                continue
            union = len(a | b)
            jaccard = (len(a & b) / union) if union > 0 else 0.0
            if jaccard >= 0.6:
                dupes.append((ids[i], ids[j]))
    return dupes


def _tokenize(text: str) -> set[str]:
    """粗分词：英文取词干 token，中文取双字 n-gram。"""
    tokens = set(re.findall(r"[a-z_][a-z0-9_]{1,}", text.lower()))
    cjk = re.findall(r"[一-鿿]", text)
    for k in range(len(cjk) - 1):
        tokens.add("".join(cjk[k:k + 2]))
    return tokens
