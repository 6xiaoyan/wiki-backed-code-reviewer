"""
skill_eval — 候选 skill 的 A/B 实验：注入 vs 不注入，比指标。

复用 eval_harness 的 runner / matcher，证明「注入后指标真的变好」，
候选 skill 才能进 live（见 SKILL_SELF_EVOLUTION.md 阶段 5）。

通过阈值（先定死，后续可调）：
  该组 recall 或 整体 precision 提升，且整体 F1 不下降。
"""

import os
import json
import shutil

from code_checker.skill_loader import SKILL_ROOT, live_dir


def _read_raw(path: str) -> str | None:
    """读文件原文，不存在返回 None。"""
    if not os.path.exists(path):
        return None
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def _write_raw(path: str, text: str) -> None:
    """写文件原文（自动建目录）。"""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def _run_metrics(repo_path: str, gt, n_trials: int) -> dict:
    """跑 N 次评测，返回第一次运行的 L1 指标 + 合并违规列表。"""
    from code_checker.eval_harness.runner import run_trials
    from code_checker.eval_harness.matcher import score_detection

    trials = run_trials(repo_path, n=n_trials)
    merged_first = trials[0].get("merged_violations") or []
    l1 = score_detection(merged_first, gt)
    return {"l1": l1, "merged": merged_first}


def _rule_recall(merged: list[dict], gt, rule: str) -> float:
    """算目标 rule 的组内召回率（该 rule 的违规检出比例）。

    rule 为空时返回 None（无目标组，只比整体指标）。
    """
    from code_checker.eval_harness.matcher import _normalize_rule_name, match_violation

    if not rule:
        return None
    target_rule = _normalize_rule_name(rule)
    target = [
        g for g in gt.violations
        if g.source_kind == "llm"
        and _normalize_rule_name(g.rule or "") == target_rule
    ]
    if not target:
        return None
    hit = sum(
        1 for g in target
        if any(match_violation(r, g, gt.line_tolerance) for r in merged)
    )
    return round(hit / len(target), 4)


def _mount_candidate(agent_name: str, candidate_file: str, rule: str) -> str:
    """把候选 skill 临时挂进 live/<agent>/（写 md + 登记 manifest）。"""
    from code_checker.skill_loader import register_skill

    base = os.path.splitext(os.path.basename(candidate_file))[0]
    skill_id = f"ab-tmp-{base}"
    skill_file = f"{skill_id}.md"
    dest_dir = live_dir(agent_name)
    os.makedirs(dest_dir, exist_ok=True)
    shutil.copyfile(candidate_file, os.path.join(dest_dir, skill_file))
    register_skill(agent_name, skill_id, skill_file, rule)
    return skill_id


def _remove_temp(agent_name: str, skill_id: str) -> None:
    """摘掉临时挂载：删 md + 从 manifest 移除条目。"""
    live = live_dir(agent_name)
    md_path = os.path.join(live, f"{skill_id}.md")
    if os.path.exists(md_path):
        os.remove(md_path)
    manifest_path = os.path.join(live, "manifest.json")
    if not os.path.exists(manifest_path):
        return
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    manifest["skills"] = [
        e for e in manifest.get("skills", []) if e["id"] != skill_id
    ]
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)


def run_ab(ground_truth_path: str, agent_name: str, candidate_file: str,
           rule: str = "", n_trials: int = 1) -> dict:
    """把候选 skill 临时挂到 live/<agent>，跑评测，对比 baseline。

    流程：
      1. 记 baseline：不注入，跑 n_trials，取整体指标 + 该组 recall
      2. 临时把 candidate 挂进 live/<agent>/manifest.json
      3. 跑 n_trials，取注入后的指标
      4. 摘掉临时挂载（快照恢复 manifest），保证可回滚

    Args:
        ground_truth_path: 标准答案 JSON 路径。
        agent_name:        域（cpp/qt/git/sqlite）。
        candidate_file:    候选 skill md 文件的绝对路径。
        rule:              候选 skill 针对的规则名（算组内 recall 用，可空）。
        n_trials:          每侧评测次数（每次全量跑，贵，默认 1）。

    Returns:
        {"baseline", "injected", "delta_recall", "delta_precision", "pass"}
    """
    from code_checker.eval_harness.dataset import load_ground_truth
    from code_checker.eval_harness.runner import resolve_repo_path

    gt = load_ground_truth(ground_truth_path)
    repo_path = resolve_repo_path(gt.repo)

    # ── 1. baseline ──
    base = _run_metrics(repo_path, gt, n_trials)

    # ── 2 + 3. 挂载 → 注入评测（finally 里恢复，保证可回滚）──
    manifest_path = os.path.join(live_dir(agent_name), "manifest.json")
    manifest_backup = _read_raw(manifest_path)
    mount_id = f"ab-tmp-{os.path.splitext(os.path.basename(candidate_file))[0]}"
    try:
        _mount_candidate(agent_name, candidate_file, rule)
        injected = _run_metrics(repo_path, gt, n_trials)
    finally:
        if manifest_backup is None:
            if os.path.exists(manifest_path):
                os.remove(manifest_path)
        else:
            _write_raw(manifest_path, manifest_backup)
        _remove_temp(agent_name, mount_id)

    # ── 4. 对比 ──
    b, i = base["l1"], injected["l1"]
    base_rule_recall = _rule_recall(base["merged"], gt, rule)
    inj_rule_recall = _rule_recall(inj["merged"], gt, rule)

    rule_recall_up = (
        inj_rule_recall is not None and base_rule_recall is not None
        and inj_rule_recall > base_rule_recall
    )
    precision_up = i["precision"] > b["precision"]
    f1_not_down = i["f1"] >= b["f1"]

    passed = (rule_recall_up or precision_up) and f1_not_down

    return {
        "baseline": {
            "recall": b["recall"],
            "precision": b["precision"],
            "f1": b["f1"],
            "rule_recall": base_rule_recall,
        },
        "injected": {
            "recall": i["recall"],
            "precision": i["precision"],
            "f1": i["f1"],
            "rule_recall": inj_rule_recall,
        },
        "delta_recall": round(i["recall"] - b["recall"], 4),
        "delta_precision": round(i["precision"] - b["precision"], 4),
        "rule": rule,
        "pass": passed,
    }
