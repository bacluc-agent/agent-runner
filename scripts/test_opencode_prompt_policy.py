from pathlib import Path


ROOT = Path(__file__).parents[1]
WORKFLOW = ROOT / ".github/workflows/opencode.yml"
COORDINATOR = ROOT / ".opencode/agent/coordinator.md"


def test_noninteractive_openai_policy_is_explicit_and_ordered():
    workflow = WORKFLOW.read_text()
    coordinator = COORDINATOR.read_text()
    runtime_prompt = next(
        line for line in workflow.splitlines() if "PROMPT=$(printf" in line
    )

    for policy in (runtime_prompt, coordinator):
        lowered = policy.lower()
        assert "never ask clarifying questions" in lowered
        assert "non-interactive" in lowered
        assert "openai models" in lowered
        assert "explicit assumptions" in lowered
        assert "comments on the target issue" in lowered

    assert runtime_prompt.index("$MODEL") < runtime_prompt.index("$PROMPT")
    assert "read -p" not in workflow
    assert "clarification loop" not in workflow.lower()
