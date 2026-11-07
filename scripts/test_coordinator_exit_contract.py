"""Regression check for the coordinator exit contract in .github/workflows/opencode.yml.

Executes the REAL `Run coordinator` run block extracted from the workflow, with a
genuinely failing `tee` (its output path is a directory, so tee exits non-zero) and a
stub `opencode` that exits 0. That is the exact state the fix is about: the
coordinator succeeded but log capture failed. The block must still exit 0.

The second run of the same harness against the pre-fix block is the negative
control: if the harness cannot tell the two apart, the first assertion proves
nothing. bacluc-agent/agent-todo#296.
"""

import os
import pathlib
import re
import stat
import subprocess

import pytest

import run_status

ROOT = pathlib.Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/opencode.yml"

# The block as it stood before the fix; only the final line differs.
PRE_FIX_TAIL = 'exit "$coordinator_tee_status"'


def extract_run_block(step_name):
    """Return the `run:` body of a workflow step without a YAML parser.

    PyYAML is not available in `uv run --group dev`, so locate the step by its
    `- name:` line, derive the indent of the step keys, then read the block scalar
    body until a line dedents below its own first non-blank line.
    """
    lines = WORKFLOW.read_text().splitlines()
    name_re = re.compile(r"^(\s*)-\s+name:\s*" + re.escape(step_name) + r"\s*$")
    start = next((i for i, line in enumerate(lines) if name_re.match(line)), None)
    assert start is not None, f"step {step_name!r} not found in {WORKFLOW}"
    key_indent = len(name_re.match(lines[start]).group(1)) + 2
    run_re = re.compile(r"^\s{%d}run:\s*[|>][-+]?\d*\s*$" % key_indent)
    run_start = next(i for i in range(start + 1, len(lines)) if run_re.match(lines[i]))
    body, base = [], None
    for line in lines[run_start + 1 :]:
        if not line.strip():
            body.append("")
            continue
        indent = len(line) - len(line.lstrip())
        if indent < key_indent:
            break
        if base is None:
            base = indent
        elif indent < base:
            break
        body.append(line)
    while body and not body[-1].strip():
        body.pop()
    assert base is not None, f"step {step_name!r} has an empty run block"
    return "\n".join(line[base:] if line.strip() else "" for line in body)


def run_coordinator_block(script, tmp_path, coordinator_exit=0):
    """Execute a coordinator run block the way the workflow's own step does."""
    runner_temp = tmp_path / "runner-temp"
    (runner_temp / "agent-runner" / "scripts").mkdir(parents=True)
    (runner_temp / "agent-runner" / "scripts" / "progress-reporting.txt").write_text("x\n")
    # tee into a directory: a real, non-zero log-capture failure.
    (runner_temp / "coordinator.out").mkdir()
    stub_bin = tmp_path / "bin"
    stub_bin.mkdir()
    stub = stub_bin / "opencode"
    stub.write_text(f"#!/usr/bin/env bash\necho 'stub coordinator'\nexit {coordinator_exit}\n")
    stub.chmod(stub.stat().st_mode | stat.S_IEXEC)
    output = runner_temp / "github-output"
    output.touch()
    env = {
        **os.environ,
        "PATH": f"{stub_bin}{os.pathsep}{os.environ['PATH']}",
        "RUNNER_TEMP": str(runner_temp),
        "GITHUB_OUTPUT": str(output),
        "PROMPT": "regression check",
        "MODEL": "opencode/big-pickle",
        "COORDINATOR_TIMEOUT": "1",
        "OPENCODE_FATAL_STAGE": "coordinator",
    }
    result = subprocess.run(
        ["bash", "-Eeuo", "pipefail", "-c", script],
        env=env,
        capture_output=True,
        text=True,
    )
    result.outputs = dict(
        line.split("=", 1) for line in output.read_text().splitlines() if "=" in line
    )
    return result


def test_successful_coordinator_ignores_failing_tee(tmp_path):
    """The fix: a successful coordinator must not fail the run over log capture."""
    result = run_coordinator_block(extract_run_block("Run coordinator"), tmp_path)
    assert result.outputs.get("coordinator_status") == "0", result.outputs
    assert result.outputs.get("coordinator_tee_status") not in (None, "0"), result.outputs
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize("coordinator_exit", [124, 7])
def test_failed_coordinator_still_propagates_its_exit_code(tmp_path, coordinator_exit):
    """Dropping the tee status must not swallow a real coordinator failure."""
    result = run_coordinator_block(
        extract_run_block("Run coordinator"), tmp_path, coordinator_exit
    )
    assert result.outputs.get("coordinator_status") == str(coordinator_exit), result.outputs
    assert result.returncode == coordinator_exit, result.stdout + result.stderr


def test_harness_rejects_the_pre_fix_contract(tmp_path):
    """Negative control: reverting the fix must make the check above fail."""
    block = extract_run_block("Run coordinator")
    assert PRE_FIX_TAIL not in WORKFLOW.read_text()
    head, _, last = block.rpartition("\n")
    assert last == "exit 0", f"coordinator block must end in 'exit 0', got {last!r}"
    pre_fix = f"{head}\n{PRE_FIX_TAIL}"
    assert run_coordinator_block(pre_fix, tmp_path).returncode != 0


def test_run_result_step_reports_success_despite_failing_tee():
    """The second changed hunk: the run-result comment must say 'completed'."""
    step = extract_run_block("Post run-result comment")
    assert 'python3 "$RUNNER_TEMP/agent-runner/scripts/run_status.py"' in step
    assert (
        "COORDINATOR_STATUS: ${{ steps.coordinator.outputs.coordinator_status }}"
        in WORKFLOW.read_text()
    )
    assert (
        "COORDINATOR_TEE_STATUS: ${{ steps.coordinator.outputs.coordinator_tee_status }}"
        in WORKFLOW.read_text()
    )
    assert run_status.classify("success", "0", "1", "") == (
        "✅ completed (log capture failed, tee exit 1)"
    )
