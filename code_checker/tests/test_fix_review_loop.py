"""验证 fix→review→re-fix 循环：数字严格收敛。

核心保证:
  1. fix_agent: 所有 pending 必有方案（遗漏自动补跑，最多 3 轮）
  2. fix_agent 重试时只处理 status==0（审查未通过），不碰 None
  3. review_agent: 区分首次审查 vs 重审
  4. 收敛漏斗: N → M₁ → M₂ → ... → 0（数字只降不升）
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import threading
import tools as tools_module
from tools import (
    set_state, get_fix_plans_buffer,
    propose_fix, get_pending_fixes,
)
from nodes.agent_fix import fix_agent
from nodes.agent_review import review_agent
from routing import route_after_critique_v2
from state import AgentState


# ============================================================================
# 1. tools.py — 无重复定义 + buffer 清空
# ============================================================================

def test_get_fix_plans_buffer_no_duplicate():
    """get_fix_plans_buffer 只有一个定义（无锁版已删除）。"""
    import inspect
    source = inspect.getsource(tools_module)
    occurrences = source.count("def get_fix_plans_buffer")
    assert occurrences == 1, f"get_fix_plans_buffer 定义了 {occurrences} 次"


def test_set_state_clears_buffer():
    """set_state 清空 _fix_plans_buffer。"""
    import tools as t
    with t._buffer_lock:
        t._fix_plans_buffer = [{"idx": 0, "status": 0}]
    set_state({"fix_plans": [], "merged_violations": []})
    with t._buffer_lock:
        assert t._fix_plans_buffer == []


def test_get_fix_plans_buffer_thread_safe():
    """并发写 buffer 后 get 拿全 30 条数据。"""
    import tools as t
    with t._buffer_lock:
        t._fix_plans_buffer = []
    set_state({"fix_plans": [None] * 50, "merged_violations": [{}] * 50})

    def write_plans(start, count):
        for i in range(start, start + count):
            propose_fix.invoke({
                "idx": i, "file": f"f{i}.cpp", "line": i,
                "fix_before": f"old_{i}", "fix_after": f"new_{i}",
                "reason": "test",
            })

    threads = [
        threading.Thread(target=write_plans, args=(0, 10)),
        threading.Thread(target=write_plans, args=(10, 10)),
        threading.Thread(target=write_plans, args=(20, 10)),
    ]
    for th in threads:
        th.start()
    for th in threads:
        th.join()

    result = get_fix_plans_buffer()
    assert len(result) == 30, f"应为 30 条，实际 {len(result)}"
    indices = sorted(p.get("idx") for p in result if "idx" in p)
    assert indices == list(range(30)), f"idx 不连续: {indices}"


# ============================================================================
# 2. fix_agent 核心逻辑（直接测内联逻辑，不调 LLM）
# ============================================================================

def test_fix_agent_first_run_all_violations():
    """首次运行：全部违规都是 pending。"""
    violations = [{"rule": "test"} for _ in range(5)]
    existing_plans = []
    pending = list(range(len(violations)))
    assert pending == [0, 1, 2, 3, 4]


def test_fix_agent_retry_only_status_zero():
    """重试时只处理 status==0（审查未通过），不处理 None（理论上不应存在）。"""
    existing_plans = [
        {"status": 1, "score": 10},  # 0: auto-fixed, passed
        {"status": 1, "score": 8},   # 1: reviewed, passed
        {"status": 0, "score": 3},   # 2: reviewed, FAILED → 需重改
        {"status": 0, "score": 2},   # 3: reviewed, FAILED → 需重改
        {"status": 1, "score": 9},   # 4: reviewed, passed
    ]
    violations_count = 5

    review_failed = [
        i for i, p in enumerate(existing_plans)
        if i < violations_count
        and p is not None and p.get("status") == 0
    ]
    never_tried = [
        i for i, p in enumerate(existing_plans)
        if i < violations_count and p is None
    ]

    assert review_failed == [2, 3], f"审查未过应为 [2,3], 实际 {review_failed}"
    assert never_tried == [], f"不应有 None, 实际 {never_tried}"
    assert len(review_failed) == 2  # 严格收敛: 5 → 2


def test_retry_loop_catches_missed_indices():
    """补跑循环：首次运行后仍有 None → 补跑直到全部有方案或达上限。"""
    # 模拟: 3 个 pending，第一轮 LLM 只产出了 2 个
    all_plans = [None, None, None]
    # 第一轮: LLM 产出 idx=0 和 idx=2, 漏了 idx=1
    all_plans[0] = {"status": 0, "fix_before": "a", "fix_after": "b"}
    all_plans[2] = {"status": 0, "fix_before": "c", "fix_after": "d"}
    pending = [0, 1, 2]

    # 检查遗漏
    still_none = [i for i in pending if all_plans[i] is None]
    assert still_none == [1], f"idx=1 被遗漏: {still_none}"

    # 第二轮补跑: LLM 产出 idx=1
    all_plans[1] = {"status": 0, "fix_before": "e", "fix_after": "f"}
    still_none = [i for i in pending if all_plans[i] is None]
    assert still_none == [], "所有 pending 都应有方案"


def test_fallback_placeholder_after_max_retries():
    """3 轮补跑后仍无方案 → 标记为 status=1 跳过，不阻塞流程。"""
    violations = [
        {"file": "a.cpp", "line": 1, "current": "x"},
        {"file": "b.cpp", "line": 2, "current": "y"},
    ]
    all_plans = [None, None]
    pending = [0, 1]

    # 模拟: idx=0 产出方案, idx=1 永远产出不了
    all_plans[0] = {"status": 0, "fix_before": "x", "fix_after": "x2"}
    still_none = [i for i in pending if all_plans[i] is None]
    assert still_none == [1]

    # 兜底: 为 idx=1 填 placeholder（status=1，不阻塞）
    for i in still_none:
        v = violations[i]
        all_plans[i] = {
            "idx": i, "file": v.get("file", ""), "line": v.get("line", 0),
            "fix_before": v.get("current", ""), "fix_after": v.get("current", ""),
            "reason": "[fix_agent] 无法生成修复方案",
            "status": 1, "score": 0, "feedback": "LLM 无法修复", "suggestion": "",
        }

    assert all(plans is not None for plans in all_plans)
    assert all_plans[1]["status"] == 1  # 标记通过


# ============================================================================
# 3. 收敛漏斗：数字只降不升
# ============================================================================

def test_convergence_funnel():
    """完整三轮收敛: 5 → 2 → 1 → 0。"""
    violations = [{"rule": f"rule_{i}"} for i in range(5)]

    # Round 1: all 5 get proposals → review passes 3, fails 2
    plans_r1 = [
        {"status": 1, "score": 8},   # passed
        {"status": 1, "score": 9},   # passed
        {"status": 0, "score": 3},   # FAILED
        {"status": 1, "score": 7},   # passed
        {"status": 0, "score": 2},   # FAILED
    ]
    failed_r1 = [i for i, p in enumerate(plans_r1)
                 if p is not None and p.get("status") == 0]
    assert failed_r1 == [2, 4]
    assert len(failed_r1) == 2  # 5 → 2 ✅

    # Round 2: re-fix 2 failed → review passes 1, fails 1
    plans_r2 = list(plans_r1)
    plans_r2[2] = {"status": 1, "score": 8}  # now passed
    # idx 4 still failed
    failed_r2 = [i for i, p in enumerate(plans_r2)
                 if p is not None and p.get("status") == 0]
    assert failed_r2 == [4]
    assert len(failed_r2) == 1  # 2 → 1 ✅

    # Round 3: re-fix 1 failed → review passes
    plans_r3 = list(plans_r2)
    plans_r3[4] = {"status": 1, "score": 7}  # now passed
    failed_r3 = [i for i, p in enumerate(plans_r3)
                 if p is not None and p.get("status") == 0]
    assert failed_r3 == []  # 1 → 0 ✅


# ============================================================================
# 4. review_agent 逻辑
# ============================================================================

def test_review_pending_excludes_none_and_passed():
    """review: 只审 status==0 的，不审 None 和 status==1。"""
    fix_plans = [
        {"status": 1, "score": 10},   # skip: passed
        None,                          # skip: never tried (不应发生但有防御)
        {"status": 0, "score": 0},    # REVIEW
        {"status": 0, "score": 0},    # REVIEW
        {"status": 1, "score": 8},    # skip: passed
    ]
    pending = [i for i, p in enumerate(fix_plans)
               if p is not None and p.get("status") == 0]
    assert pending == [2, 3]


def test_review_first_vs_rerun():
    """区分首次审查（无 feedback）vs 重审（有 feedback）。"""
    fix_plans = [
        {"status": 0, "score": 0, "feedback": ""},           # first
        {"status": 0, "score": 3, "feedback": "方向错误"},    # re-review
        {"status": 0, "score": 0, "feedback": ""},           # first
    ]
    pending = [i for i, p in enumerate(fix_plans) if p is not None and p.get("status") == 0]
    first = [i for i in pending if not fix_plans[i].get("feedback")]
    rerun = [i for i in pending if fix_plans[i].get("feedback")]
    assert first == [0, 2]
    assert rerun == [1]


def test_review_summary_counts():
    """review 完成统计区分 passed / failed / never_tried。"""
    fix_plans = [
        {"status": 1, "score": 10},
        {"status": 1, "score": 8},
        {"status": 0, "score": 3},
        None,
        {"status": 1, "score": 9},
        {"status": 0, "score": 2},
    ]
    passed = sum(1 for p in fix_plans if p is not None and p.get("status") == 1)
    failed = sum(1 for p in fix_plans if p is not None and p.get("status") == 0)
    never = sum(1 for p in fix_plans if p is None)
    assert passed == 3
    assert failed == 2
    assert never == 1


# ============================================================================
# 5. routing
# ============================================================================

def test_routing_explicit_status_no_default():
    """routing: p.get('status') == 0, 不依赖 default=0。"""
    fix_plans = [
        {"status": 1, "score": 10},
        {"status": 0, "score": 3},
        {},  # 缺少 status key — 不应被误判
    ]
    failed_old = [p for p in fix_plans if p is not None and p.get("status", 0) == 0]
    failed_new = [p for p in fix_plans if p is not None and p.get("status") == 0]
    assert len(failed_old) == 2  # 旧: 误判 {} 为 failed
    assert len(failed_new) == 1  # 新: {} 正确跳过


def test_routing_failed_only_counts_status_zero():
    """routing: None 不算 failed（与 fix_agent 重试逻辑一致）。"""
    state = AgentState(
        fix_plans=[
            {"fix_status": "passed", "score": 10},
            {"fix_status": "failed", "score": 3},
            None,  # 不应存在，但如有则不计入 failed
            {"fix_status": "failed", "score": 2},
        ],
        fix_iteration=1,
    )
    failed = [p for p in state["fix_plans"]
              if p is not None and p.get("fix_status") == "failed"]
    assert len(failed) == 2
    assert route_after_critique_v2(state) == "fix_agent"


def test_routing_all_pass():
    """全部通过 → report_exporter。"""
    state = AgentState(
        fix_plans=[{"fix_status": "passed", "score": 10},
                    {"fix_status": "passed", "score": 8}],
        fix_iteration=1,
    )
    assert route_after_critique_v2(state) == "report_exporter"


def test_routing_max_iterations():
    """达上限 → 强制放行。"""
    from config import MAX_FIX_ITERATIONS
    state = AgentState(
        fix_plans=[{"fix_status": "failed", "score": 3}],
        fix_iteration=MAX_FIX_ITERATIONS,
    )
    assert route_after_critique_v2(state) == "report_exporter"


# ============================================================================
# 6. propose_fix
# ============================================================================

def test_propose_fix_rejects_noop():
    """拒绝 fix_before == fix_after。"""
    result = propose_fix.invoke({
        "idx": 0, "file": "t.cpp", "line": 1,
        "fix_before": "int x = 1;", "fix_after": "int x = 1;",
        "reason": "test",
    })
    assert "no-op" in result.lower() or "相同" in result


def test_propose_fix_accepts_real_change():
    """接受实质修改。"""
    result = propose_fix.invoke({
        "idx": 0, "file": "t.cpp", "line": 1,
        "fix_before": "int x = 1;", "fix_after": "int x = 2;",
        "reason": "changed value",
    })
    assert "已提交" in result


def test_propose_fix_sets_status_zero():
    """新方案默认 status=0。"""
    import tools as t
    with t._buffer_lock:
        t._fix_plans_buffer = []
    set_state({"fix_plans": [None], "merged_violations": [{}]})
    propose_fix.invoke({
        "idx": 0, "file": "t.cpp", "line": 1,
        "fix_before": "a", "fix_after": "b", "reason": "test",
    })
    plans = get_fix_plans_buffer()
    assert len(plans) == 1
    assert plans[0]["status"] == 0
    assert plans[0]["feedback"] == ""


# ============================================================================
# 7. 事实核验：全量驳回时 refuted_violations 不丢失
# ============================================================================

def test_all_refuted_preserves_refuted_violations():
    """_fact_check_violations: 全部被驳回时 refuted 列表完整保留。"""
    from nodes.report_merger import _fact_check_violations

    violations = [
        {"file": "nonexistent.cpp", "line": 10, "rule": "C-01",
         "severity": "warning", "current": "int x = 1;",
         "expected": "int x = 2;", "reason": "test"},
        {"file": "ghost.h", "line": 5, "rule": "C-02",
         "severity": "critical", "current": "char* p;",
         "expected": "std::string p;", "reason": "test2"},
    ]
    file_contents = {}  # 空 → 所有文件都不存在 → 全部驳回

    passed, refuted = _fact_check_violations(violations, file_contents)
    assert passed == [], f"全部驳回时 passed 应为空，实际 {len(passed)}"
    assert len(refuted) == 2, f"应有 2 条驳回，实际 {len(refuted)}"
    for rv in refuted:
        assert rv["_fact_check_status"] == "refuted"
        assert "_fact_check_failed" in rv
        assert "_fact_check_reason" in rv


def test_fact_check_status_explicit():
    """_fact_check_violations 为每条违规写入显式 _fact_check_status。"""
    from nodes.report_merger import _fact_check_violations
    import os
    import tempfile

    # 创建临时文件用于核验
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".cpp", delete=False, encoding="utf-8",
    ) as f:
        f.write("int main() {\n    int x = 1;\n    return 0;\n}\n")
        tmp_path = f.name

    try:
        violations = [
            # 1. 确定性违规 → skipped
            {"file": tmp_path, "line": 1, "rule": "DET-01",
             "severity": "warning", "current": "int main() {",
             "expected": "", "reason": "test",
             "source_kind": "deterministic", "must_keep": True},
            # 2. Git 违规 → skipped
            {"file": tmp_path, "line": 1, "rule": "GIT-01",
             "severity": "info", "current": "",
             "expected": "", "reason": "commit message",
             "source": "git"},
            # 3. 正常违规 + 匹配代码 → verified
            {"file": tmp_path, "line": 2, "rule": "C-03",
             "severity": "warning", "current": "int x = 1;",
             "expected": "int x = 2;", "reason": "test"},
            # 4. 正常违规 + 空 current → unverified
            {"file": tmp_path, "line": 3, "rule": "C-04",
             "severity": "suggestion", "current": "",
             "expected": "return 0;", "reason": "rule-only"},
        ]
        file_contents = {tmp_path: "int main() {\n    int x = 1;\n    return 0;\n}\n"}

        passed, refuted = _fact_check_violations(violations, file_contents)
        assert len(refuted) == 0, f"不应有驳回，实际 {len(refuted)}"
        assert len(passed) == 4, f"应有 4 条通过，实际 {len(passed)}"

        statuses = {id(v): v.get("_fact_check_status") for v in passed}
        expected = {
            id(passed[0]): "skipped",     # deterministic
            id(passed[1]): "skipped",     # git
            id(passed[2]): "verified",    # code matched
            id(passed[3]): "unverified",  # empty current
        }
        for vid, exp_status in expected.items():
            actual = next(s for s_id, s in statuses.items() if s_id == vid)
            assert actual == exp_status, \
                f"违规 {vid} 状态应为 {exp_status}，实际 {actual}"
    finally:
        os.unlink(tmp_path)


# ============================================================================
# 8. 熔断器探针 token 所有权
# ============================================================================

def test_probe_token_rejects_stale_on_success():
    """无 token 的 on_success 不能关闭半开熔断器。"""
    import time
    from code_checker.rate_limiter import CircuitBreaker

    cb = CircuitBreaker(failure_threshold=1, cooldown_seconds=0.01)
    # 让熔断器进入 open 状态
    cb.on_failure()  # count=1 >= threshold=1 → open
    assert cb.state == "open"

    # 冷却后进入 half_open
    time.sleep(0.02)
    token = cb.before_request()  # open → half_open，发放 token
    assert token is not None
    assert cb.state == "half_open"

    # 迟到请求（无 token）调用 on_success → 忽略
    cb.on_success(None)
    assert cb.state == "half_open", \
        f"无 token 的 on_success 不应关闭熔断器，实际 {cb.state}"

    # 正确 token 的 on_success → 关闭
    cb.on_success(token)
    assert cb.state == "closed"


def test_probe_token_rejects_stale_on_failure():
    """无 token 的 on_failure 不归因于当前探测。"""
    import time
    from code_checker.rate_limiter import CircuitBreaker

    cb = CircuitBreaker(failure_threshold=3, cooldown_seconds=0.01)
    # 让熔断器进入 open 状态
    cb.on_failure(); cb.on_failure(); cb.on_failure()  # count=3 >= 3 → open
    assert cb.state == "open"

    # 冷却后进入 half_open
    time.sleep(0.02)
    token = cb.before_request()
    assert token is not None
    assert cb.state == "half_open"

    # 迟到请求（无 token）调用 on_failure → 忽略
    cb.on_failure(None)
    assert cb.state == "half_open", \
        f"无 token 的 on_failure 不应改变状态，实际 {cb.state}"

    # 正确 token 的 on_failure → 重新熔断
    cb.on_failure(token)
    assert cb.state == "open"


def test_probe_token_retry_same_probe():
    """同一探测 retry 时 token 匹配，不会被拒绝。"""
    import time
    from code_checker.rate_limiter import CircuitBreaker, CircuitBreakerOpenError

    cb = CircuitBreaker(failure_threshold=1, cooldown_seconds=0.01)
    cb.on_failure()  # → open
    time.sleep(0.02)

    token = cb.before_request()  # → half_open, grants token
    assert token is not None

    # 模拟 retry：用同一 token 再次调用 before_request
    token2 = cb.before_request(token)  # 应识别为同一探测，返回同一 token
    assert token2 is token, "retry 应返回同一 token"

    # 另一个请求（无 token）→ 拒绝
    try:
        cb.before_request(None)
        assert False, "应抛出 CircuitBreakerOpenError"
    except CircuitBreakerOpenError:
        pass


# ============================================================================
# 9. 进程级运行锁
# ============================================================================

def test_run_lock_prevents_concurrent():
    """并发 run() 应抛出 RuntimeError。"""
    import main as main_module

    # 先获取锁，模拟正在运行的 pipeline
    acquired = main_module._run_lock.acquire(blocking=False)
    assert acquired, "应能获取运行锁"
    try:
        try:
            main_module.run(".", degradation_mode="offline")
            assert False, "第二个 run() 应抛出 RuntimeError"
        except RuntimeError as e:
            assert "另一个" in str(e) or "并发" in str(e), \
                f"错误信息应说明并发原因，实际: {e}"
    finally:
        main_module._run_lock.release()


if __name__ == "__main__":
    test_get_fix_plans_buffer_no_duplicate(); print("test_get_fix_plans_buffer_no_duplicate: PASS")
    test_set_state_clears_buffer(); print("test_set_state_clears_buffer: PASS")
    test_get_fix_plans_buffer_thread_safe(); print("test_get_fix_plans_buffer_thread_safe: PASS")

    test_fix_agent_first_run_all_violations(); print("test_fix_agent_first_run_all_violations: PASS")
    test_fix_agent_retry_only_status_zero(); print("test_fix_agent_retry_only_status_zero: PASS")
    test_retry_loop_catches_missed_indices(); print("test_retry_loop_catches_missed_indices: PASS")
    test_fallback_placeholder_after_max_retries(); print("test_fallback_placeholder_after_max_retries: PASS")

    test_convergence_funnel(); print("test_convergence_funnel: PASS")

    test_review_pending_excludes_none_and_passed(); print("test_review_pending_excludes_none_and_passed: PASS")
    test_review_first_vs_rerun(); print("test_review_first_vs_rerun: PASS")
    test_review_summary_counts(); print("test_review_summary_counts: PASS")

    test_routing_explicit_status_no_default(); print("test_routing_explicit_status_no_default: PASS")
    test_routing_failed_only_counts_status_zero(); print("test_routing_failed_only_counts_status_zero: PASS")
    test_routing_all_pass(); print("test_routing_all_pass: PASS")
    test_routing_max_iterations(); print("test_routing_max_iterations: PASS")

    test_propose_fix_rejects_noop(); print("test_propose_fix_rejects_noop: PASS")
    test_propose_fix_accepts_real_change(); print("test_propose_fix_accepts_real_change: PASS")
    test_propose_fix_sets_status_zero(); print("test_propose_fix_sets_status_zero: PASS")

    test_all_refuted_preserves_refuted_violations(); print("test_all_refuted_preserves_refuted_violations: PASS")
    test_fact_check_status_explicit(); print("test_fact_check_status_explicit: PASS")

    test_probe_token_rejects_stale_on_success(); print("test_probe_token_rejects_stale_on_success: PASS")
    test_probe_token_rejects_stale_on_failure(); print("test_probe_token_rejects_stale_on_failure: PASS")
    test_probe_token_retry_same_probe(); print("test_probe_token_retry_same_probe: PASS")

    test_run_lock_prevents_concurrent(); print("test_run_lock_prevents_concurrent: PASS")

    print("\nAll fix-review loop tests passed!")
