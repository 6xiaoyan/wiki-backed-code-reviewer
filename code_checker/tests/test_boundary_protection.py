"""压力测试：验证 snip_compact 边界保护在 100 个随机场景下无孤儿 tool_call。"""
import random
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage
from code_checker.context_compaction import run_compaction_pipeline


def test_random_scenarios():
    random.seed(42)
    for scenario in range(100):
        msgs = [SystemMessage(content="sys"), HumanMessage(content="hi")]
        call_id = 0
        for _ in range(random.randint(10, 40)):
            n_tools = random.randint(1, 5)
            tool_calls = [
                {"name": f"t{call_id + ti}", "args": {}, "id": f"id{call_id + ti}"}
                for ti in range(n_tools)
            ]
            call_id += n_tools
            msgs.append(AIMessage(content="", tool_calls=tool_calls))
            for ti in range(n_tools):
                tc_id = call_id - n_tools + ti
                msgs.append(ToolMessage(
                    content="r" + str(tc_id),
                    tool_call_id="id" + str(tc_id),
                    name="t" + str(tc_id),
                ))
        msgs.append(AIMessage(content="done"))

        compacted = run_compaction_pipeline(msgs, agent_name="test", telemetry=False)

        # 验证无孤儿
        tool_ids = {m.tool_call_id for m in compacted if isinstance(m, ToolMessage)}
        for m in compacted:
            if isinstance(m, AIMessage) and getattr(m, "tool_calls", None):
                for tc in m.tool_calls:
                    assert tc["id"] in tool_ids, (
                        f"scenario={scenario} orphan={tc['id']} "
                        f"msgs={len(msgs)}->{len(compacted)}"
                    )

    print("100/100 random scenarios passed!")


if __name__ == "__main__":
    test_random_scenarios()
