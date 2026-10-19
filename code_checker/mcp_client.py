"""
mcp_client — MCP 协议客户端封装。

MCP（Model Context Protocol）是 AI 应用接入外部工具的标准协议。
它本质上是 JSON-RPC 2.0 通过子进程的标准输入/输出通信。

这个模块封装了与 GitHub MCP 服务器的通信细节，对外暴露三个函数：
  - connect_github_mcp(): 启动 GitHub MCP 服务器，完成握手，返回会话
  - call_mcp_tool():     调用 MCP 服务器暴露的任意工具
  - disconnect_mcp():    关闭连接，清理子进程

通信流程示意：

    你的 Python 代码
        │
        ├─ ① 启动子进程: npx @modelcontextprotocol/server-github
        │       通过环境变量 GITHUB_PERSONAL_ACCESS_TOKEN 传认证令牌
        │
        ├─ ② 握手: 发送 initialize 请求 → 收到协议版本和能力声明
        │
        ├─ ③ 发现工具: 发送 tools/list 请求 → 收到工具清单
        │       [search_repositories, get_file_contents, list_commits, ...]
        │
        ├─ ④ 调用工具: 发送 tools/call 请求 → 收到执行结果
        │
        └─ ⑤ 关闭子进程

参考: https://modelcontextprotocol.io/docs/concepts/architecture
"""

import os
import json
import subprocess
import threading
from typing import Any

# ============================================================================
# 配置
# ============================================================================

GITHUB_MCP_SERVER = "@modelcontextprotocol/server-github"
"""GitHub MCP 服务器的 npm 包名，由 npx 自动下载和启动。"""

MCP_PROTOCOL_VERSION = "2024-11-05"
"""MCP 协议版本。"""


# ============================================================================
# 连接管理
# ============================================================================


def connect_github_mcp(github_token: str = "") -> tuple[subprocess.Popen, dict, list[dict]]:
    """启动 GitHub MCP 服务器并完成协议握手。

    这个函数做三件事：
    1. 启动一个子进程运行 GitHub MCP 服务器
    2. 发送 initialize 请求完成协议握手
    3. 发送 tools/list 请求获取服务器提供的工具清单

    Args:
        github_token: GitHub Personal Access Token。如果不传，尝试从环境变量
                      GITHUB_TOKEN 或 GITHUB_PERSONAL_ACCESS_TOKEN 读取。

    Returns:
        (process, server_info, tools) 三元组：
        - process:     子进程对象，用于后续工具调用和最终关闭
        - server_info: 服务器声明的能力信息（名称、版本等）
        - tools:       工具清单列表，每条包含 name/description/inputSchema

    Raises:
        RuntimeError: 子进程启动失败或协议握手失败
        ValueError:  未找到 GitHub 令牌
    """
    # ── 解析令牌 ──
    token = github_token or os.environ.get("GITHUB_TOKEN") or os.environ.get("GITHUB_PERSONAL_ACCESS_TOKEN", "")
    if not token:
        raise ValueError(
            "GitHub 令牌未设置。请通过以下任一方式提供：\n"
            "  1. 参数传入: connect_github_mcp('ghp_xxx')\n"
            "  2. 环境变量: $env:GITHUB_TOKEN = 'ghp_xxx'\n"
            "  3. 在 GitHub Settings → Developer settings → Personal access tokens 生成"
        )

    # ── 启动 MCP 服务器子进程 ──
    # 服务器通过 stdin/stdout 与客户端通信（每行一个 JSON-RPC 消息）
    # stderr 保留用于服务器日志输出
    try:
        process = subprocess.Popen(
            ["npx", "-y", GITHUB_MCP_SERVER],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8",
            env={
                **os.environ,
                "GITHUB_PERSONAL_ACCESS_TOKEN": token,
            },
        )
    except FileNotFoundError:
        raise RuntimeError(
            "无法启动 GitHub MCP 服务器。请确认 Node.js 和 npx 已安装。\n"
            "  node --version  # 检查 Node.js\n"
            "  npx --version   # 检查 npx"
        )

    # ── 协议握手：initialize ──
    server_info = _send_request(process, "initialize", {
        "protocolVersion": MCP_PROTOCOL_VERSION,
        "capabilities": {},
        "clientInfo": {
            "name": "code-checker",
            "version": "1.0.0",
        },
    })

    if "error" in server_info:
        _safe_kill(process)
        raise RuntimeError(f"MCP 握手失败: {server_info['error']}")

    server_name = server_info.get("result", {}).get("serverInfo", {}).get("name", "unknown")
    server_version = server_info.get("result", {}).get("serverInfo", {}).get("version", "?")
    print(f"  [MCP] 已连接到 {server_name} v{server_version}")

    # ── 必须发送 initialized 通知 ──
    _send_notification(process, "notifications/initialized", {})

    # ── 获取工具清单：tools/list ──
    tools_response = _send_request(process, "tools/list", {})
    tools = tools_response.get("result", {}).get("tools", [])

    tool_names = [t["name"] for t in tools]
    print(f"  [MCP] 服务器暴露 {len(tools)} 个工具: {', '.join(tool_names[:8])}"
          f"{'...' if len(tools) > 8 else ''}")

    return process, server_info.get("result", {}), tools


def disconnect_mcp(process: subprocess.Popen) -> None:
    """关闭 MCP 连接，终止子进程。

    Args:
        process: connect_github_mcp 返回的子进程对象
    """
    if process is None:
        return
    try:
        _safe_kill(process)
        print("  [MCP] 连接已关闭")
    except Exception:
        pass  # 子进程可能已经自己结束了


# ============================================================================
# 工具调用
# ============================================================================


def call_mcp_tool(process: subprocess.Popen, tool_name: str, arguments: dict[str, Any]) -> Any:
    """调用 MCP 服务器暴露的任意工具。

    Args:
        process:   connect_github_mcp 返回的子进程对象
        tool_name: 工具名称，如 "get_file_contents"
        arguments: 传给工具的参数，如 {"owner": "x", "repo": "y", "path": "z"}

    Returns:
        工具执行结果（Python 原生类型，从 JSON 反序列化而来）

    Raises:
        RuntimeError: 工具调用失败或返回错误
    """
    response = _send_request(process, "tools/call", {
        "name": tool_name,
        "arguments": arguments,
    })

    if "error" in response:
        error_msg = response["error"]
        raise RuntimeError(f"MCP 工具 '{tool_name}' 调用失败: {error_msg}")

    result = response.get("result", {})
    content = result.get("content", [])

    # ── 解析返回内容 ──
    # MCP 协议: content 是一个列表，每项是 {"type": "text", "text": "..."}
    # 也可能直接是字符串
    if isinstance(content, list) and len(content) > 0:
        texts = [item.get("text", "") for item in content if isinstance(item, dict)]
        return "\n".join(texts) if len(texts) > 1 else (texts[0] if texts else "")
    if isinstance(content, str):
        return content
    return content


def list_mcp_tools(process: subprocess.Popen) -> list[dict]:
    """重新获取工具清单（用于调试或动态发现）。"""
    response = _send_request(process, "tools/list", {})
    return response.get("result", {}).get("tools", [])


# ============================================================================
# JSON-RPC 底层通信
# ============================================================================

# 请求 ID 计数器 + 线程锁（保证并发安全）
_next_id = 0
_id_lock = threading.Lock()


def _next_request_id() -> int:
    """生成递增的 JSON-RPC 请求 ID（线程安全）。"""
    global _next_id
    with _id_lock:
        _next_id += 1
        return _next_id


def _send_request(process: subprocess.Popen, method: str, params: dict) -> dict:
    """发送 JSON-RPC 2.0 请求并等待响应。

    协议格式：
      请求:  {"jsonrpc": "2.0", "id": N, "method": "...", "params": {...}}
      响应:  {"jsonrpc": "2.0", "id": N, "result": {...}}
      错误:  {"jsonrpc": "2.0", "id": N, "error": {...}}

    Args:
        process: 子进程对象
        method:  JSON-RPC 方法名
        params:  参数字典

    Returns:
        解析后的响应 JSON 字典
    """
    request_id = _next_request_id()
    request = {
        "jsonrpc": "2.0",
        "id": request_id,
        "method": method,
        "params": params,
    }

    # ── 发送请求到子进程的 stdin ──
    request_json = json.dumps(request, ensure_ascii=False)
    try:
        process.stdin.write(request_json + "\n")
        process.stdin.flush()
    except (BrokenPipeError, OSError) as e:
        raise RuntimeError(f"MCP 通信中断（子进程可能已退出）: {e}")

    # ── 从子进程的 stdout 读取响应 ──
    # 响应可能跨多行（如工具返回多行文本），但 JSON-RPC 协议保证
    # 每条响应是完整的一行 JSON
    try:
        response_line = process.stdout.readline()
    except Exception as e:
        raise RuntimeError(f"读取 MCP 响应失败: {e}")

    if not response_line:
        # 检查 stderr 获取进程退出原因
        stderr_output = ""
        try:
            returncode = process.poll()
            if returncode is not None:
                stderr_output = process.stderr.read()
        except Exception:
            pass
        raise RuntimeError(
            f"MCP 服务器无响应（进程可能已退出，返回码={process.poll()}）\n"
            f"stderr: {stderr_output[:500] if stderr_output else '(无输出)'}"
        )

    try:
        response = json.loads(response_line.strip())
    except json.JSONDecodeError:
        raise RuntimeError(f"MCP 响应不是合法 JSON: {response_line[:200]}")

    return response


def _send_notification(process: subprocess.Popen, method: str, params: dict) -> None:
    """发送 JSON-RPC 2.0 通知（无 id，不等待响应）。

    用于 initialized 通知等协议要求的单向消息。

    Args:
        process: 子进程对象
        method:  通知方法名
        params:  参数字典
    """
    notification = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
    }
    request_json = json.dumps(notification, ensure_ascii=False)
    try:
        process.stdin.write(request_json + "\n")
        process.stdin.flush()
    except (BrokenPipeError, OSError):
        pass  # 通知是 fire-and-forget，失败也不阻塞


def _safe_kill(process: subprocess.Popen) -> None:
    """安全终止子进程。先尝试优雅关闭，超时后强制结束。"""
    if process is None:
        return
    try:
        # 关闭 stdin，告诉子进程没有更多输入
        if process.stdin:
            process.stdin.close()
    except Exception:
        pass
    try:
        process.terminate()
        process.wait(timeout=5)
    except subprocess.TimeoutExpired:
        process.kill()
        process.wait()
    except Exception:
        pass
