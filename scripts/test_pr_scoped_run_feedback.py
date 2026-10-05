from pathlib import Path


class TestPrScopedRunFeedback:
    """review-fixes legs must scope opencode runs to the target PR's repository."""

    def test_process_prs_forwards_issue_number_and_repository(self):
        content = Path(".github/workflows/review-fixes.yml").read_text()
        uses = content.index("uses: ./.github/workflows/opencode.yml")
        block = content[uses:content.index("secrets: inherit", uses)]
        assert "issue_number:" in block
        assert "issue_repository:" in block

    def test_opencode_declares_issue_repository_input(self):
        content = Path(".github/workflows/opencode.yml").read_text()
        workflow_call = content.index("workflow_call:")
        inputs = content[workflow_call:content.index("permissions:", workflow_call)]
        assert "issue_repository:" in inputs

    def test_issue_repository_env_falls_back_to_input(self):
        content = Path(".github/workflows/opencode.yml").read_text()
        line = next(
            line
            for line in content.splitlines()
            if line.strip().startswith("ISSUE_REPOSITORY:")
        )
        assert "inputs.issue_repository" in line
        assert "vars.ISSUE_REPOSITORY" in line
        assert "github.repository" in line

    def test_pr_detection_emits_is_pr_output(self):
        content = Path(".github/workflows/opencode.yml").read_text()
        step = content.index("- name: Extract target issue number")
        next_step = content.find("- name:", step + 1)
        block = content[step:next_step if next_step != -1 else len(content)]
        assert "gh pr view" in block
        assert "is_pr=true" in block

    def test_push_step_is_skipped_for_pr_targets(self):
        content = Path(".github/workflows/opencode.yml").read_text()
        step = content.index("- name: Ensure work is pushed")
        next_step = content.find("- name:", step + 1)
        guard = content[step:next_step if next_step != -1 else len(content)]
        assert "is_pr" in guard

    def test_run_result_comment_still_posts_for_pr_targets(self):
        content = Path(".github/workflows/opencode.yml").read_text()
        step = content.index("- name: Post run-result comment")
        next_step = content.find("- name:", step + 1)
        guard = content[step:next_step if next_step != -1 else len(content)]
        assert "is_pr" not in guard
