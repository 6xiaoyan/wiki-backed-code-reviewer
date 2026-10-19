#!/usr/bin/env python3
"""本地离线演示：在临时 Git 仓库上模拟一次 PR 审查。

不需要模型凭据、不需要 GitHub、不会访问网络。演示内容：
  * 新增一个带 Tab 缩进的函数 → 报告为本次新增问题；
  * 修改 legacy.cpp，但其中历史 Tab 缩进未改动 → 被过滤，不计为本次新增；
  * 结果状态为 incomplete（离线未执行 LLM 审查），退出码 2。

用法：
    python scripts/demo_local.py [--keep]
"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(cmd, cwd, env=None, check=True):
    proc = subprocess.run(
        cmd, cwd=cwd, env=env, capture_output=True, text=True,
        encoding="utf-8", errors="replace",
    )
    if check and proc.returncode != 0:
        print(proc.stdout)
        print(proc.stderr, file=sys.stderr)
        raise SystemExit(f"命令失败: {' '.join(map(str, cmd))}")
    return proc


def git(repo: Path, *args: str) -> str:
    proc = run([
        "git", "-C", str(repo), "-c", "core.autocrlf=false",
        "-c", "commit.gpgsign=false", "-c", "user.email=demo@example.com",
        "-c", "user.name=Demo", *args,
    ], cwd=ROOT)
    return proc.stdout.strip()


def write(repo: Path, relative: str, text: str) -> None:
    path = repo / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--keep", action="store_true", help="保留临时目录")
    args = parser.parse_args()

    workdir = Path(tempfile.mkdtemp(prefix="pr-review-demo-"))
    repo = workdir / "repo"
    repo.mkdir()
    out = workdir / "artifacts"
    try:
        git(repo, "init", "-b", "main")
        for name in ("src/main.cpp", "src/db.h", "src/db.cpp",
                     "src/widget.h", "src/widget.cpp", "src/legacy.cpp",
                     "CMakeLists.txt", "README.md"):
            source = ROOT / "examples" / "review-target" / name
            write(repo, name, source.read_text(encoding="utf-8"))
        git(repo, "add", "-A")
        git(repo, "commit", "-m", "feat: demo baseline")

        git(repo, "checkout", "-b", "pr")
        main_cpp = (repo / "src/main.cpp").read_text(encoding="utf-8")
        write(repo, "src/main.cpp", main_cpp + """
int demoHelper() {
\treturn 42;
}
""")
        legacy = (repo / "src/legacy.cpp").read_text(encoding="utf-8")
        write(repo, "src/legacy.cpp", legacy + """
std::string legacyExtra() {
    return "extra";
}
""")
        git(repo, "add", "-A")
        git(repo, "commit", "-m", "feat: add demo helper")

        env = dict(os.environ)
        env["PYTHONPATH"] = str(ROOT)
        env["PYTHONIOENCODING"] = "utf-8"
        env.pop("DEEPSEEK_API_KEY", None)
        env.pop("OPENAI_API_KEY", None)
        env["CODE_REVIEW_OFFLINE"] = "1"
        proc = run([
            sys.executable, "-m", "code_checker.pr_review", "local",
            "--repo-path", str(repo), "--base", "main", "--head", "pr",
            "--offline", "--output-dir", str(out),
        ], cwd=ROOT, env=env, check=False)
        print(proc.stdout)
        if proc.stderr.strip():
            print(proc.stderr, file=sys.stderr)

        result_path = out / "review-result.json"
        if not result_path.is_file():
            print("未生成 review-result.json", file=sys.stderr)
            return 1
        data = json.loads(result_path.read_text(encoding="utf-8"))
        print("=" * 68)
        print(f"状态: {data['status']}")
        print("已确认问题:")
        for f in data["findings"]:
            print(f"  - [{f['severity']}] {f['file']}:{f['line']} {f['rule_id']}")
        print("已过滤（历史/无关）:")
        for item in data["filtered_findings"]:
            print(f"  - {item['file']}:{item['line']} — {item['reason']}")
        print(f"产物目录: {out}")

        expected_tab = any(
            f["file"] == "src/main.cpp" and f["rule_id"].endswith("check_tab_indentation")
            for f in data["findings"]
        )
        historical_filtered = any(
            item["file"] == "src/legacy.cpp" for item in data["filtered_findings"]
        )
        if not expected_tab or not historical_filtered:
            print("演示断言失败：新增违规未报告或历史违规未过滤", file=sys.stderr)
            return 1
        print("演示断言通过：新增 Tab 违规被报告，legacy.cpp 历史违规被过滤。")
        print("注意：离线模式只执行确定性检查，状态为 incomplete，退出码应为 2。")
        return 0 if proc.returncode == 2 else 1
    finally:
        if args.keep:
            print(f"临时目录已保留: {workdir}")
        else:
            shutil.rmtree(workdir, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
