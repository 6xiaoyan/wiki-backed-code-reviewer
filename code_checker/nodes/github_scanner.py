"""
github_scanner — GitHub 远程仓库扫描节点。

这是流水线的可选入口（替代 repo_scanner）。当用户传入 GitHub URL 而非本地路径时，
此节点通过 MCP 协议连接 GitHub MCP 服务器，远程读取仓库文件和提交记录。

与 repo_scanner 的关系：
  - repo_scanner:  os.walk 本地目录 → file_list + file_contents
  - github_scanner: GitHub API（通过 MCP）→ file_list + file_contents + git 日志

两者产出格式完全一致，后续 8 个站点无感知切换。

文件路径约定：
  远程文件没有本地路径。系统构造虚拟路径，格式为：
    github://<owner>/<repo>/<branch>/<file_path>
  例: github://zhuyiming/password-manager/main/src/main.cpp
  这让后续的违规报告能追溯到具体仓库和分支。
"""

import os
import re
import json
import urllib.request
import urllib.error
from code_checker.state import AgentState
from code_checker.config import SOURCE_EXTENSIONS
from code_checker.mcp_client import connect_github_mcp, call_mcp_tool, disconnect_mcp


# ── GitHub URL 解析 ──
# 支持三种格式：
#   1. 完整 URL: https://github.com/owner/repo
#   2. 带分支:   https://github.com/owner/repo/tree/branch
#   3. 简写:     owner/repo
GITHUB_URL_RE = re.compile(
    r"(?:https?://)?github\.com/([^/]+)/([^/]+?)(?:\.git)?(?:/tree/([^/]+))?/?$"
)
SHORT_RE = re.compile(r"^([^/]+)/([^/]+)$")


def parse_github_url(repo_path: str) -> tuple[str, str, str]:
    """解析 GitHub URL，提取 owner、repo、分支名。

    Args:
        repo_path: GitHub URL 或简写

    Returns:
        (owner, repo, branch) 三元组。branch 默认为 "main"。

    Raises:
        ValueError: 无法解析为有效的 GitHub 地址
    """
    # 格式 1/2: 完整 URL
    m = GITHUB_URL_RE.match(repo_path.strip().rstrip("/"))
    if m:
        owner = m.group(1)
        repo = m.group(2)
        branch = m.group(3) or "main"
        return owner, repo, branch

    # 格式 3: 简写 owner/repo
    m = SHORT_RE.match(repo_path.strip())
    if m:
        return m.group(1), m.group(2), "main"

    raise ValueError(
        f"无法解析 GitHub 地址: '{repo_path}'\n"
        f"支持的格式:\n"
        f"  https://github.com/owner/repo\n"
        f"  https://github.com/owner/repo/tree/branch\n"
        f"  owner/repo"
    )


# ============================================================================
# 主节点函数
# ============================================================================


def github_scanner(state: AgentState) -> dict:
    """GitHub 远程仓库扫描节点。

    通过 MCP 协议读取 GitHub 仓库的文件列表和内容。

    流程：
      1. 解析 GitHub URL → owner / repo / branch
      2. 连接 GitHub MCP 服务器（通过令牌认证）
      3. 获取仓库文件树（递归列出所有文件）
      4. 逐个读取源代码文件内容
      5. 关闭 MCP 连接
      6. 返回 file_list + file_contents

    性能说明：
      - 文件树获取：1 次 GitHub REST API 调用（递归树接口）
      - 文件内容读取：每个源文件 1 次 MCP 工具调用
      - 单线程顺序读取，大型仓库可能需要数十秒

    Args:
        state: LangGraph 全局状态，从中读取 repo_path

    Returns:
        {"file_list": [...], "file_contents": {...}}
    """
    repo_path = state.get("repo_path", "")
    print(f"[GitHub 扫描] 启动... 仓库: {repo_path}")

    # ── 第一步：解析 URL ──
    owner, repo, branch = parse_github_url(repo_path)
    print(f"  [GitHub 扫描] owner={owner}  repo={repo}  branch={branch}")

    # ── 第二步：连接 MCP 服务器 ──
    process, server_info, tools = connect_github_mcp()

    try:
        # ── 第三步：获取文件树（通过 GitHub REST API 递归树接口）──
        # 这是获取仓库全部文件列表最快的方式——一次 API 调用，
        # 不需要逐层遍历目录
        all_files = _fetch_repo_tree(owner, repo, branch)
        total_files = len(all_files)

        # ── 筛选源代码文件（按扩展名）──
        source_files = [
            f for f in all_files
            if os.path.splitext(f)[1].lower() in SOURCE_EXTENSIONS
        ]
        skipped = total_files - len(source_files)
        print(f"  [GitHub 扫描] 仓库共 {total_files} 个文件, "
              f"源代码 {len(source_files)} 个, 跳过 {skipped} 个")

        if not source_files:
            print("  [GitHub 扫描] 未找到源代码文件")
            return {"file_list": [], "file_contents": {}}

        # ── 第四步：逐个读取文件内容（通过 MCP get_file_contents 工具）──
        file_list: list[str] = []
        file_contents: dict[str, str] = {}

        for i, filename in enumerate(source_files):
            # 构造 MCP 虚拟路径（遵循 github:// 伪协议）
            virtual_path = f"github://{owner}/{repo}/{branch}/{filename}"

            try:
                content = call_mcp_tool(process, "get_file_contents", {
                    "owner": owner,
                    "repo": repo,
                    "path": filename,
                    "ref": branch,
                })

                file_list.append(virtual_path)
                # MCP 返回的可能是纯文本或 JSON 结构
                if isinstance(content, str):
                    file_contents[virtual_path] = content
                elif isinstance(content, dict):
                    # GitHub API 返回的 JSON 结构中文件内容在 content 字段（base64）
                    text = content.get("text", "") or content.get("content", "")
                    file_contents[virtual_path] = str(text)
                else:
                    file_contents[virtual_path] = str(content)

            except Exception as e:
                print(f"  [GitHub 扫描] ⚠️ 读取失败 {filename}: {e}")
                file_list.append(virtual_path)
                file_contents[virtual_path] = f"[读取失败: {e}]"

            if (i + 1) % 20 == 0:
                print(f"  [GitHub 扫描] 进度: {i + 1}/{len(source_files)}")

        print(f"  [GitHub 扫描] 完成: {len(file_list)} 个文件已读取")

    finally:
        # ── 第五步：无论如何都要关闭 MCP 连接 ──
        disconnect_mcp(process)

    return {"file_list": file_list, "file_contents": file_contents}


# ============================================================================
# 辅助：GitHub REST API 文件树获取
# ============================================================================

# GitHub REST API 的递归文件树接口
# GET /repos/{owner}/{repo}/git/trees/{branch}?recursive=1
# 无需认证即可读取公开仓库（有认证可提高速率限制）
GITHUB_API_TREE = "https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"


def _get_github_token() -> str:
    """获取 GitHub 令牌（与 MCP 客户端保持一致）。"""
    return os.environ.get("GITHUB_TOKEN") or os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN", "")


def _fetch_repo_tree(owner: str, repo: str, branch: str = "main") -> list[str]:
    """通过 GitHub REST API 获取仓库完整文件树。

    使用 Git Trees API 的 recursive 模式，一次请求获取仓库中所有文件的
    路径列表。这是获取文件列表最高效的方式——无论仓库有多少层目录结构，
    只需要一次 HTTP GET。

    Args:
        owner:  仓库所有者
        repo:   仓库名称
        branch: 分支名（默认 main）

    Returns:
        文件路径列表，如 ["src/main.cpp", "include/config.h", ...]

    Raises:
        RuntimeError: API 请求失败（网络错误、仓库不存在、权限不足等）
    """
    url = GITHUB_API_TREE.format(owner=owner, repo=repo, branch=branch)
    token = _get_github_token()

    req = urllib.request.Request(url)
    req.add_header("Accept", "application/vnd.github+json")
    req.add_header("X-GitHub-Api-Version", "2022-11-28")
    req.add_header("User-Agent", "code-checker-mcp")
    if token:
        req.add_header("Authorization", f"Bearer {token}")

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        error_body = ""
        try:
            error_body = e.read().decode("utf-8")[:300]
        except Exception:
            pass
        if e.code == 404:
            raise RuntimeError(
                f"GitHub 仓库不存在或无权访问: {owner}/{repo}\n"
                f"请确认:\n"
                f"  1. 仓库名拼写正确\n"
                f"  2. 仓库是公开的，或令牌有访问权限\n"
                f"  3. 分支 '{branch}' 存在"
            )
        elif e.code == 403:
            raise RuntimeError(
                f"GitHub API 访问被拒绝（可能是速率限制）。\n"
                f"设置 GITHUB_TOKEN 环境变量可提高限制。"
            )
        elif e.code == 401:
            raise RuntimeError(
                f"GitHub API 认证失败。请检查 GITHUB_TOKEN 是否有效。"
            )
        else:
            raise RuntimeError(f"GitHub API 错误 ({e.code}): {error_body}")
    except urllib.error.URLError as e:
        raise RuntimeError(f"无法连接到 GitHub API: {e.reason}")

    if "tree" not in body or not isinstance(body["tree"], list):
        raise RuntimeError(
            f"GitHub API 返回了意外的数据结构。\n"
            f"返回内容: {json.dumps(body, ensure_ascii=False)[:500]}"
        )

    # ── 过滤：只要文件（blob），不要目录（tree）──
    files = [
        item["path"]
        for item in body["tree"]
        if item.get("type") == "blob"
    ]

    print(f"  [GitHub API] {owner}/{repo} ({branch}): {len(files)} 个文件")
    return files
