from selection_tiers import Candidate, is_standing, parse_branches, render_prompt, select_tier, tier


def candidate(number=1, **values):
    defaults = dict(
        number=number,
        title="Issue",
        labels=[],
        created_at="2026-01-01T00:00:00Z",
        pr_state="none",
        pr_number=None,
        pr_updated_at=None,
        last_human_comment_at=None,
        attempts=0,
        recent_attempts=0,
        is_standing=False,
    )
    defaults.update(values)
    result = Candidate(**defaults)
    result.tier = tier(result)
    if result.recent_attempts and not (result.tier == 0 and not result.is_standing):
        result.tier = 3
    return result


def test_branch_history_and_recent_repeat():
    branches = ["agent-run/330-37135909176", "issue-2-37135909177", "invalid"]
    assert parse_branches(branches) == [(2, 37135909177), (330, 37135909176)]
    assert not any(__import__("re").search(r"issue-[0-9]+", branch) for branch in branches[:1])
    assert candidate(330, attempts=1).tier == 2
    assert candidate(9, attempts=3, recent_attempts=1).tier == 3
    assert candidate(76, title="Standing research", attempts=14, recent_attempts=1, is_standing=True).tier == 3


def test_tiers_cover_feedback_history_and_finished_work():
    assert candidate(pr_state="open", pr_updated_at="2026-01-01T00:00:00Z", last_human_comment_at="2026-01-02T00:00:00Z").tier == 0
    assert candidate(pr_state="open").tier == 3
    assert candidate(pr_state="open", pr_updated_at="2026-01-02T00:00:00Z", last_human_comment_at="2026-01-01T00:00:00Z").tier == 3
    assert candidate(pr_state="merged").tier == 2
    assert candidate(pr_state="closed").tier == 2
    assert candidate().tier == 1
    assert is_standing("Standing project")
    assert is_standing("Some task", ["meta: standing"])


def test_select_best_available_and_render_only_that_tier():
    better, awaiting = candidate(2), candidate(3, pr_state="open")
    assert select_tier([awaiting, better]) == 1
    assert select_tier([awaiting]) == 3
    big = candidate(4)
    big.body = "x" * 3000
    big.labels = ["many", "labels"]
    assert big.tier == candidate(5).tier
    prompt = render_prompt([better, awaiting], 1, "Reply\nSELECTED_ISSUE: <number>")
    assert "2: Issue" in prompt and "3: Issue" not in prompt
    assert "[attempts: 0] [tier: 1]" in prompt
    assert "avoid" not in prompt.lower()
    assert prompt.rstrip().endswith("SELECTED_ISSUE: <number>")
