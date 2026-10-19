"""证据核验：模型发现必须与固定版本和改动范围一致（PRD §6.2、§9）。"""

from code_checker.pr_review.deterministic_pr import filter_deterministic_violations
from code_checker.pr_review.evidence import verify_findings
from code_checker.pr_review.models import ChangedFile, DiffLine, Hunk

REGISTRY = {
    "cpp/no-bare-new-delete": {"title": "禁止裸 new/delete", "domain": "cpp"},
    "cpp/indentation": {"title": "禁止 Tab 缩进", "domain": "cpp"},
    "sqlite/must-use-sqlcipher": {"title": "必须使用 SQLCipher", "domain": "sqlite"},
}

HEAD = "// header\nint value = 1;\nint tail = 2;\n"
BASE = "// header\nint value = 0;\nint tail = 2;\n"


def _changed(path="src/a.cpp", *, status="modified", added=(2,), context=(1, 3),
             old_path=None):
    hunk = Hunk(1, 2, 1, 3)
    for line in (1, 2, 3):
        if line in added:
            hunk.lines.append(DiffLine("+", HEAD.split("\n")[line - 1], None, line))
        elif line in context:
            hunk.lines.append(DiffLine(" ", HEAD.split("\n")[line - 1], line, line))
    return ChangedFile(path=path, old_path=old_path, status=status, additions=1,
                       deletions=1, hunks=[hunk])


def _verify(raw, files=None, head=None, base=None):
    return verify_findings(
        raw,
        files=files or [_changed()],
        head_contents=head or {"src/a.cpp": HEAD},
        base_contents=base or {"src/a.cpp": BASE},
        registry=REGISTRY,
        default_source="model",
    )


def test_added_line_with_matching_code_and_rule_is_confirmed():
    out = _verify([{
        "file": "src/a.cpp", "line": 2, "rule_id": "cpp/no-bare-new-delete",
        "severity": "warning", "message": "使用了裸 new", "code": "int value = 1;",
        "suggestion": "改用 make_unique",
    }])
    assert len(out["confirmed"]) == 1
    f = out["confirmed"][0]
    assert f.change_relation == "added"
    assert f.severity == "warning"
    assert f.rule_title == "禁止裸 new/delete"
    assert "未执行验证" in f.suggestion


def test_context_line_finding_is_filtered_as_historical():
    out = _verify([{
        "file": "src/a.cpp", "line": 1, "rule_id": "cpp/no-bare-new-delete",
        "severity": "critical", "message": "历史问题", "code": "// header",
    }])
    assert not out["confirmed"]
    assert out["filtered"][0]["reason"].startswith("同一问题在改动前的版本中已存在")


def test_fabricated_code_goes_to_uncertain():
    out = _verify([{
        "file": "src/a.cpp", "line": 2, "rule_id": "cpp/no-bare-new-delete",
        "severity": "critical", "message": "幻觉", "code": "auto* p = new Widget();",
    }])
    assert not out["confirmed"]
    assert "疑似幻觉" in out["uncertain"][0]["reason"]


def test_unknown_rule_basis_goes_to_uncertain():
    out = _verify([{
        "file": "src/a.cpp", "line": 2, "rule_id": "cpp/invented-rule",
        "severity": "warning", "message": "x", "code": "int value = 1;",
    }])
    assert not out["confirmed"]
    assert "规则依据" in out["uncertain"][0]["reason"]


def test_out_of_range_line_goes_to_uncertain():
    out = _verify([{
        "file": "src/a.cpp", "line": 999, "rule_id": "cpp/no-bare-new-delete",
        "severity": "warning", "message": "x", "code": "y",
    }])
    assert not out["confirmed"]
    assert "超出" in out["uncertain"][0]["reason"]


def test_file_outside_scope_goes_to_uncertain():
    out = _verify([{
        "file": "src/other.cpp", "line": 1, "rule_id": "cpp/no-bare-new-delete",
        "severity": "warning", "message": "x", "code": "y",
    }])
    assert not out["confirmed"]
    assert "不在本次审查范围" in out["uncertain"][0]["reason"]


def test_line_off_by_one_is_corrected():
    out = _verify([{
        "file": "src/a.cpp", "line": 3, "rule_id": "cpp/no-bare-new-delete",
        "severity": "warning", "message": "x", "code": "int value = 1;",
    }])
    assert out["confirmed"][0].line == 2


def test_deleted_file_finding_on_removed_line():
    cf = _changed(status="deleted", added=(), context=())
    cf.hunks[0].lines = [DiffLine("-", "int value = 0;", 2, None)]
    out = verify_findings(
        [{"file": "src/a.cpp", "line": 2, "rule_id": "cpp/no-bare-new-delete",
          "severity": "critical", "message": "删除校验", "code": "int value = 0;"}],
        files=[cf], head_contents={"src/a.cpp": BASE},
        base_contents={"src/a.cpp": BASE}, registry=REGISTRY,
        default_source="model",
    )
    assert out["confirmed"][0].change_relation == "deleted"


# ---------------------------------------------------------------------------
# 确定性检查的改动关联性过滤
# ---------------------------------------------------------------------------
def _det_violation(line, rule, check_id, severity="critical", current="bad line"):
    return {
        "file": "src/a.cpp", "line": line, "rule": rule,
        "severity": severity, "current": current,
        "expected": "good line", "reason": "reason",
        "source": "cpp", "check_id": check_id,
    }


def test_deterministic_added_violation_confirmed():
    out = filter_deterministic_violations(
        [_det_violation(2, "禁止 Tab 缩进", "check_tab_indentation",
                        current="int value = 1;")],
        [_changed()], {"src/a.cpp": HEAD}, {"src/a.cpp": BASE},
        rule_page_resolver=lambda slug: False,
    )
    assert len(out["confirmed"]) == 1
    assert out["confirmed"][0].change_relation == "added"
    assert out["confirmed"][0].code_evidence.startswith("+")


def test_deterministic_historical_violation_filtered():
    out = filter_deterministic_violations(
        [_det_violation(3, "禁止 Tab 缩进", "check_tab_indentation",
                        current="int tail = 2;")],
        [_changed()], {"src/a.cpp": HEAD}, {"src/a.cpp": BASE},
        rule_page_resolver=lambda slug: False,
    )
    assert not out["confirmed"]
    assert len(out["filtered"]) == 1
    assert "历史问题" in out["filtered"][0]["reason"]


def test_deterministic_file_level_on_new_file_confirmed():
    cf = _changed("src/db.cpp", status="added", added=(1, 2, 3), context=())
    out = filter_deterministic_violations(
        [{
            "file": "src/db.cpp", "line": 1,
            "rule": "SQLite 必须使用 SQLCipher 加密",
            "severity": "critical", "current": "（未找到 PRAGMA key 设置）",
            "expected": "PRAGMA key", "reason": "未找到密钥设置",
            "source": "sqlite", "check_id": "check_sqlite_pragma_key",
        }],
        [cf], {"src/db.cpp": "a\nb\nc\n"}, {},
        rule_page_resolver=lambda slug: False,
    )
    assert len(out["confirmed"]) == 1
    assert out["confirmed"][0].change_relation == "added"


def test_deterministic_file_level_on_modified_file_is_uncertain():
    out = filter_deterministic_violations(
        [{
            "file": "src/a.cpp", "line": 1,
            "rule": "SQLite 必须使用 SQLCipher 加密",
            "severity": "critical", "current": "（未找到 PRAGMA key 设置）",
            "expected": "PRAGMA key", "reason": "未找到密钥设置",
            "source": "sqlite", "check_id": "check_sqlite_pragma_key",
        }],
        [_changed()], {"src/a.cpp": HEAD}, {"src/a.cpp": BASE},
        rule_page_resolver=lambda slug: False,
    )
    assert not out["confirmed"]
    assert "无法证明" in out["uncertain"][0]["reason"] or \
        "证据不足" in out["uncertain"][0]["reason"]


def test_deterministic_evidence_mismatch_dropped():
    out = filter_deterministic_violations(
        [_det_violation(2, "禁止 Tab 缩进", "check_tab_indentation",
                        current="completely different();")],
        [_changed()], {"src/a.cpp": HEAD}, {"src/a.cpp": BASE},
        rule_page_resolver=lambda slug: False,
    )
    assert not out["confirmed"]
    assert out["filtered"][0]["reason"].startswith("声称的代码")
