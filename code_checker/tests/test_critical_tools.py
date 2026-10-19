"""验证 critical_tool_names 保护机制。"""
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage
from code_checker.context_compaction import run_compaction_pipeline


def test_critical_tool_protection():
    msgs = [
        HumanMessage(content="开始合并去重"),
        AIMessage(content="", tool_calls=[{"name": "get_all_violations", "args": {}, "id": "id1"}]),
        ToolMessage(content="违规数据: " + "x" * 500, tool_call_id="id1", name="get_all_violations"),
        AIMessage(content="", tool_calls=[{"name": "read_file", "args": {}, "id": "id2"}]),
        ToolMessage(content="文件内容: " + "y" * 500, tool_call_id="id2", name="read_file"),
        AIMessage(content="", tool_calls=[{"name": "get_rules_text", "args": {}, "id": "id3"}]),
        ToolMessage(content="规范文本: " + "z" * 500, tool_call_id="id3", name="get_rules_text"),
        AIMessage(content="", tool_calls=[{"name": "read_file", "args": {}, "id": "id4"}]),
        ToolMessage(content="另一个文件: " + "w" * 500, tool_call_id="id4", name="read_file"),
        AIMessage(content="", tool_calls=[{"name": "read_file", "args": {}, "id": "id5"}]),
        ToolMessage(content="第三个文件: " + "v" * 500, tool_call_id="id5", name="read_file"),
    ]

    # 无保护：L2 压缩掉 get_all_violations 和 get_rules_text
    result_no = run_compaction_pipeline(
        list(msgs), agent_name="test", telemetry=False,
        keep_recent_tool_results=3,
    )

    # 有保护
    result_yes = run_compaction_pipeline(
        list(msgs), agent_name="test", telemetry=False,
        keep_recent_tool_results=3,
        critical_tool_names={"get_all_violations", "get_rules_text"},
    )

    def find_tool(msgs, name):
        return [m for m in msgs if isinstance(m, ToolMessage) and getattr(m, "name", None) == name]

    # 无保护：get_all_violations 被压缩
    no_protect = find_tool(result_no, "get_all_violations")
    assert no_protect, "get_all_violations ToolMessage should exist"
    assert "已压缩" in no_protect[0].content, (
        f"无保护时 get_all_violations 应被压缩, 实际: {no_protect[0].content[:80]}"
    )

    # 有保护：get_all_violations 完整
    protected = find_tool(result_yes, "get_all_violations")
    assert protected, "get_all_violations ToolMessage should exist"
    assert "违规数据" in protected[0].content, (
        f"有保护时 get_all_violations 不应被压缩, 实际: {protected[0].content[:80]}"
    )

    # 有保护：get_rules_text 完整
    rules = find_tool(result_yes, "get_rules_text")
    assert rules and "规范文本" in rules[0].content, "get_rules_text 不应被压缩"

    # read_file 仍然被压缩（不在 critical 列表）
    read_results = find_tool(result_yes, "read_file")
    compacted = [m for m in read_results if "已压缩" in str(m.content)]
    assert len(compacted) > 0, "非关键的 read_file 应被正常压缩"

    print("critical_tool_names 保护机制验证通过!")


if __name__ == "__main__":
    test_critical_tool_protection()
