from pathlib import Path


WORKFLOW = Path(__file__).parents[1] / ".github/workflows/refine-issues.yml"


def test_first_time_candidate_search_preserves_the_five_issue_limit():
    workflow = WORKFLOW.read_text()
    candidate_search = next(
        line for line in workflow.splitlines() if "search/issues?q=repo:" in line
    )

    assert "+-label:agent-refined" in candidate_search
    assert "+-label:agent-ignore" in candidate_search
    assert "+-label:ready-for-implementation" not in candidate_search
    assert "per_page=5" in candidate_search


def test_refined_candidates_are_scanned_in_bounded_fair_windows():
    workflow = WORKFLOW.read_text()

    assert "repos/$ISSUE_REPOSITORY/issues?state=open&labels=agent-refined" in workflow
    assert "--include \"$refined_query&page=1\"" in workflow
    assert 'rel="last"' in workflow
    assert "scan_window=20" in workflow
    assert "GITHUB_RUN_NUMBER % scan_windows" in workflow
    assert "page=$page" in workflow
    assert "unique_by(.number)" in workflow
    assert "select(.pull_request == null)" in workflow
    assert 'index(\\"agent-ignore\\") == null' in workflow


def test_refined_candidates_require_new_filtered_human_comments():
    workflow = WORKFLOW.read_text()

    assert "agent-refined-through:" in workflow
    assert "created_at" in workflow
    assert 'select(.created_at > $marker)' in workflow
    assert "agent-refined" in workflow


def test_marker_is_added_only_after_validation_and_removed_from_prompt():
    workflow = WORKFLOW.read_text()

    validation = workflow.index("if (( validation_status == 0 )); then")
    marker = workflow.rindex("agent-refined-through:")
    body_update = workflow.index('gh issue edit "$number" --body-file "$final_body"')
    assert validation < marker < body_update
    assert "sed -E '/<!-- agent-refined-through:" in workflow
    assert 'max_by(.created_at).created_at' in workflow
    assert "if (( validation_status == 0 )); then" in workflow
    assert "validator_unavailable" in workflow


def test_refined_marker_comparison_is_strict_and_unmarked_refinements_keep_first_run_behavior():
    workflow = WORKFLOW.read_text()

    assert "select(.created_at > $marker)" in workflow
    assert "select(.created_at >= $marker)" not in workflow
    assert 'if [[ -n "$marker" ]]; then' in workflow
    assert '[[ "$refined" == true ]]' in workflow


def test_refinement_still_includes_human_comments_and_filters_agent_comments():
    workflow = WORKFLOW.read_text()

    assert 'select(.user.type != "Bot")' in workflow
    assert 'select(.user.login != "bacluc-agent")' in workflow
    assert 'contains("<!-- agent-progress -->") | not' in workflow
    assert "Reviewer comments (feedback to fold into the Goal and steps" in workflow
