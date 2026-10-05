import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).parents[1]
WORKFLOW = ROOT / ".github/workflows/refine-issues.yml"
AGENT = ROOT / ".opencode/agent/issue-refiner.md"


def test_refiner_denies_all_tools_and_marks_issue_data_untrusted():
    agent = AGENT.read_text()
    assert '"*": deny' in agent
    assert "untrusted data" in agent


def test_refiner_scopes_secrets_and_scrubs_agent_environment():
    workflow = WORKFLOW.read_text()
    job = workflow[workflow.index("  refine:\n") : workflow.index("    steps:\n")]
    assert "secrets." not in job
    assert 'env -i "HOME=$HOME" "PATH=$PATH"' in workflow
    assert '"GITHUB_TOKEN=' not in workflow[workflow.index("opencode_env=(env -i") :]
    assert '"OPENCODE_AUTH_CONTENT=' not in workflow[workflow.index("opencode_env=(env -i") :]
    assert "gh issue edit" in workflow
    assert "validate_refined_issue.py" in workflow


def test_refiner_removes_setup_auth_before_starting_child(tmp_path):
    workflow = WORKFLOW.read_text()
    setup = (ROOT / ".github/actions/setup-opencode/action.yml").read_text()
    cleanup = 'rm -f "$HOME/.local/share/opencode/auth.json"'
    invocation = 'timeout 8m "${opencode_env[@]}" opencode run'

    assert "~/.local/share/opencode/auth.json" in setup
    assert workflow.index(cleanup) < workflow.index(invocation)

    auth_file = tmp_path / ".local/share/opencode/auth.json"
    auth_file.parent.mkdir(parents=True)
    auth_file.write_text("oauth", encoding="utf-8")
    subprocess.run(["bash", "-c", cleanup], check=True, env={**os.environ, "HOME": str(tmp_path)})
    assert not auth_file.exists()
