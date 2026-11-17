"""Download pinned baseline materials and count text tokens; never execute targets."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import subprocess
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

import requests
import tiktoken


PROJECT = Path(__file__).resolve().parents[1]
TARGET_SHA = "2fb0c600245f50670e8b9233c784afe61e8b340b"
JUDGE_SHA = "90c3221a83e44242b7b67555094349107c21283f"
SPARSE_PATHS = [
    "/score.py", "/scorer/", "/parsers/", "/config/",
    "/ground-truth/realvuln-pygoat/", "/benchmark-manifest.json",
    "/validate_gt.py", "/compute_gt_hash.py", "/README.md", "/LICENSE",
    "/pyproject.toml", "/tests/", "/llm-bench/prompts/",
    "/llm-bench/README.md", "/docs/",
]
SOURCES = {
    "tencent": ("Tencent/secguide", "main"),
    "django": ("django/django", "4.2"),
    "owasp": ("OWASP/CheatSheetSeries", "master"),
    "google": ("google/styleguide", "gh-pages"),
    "pep": ("python/peps", "main"),
}
DOCUMENTS = [
    ("core", "tencent-python-security.md", "tencent", "Python安全指南.md"),
    ("core", "django-4.2-security.rst", "django", "docs/topics/security.txt"),
    ("core", "django-4.2-deployment-checklist.rst", "django", "docs/howto/deployment/checklist.txt"),
    ("core", "owasp-django-security.md", "owasp", "cheatsheets/Django_Security_Cheat_Sheet.md"),
    ("supplemental", "owasp-sql-injection-prevention.md", "owasp", "cheatsheets/SQL_Injection_Prevention_Cheat_Sheet.md"),
    ("supplemental", "owasp-xss-prevention.md", "owasp", "cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.md"),
    ("supplemental", "owasp-ssrf-prevention.md", "owasp", "cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.md"),
    ("supplemental", "owasp-deserialization.md", "owasp", "cheatsheets/Deserialization_Cheat_Sheet.md"),
    ("supplemental", "owasp-authorization.md", "owasp", "cheatsheets/Authorization_Cheat_Sheet.md"),
    ("optional-style", "google-python-style.md", "google", "pyguide.md"),
    ("optional-style", "pep-0008.rst", "pep", "peps/pep-0008.rst"),
]


def git(path: Path | None, *args: str) -> str:
    command = ["git", "-c", "http.version=HTTP/1.1"]
    if path is not None:
        command += ["-C", str(path)]
    result = subprocess.run(command + list(args), capture_output=True,
                            encoding="utf-8", errors="replace", timeout=120)
    if result.returncode:
        raise RuntimeError(f"git {args[0]} failed: {result.stderr[-1500:]}")
    return result.stdout.strip()


def ensure_checkout(path: Path, url: str, sha: str, sparse: bool = False) -> None:
    if not (path / ".git").exists():
        if path.exists() and any(path.iterdir()):
            raise RuntimeError(f"Refusing to overwrite nonempty directory: {path}")
        path.parent.mkdir(parents=True, exist_ok=True)
        args = ["clone", "--depth", "1"]
        if sparse:
            args += ["--filter=blob:none", "--sparse", "--no-checkout"]
        git(None, *args, url, str(path))
    if git(path, "remote", "get-url", "origin").removesuffix(".git") != url.removesuffix(".git"):
        raise RuntimeError(f"Unexpected origin: {path}")
    if git(path, "status", "--porcelain"):
        raise RuntimeError(f"Checkout is not clean: {path}")
    if sparse:
        git(path, "sparse-checkout", "set", "--no-cone", *SPARSE_PATHS)
    try:
        git(path, "cat-file", "-e", f"{sha}^{{commit}}")
    except RuntimeError:
        git(path, "fetch", "--depth", "1", "origin", sha)
    git(path, "checkout", "--detach", sha)
    if git(path, "rev-parse", "HEAD") != sha:
        raise RuntimeError(f"Pinned checkout mismatch: {path}")


def fetch(url: str) -> bytes:
    for attempt in range(3):
        try:
            response = requests.get(url, timeout=(15, 45),
                                    headers={"User-Agent": "pygoat-baseline-materials/1.0"})
            response.raise_for_status()
            return response.content
        except requests.RequestException:
            if attempt == 2:
                raise
            time.sleep(attempt + 1)
    raise AssertionError("unreachable")


def resolve_source(item: tuple[str, tuple[str, str]]) -> tuple[str, dict]:
    key, (repo, ref) = item
    data = json.loads(fetch(f"https://api.github.com/repos/{repo}/commits/{quote(ref, safe='')}"))
    return key, {"repository": repo, "requested_ref": ref, "commit": data["sha"]}


def download_document(item: tuple, sources: dict, root: Path) -> dict:
    group, name, source_key, upstream_path = item
    source = sources[source_key]
    url = f"https://raw.githubusercontent.com/{source['repository']}/{source['commit']}/{quote(upstream_path)}"
    data = fetch(url)
    data.decode("utf-8-sig")  # Fail instead of saving an HTML/error/binary response as a rule.
    if data.lstrip().lower().startswith((b"<!doctype html", b"<html")):
        raise ValueError(f"Expected raw documentation, received HTML: {url}")
    path = root / "rules" / group / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    print(f"Downloaded rule: {group}/{name} ({len(data)} bytes)", flush=True)
    return {"group": group, "path": path.relative_to(root).as_posix(),
            "source_url": url, "source_repository": source["repository"],
            "source_commit": source["commit"], "upstream_path": upstream_path,
            "bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def target_category(path: str) -> str:
    p = Path(path)
    parts = set(p.parts)
    if p.suffix.lower() == ".py":
        return "target_python"
    if "static" in parts or "staticfiles" in parts:
        return "target_static_assets"
    if p.suffix.lower() in {".html", ".htm", ".jinja", ".jinja2"}:
        return "target_templates"
    if p.suffix.lower() in {".md", ".rst"} or p.name.lower().startswith(("readme", "license")):
        return "target_documentation"
    return "target_other_text"


def count_materials(root: Path, manifest: dict, report_dir: Path) -> dict:
    encodings = {name: tiktoken.get_encoding(name) for name in ("o200k_base", "cl100k_base")}
    rows, skipped = [], []
    for role, folder in (("target", root / "targets" / "pygoat"),
                         ("judge", root / "judge" / "realvuln"),
                         ("rules", root / "rules")):
        if role in {"target", "judge"}:
            paths = [folder / p for p in git(folder, "ls-files").splitlines() if (folder / p).is_file()]
        else:
            paths = sorted(p for p in folder.rglob("*") if p.is_file())
        for path in paths:
            rel = path.relative_to(folder).as_posix()
            data = path.read_bytes()
            try:
                if b"\x00" in data:
                    raise UnicodeError("NUL byte")
                content = data.decode("utf-8-sig")
            except UnicodeError:
                skipped.append({"role": role, "path": rel, "bytes": len(data),
                                "reason": "binary or non-UTF-8; not counted"})
                continue
            if role == "target":
                category = target_category(rel)
            elif role == "rules":
                category = "rules_" + rel.split("/")[0]
            elif rel.startswith("ground-truth/"):
                category = "judge_ground_truth"
            elif rel == "score.py" or rel.startswith(("scorer/", "parsers/", "config/")):
                category = "judge_scoring_code_and_config"
            else:
                category = "judge_supporting_materials"
            row = {"role": role, "category": category, "path": rel,
                   "bytes": len(data), "characters": len(content),
                   "lines": len(content.splitlines()),
                   "sha256": hashlib.sha256(data).hexdigest()}
            row.update({name: len(enc.encode(content, disallowed_special=()))
                        for name, enc in encodings.items()})
            rows.append(row)
    totals = defaultdict(lambda: {"files": 0, "bytes": 0, "o200k_base": 0, "cl100k_base": 0})
    for row in rows:
        total = totals[row["category"]]
        total["files"] += 1
        for key in ("bytes", "o200k_base", "cl100k_base"):
            total[key] += row[key]
    combinations = {
        "python_and_templates": ["target_python", "target_templates"],
        "python_templates_and_core_security_rules": ["target_python", "target_templates", "rules_core"],
        "python_templates_and_all_security_rules": ["target_python", "target_templates", "rules_core", "rules_supplemental"],
        "all_target_text": [k for k in totals if k.startswith("target_")],
        "all_rule_documents": [k for k in totals if k.startswith("rules_")],
    }
    input_scenarios = {name: {key: sum(totals[cat][key] for cat in cats)
                             for key in ("files", "bytes", "o200k_base", "cl100k_base")}
                       for name, cats in combinations.items()}
    report = {"created_at_utc": datetime.now(timezone.utc).isoformat(),
              "asset_root": str(root), "tiktoken_version": tiktoken.__version__,
              "method": "Sum of independently tokenized UTF-8 file contents; excludes Git internals, binary/non-UTF-8 files, chat framing, tool schemas, prompts and model output. Tokenizers are proxies, not verified tokenizers for every baseline model.",
              "repositories": manifest["repositories"], "ground_truth": manifest["ground_truth"],
              "totals_by_category": dict(sorted(totals.items())),
              "input_scenarios": input_scenarios,
              "all_downloaded_text": {key: sum(r[key] for r in rows)
                                      for key in ("bytes", "o200k_base", "cl100k_base")},
              "skipped_files": skipped,
              "largest_target_files": sorted((r for r in rows if r["role"] == "target"),
                                             key=lambda r: r["o200k_base"], reverse=True)[:15]}
    report_dir.mkdir(parents=True, exist_ok=True)
    (report_dir / "token-report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with (report_dir / "token-inventory.csv").open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(sorted(rows, key=lambda row: (row["role"], row["path"])))
    (report_dir / "assets.lock.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = ["# PyGoat material token inventory", "",
             "Counts are sums of independently tokenized UTF-8 file contents. Both encodings are proxies; actual baseline-model tokenizers may differ.",
             "", "| Category | Files | o200k_base | cl100k_base |",
             "| --- | ---: | ---: | ---: |"]
    for category, total in sorted(totals.items()):
        lines.append(f"| {category} | {total['files']} | {total['o200k_base']:,} | {total['cl100k_base']:,} |")
    lines += ["", "## Combined input sizes", "",
              "| Scope | o200k_base | cl100k_base |", "| --- | ---: | ---: |"]
    for name, total in input_scenarios.items():
        lines.append(f"| {name} | {total['o200k_base']:,} | {total['cl100k_base']:,} |")
    lines += ["", "## Boundaries", "",
              "- Judge files and ground truth are not model inputs.",
              "- Target text includes Solutions/solution.md and teaching/discussion content inside templates. These are preserved upstream materials, not an approved answer-free experiment input.",
              "- Static assets include SVG and CSS; they must not be presented as Python backend code size.",
              "- Optional style documents are excluded from security-only rule totals.",
              "- Raw security documents require a version/applicability review before group B is frozen.",
              "- No target code, dependencies, model calls or vulnerability evaluation were executed.",
              "- No chat framing, system prompts, tool schemas, image tokens, reasoning or output budget is included.", ""]
    (report_dir / "token-report.md").write_text("\n".join(lines), encoding="utf-8")
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asset-root", type=Path,
                        default=PROJECT.parent / "benchmark-data" / "pygoat-baseline")
    parser.add_argument("--count-only", action="store_true")
    args = parser.parse_args()
    root = args.asset_root.resolve()
    metadata = root / "metadata"
    metadata.mkdir(parents=True, exist_ok=True)
    lock_path = metadata / "assets.lock.json"
    if args.count_only:
        manifest = json.loads(lock_path.read_text(encoding="utf-8"))
    else:
        judge = root / "judge" / "realvuln"
        ensure_checkout(judge, "https://github.com/kolega-ai/Real-Vuln-Benchmark.git", JUDGE_SHA, sparse=True)
        gt_path = judge / "ground-truth" / "realvuln-pygoat" / "ground-truth.json"
        gt = json.loads(gt_path.read_text(encoding="utf-8"))
        if gt["commit_sha"] != TARGET_SHA:
            raise RuntimeError("Ground truth target changed; review the version before proceeding")
        target = root / "targets" / "pygoat"
        ensure_checkout(target, gt["repo_url"], TARGET_SHA)
        missing = [e["file"] for e in gt["findings"] if not (target / e["file"]).is_file()]
        if missing:
            raise RuntimeError(f"Ground truth references missing files: {sorted(set(missing))}")
        with ThreadPoolExecutor(max_workers=5) as pool:
            sources = dict(pool.map(resolve_source, SOURCES.items()))
            documents = list(pool.map(lambda doc: download_document(doc, sources, root), DOCUMENTS))
        labels = Counter("non_scoring" if e.get("scoring") == "non_scoring"
                         else "vulnerable" if e["is_vulnerable"] else "false_positive_trap"
                         for e in gt["findings"])
        manifest = {"prepared_at_utc": datetime.now(timezone.utc).isoformat(),
                    "repositories": {"pygoat": {"url": gt["repo_url"], "commit": TARGET_SHA},
                                     "realvuln": {"url": "https://github.com/kolega-ai/Real-Vuln-Benchmark", "commit": JUDGE_SHA, "sparse_checkout": SPARSE_PATHS}},
                    "ground_truth": {"path": str(gt_path), "sha256": hashlib.sha256(gt_path.read_bytes()).hexdigest(),
                                     "labels": dict(labels)},
                    "rule_sources": sources, "documents": documents,
                    "notes": ["PyGoat pins Django 4.2; Django documentation is pinned to tag 4.2.",
                              "OWASP and Tencent documents include version-dependent or dated recommendations; raw snapshots are not yet an adjudicated experimental ruleset.",
                              "Optional Google/PEP8 style documents are excluded from the proposed security-only group B.",
                              "Judge/ground-truth are stored outside the target checkout. This is directory separation, not an enforced access-control boundary.",
                              "No target dependencies installed, no target code executed, no model evaluation run."]}
        lock_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report = count_materials(root, manifest, PROJECT / "benchmarks" / "pygoat")
    print(json.dumps({"labels": manifest["ground_truth"]["labels"],
                      "totals_by_category": report["totals_by_category"],
                      "input_scenarios": report["input_scenarios"],
                      "all_downloaded_text": report["all_downloaded_text"]}, indent=2))


if __name__ == "__main__":
    main()
