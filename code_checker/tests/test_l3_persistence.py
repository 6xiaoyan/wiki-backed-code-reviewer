"""验证 L3 tool_result_persist 落盘持久化。"""
import os
import tempfile
import shutil
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage
from code_checker.context_compaction import (
    tool_result_persist, _persist_large_output, _get_persist_dir,
    _PERSIST_DIR,
)


def test_persist_large_output_creates_file():
    """大结果落盘后文件存在且内容完整。"""
    # 使用临时目录避免污染
    import code_checker.context_compaction as m
    old_dir = m._PERSIST_DIR
    tmpdir = tempfile.mkdtemp()
    m._PERSIST_DIR = tmpdir
    try:
        content = "x" * 15000
        result = _persist_large_output("test_id_1", content)

        # 验证返回的标记格式
        assert "<persisted-output>" in result
        assert "Full output:" in result
        assert "Preview" in result
        assert content[:2000] in result
        assert "15000 chars total" in result

        # 验证文件落盘
        filepath = os.path.join(tmpdir, "test_id_1.txt")
        assert os.path.exists(filepath)
        with open(filepath, "r", encoding="utf-8") as f:
            saved = f.read()
        assert saved == content
    finally:
        m._PERSIST_DIR = old_dir
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_tool_result_persist_large():
    """超 threshold 的 ToolMessage 被持久化。"""
    msgs = [
        SystemMessage(content="sys"),
        HumanMessage(content="hi"),
        AIMessage(content="", tool_calls=[{"name": "big_result", "args": {}, "id": "id1"}]),
        ToolMessage(content="a" * 15000, tool_call_id="id1", name="big_result"),
        AIMessage(content="", tool_calls=[{"name": "small_result", "args": {}, "id": "id2"}]),
        ToolMessage(content="hello", tool_call_id="id2", name="small_result"),
    ]

    import code_checker.context_compaction as m
    old_dir = m._PERSIST_DIR
    tmpdir = tempfile.mkdtemp()
    m._PERSIST_DIR = tmpdir
    try:
        result, action = tool_result_persist(msgs, persist_threshold=10000)

        # 验证 action
        assert action["triggered"] is True
        assert action["results_persisted"] == 1
        assert action["chars_saved"] == 13000  # 15000 - 2000

        # 大结果被替换
        big_tool = [m for m in result if isinstance(m, ToolMessage) and m.tool_call_id == "id1"]
        assert len(big_tool) == 1
        assert "<persisted-output>" in big_tool[0].content
        assert "a" * 2000 in big_tool[0].content  # preview

        # 小结果不变
        small_tool = [m for m in result if isinstance(m, ToolMessage) and m.tool_call_id == "id2"]
        assert len(small_tool) == 1
        assert small_tool[0].content == "hello"

        # 文件落盘
        assert os.path.exists(os.path.join(tmpdir, "id1.txt"))
    finally:
        m._PERSIST_DIR = old_dir
        shutil.rmtree(tmpdir, ignore_errors=True)


def test_tool_result_persist_critical_tool_skipped():
    """关键工具结果不落盘（保持完整）。"""
    msgs = [
        SystemMessage(content="sys"),
        AIMessage(content="", tool_calls=[{"name": "get_rules_text", "args": {}, "id": "id1"}]),
        ToolMessage(content="r" * 15000, tool_call_id="id1", name="get_rules_text"),
    ]

    result, action = tool_result_persist(
        msgs,
        persist_threshold=10000,
        critical_tool_names={"get_rules_text"},
    )

    assert action["triggered"] is False
    rules_tool = [m for m in result if isinstance(m, ToolMessage) and m.tool_call_id == "id1"]
    assert "r" * 15000 == rules_tool[0].content  # 没有被替换


def test_tool_result_persist_below_threshold():
    """未超 threshold 的结果不处理。"""
    msgs = [
        SystemMessage(content="sys"),
        AIMessage(content="", tool_calls=[{"name": "read", "args": {}, "id": "id1"}]),
        ToolMessage(content="short", tool_call_id="id1", name="read"),
    ]

    result, action = tool_result_persist(msgs, persist_threshold=10000)

    assert action["triggered"] is False
    assert result[2].content == "short"


if __name__ == "__main__":
    test_persist_large_output_creates_file()
    print("test_persist_large_output_creates_file: PASS")
    test_tool_result_persist_large()
    print("test_tool_result_persist_large: PASS")
    test_tool_result_persist_critical_tool_skipped()
    print("test_tool_result_persist_critical_tool_skipped: PASS")
    test_tool_result_persist_below_threshold()
    print("test_tool_result_persist_below_threshold: PASS")
    print("All L3 persistence tests passed!")
