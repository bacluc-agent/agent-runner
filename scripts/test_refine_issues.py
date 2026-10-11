from pathlib import Path


WORKFLOW = Path(__file__).parents[1] / ".github/workflows/refine-issues.yml"


def test_candidate_search_includes_refined_but_excludes_ignored_issues():
    workflow = WORKFLOW.read_text()
    candidate_search = next(
        line for line in workflow.splitlines() if "search/issues?q=repo:" in line
    )

    assert "+-label:agent-refined" not in candidate_search
    assert "+-label:agent-ignore" in candidate_search
    assert "+-label:ready-for-implementation" not in candidate_search
    assert "unique_by(.number)" in workflow


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
