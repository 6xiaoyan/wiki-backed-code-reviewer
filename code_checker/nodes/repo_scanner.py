"""
repo_scanner — 递归扫描仓库中的源代码文件。

遍历 repo_path 下的所有文件，过滤出 C++/Qt 源码文件（按扩展名），
将文件名列表和全文内容写入 state。
"""

import os
from code_checker.state import AgentState
from code_checker.config import SOURCE_EXTENSIONS
from code_checker.utils import read_file_content


def repo_scanner(state: AgentState) -> dict:
    print("[扫描] 启动...")

    file_list: list[str] = []
    file_contents: dict[str, str] = {}

    for root, dirs, files in os.walk(state["repo_path"]):
        for filename in files:
            ext = os.path.splitext(filename)[1].lower()
            if ext not in SOURCE_EXTENSIONS:
                continue

            file_path = os.path.join(root, filename)
            file_list.append(file_path)

            content = read_file_content(file_path)
            file_contents[file_path] = content if content is not None else "[读取失败]"

    print(f"  [扫描] {len(file_list)} 个文件")
    return {"file_list": file_list, "file_contents": file_contents}
