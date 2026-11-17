"""Create an immutable-content review copy, excluding standalone answer material.

Does not execute PyGoat, install dependencies, call models, or run a scorer.
The inclusion policy is independent of vulnerability labels.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from collections import Counter
from pathlib import Path

import tiktoken


EXPERIMENT = Path(__file__).resolve().parent
PROJECT = EXPERIMENT.parents[1]
ASSETS = PROJECT.parent / "benchmark-data" / "pygoat-baseline"
SOURCE = ASSETS / "targets" / "pygoat"
DESTINATION = ASSETS / "inputs" / "experiment-01" / "pygoat"
EXPECTED_COMMIT = "2fb0c600245f50670e8b9233c784afe61e8b340b"
EXCLUDED_DIRECTORIES = {"solutions", "docs", ".github", ".vscode", "chatbot"}
EXCLUDED_EXTENSIONS = {".md", ".rst", ".ipynb"}


def git(*args: str) -> str:
    result = subprocess.run(["git", "-C", str(SOURCE), *args], check=True,
                            capture_output=True, encoding="utf-8")
    return result.stdout.strip()


def exclusion(path: str) -> str | None:
    p = Path(path)
    if any(part.lower() in EXCLUDED_DIRECTORIES for part in p.parts):
        return "standalone answers, documentation, notebooks, or development metadata"
    if p.suffix.lower() in EXCLUDED_EXTENSIONS and not p.name.lower().startswith("license"):
        return "standalone documentation or notebook"
    return None


def main() -> None:
    if git("rev-parse", "HEAD") != EXPECTED_COMMIT:
        raise RuntimeError("Unexpected source commit")
    if git("status", "--porcelain"):
        raise RuntimeError("Source checkout must be clean")
    files = git("ls-files").splitlines()
    included, excluded = [], []
    enc = tiktoken.get_encoding("o200k_base")
    for rel in files:
        if reason := exclusion(rel):
            excluded.append({"path": rel, "reason": reason})
            continue
        src, dst = SOURCE / rel, DESTINATION / rel
        if src.is_symlink():
            raise RuntimeError(f"Review symlink before copying: {rel}")
        data = src.read_bytes()
        if dst.exists() and dst.read_bytes() != data:
            raise RuntimeError(f"Refusing to overwrite changed input: {dst}")
        dst.parent.mkdir(parents=True, exist_ok=True)
        if not dst.exists():
            shutil.copy2(src, dst)
        try:
            if b"\0" in data:
                raise UnicodeError("binary")
            text = data.decode("utf-8-sig")
            tokens = len(enc.encode(text, disallowed_special=()))
        except UnicodeError:
            tokens = None
        included.append({"path": rel, "bytes": len(data),
                         "sha256": hashlib.sha256(data).hexdigest(), "o200k_base": tokens})
    expected = {r["path"] for r in included}
    actual = {p.relative_to(DESTINATION).as_posix() for p in DESTINATION.rglob("*") if p.is_file()}
    if actual != expected:
        raise RuntimeError(f"Unexpected files in review input: {sorted(actual - expected)}")
    # Integrity check only: labels never determine which files are included.
    gt_path = ASSETS / "judge" / "realvuln" / "ground-truth" / "realvuln-pygoat" / "ground-truth.json"
    gt = json.loads(gt_path.read_text(encoding="utf-8"))
    referenced = {entry["file"] for entry in gt["findings"]}
    if not referenced <= expected:
        raise RuntimeError("Input policy removed files referenced by the official labels")
    content_hash = hashlib.sha256()
    for entry in included:
        content_hash.update((entry["path"] + "\n" + entry["sha256"] + "\n").encode())
    manifest = {
        "experiment_id": "01-pygoat-models-pi-agent",
        "source_commit": EXPECTED_COMMIT,
        "source_directory": str(SOURCE),
        "review_directory": str(DESTINATION),
        "input_policy": {"excluded_directories": sorted(EXCLUDED_DIRECTORIES),
                         "excluded_extensions": sorted(EXCLUDED_EXTENSIONS),
                         "license_documents_retained": True,
                         "all_other_tracked_files_retained_unchanged": True},
        "content_manifest_sha256": content_hash.hexdigest(),
        "included_file_count": len(included),
        "excluded_file_count": len(excluded),
        "text_file_count": sum(e["o200k_base"] is not None for e in included),
        "o200k_base_text_tokens": sum(e["o200k_base"] or 0 for e in included),
        "ground_truth_location_integrity": "All referenced files retained with identical bytes; no labels or answer files copied into input",
        "limitations": [
            "Directory separation is not filesystem or network access control.",
            "Source, template content, lab names and comments retain intrinsic teaching hints; this is not a decontaminated or production-code benchmark.",
            "Two groups must use this identical input snapshot.",
        ],
        "included_files": included,
        "excluded_files": excluded,
    }
    (EXPERIMENT / "input-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({key: manifest[key] for key in (
        "review_directory", "included_file_count", "excluded_file_count",
        "text_file_count", "o200k_base_text_tokens", "content_manifest_sha256")}, indent=2))


if __name__ == "__main__":
    main()
