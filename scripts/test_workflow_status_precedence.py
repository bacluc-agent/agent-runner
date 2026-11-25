"""Execute the real workflow shell for the coordinator status paths."""

import os
import subprocess
from pathlib import Path
from tempfile import TemporaryDirectory

WORKFLOW = Path(__file__).parents[1] / ".github/workflows/opencode.yml"


def test_coordinator_success_is_never_reported_as_failed():
    text = WORKFLOW.read_text()

    def fragment(start, end):
        i = text.index(start)
        return text[i : text.index(end, i)]

    def bash(script, **env):
        return subprocess.run(
            ["bash", "-Eeuo", "pipefail", "-c", script],
            env=dict(os.environ, **env), capture_output=True, text=True,
        )

    classifier = fragment("          # Determine status", "\n\n          # Check for existing PRs")
    cases = [
        ("0", "0", "", "✅ completed"),
        ("0", "9", "", "✅ completed (tee log capture failed: exit 9)"),
        ("124", "0", "", "⏱️ coordinator timed out (exit 124)"),
        ("124", "9", "auth", "⏱️ coordinator timed out (exit 124)"),
        ("7", "0", "auth", "❌ fatal error: auth"),
        ("7", "0", "", "⚠️ failed (coordinator exit 7)"),
    ]
    for status, tee, fatal, expected in cases:
        result = bash(classifier + '\nprintf "%s\\n" "$STATUS"',
                      COORDINATOR_STATUS=status, COORDINATOR_TEE_STATUS=tee, FATAL_REASON=fatal)
        assert result.returncode == 0, result.stderr
        assert result.stdout.strip() == expected, (status, tee, fatal, result.stdout)

    step = fragment("          set +e\n          timeout", "\n\n      - name: Fatal guard")
    with TemporaryDirectory() as tmp:
        root = Path(tmp)
        bin_dir = root / "bin"
        bin_dir.mkdir()
        for name, body in (("timeout", 'exit "$FAKE_STATUS"\n'), ("tee", 'cat >/dev/null\nexit "$FAKE_TEE"\n')):
            path = bin_dir / name
            path.write_text("#!/bin/bash\n" + body)
            path.chmod(0o755)
        (root / "agent-runner/scripts").mkdir(parents=True)
        (root / "agent-runner/scripts/progress-reporting.txt").write_text("")
        result = bash(step, PATH=f"{bin_dir}:{os.environ['PATH']}", RUNNER_TEMP=str(root),
                      GITHUB_OUTPUT=str(root / "out"), FAKE_STATUS="0", FAKE_TEE="9",
                      COORDINATOR_TIMEOUT="10", MODEL="m", AGENT="coordinator", PROMPT="p",
                      coordinator_session_title="coordinator-run", stop_token="test-token")
        assert result.returncode == 0, result.stderr
        assert "coordinator log capture failed (tee exit 9)" in result.stdout
        assert "coordinator_status=0" in (root / "out").read_text()
