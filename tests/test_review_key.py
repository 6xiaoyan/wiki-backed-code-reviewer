"""review_key：同一组输入稳定、任一输入变化即变化（PRD §8）。"""

from code_checker.pr_review.models import ReviewRequest, make_review_key


def _request(**kw):
    data = dict(
        repo="owner/repo", pr_number=1, base_sha="a" * 40,
        head_sha="b" * 40, merge_base_sha="c" * 40,
        program_sha="d" * 40, run_id="1", run_attempt=1,
        rules_digest="r1", prompts_digest="p1", config_digest="c1",
        model_id="deepseek-v4-flash",
    )
    data.update(kw)
    return ReviewRequest(**data)


def test_key_is_stable_and_ignores_execution_identifiers():
    a = make_review_key(_request())
    b = make_review_key(_request(run_id="999", run_attempt=3, run_url="https://x"))
    assert a == b
    assert len(a) == 64


def test_key_changes_with_code_versions():
    base = make_review_key(_request())
    assert base != make_review_key(_request(head_sha="e" * 40))
    assert base != make_review_key(_request(base_sha="e" * 40))
    assert base != make_review_key(_request(merge_base_sha="e" * 40))
    assert base != make_review_key(_request(program_sha="e" * 40))


def test_key_changes_with_review_configuration():
    base = make_review_key(_request())
    assert base != make_review_key(_request(rules_digest="r2"))
    assert base != make_review_key(_request(prompts_digest="p2"))
    assert base != make_review_key(_request(config_digest="c2"))
    assert base != make_review_key(_request(model_id="other-model"))


def test_key_changes_with_budget_and_pr_identity():
    base = make_review_key(_request())
    changed_budget = _request()
    changed_budget.budget = changed_budget.budget.__class__(max_model_requests=10)
    assert base != make_review_key(changed_budget)
    assert base != make_review_key(_request(pr_number=2))
    assert base != make_review_key(_request(repo="other/repo"))
