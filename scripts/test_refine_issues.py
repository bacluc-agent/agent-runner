from pathlib import Path


WORKFLOW = Path(__file__).parents[1] / ".github/workflows/refine-issues.yml"


def test_first_time_candidate_search_preserves_the_five_issue_limit():
    workflow = WORKFLOW.read_text()
    candidate_search = next(
        line for line in workflow.splitlines() if "search/issues?q=repo:" in line and "+-label:agent-refined" in line and "+-label:agent-ignore" in line
    )

    assert "+-label:agent-refined" in candidate_search
    assert "+-label:agent-ignore" in candidate_search
    assert "+-label:ready-for-implementation" not in candidate_search
    assert "per_page=5" in candidate_search


def test_only_unrefined_candidates_are_selected_with_the_search_limit():
    workflow = WORKFLOW.read_text()
    searches = [line for line in workflow.splitlines() if "search/issues?q=" in line]

    assert len(searches) == 1
    assert (
        'search/issues?q=repo:${ISSUE_REPOSITORY}+is:open+is:issue+-label:agent-refined'
        "+-label:agent-ignore+sort:created-asc&per_page=5" in searches[0]
    )


def test_candidates_include_filtered_human_comments():
    workflow = WORKFLOW.read_text()

    assert 'jq -r \'.[].number\' "$search_json"' in workflow
    assert "agent-refined-through:" not in workflow
    assert "refined-candidates" not in workflow


def test_refinement_still_includes_human_comments_and_filters_bot_and_progress_comments():
    workflow = WORKFLOW.read_text()

    assert 'select(.user.type != "Bot")' in workflow
    assert 'contains("<!-- agent-progress -->") | not' in workflow
    assert "Reviewer comments (feedback to fold into the Goal and steps" in workflow


def test_issue_body_is_read_from_the_fresh_issue_view():
    workflow = WORKFLOW.read_text()

    assert (
        'issue_json="$(gh issue view "$number" -R "$ISSUE_REPOSITORY" --json title,body)"'
        in workflow
    )
    assert 'body="$(jq -r \'.body // ""\' <<<"$issue_json")"' in workflow
    assert 'select(.number == $number)' not in workflow
