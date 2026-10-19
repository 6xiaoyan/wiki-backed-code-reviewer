"""验证 critical_guard 硬限保护。"""
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage
from code_checker.context_compaction import critical_guard, _estimate_chars


def test_no_trigger_below_limit():
    """未超硬限时不触发。"""
    msgs = [
        SystemMessage(content="sys"),
        HumanMessage(content="hello"),
        AIMessage(content="ok"),
    ]

    result, action = critical_guard(msgs, critical_char_limit=1000)
    assert action["triggered"] is False
    assert result == msgs


def test_triggers_above_limit():
    """超硬限时触发激进裁剪。"""
    msgs = [SystemMessage(content="sys")]
    # 添加大量消息使字符数超过限制
    for i in range(100):
        msgs.append(HumanMessage(content=f"message {i}: " + "x" * 200))
        msgs.append(AIMessage(content=f"response {i}: " + "y" * 200))

    result, action = critical_guard(msgs, critical_char_limit=5000)

    assert action["triggered"] is True
    assert action["messages_cut"] > 0
    # 结果应该比原来短
    assert len(result) < len(msgs)
    # SystemMessage 在最前面
    assert isinstance(result[0], SystemMessage)


def test_keep_recent_context():
    """裁剪后保留最近的对话上下文。"""
    msgs = [
        SystemMessage(content="sys"),
        HumanMessage(content="task: check file.cpp"),
        AIMessage(content="ok"),
    ]
    # 前面填充大量旧消息
    for i in range(50):
        msgs.insert(1, HumanMessage(content="x" * 300))
        msgs.insert(2, AIMessage(content="y" * 300))

    # 末尾是最近的对话
    msgs.append(HumanMessage(content="what about line 42?"))
    msgs.append(AIMessage(content="found tab at line 42"))

    result, action = critical_guard(msgs, critical_char_limit=5000)

    assert action["triggered"] is True
    # 尾部最近消息应保留
    assert any("what about line 42" in str(m.content) for m in result)
    assert any("found tab at line 42" in str(m.content) for m in result)
    # 占位符在中间
    assert any("紧急裁剪" in str(m.content) for m in result if isinstance(m, HumanMessage))


def test_no_orphans_after_cut():
    """裁剪后无孤儿 tool_call。"""
    msgs = [SystemMessage(content="sys")]
    # 构造 tool_use/tool_result 配对
    for i in range(30):
        call_id = f"id{i}"
        msgs.append(AIMessage(content="", tool_calls=[
            {"name": f"check_{i}", "args": {}, "id": call_id}
        ]))
        msgs.append(ToolMessage(content="r" * 500, tool_call_id=call_id, name=f"check_{i}"))

    result, action = critical_guard(msgs, critical_char_limit=8000)

    assert action["triggered"] is True
    # 验证无孤儿
    tool_ids = {m.tool_call_id for m in result if isinstance(m, ToolMessage)}
    for m in result:
        if isinstance(m, AIMessage) and getattr(m, "tool_calls", None):
            for tc in m.tool_calls:
                assert tc["id"] in tool_ids, f"orphan tool_call: {tc['id']}"


if __name__ == "__main__":
    test_no_trigger_below_limit()
    print("test_no_trigger_below_limit: PASS")
    test_triggers_above_limit()
    print("test_triggers_above_limit: PASS")
    test_keep_recent_context()
    print("test_keep_recent_context: PASS")
    test_no_orphans_after_cut()
    print("test_no_orphans_after_cut: PASS")
    print("All critical_guard tests passed!")
