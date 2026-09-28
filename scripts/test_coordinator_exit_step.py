"""Execute the real `Run coordinator` step from .github/workflows/opencode.yml.

The run block is extracted from the workflow and run with stub `opencode` and
`tee` binaries on PATH, so `PIPESTATUS` is deterministic. Reverting the final
`exit 0` back to `exit "$coordinator_tee_status"` fails the `(0, 1) -> 0` case.
"""

import os
import re
import subprocess
from pathlib import Path

import pytest

WORKFLOW = Path(__file__).resolve().parent.parent / ".github/workflows/opencode.yml"

# ponytail: regex extraction assumes the 10-space "run: |" block shape; swap in a real YAML parser if the workflow's indentation ever changes.
STEP_RE = re.compile(r"^      - name: Run coordinator\n.*?(?=^      - name: Fatal guard)", re.M | re.S)
RUN_BLOCK_RE = re.compile(r"^        run: \|\n((?:          .*\n|\n)+)", re.M)

STUB = '#!/usr/bin/env bash\ncat > /dev/null\nexit {code}\n'


def run_step(tmp_path, coordinator_exit, tee_exit):
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    for name, code in (("opencode", coordinator_exit), ("tee", tee_exit)):
        stub = bin_dir / name
        stub.write_text(STUB.format(code=code))
        stub.chmod(0o755)

    runner_temp = tmp_path / "runner-temp"
    (runner_temp / "agent-runner/scripts").mkdir(parents=True)
    (runner_temp / "agent-runner/scripts/progress-reporting.txt").write_text("progress")
    github_output = tmp_path / "github-output"
    github_output.write_text("")

    body = RUN_BLOCK_RE.search(STEP_RE.search(WORKFLOW.read_text()).group(0)).group(1)
    script = tmp_path / "coordinator.sh"
    script.write_text(re.sub(r"^ {10}", "", body, flags=re.M))
    script.chmod(0o755)

    return subprocess.run(
        ["bash", str(script)],
        env={
            "PATH": f"{bin_dir}:{os.environ['PATH']}",
            "RUNNER_TEMP": str(runner_temp),
            "GITHUB_OUTPUT": str(github_output),
            "COORDINATOR_TIMEOUT": "5",
            "MODEL": "test/model",
            "PROMPT": "test prompt",
        },
        capture_output=True,
        text=True,
    )


@pytest.mark.parametrize(
    ("coordinator_exit", "tee_exit", "expected"),
    [
        (0, 1, 0),
        (0, 0, 0),
        (124, 0, 124),
        (7, 0, 7),
    ],
)
def test_coordinator_step_exit_code(tmp_path, coordinator_exit, tee_exit, expected):
    assert run_step(tmp_path, coordinator_exit, tee_exit).returncode == expected
