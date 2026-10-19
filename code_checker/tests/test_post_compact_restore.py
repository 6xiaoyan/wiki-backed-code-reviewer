"""验证 v2 context compaction 修复：ReadFileTracker、post_compact_restore、
L4CircuitBreaker、snip_compact 目标保护、micro_compact keep_recent 变更。"""

import time
import threading

import pytest
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage

from code_checker.context_compaction import (
    ReadFileTracker,
    L4CircuitBreaker,
    _extract_user_goal,
    post_compact_restore,
    snip_compact,
    micro_compact,
    compact_history,
    run_compaction_pipeline,
    CompactionHookFactory,
    register_tracker,
    unregister_tracker,
    get_tracker,
    register_breaker,
    get_breaker,
    DEFAULTS,
    POST_COMPACT_MAX_FILES,
    POST_COMPACT_MAX_CHARS_PER_FILE,
    POST_COMPACT_TOKEN_BUDGET,
    _BOUNDARY_MARKER,
)


# ============================================================================
# ReadFileTracker 测试
# ============================================================================

class TestReadFileTracker:
    """T1: ReadFileTracker 基本行为测试。"""

    def test_record_and_retrieve(self):
        """基本记录和恢复：记录的文件可在 get_recent 中检索。"""
        tracker = ReadFileTracker()
        tracker.record_read("/path/a.cpp", "content A")
        tracker.record_read("/path/b.cpp", "content B")

        recent = tracker.get_recent(n=5)
        assert len(recent) == 2
        paths = [p for p, _ in recent]
        assert "/path/b.cpp" in paths  # 最新的在前
        assert "/path/a.cpp" in paths

    def test_update_existing(self):
        """重复记录同一文件应更新内容和时间戳，移到 LRU 尾部。"""
        tracker = ReadFileTracker()
        tracker.record_read("/path/a.cpp", "old content")
        tracker.record_read("/path/b.cpp", "content B")
        tracker.record_read("/path/a.cpp", "new content")  # 更新

        recent = tracker.get_recent(n=2)
        assert len(recent) == 2
        # 最新的是 a.cpp（被更新并移到尾部）
        assert recent[0][0] == "/path/a.cpp"
        assert "new content" in recent[0][1]

    def test_lru_eviction(self):
        """超过 max_files 时淘汰最旧文件。"""
        tracker = ReadFileTracker(max_files=3)
        tracker.record_read("/path/1.cpp", "c1")
        tracker.record_read("/path/2.cpp", "c2")
        tracker.record_read("/path/3.cpp", "c3")
        tracker.record_read("/path/4.cpp", "c4")  # 触发淘汰：1.cpp 被移除

        recent = tracker.get_recent(n=10)
        paths = [p for p, _ in recent]
        assert "/path/1.cpp" not in paths
        assert len(paths) == 3

    def test_budget_total_chars(self):
        """get_recent 遵守 total_budget_chars 总预算。"""
        tracker = ReadFileTracker()
        content = "x" * 3000
        tracker.record_read("/path/a.cpp", content)
        tracker.record_read("/path/b.cpp", content)

        recent = tracker.get_recent(n=5, total_budget_chars=4000)
        # 两个文件各 3000 字符，总预算 4000 → 第二个文件应被截断或跳过
        total_chars = sum(len(c) for _, c in recent)
        assert total_chars <= 4200  # 允许小幅偏差（截断消息开销）

    def test_budget_max_chars_per_file(self):
        """get_recent 遵守单文件字符数限制。"""
        tracker = ReadFileTracker()
        tracker.record_read("/path/a.cpp", "y" * 8000)

        recent = tracker.get_recent(n=1, max_chars_per_file=3000)
        assert len(recent) == 1
        _, content = recent[0]
        assert len(content) <= 3100  # 允许截断消息开销

    def test_max_files_limit(self):
        """get_recent 遵守 n 参数的文件数限制。"""
        tracker = ReadFileTracker()
        for i in range(10):
            tracker.record_read(f"/path/{i}.cpp", f"content {i}")

        recent = tracker.get_recent(n=3)
        assert len(recent) == 3

    def test_clear(self):
        """clear() 后 tracker 为空。"""
        tracker = ReadFileTracker()
        tracker.record_read("/path/a.cpp", "content")
        tracker.clear()
        assert tracker.get_recent(n=10) == []

    def test_content_truncation_on_record(self):
        """record_read 自动截断超大内容。"""
        tracker = ReadFileTracker()
        huge = "z" * (ReadFileTracker.MAX_CONTENT_CHARS + 5000)
        tracker.record_read("/path/a.cpp", huge)

        recent = tracker.get_recent(n=1, max_chars_per_file=99999)
        _, content = recent[0]
        assert len(content) <= ReadFileTracker.MAX_CONTENT_CHARS + 200
        assert "截断" in content

    def test_thread_safety(self):
        """多线程并发 record_read 不丢数据、不崩溃。"""
        tracker = ReadFileTracker(max_files=50)
        errors = []

        def record_batch(start: int):
            try:
                for i in range(start, start + 100):
                    tracker.record_read(f"/path/{i}.cpp", f"content {i}")
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=record_batch, args=(i * 100,))
                    for i in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert not errors
        recent = tracker.get_recent(n=200)
        assert len(recent) <= 50  # max_files=50

    def test_empty_budget(self):
        """预算不足时不返回文件。"""
        tracker = ReadFileTracker()
        tracker.record_read("/path/a.cpp", "some content here")

        recent = tracker.get_recent(n=5, total_budget_chars=10)
        # 预算只有 10 字符，不足以放入任何文件（最小 200 字符才有意义）
        assert len(recent) == 0


# ============================================================================
# Tracker 注册表测试
# ============================================================================

class TestTrackerRegistry:
    """T1: ReadFileTracker per-agent 注册表测试。"""

    def test_register_and_get_exact_match(self):
        """精确 agent_name 匹配。"""
        tracker = ReadFileTracker()
        register_tracker("cpp_agent", tracker)
        try:
            assert get_tracker("cpp_agent") is tracker
        finally:
            unregister_tracker("cpp_agent")

    def test_prefix_match(self):
        """前缀匹配：'cpp_agent/file1' → 'cpp_agent'。"""
        tracker = ReadFileTracker()
        register_tracker("cpp_agent", tracker)
        try:
            assert get_tracker("cpp_agent/file1") is tracker
            assert get_tracker("cpp_agent/file5") is tracker
        finally:
            unregister_tracker("cpp_agent")

    def test_miss_returns_none(self):
        """未注册的 agent 返回 None。"""
        assert get_tracker("nonexistent_agent") is None

    def test_per_agent_isolation(self):
        """两个 agent 的 tracker 不互相污染。"""
        t1 = ReadFileTracker()
        t2 = ReadFileTracker()
        register_tracker("cpp_agent", t1)
        register_tracker("qt_agent", t2)
        try:
            t1.record_read("/path/cpp.cpp", "cpp content")
            t2.record_read("/path/qt.cpp", "qt content")

            r1 = get_tracker("cpp_agent")
            r2 = get_tracker("qt_agent")
            assert r1 is t1
            assert r2 is t2

            recent1 = r1.get_recent(n=5)
            recent2 = r2.get_recent(n=5)
            paths1 = [p for p, _ in recent1]
            paths2 = [p for p, _ in recent2]
            assert "/path/cpp.cpp" in paths1
            assert "/path/cpp.cpp" not in paths2
            assert "/path/qt.cpp" in paths2
            assert "/path/qt.cpp" not in paths1
        finally:
            unregister_tracker("cpp_agent")
            unregister_tracker("qt_agent")


# ============================================================================
# _extract_user_goal 测试
# ============================================================================

class TestExtractUserGoal:
    """T2: _extract_user_goal 行为测试。"""

    def test_normal_extraction(self):
        """正常提取第一条 HumanMessage。"""
        msgs = [
            SystemMessage(content="system"),
            HumanMessage(content="审查单个 C++ 文件（1/5）：/path/a.cpp"),
            AIMessage(content="ok"),
        ]
        goal = _extract_user_goal(msgs)
        assert goal is not None
        assert "/path/a.cpp" in goal

    def test_none_when_no_human(self):
        """无 HumanMessage 时返回 None。"""
        msgs = [
            SystemMessage(content="system"),
            AIMessage(content="hello"),
        ]
        assert _extract_user_goal(msgs) is None

    def test_long_goal_truncated(self):
        """超过 2000 字符的目标被截断。"""
        msgs = [
            HumanMessage(content="x" * 3000),
        ]
        goal = _extract_user_goal(msgs)
        assert goal is not None
        assert len(goal) <= 2100  # 2000 + 截断消息
        assert "截断" in goal

    def test_empty_string_goal(self):
        """空字符串 HumanMessage 返回 None。"""
        msgs = [HumanMessage(content="")]
        goal = _extract_user_goal(msgs)
        assert goal is None


# ============================================================================
# post_compact_restore 测试
# ============================================================================

class TestPostCompactRestore:
    """T3: post_compact_restore 核心修复验证。"""

    def _make_compacted(self, summary_text="[对话摘要] test summary"):
        """构造 compact_history 风格的输出。"""
        return [
            SystemMessage(content="You are a C++ code reviewer."),
            HumanMessage(content=summary_text),
            HumanMessage(content="I'll check file X."),
            AIMessage(content="Let me read the file."),
            ToolMessage(content="file content here", tool_call_id="tc1",
                         name="read_file"),
            AIMessage(content="File looks good."),
        ]

    def test_boundary_marker_present(self):
        """压缩恢复后消息列表中包含 Boundary Marker。"""
        original = [
            SystemMessage(content="sys"),
            HumanMessage(content="审查单个 C++ 文件（1/1）：/path/a.cpp"),
            AIMessage(content="ok"),
        ]
        compacted = self._make_compacted()
        result = post_compact_restore(compacted, original, "test_agent")

        messages_with_marker = [
            m for m in result
            if isinstance(m, SystemMessage) and "上下文分界" in str(m.content)
        ]
        assert len(messages_with_marker) == 1

    def test_boundary_marker_after_summary(self):
        """Boundary Marker 出现在摘要之后、近期消息之前。"""
        original = [
            SystemMessage(content="sys"),
            HumanMessage(content="任务：审查 /path/a.cpp"),
        ]
        compacted = self._make_compacted("[对话摘要] summary")
        result = post_compact_restore(compacted, original, "test_agent")

        # 找到摘要位置
        summary_idx = None
        boundary_idx = None
        for i, m in enumerate(result):
            content = str(getattr(m, "content", ""))
            if "[对话摘要]" in content:
                summary_idx = i
            if isinstance(m, SystemMessage) and "上下文分界" in content:
                boundary_idx = i

        assert summary_idx is not None
        assert boundary_idx is not None
        assert summary_idx < boundary_idx, (
            f"Boundary Marker ({boundary_idx}) 应在摘要 ({summary_idx}) 之后"
        )

    def test_goal_preserved(self):
        """用户目标在 compact 后出现在恢复内容中。"""
        original = [
            SystemMessage(content="sys"),
            HumanMessage(content="审查单个 C++ 文件（3/5）：/path/x.cpp"),
            AIMessage(content="ok"),
        ]
        compacted = self._make_compacted()
        result = post_compact_restore(compacted, original, "test_agent")

        goal_msgs = [
            m for m in result
            if isinstance(m, HumanMessage) and "[任务目标]" in str(m.content)
        ]
        assert len(goal_msgs) == 1
        assert "/path/x.cpp" in str(goal_msgs[0].content)

    def test_no_goal_when_none(self):
        """原始消息无 HumanMessage 时不崩溃，不注入目标消息。"""
        original = [SystemMessage(content="sys")]
        compacted = self._make_compacted()
        result = post_compact_restore(compacted, original, "test_agent")

        goal_msgs = [
            m for m in result
            if isinstance(m, HumanMessage) and "[任务目标]" in str(m.content)
        ]
        assert len(goal_msgs) == 0

    def test_file_restoration_with_tracker(self):
        """注册了 tracker 后，恢复内容包含文件。"""
        tracker = ReadFileTracker()
        tracker.record_read("/path/a.cpp", "int main() { return 0; }")
        register_tracker("test_file_agent", tracker)
        try:
            original = [
                HumanMessage(content="审查 /path/a.cpp"),
            ]
            compacted = self._make_compacted()
            result = post_compact_restore(compacted, original, "test_file_agent")

            file_msgs = [
                m for m in result
                if isinstance(m, HumanMessage) and "[恢复文件]" in str(m.content)
            ]
            assert len(file_msgs) >= 1
            assert "int main()" in str(file_msgs[0].content)
        finally:
            unregister_tracker("test_file_agent")

    def test_no_file_when_tracker_empty(self):
        """tracker 为空时不注入文件消息。"""
        register_tracker("empty_agent", ReadFileTracker())
        try:
            original = [HumanMessage(content="task")]
            compacted = self._make_compacted()
            result = post_compact_restore(compacted, original, "empty_agent")

            file_msgs = [
                m for m in result
                if isinstance(m, HumanMessage) and "[恢复文件]" in str(m.content)
            ]
            assert len(file_msgs) == 0
        finally:
            unregister_tracker("empty_agent")

    def test_no_summary_still_injects_restore(self):
        """即使没有摘要消息，恢复内容仍然注入。"""
        original = [HumanMessage(content="任务：审查文件")]
        compacted = [SystemMessage(content="sys"), AIMessage(content="hello")]
        result = post_compact_restore(compacted, original, "test_agent")

        # Boundary marker 应该存在
        markers = [
            m for m in result
            if isinstance(m, SystemMessage) and "上下文分界" in str(m.content)
        ]
        assert len(markers) == 1

    def test_system_messages_at_front(self):
        """SystemMessage 保持在消息列表最前面。"""
        original = [HumanMessage(content="task")]
        compacted = self._make_compacted()
        result = post_compact_restore(compacted, original, "test_agent")

        # 第一个消息应该是 SystemMessage
        assert isinstance(result[0], SystemMessage)
        # 规则 system message 在最前面
        assert "code reviewer" in str(result[0].content).lower()


# ============================================================================
# L4CircuitBreaker 测试
# ============================================================================

class TestL4CircuitBreaker:
    """T4: L4CircuitBreaker 熔断逻辑验证。"""

    def test_closed_to_open_after_consecutive_failures(self):
        """连续 3 次负节省率 → 熔断打开。"""
        breaker = L4CircuitBreaker(failure_threshold=3, min_savings_pct=-0.10)

        # -15% savings（负节省率超过 -10% 阈值）
        breaker.record_result(pre_tokens=1000, post_tokens=1150)
        assert not breaker.is_open
        assert breaker.failure_count == 1

        breaker.record_result(pre_tokens=1000, post_tokens=1200)
        assert not breaker.is_open
        assert breaker.failure_count == 2

        breaker.record_result(pre_tokens=1000, post_tokens=1150)
        assert breaker.is_open  # 第 3 次：熔断
        assert breaker.failure_count == 3

    def test_threshold_tolerance(self):
        """-5% 不触发（在 -10% 容限内），-15% 触发。"""
        breaker = L4CircuitBreaker(failure_threshold=3, min_savings_pct=-0.10)

        # -5%：在容限内，不计数
        breaker.record_result(pre_tokens=1000, post_tokens=1050)
        assert breaker.failure_count == 0

        # -15%：超出容限，计数
        breaker.record_result(pre_tokens=1000, post_tokens=1150)
        assert breaker.failure_count == 1

    def test_resets_on_positive_savings(self):
        """正节省率重置连续失败计数。"""
        breaker = L4CircuitBreaker(failure_threshold=3, min_savings_pct=-0.10)

        breaker.record_result(pre_tokens=1000, post_tokens=1200)  # failure
        breaker.record_result(pre_tokens=1000, post_tokens=1200)  # failure
        assert breaker.failure_count == 2

        breaker.record_result(pre_tokens=1000, post_tokens=600)   # success
        assert breaker.failure_count == 0

    def test_record_ignored_when_open(self):
        """熔断后 record_result 不改变状态。"""
        breaker = L4CircuitBreaker(failure_threshold=2, min_savings_pct=-0.10)

        breaker.record_result(pre_tokens=1000, post_tokens=1200)
        breaker.record_result(pre_tokens=1000, post_tokens=1200)
        assert breaker.is_open

        # 熔断后即使正节省率也不恢复
        breaker.record_result(pre_tokens=1000, post_tokens=500)
        assert breaker.is_open  # 仍然熔断

    def test_reset_after_manual(self):
        """手动 reset() 关闭熔断器。"""
        breaker = L4CircuitBreaker(failure_threshold=2, min_savings_pct=-0.10)

        breaker.record_result(pre_tokens=1000, post_tokens=1200)
        breaker.record_result(pre_tokens=1000, post_tokens=1200)
        assert breaker.is_open

        breaker.reset()
        assert not breaker.is_open
        assert breaker.failure_count == 0

    def test_zero_pre_tokens(self):
        """pre_tokens=0 时不崩溃。"""
        breaker = L4CircuitBreaker(failure_threshold=3, min_savings_pct=-0.10)
        breaker.record_result(pre_tokens=0, post_tokens=100)
        assert breaker.failure_count == 0  # savings_pct = 0，≥ -0.10，不触发


# ============================================================================
# snip_compact 目标保护 测试
# ============================================================================

class TestSnipCompactGoalProtection:
    """T6: snip_compact 第一条 HumanMessage 保护验证。"""

    def test_first_human_not_snipped(self):
        """第一条 HumanMessage 不被裁剪——即使 keep_head 很小。"""
        msgs = [
            SystemMessage(content="system"),
            HumanMessage(content="审查单个 C++ 文件（1/1）：/path/a.cpp"),
        ]
        # 构造足够多的消息使其超过 max_messages 阈值
        for i in range(40):
            msgs.append(AIMessage(content=f"thinking {i}"))
            msgs.append(ToolMessage(content=f"result {i}", tool_call_id=f"tc{i}",
                                     name="read_file"))

        result, action = snip_compact(
            msgs, max_messages=10, keep_head=1, keep_tail=5,
        )

        # 第一条 HumanMessage 必须保留
        human_contents = [
            str(m.content) for m in result
            if isinstance(m, HumanMessage) and "/path/a.cpp" in str(m.content)
        ]
        assert len(human_contents) >= 1, (
            "第一条 HumanMessage（任务目标）被裁剪了！"
        )

    def test_goal_not_triggered_when_within_head(self):
        """当 keep_head 已包含第一条 HumanMessage 时不改变行为。"""
        msgs = [
            SystemMessage(content="sys"),
            HumanMessage(content="task: review file"),
            AIMessage(content="ok"),
        ]
        for i in range(30):
            msgs.append(AIMessage(content=f"msg {i}"))
            msgs.append(ToolMessage(content=f"result {i}", tool_call_id=f"tc{i}",
                                     name="read_file"))

        # keep_head=5 应该已经包含了前 3 条消息（包括 HumanMessage）
        result, action = snip_compact(
            msgs, max_messages=15, keep_head=5, keep_tail=10,
        )
        assert action["triggered"]  # 应该仍然触发了裁剪
        # 第一条 HumanMessage 仍然存在
        human_msgs = [m for m in result if isinstance(m, HumanMessage)]
        task_msgs = [m for m in human_msgs if "task: review file" in str(m.content)]
        assert len(task_msgs) == 1


# ============================================================================
# micro_compact keep_recent 测试
# ============================================================================

class TestMicroCompactKeepRecent:
    """T5: micro_compact keep_recent=8 验证。"""

    def test_keep_recent_default_is_8(self):
        """DEFAULTS 中 keep_recent_tool_results 应为 8。"""
        assert DEFAULTS["keep_recent_tool_results"] == 8

    def test_micro_compact_keeps_8_when_default(self):
        """使用默认参数时保留最近 8 条 ToolMessage。"""
        msgs = [SystemMessage(content="sys")]
        for i in range(15):
            msgs.append(AIMessage(content=f"call {i}"))
            msgs.append(ToolMessage(
                content=f"x" * 200, tool_call_id=f"tc{i}", name="read_file"
            ))

        result, action = micro_compact(msgs)
        # 应该压缩了前 7 条（15 - 8 = 7）
        assert action["results_compacted"] == 7
        # 最近 8 条完整保留
        full_tools = [
            m for m in result
            if isinstance(m, ToolMessage) and "[已压缩]" not in str(m.content)
        ]
        assert len(full_tools) == 8

    def test_critical_tools_never_compacted(self):
        """白名单工具结果永不压缩。"""
        msgs = [SystemMessage(content="sys")]
        for i in range(10):
            msgs.append(AIMessage(content=f"call {i}"))
            name = "report_violation" if i < 3 else "read_file"
            msgs.append(ToolMessage(
                content=f"x" * 200, tool_call_id=f"tc{i}", name=name
            ))

        result, action = micro_compact(
            msgs, keep_recent=3,
            critical_tool_names={"report_violation"},
        )
        # report_violation 的 ToolMessage 不被压缩
        report_msgs = [
            m for m in result
            if isinstance(m, ToolMessage)
            and getattr(m, "name", None) == "report_violation"
            and "[已压缩]" not in str(m.content)
        ]
        assert len(report_msgs) == 3  # 全部 3 条 report_violation 保留

    def test_short_content_not_compacted(self):
        """短内容（≤120 字符）的 ToolMessage 不被压缩。"""
        msgs = [SystemMessage(content="sys")]
        for i in range(10):
            msgs.append(AIMessage(content=f"call {i}"))
            msgs.append(ToolMessage(
                content=f"short {i}", tool_call_id=f"tc{i}", name="tool"
            ))

        result, action = micro_compact(msgs, keep_recent=3)
        # 短内容不应该被替换为占位符
        assert action["results_compacted"] == 0


# ============================================================================
# CompactionHookFactory v2 集成测试
# ============================================================================

class TestCompactionHookFactoryV2:
    """T7: CompactionHookFactory v2 集成验证。"""

    def test_creates_per_agent_tracker(self):
        """CompactionHookFactory 创建 per-agent ReadFileTracker 并注册。"""
        factory = CompactionHookFactory(
            "test_integration_agent",
            critical_tool_names={"tool_a", "tool_b"},
        )
        try:
            # tracker 已注册
            tracker = get_tracker("test_integration_agent")
            assert tracker is not None
            assert tracker is factory.read_tracker

            # breaker 已创建
            assert factory.l4_breaker is not None
            assert not factory.l4_breaker.is_open
        finally:
            unregister_tracker("test_integration_agent")

    def test_tracker_isolation_between_factories(self):
        """两个 factory 的 tracker 互相隔离。"""
        f1 = CompactionHookFactory("agent_a")
        f2 = CompactionHookFactory("agent_b")
        try:
            f1.read_tracker.record_read("/path/a.cpp", "content A")
            f2.read_tracker.record_read("/path/b.cpp", "content B")

            r1 = f1.read_tracker.get_recent(n=5)
            r2 = f2.read_tracker.get_recent(n=5)

            paths1 = [p for p, _ in r1]
            paths2 = [p for p, _ in r2]
            assert "/path/a.cpp" in paths1
            assert "/path/a.cpp" not in paths2
            assert "/path/b.cpp" in paths2
            assert "/path/b.cpp" not in paths1
        finally:
            unregister_tracker("agent_a")
            unregister_tracker("agent_b")

    def test_hook_does_not_crash_without_messages(self):
        """空消息列表时 hook 不崩溃。"""
        factory = CompactionHookFactory("hook_test_agent")
        try:
            result = factory.hook({"messages": []})
            assert result == {}
        finally:
            unregister_tracker("hook_test_agent")


# ============================================================================
# F5: Breaker 持久化测试
# ============================================================================

class TestBreakerPersistence:
    """F2: L4CircuitBreaker 跨 CompactionHookFactory 持久化。"""

    def test_breaker_reused_across_factories(self):
        """同一 agent_name 的第二个 factory 复用已有 breaker。"""
        agent = "persist_test_agent"

        f1 = CompactionHookFactory(agent)
        try:
            b1 = f1.l4_breaker
            # 记录 2 次失败
            b1.record_result(1000, 1200)  # -20%, failure
            b1.record_result(1000, 1300)  # -30%, failure
            assert b1.failure_count == 2
            assert not b1.is_open
        finally:
            unregister_tracker(agent)

        # 第二个 factory（模拟第二轮 review_agent 调用）
        f2 = CompactionHookFactory(agent)
        try:
            b2 = f2.l4_breaker
            # 应该是同一个 breaker，状态延续
            assert b2 is b1
            assert b2.failure_count == 2

            # 第 3 次失败 → 熔断
            b2.record_result(1000, 1400)  # -40%, failure
            assert b2.failure_count == 3
            assert b2.is_open
        finally:
            unregister_tracker(agent)

    def test_breaker_registry_independent_agents(self):
        """不同 agent 的 breaker 互相隔离。"""
        fa = CompactionHookFactory("indep_agent_a")
        fb = CompactionHookFactory("indep_agent_b")
        try:
            ba = fa.l4_breaker
            bb = fb.l4_breaker

            assert ba is not bb  # 不同实例
            assert get_breaker("indep_agent_a") is ba
            assert get_breaker("indep_agent_b") is bb

            # agent_a 熔断，agent_b 不受影响
            for _ in range(3):
                ba.record_result(1000, 1200)
            assert ba.is_open
            assert not bb.is_open
        finally:
            unregister_tracker("indep_agent_a")
            unregister_tracker("indep_agent_b")

    def test_get_breaker_nonexistent(self):
        """未注册的 agent 返回 None。"""
        assert get_breaker("nonexistent_agent_xyz") is None


# ============================================================================
# F5: Post-compact 预算测试
# ============================================================================

class TestPostCompactRestoreBudget:
    """F4: 验证 POST_COMPACT_TOKEN_BUDGET / MAX_FILES 约束。"""

    def test_budget_values_reduced(self):
        """v2 预算已从 50K/5 调低到 20K/3。"""
        assert POST_COMPACT_TOKEN_BUDGET == 20000
        assert POST_COMPACT_MAX_FILES == 3

    def test_restore_respects_max_files_limit(self):
        """恢复内容不超过 POST_COMPACT_MAX_FILES 个文件。"""
        tracker = ReadFileTracker()
        agent = "budget_test_agent"
        register_tracker(agent, tracker)

        # 记录 5 个文件
        for i in range(5):
            tracker.record_read(f"/path/file_{i}.cpp", f"content of file {i}" * 50)

        working = [
            SystemMessage(content="system"),
            HumanMessage(content="任务：检查代码规范"),
            AIMessage(content="[对话摘要] 这是压缩后的摘要内容"),
        ]
        original = [
            SystemMessage(content="system"),
            HumanMessage(content="任务：检查代码规范"),
        ]

        result = post_compact_restore(working, original, agent)
        # 最多恢复 3 个文件
        file_count = sum(1 for m in result if isinstance(m, HumanMessage)
                         and "恢复文件" in str(m.content))
        assert file_count <= POST_COMPACT_MAX_FILES
        unregister_tracker(agent)

    def test_restore_respects_total_budget(self):
        """恢复内容总字符数不超过 POST_COMPACT_TOKEN_BUDGET。"""
        tracker = ReadFileTracker()
        agent = "budget_total_test"
        register_tracker(agent, tracker)

        # 记录大文件
        for i in range(3):
            tracker.record_read(f"/path/big_{i}.cpp", "x" * 15000)

        working = [
            SystemMessage(content="system"),
            HumanMessage(content="任务：检查代码规范"),
            AIMessage(content="[对话摘要] 压缩摘要"),
        ]
        original = [
            SystemMessage(content="system"),
            HumanMessage(content="任务：检查代码规范"),
        ]

        result = post_compact_restore(working, original, agent)
        # 验证结果中的内容总字符数不超过预算
        restore_msgs = [m for m in result if isinstance(m, HumanMessage)
                        and "恢复文件" in str(m.content)]
        total_chars = sum(len(str(m.content)) for m in restore_msgs)
        assert total_chars <= POST_COMPACT_TOKEN_BUDGET + 500  # 允许一些标记字符
        unregister_tracker(agent)
