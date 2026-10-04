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
    return Candidate(**defaults)


def test_branch_history_and_recent_repeat():
    branches = ["agent-run/330-37135909176", "issue-2-37135909177", "invalid"]
    assert parse_branches(branches) == [(2, 37135909177), (330, 37135909176)]
    assert not any(__import__("re").search(r"issue-[0-9]+", branch) for branch in branches[:1])
    assert tier(candidate(330, attempts=1)) == 2
    assert tier(candidate(9, attempts=3, recent_attempts=1)) == 3
    assert tier(candidate(76, title="Standing research", attempts=14, recent_attempts=1, is_standing=True)) == 3


def test_durable_attempt_label_counts_as_history_without_branch():
    import json
    from pathlib import Path
    from tempfile import TemporaryDirectory
    from subprocess import run

    with TemporaryDirectory() as directory:
        candidates = Path(directory) / "candidates.json"
        branches = Path(directory) / "branches.txt"
        tail = Path(directory) / "tail.txt"
        candidates.write_text(json.dumps([{"number": 42, "labels": [{"name": "agent-attempted"}]}]))
        branches.write_text("")
        tail.write_text("Choose\n")
        result = run(["python3", "scripts/selection_tiers.py", "--candidates", str(candidates), "--branches", str(branches), "--tail-file", str(tail)], check=True, capture_output=True, text=True)
    assert "attempts for 42: 1" in result.stderr
    assert "Candidate tiers: 0=0 1=0 2=1 3=0" in result.stderr
    assert "[attempts: 1] [tier: 2]" in result.stdout


def test_tiers_cover_feedback_history_and_finished_work():
    assert tier(candidate(pr_state="open", pr_updated_at="2026-01-01T00:00:00Z", last_human_comment_at="2026-01-02T00:00:00Z")) == 0
    assert tier(candidate(pr_state="open")) == 3
    assert tier(candidate(pr_state="open", pr_updated_at="2026-01-02T00:00:00Z", last_human_comment_at="2026-01-01T00:00:00Z")) == 3
    assert tier(candidate(pr_state="merged")) == 2
    assert tier(candidate(pr_state="closed")) == 2
    assert tier(candidate()) == 1
    assert is_standing("Standing project")
    assert is_standing("Some task", ["meta: standing"])


def test_select_best_available_and_render_only_that_tier():
    better, awaiting = candidate(2), candidate(3, pr_state="open")
    assert select_tier([awaiting, better]) == 1
    assert select_tier([awaiting]) == 3
    big = candidate(4)
    big.body = "x" * 3000
    big.labels = ["many", "labels"]
    assert tier(big) == tier(candidate(5))
    prompt = render_prompt([better, awaiting], 1, "Reply\nSELECTED_ISSUE: <number>")
    assert "2: Issue" in prompt and "3: Issue" not in prompt
    assert "[attempts: 0] [tier: 1]" in prompt
    assert "avoid" not in prompt.lower()
    assert prompt.rstrip().endswith("SELECTED_ISSUE: <number>")
