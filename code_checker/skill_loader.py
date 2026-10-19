"""
skill_loader — 读取某 agent 的 live skill，拼成注入文本。

每个 agent 只读自己域下的 live 目录，天然定向隔离。
skill 元数据存 manifest.json，正文存 <id>.md，二者分离：
utility 更新只改 manifest，不用解析 md。

职责边界（见 SKILL_SELF_EVOLUTION.md）：
  - 只负责「读」和「登记」，不生成 skill（生成在 skill_generator.py）
  - 不做语义去重 / 退役判定（那在 skill_maintain.py）
"""

import os
import json
import datetime

SKILL_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "agent-skills")

_INJECT_HEADER = (
    "=== Agent Skill（语义经验，来自评测反馈）===\n"
    "以下经验不改变规则本身，只补充「如何识别某个语义场景」。\n"
    "规则原文以 wiki 页面为准，若两者冲突，以 wiki 为准。\n"
)


def _today() -> str:
    """返回今天的 ISO 日期字符串（manifest 的 created/last_used 用）。"""
    return datetime.date.today().isoformat()


def load_live_skills(agent_name: str) -> str:
    """返回某 agent 的 live skill 正文拼接，无 skill 时返回空串。

    Args:
        agent_name: cpp / qt / git / sqlite（定向隔离的域）。

    Returns:
        注入文本（含头部说明 + 各 skill 正文），无 skill 返回 ""。
    """
    live_dir = os.path.join(SKILL_ROOT, "live", agent_name)
    manifest_path = os.path.join(live_dir, "manifest.json")
    if not os.path.exists(manifest_path):
        return ""
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    chunks = []
    for entry in manifest.get("skills", []):
        if entry.get("stale"):
            continue
        md_path = os.path.join(live_dir, entry["file"])
        if not os.path.exists(md_path):
            continue
        with open(md_path, "r", encoding="utf-8") as f:
            chunks.append(f.read().strip())
    if not chunks:
        return ""
    return _INJECT_HEADER + "\n\n".join(chunks) + "\n"


def _load_manifest(agent_name: str) -> dict | None:
    """读取某 agent 的 manifest，不存在返回 None。"""
    manifest_path = os.path.join(SKILL_ROOT, "live", agent_name, "manifest.json")
    if not os.path.exists(manifest_path):
        return None
    with open(manifest_path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_manifest(agent_name: str, manifest: dict) -> None:
    """写回某 agent 的 manifest（自动建目录）。"""
    live_dir = os.path.join(SKILL_ROOT, "live", agent_name)
    os.makedirs(live_dir, exist_ok=True)
    manifest_path = os.path.join(live_dir, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)


def bump_utility(agent_name: str, skill_id: str, delta: int) -> None:
    """实验后更新某条 skill 的 utility 与 last_used。

    Args:
        agent_name: 域（cpp/qt/git/sqlite）。
        skill_id:   manifest 里的 id 字段（如 "001-初始化失败后未中止操作"）。
        delta:      +1（经验正确发挥作用）或 -1（反效果）。
    """
    manifest = _load_manifest(agent_name)
    if manifest is None:
        return
    for entry in manifest.get("skills", []):
        if entry["id"] == skill_id:
            entry["utility"] = entry.get("utility", 0) + delta
            entry["last_used"] = _today()
    _save_manifest(agent_name, manifest)


def register_skill(agent_name: str, skill_id: str, skill_file: str, rule: str) -> None:
    """把一条 skill 登记进 live manifest（正文由调用方先写入 live/<agent>/）。

    幂等：id 已存在则跳过，不覆盖已有条目。

    Args:
        agent_name: 域。
        skill_id:   唯一 id（建议 "NNN-语义名"）。
        skill_file: 正文文件名（相对 live/<agent>/，如 "001-xxx.md"）。
        rule:       关联规则（wiki 页面 slug，如 "cpp/exception-safety-guarantees"）。
    """
    manifest = _load_manifest(agent_name)
    if manifest is None:
        manifest = {"skills": []}
    for entry in manifest.get("skills", []):
        if entry["id"] == skill_id:
            return
    manifest["skills"].append({
        "id": skill_id,
        "file": skill_file,
        "rule": rule,
        "utility": 0,
        "stale": False,
        "created": _today(),
        "last_used": None,
    })
    _save_manifest(agent_name, manifest)


def live_dir(agent_name: str) -> str:
    """返回某 agent 的 live 目录绝对路径（供生成器落正文用）。"""
    return os.path.join(SKILL_ROOT, "live", agent_name)
