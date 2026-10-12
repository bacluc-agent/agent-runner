"""Regression check for the tee exit contract in the discovery and selection steps.

Same defect as the coordinator step: `Select model` (.github/workflows/opencode.yml)
and `Pick issue and dispatch` (.github/workflows/hourly-issue.yml) exited with
tee's status even when the wrapped opencode run itself exited 0, so a log-capture
failure failed the whole step. These tests execute the REAL run blocks extracted
from the real workflow files with a stub `opencode` that exits 0 and a stub
`tee` that writes the output file through to the real tee and then exits 1.
The blocks must still exit 0 and report the agent's own result.
bacluc-agent/agent-todo#296.
"""

import os
import pathlib
import re
import shutil
import stat
import subprocess

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[1]
OPENCODE_WORKFLOW = ROOT / ".github/workflows/opencode.yml"
HOURLY_WORKFLOW = ROOT / ".github/workflows/hourly-issue.yml"

TEE_EXIT_RE = re.compile(r'exit "\$\w*tee_status"')

# The pre-fix blocks, in extracted-block coordinates (dedented like the run
# body): exit with tee's status right after the diagnostic printf line.
PRE_FIX_DISCOVERY_BLOCK = '''if ((discovery_tee_status != 0)); then
  exit "$discovery_tee_status"
fi'''

PRE_FIX_SELECTION_BLOCK = '''if (( selection_tee_status != 0 )); then
  exit "$selection_tee_status"
fi'''

GH_STUB = '''case "$1" in
  api)
    printf '%s\\n' '[{"number":123,"title":"contract","body":"","created_at":"2026-01-01T00:00:00Z","labels":[]}]'
    ;;
  repo)
    exit 1
    ;;
  pr)
    exit 0
    ;;
  issue)
    printf '%s\\n' '{"comments": []}'
    ;;
  *)
    exit 0
    ;;
esac'''


def extract_run_block(workflow_path, step_name):
    """Return the `run:` body of a workflow step without a YAML parser.

    PyYAML is not available in `uv run --group dev`, so locate the step by its
    `- name:` line, derive the indent of the step keys, then read the block scalar
    body until a line dedents below its own first non-blank line.
    """
    lines = pathlib.Path(workflow_path).read_text().splitlines()
    name_re = re.compile(r"^(\s*)-\s+name:\s*" + re.escape(step_name) + r"\s*$")
    start = next((i for i, line in enumerate(lines) if name_re.match(line)), None)
    assert start is not None, f"step {step_name!r} not found in {workflow_path}"
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


def write_stub(bin_dir, name, body):
    stub = bin_dir / name
    stub.write_text(f"#!/usr/bin/env bash\n{body}\n")
    stub.chmod(stub.stat().st_mode | stat.S_IEXEC)
    return stub


def failing_tee_body():
    """Run the real tee so the log file IS written, then fail: log capture failed."""
    real_tee = shutil.which("tee")
    assert real_tee is not None, "no tee on PATH"
    return f'{real_tee} "$@"\nexit 1'


def run_block(script, stubs, tmp_path, cwd=None, extra_env=None):
    """Execute a run block the way the workflow's own step does.

    `stubs` maps tool names to stub bodies; each stub is placed on PATH ahead of
    the real tool. `tee` is always stubbed to fail after writing the log file.
    """
    stub_bin = tmp_path / "bin"
    stub_bin.mkdir()
    write_stub(stub_bin, "tee", failing_tee_body())
    for name, body in stubs.items():
        write_stub(stub_bin, name, body)
    env = {**os.environ, "PATH": f"{stub_bin}{os.pathsep}{os.environ['PATH']}"}
    env.update(extra_env or {})
    return subprocess.run(
        ["bash", "-Eeuo", "pipefail", "-c", script],
        env=env,
        cwd=None if cwd is None else str(cwd),
        capture_output=True,
        text=True,
    )


def read_output(result, output):
    result.outputs = dict(
        line.split("=", 1) for line in output.read_text().splitlines() if "=" in line
    )
    return result


def reinsert_tee_exit(block, pre_fix_block):
    """Re-insert a pre-fix tee-exit block right after the diagnostic printf line."""
    lines = block.splitlines()
    idx = next(i for i, line in enumerate(lines) if "statuses: opencode=" in line)
    indent = lines[idx][: len(lines[idx]) - len(lines[idx].lstrip())]
    inserted = [indent + line if line.strip() else line for line in pre_fix_block.splitlines()]
    lines[idx + 1 : idx + 1] = inserted
    return "\n".join(lines)


def run_discovery_block(script, tmp_path):
    """Execute the `Select model` run block: opencode succeeds, tee fails."""
    runner_temp = tmp_path / "runner-temp"
    (runner_temp / "agent-runner" / "scripts").mkdir(parents=True)
    shutil.copy(
        ROOT / "scripts/model-deny-list.txt",
        runner_temp / "agent-runner/scripts/model-deny-list.txt",
    )
    output = runner_temp / "github-output"
    output.touch()
    result = run_block(
        script,
        {"opencode": "echo 'coordinator: opencode/big-pickle'\nexit 0"},
        tmp_path,
        extra_env={
            "MODEL_TEXT": "",
            "MODEL_CHOICE": "auto",
            "AVAILABLE_MODELS": "opencode/big-pickle",
            "GITHUB_TOKEN": "dummy",
            "BACLUC_AGENT_GITHUB_TOKEN": "dummy",
            "OPENCODE_GO_API_KEY": "dummy",
            "OPENCODE_GO_2_API_KEY": "dummy",
            "OPENROUTER_API_KEY": "dummy",
            "OPENCODE_AUTH_CONTENT": "dummy",
            "DISCOVERY_TIMEOUT": "1",
            "RUNNER_TEMP": str(runner_temp),
            "GITHUB_OUTPUT": str(output),
            "PROMPT": "contract test",
            "ISSUE_REPOSITORY": "bacluc-agent/agent-todo",
            "RUNNER_NAME": "local",
            "GITHUB_RUN_ID": "local",
        },
    )
    return read_output(result, output)


def run_selection_block(script, tmp_path):
    """Execute the `Pick issue and dispatch` run block: opencode and gh succeed, tee fails."""
    work = tmp_path / "work"
    (work / "scripts").mkdir(parents=True)
    shutil.copy(
        ROOT / "scripts/issue-selection-tail.txt", work / "scripts/issue-selection-tail.txt"
    )
    shutil.copy(ROOT / "scripts/model-deny-list.txt", work / "scripts/model-deny-list.txt")
    shutil.copy(ROOT / "scripts/selection_tiers.py", work / "scripts/selection_tiers.py")
    runner_temp = tmp_path / "runner-temp"
    runner_temp.mkdir()
    output = runner_temp / "github-output"
    output.touch()
    result = run_block(
        script,
        {
            "opencode": "echo 'SELECTED_ISSUE: 123'\nexit 0",
            "gh": GH_STUB,
        },
        tmp_path,
        cwd=work,
        extra_env={
            "ISSUE_REPOSITORY": "bacluc-agent/agent-todo",
            "GITHUB_REPOSITORY": "bacluc-agent/agent-runner",
            "AVAILABLE_MODELS": "opencode/big-pickle",
            "SELECTION_PROMPT": "",
            "SELECTION_TIMEOUT_MINUTES": "1",
            "OPENCODE_FATAL_STAGE": "selection",
            "GITHUB_TOKEN": "dummy",
            "OPENCODE_GO_API_KEY": "dummy",
            "OPENCODE_GO_2_API_KEY": "dummy",
            "OPENROUTER_API_KEY": "dummy",
            "OPENCODE_AUTH_CONTENT": "dummy",
            "MODEL_AVAILABILITY_CACHE_ISSUE": "",
            "RUNNER_TEMP": str(runner_temp),
            "GITHUB_OUTPUT": str(output),
            "GITHUB_RUN_ID": "local",
            "RUNNER_NAME": "local",
            "GITHUB_ACTIONS": "true",
        },
    )
    return read_output(result, output)


def test_no_workflow_exits_on_tee_status():
    """The defect must not return to any of the four tee sites."""
    workflows = sorted((ROOT / ".github/workflows").glob("*.yml"))
    assert workflows
    for workflow in workflows:
        for lineno, line in enumerate(workflow.read_text().splitlines(), 1):
            assert TEE_EXIT_RE.search(line) is None, f"{workflow}:{lineno}: {line.strip()}"


def test_successful_discovery_ignores_failing_tee(tmp_path):
    """A successful model discovery must not fail the run over log capture."""
    result = run_discovery_block(
        extract_run_block(OPENCODE_WORKFLOW, "Select model"), tmp_path
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.outputs.get("model") == "opencode/big-pickle", result.outputs
    assert "Model detection statuses: opencode=0 tee=1" in result.stdout
    assert "source: discovery" in result.stdout


def test_discovery_harness_rejects_the_pre_fix_contract(tmp_path):
    """Negative control: reverting the fix must make the check above fail."""
    block = extract_run_block(OPENCODE_WORKFLOW, "Select model")
    assert PRE_FIX_DISCOVERY_BLOCK not in OPENCODE_WORKFLOW.read_text()
    pre_fix = reinsert_tee_exit(block, PRE_FIX_DISCOVERY_BLOCK)
    assert run_discovery_block(pre_fix, tmp_path).returncode != 0


def test_successful_selection_ignores_failing_tee(tmp_path):
    """A successful issue selection must not fail the run over log capture."""
    result = run_selection_block(
        extract_run_block(HOURLY_WORKFLOW, "Pick issue and dispatch"), tmp_path
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.outputs.get("issue_number") == "123", result.outputs
    assert "Model selection statuses: opencode=0 tee=1" in result.stdout


def test_selection_harness_rejects_the_pre_fix_contract(tmp_path):
    """Negative control: reverting the fix must make the check above fail."""
    block = extract_run_block(HOURLY_WORKFLOW, "Pick issue and dispatch")
    assert PRE_FIX_SELECTION_BLOCK not in HOURLY_WORKFLOW.read_text()
    pre_fix = reinsert_tee_exit(block, PRE_FIX_SELECTION_BLOCK)
    assert run_selection_block(pre_fix, tmp_path).returncode != 0
