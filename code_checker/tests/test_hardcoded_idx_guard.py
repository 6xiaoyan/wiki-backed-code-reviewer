"""验证硬编码 idx 校验：工具函数拒绝越界操作。"""
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from tools import (
    set_state, set_allowed_indices, _check_idx_allowed,
    propose_fix, submit_review, get_pending_fixes, get_violation_detail,
    get_fix_plans_buffer,
)
import tools as t


def setup():
    """创建 5 条违规 + 5 条 fix_plans 的测试状态。"""
    state = {
        "merged_violations": [
            {"file": f"f{i}.cpp", "line": i, "rule": "test",
             "current": f"old_{i}", "expected": f"new_{i}",
             "reason": "test", "severity": "warning", "surrounding": ""}
            for i in range(5)
        ],
        "fix_plans": [
            {"file": "f0.cpp", "line": 0, "fix_before": "a", "fix_after": "b",
             "status": 0, "score": 0, "feedback": "", "suggestion": ""},
            {"file": "f1.cpp", "line": 1, "fix_before": "c", "fix_after": "d",
             "status": 0, "score": 0, "feedback": "", "suggestion": ""},
            {"file": "f2.cpp", "line": 2, "fix_before": "e", "fix_after": "f",
             "status": 0, "score": 0, "feedback": "", "suggestion": ""},
            {"file": "f3.cpp", "line": 3, "fix_before": "g", "fix_after": "h",
             "status": 1, "score": 9, "feedback": "ok", "suggestion": ""},
            {"file": "f4.cpp", "line": 4, "fix_before": "i", "fix_after": "j",
             "status": 0, "score": 0, "feedback": "", "suggestion": ""},
        ],
    }
    set_state(state)
    # 模拟：当前 agent 只允许操作 idx 0, 2, 4
    set_allowed_indices({0, 2, 4})


def test_check_idx_allowed():
    assert _check_idx_allowed(0) is None
    assert _check_idx_allowed(2) is None
    assert _check_idx_allowed(4) is None
    assert _check_idx_allowed(1) is not None  # 拒绝
    assert _check_idx_allowed(3) is not None  # 拒绝（status=1，不在 allowed）


def test_propose_fix_rejects_out_of_range():
    r = propose_fix.invoke({
        "idx": 1, "file": "f1.cpp", "line": 1,
        "fix_before": "x", "fix_after": "y", "reason": "test",
    })
    assert "硬约束拒绝" in r, f"应拒绝 idx=1, 实际: {r}"


def test_propose_fix_accepts_allowed():
    r = propose_fix.invoke({
        "idx": 0, "file": "f0.cpp", "line": 0,
        "fix_before": "old_code", "fix_after": "new_code", "reason": "test",
    })
    assert "已提交" in r, f"应接受 idx=0, 实际: {r}"


def test_submit_review_rejects_out_of_range():
    r = submit_review.invoke({
        "idx": 3, "score": 9, "passed": True,
        "feedback": "good", "suggestion": "", "rule_snippet": "test",
    })
    assert "硬约束拒绝" in r, f"应拒绝 idx=3, 实际: {r}"


def test_get_pending_fixes_filters_by_allowed():
    pf = get_pending_fixes.invoke({})
    indices = [p["idx"] for p in pf]
    # idx=1 是 status=0 但不在 allowed → 应被隐藏
    # idx=3 是 status=1 → 本来就跳过
    # 可见的: 0, 2, 4（都是 status=0 且在 allowed 内）
    assert indices == [0, 2, 4], f"应只可见 0,2,4, 实际: {indices}"


def test_get_violation_detail_rejects_out_of_range():
    r = get_violation_detail.invoke({"violation_idx": 1})
    assert "硬约束拒绝" in str(r), f"应拒绝 idx=1, 实际: {r}"


def test_clear_allowed_restores_full_access():
    set_allowed_indices(None)
    pf = get_pending_fixes.invoke({})
    indices = [p["idx"] for p in pf]
    assert 1 in indices, "清除限制后 idx=1 应该可见"
    assert len(indices) == 4, f"应有 4 条 status=0, 实际: {len(indices)}"


if __name__ == "__main__":
    setup()
    test_check_idx_allowed(); print("test_check_idx_allowed: PASS")
    test_propose_fix_rejects_out_of_range(); print("test_propose_fix_rejects_out_of_range: PASS")
    test_propose_fix_accepts_allowed(); print("test_propose_fix_accepts_allowed: PASS")
    setup(); test_submit_review_rejects_out_of_range(); print("test_submit_review_rejects_out_of_range: PASS")
    setup(); test_get_pending_fixes_filters_by_allowed(); print("test_get_pending_fixes_filters_by_allowed: PASS")
    setup(); test_get_violation_detail_rejects_out_of_range(); print("test_get_violation_detail_rejects_out_of_range: PASS")
    setup(); test_clear_allowed_restores_full_access(); print("test_clear_allowed_restores_full_access: PASS")
    print("\nAll hardcoded idx guard tests passed!")
