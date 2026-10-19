"""公开前检查：不得包含真实凭据、机器绝对路径或可执行 PR 代码的入口。"""

import os
import re
from pathlib import Path

import pytest

def _find_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "code_checker").is_dir() and (parent / "examples").is_dir():
            return parent
    return here.parents[3]


ROOT = _find_root()

PUBLISHABLE_SOURCES = [
    ROOT / "code_checker" / "config.py",
    *sorted((ROOT / "code_checker" / "pr_review").glob("*.py")),
    ROOT / ".github" / "workflows" / "pr-review.yml",
    ROOT / ".env.example",
    *sorted((ROOT / "examples" / "review-target").rglob("*")),
]

SECRET_PATTERNS = (
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
    re.compile(r"ghp_[A-Za-z0-9]{20,}"),
    re.compile(r"github_pat_[A-Za-z0-9_]{20,}"),
    re.compile(r"AKIA[0-9A-Z]{16}"),
)

WINDOWS_ABS_RE = re.compile(r"\b[A-Za-z]:\\")


def _text_files():
    for path in PUBLISHABLE_SOURCES:
        if path.is_dir():
            continue
        if path.suffix.lower() in (".png", ".jpg", ".jpeg", ".pdf", ".zip"):
            continue
        yield path


def test_no_hardcoded_credentials_in_publishable_sources():
    hits = []
    for path in _text_files():
        text = path.read_text(encoding="utf-8", errors="replace")
        for rx in SECRET_PATTERNS:
            if rx.search(text):
                hits.append((str(path), rx.pattern))
    assert not hits, f"发现疑似硬编码凭据: {hits}"


def test_config_reads_credentials_from_environment_only():
    source = (ROOT / "code_checker" / "config.py").read_text(encoding="utf-8")
    assert 'os.environ.get("DEEPSEEK_API_KEY")' in source
    assert 'api_key="sk-' not in source
    # 不再包含形如真实 Key 的 32+ 位十六进制字面量
    assert not re.search(r'api_key\s*=\s*"[A-Za-z0-9]{32,}"', source)


def test_has_llm_credentials_tracks_environment(monkeypatch):
    from code_checker import config

    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert config.has_llm_credentials() is False
    monkeypatch.setenv("DEEPSEEK_API_KEY", "test-placeholder")
    assert config.has_llm_credentials() is True


def test_no_machine_specific_absolute_paths_in_pr_modules():
    for path in sorted((ROOT / "code_checker" / "pr_review").glob("*.py")):
        text = path.read_text(encoding="utf-8")
        assert not WINDOWS_ABS_RE.search(text), f"{path.name} 含机器绝对路径"
        assert "/home/" not in text
        assert "/Users/" not in text


def test_env_example_contains_placeholders_only():
    text = (ROOT / ".env.example").read_text(encoding="utf-8")
    assert "DEEPSEEK_API_KEY=" in text
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        if name == "CODE_REVIEW_BUDGET":
            continue  # 预算不是凭据
        assert value == "", f"{name} 在 .env.example 中必须为空占位符"


def test_example_target_has_no_real_secrets():
    target = ROOT / "examples" / "review-target"
    assert target.is_dir()
    for path in target.rglob("*"):
        if path.is_file():
            text = path.read_text(encoding="utf-8", errors="replace")
            for rx in SECRET_PATTERNS:
                assert not rx.search(text), f"{path} 含疑似凭据"
