import subprocess
import threading

import pytest

import subagent_runner


def test_commands_select_opencode_and_explicit_model():
    assert subagent_runner.command("opencode", "alpha/model", "task") == [
        "opencode", "run", "--agent", "coordinator", "--model", "alpha/model", "task"
    ]
    assert subagent_runner.command("t3-code", "alpha/model", "task") == [
        "t3-code", "run", "--model", "alpha/model", "--prompt", "task"
    ]


def test_t3_code_missing_cli_has_actionable_error(monkeypatch):
    monkeypatch.setattr(subagent_runner.shutil, "which", lambda executable: None)
    with pytest.raises(RuntimeError, match="headless agent execution is experimental and unsupported.*use OpenCode"):
        subagent_runner.run_agent({"model": "m", "prompt": "p"}, "t3-code")


def test_t3_code_discovery_tries_code_then_t3(monkeypatch):
    checked = []

    def which(executable):
        checked.append(executable)
        return {"t3-code": None, "t3": "/usr/bin/t3"}[executable]

    monkeypatch.setattr(subagent_runner.shutil, "which", which)
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda args, **kwargs: subprocess.CompletedProcess(
            args, 0, stdout="Usage: t3 run --model <model> --prompt <prompt>"
        ),
    )
    assert subagent_runner.t3_code_executable() == "/usr/bin/t3"
    assert checked == ["t3-code", "t3"]


def test_t3_code_discovery_falls_back_when_first_installed_cli_is_unsupported(monkeypatch):
    checked = []

    def which(executable):
        checked.append(executable)
        return f"/usr/bin/{executable}"

    monkeypatch.setattr(subagent_runner.shutil, "which", which)
    probes = []

    def run(args, **kwargs):
        probes.append(args)
        if args[0] == "/usr/bin/t3-code":
            return subprocess.CompletedProcess(args, 1, stdout="unsupported")
        return subprocess.CompletedProcess(
            args, 0, stdout="Usage: t3 run --model <model> --prompt <prompt>"
        )

    monkeypatch.setattr(subprocess, "run", run)
    assert subagent_runner.t3_code_executable() == "/usr/bin/t3"
    assert checked == ["t3-code", "t3"]
    assert probes == [
        ["/usr/bin/t3-code", "run", "--help"],
        ["/usr/bin/t3", "run", "--help"],
    ]


@pytest.mark.parametrize(
    ("returncode", "help_text", "supported"),
    [
        (0, "Usage: t3 run --model <model> --prompt <prompt>", True),
        (0, "Usage: t3 serve [--host <host>]", False),
        (1, "error: unknown command 'run'", False),
    ],
)
def test_t3_code_capability_probe_checks_command_and_flags(
    monkeypatch, returncode, help_text, supported
):
    calls = []
    monkeypatch.setattr(subagent_runner.shutil, "which", lambda executable: "/bin/t3")
    monkeypatch.setattr(
        subprocess,
        "run",
        lambda args, **kwargs: calls.append((args, kwargs))
        or subprocess.CompletedProcess(args, returncode, stdout=help_text),
    )
    if supported:
        assert subagent_runner.t3_code_executable() == "/bin/t3"
    else:
        with pytest.raises(RuntimeError, match="headless agent execution is unsupported"):
            subagent_runner.t3_code_executable()
    assert calls[0][0] == ["/bin/t3", "run", "--help"]


def test_run_agent_probes_t3_before_invoking_supported_cli(monkeypatch):
    calls = []
    monkeypatch.setattr(
        subagent_runner.shutil, "which", lambda executable: "/usr/bin/t3"
    )

    def run(args, **kwargs):
        calls.append(args)
        if args[-1] == "--help":
            return subprocess.CompletedProcess(
                args, 0, stdout="Usage: t3 run --model <model> --prompt <prompt>"
            )
        return subprocess.CompletedProcess(args, 0, stdout="done")

    monkeypatch.setattr(subprocess, "run", run)
    assert subagent_runner.run_agent({"model": "m", "prompt": "p"}, "t3-code") == "done"
    assert calls == [
        ["/usr/bin/t3", "run", "--help"],
        ["/usr/bin/t3", "run", "--model", "m", "--prompt", "p"],
    ]


def test_agents_dispatch_in_parallel(monkeypatch):
    barrier = threading.Barrier(2)
    active = 0
    peak = 0
    lock = threading.Lock()

    def run(agent, backend):
        nonlocal active, peak
        with lock:
            active += 1
            peak = max(peak, active)
        barrier.wait(timeout=2)
        with lock:
            active -= 1
        return agent["name"]

    monkeypatch.setattr(subagent_runner, "run_agent", run)
    assert subagent_runner.dispatch([{"name": "a"}, {"name": "b"}], "opencode") == ["a", "b"]
    assert peak == 2


def test_judge_skips_on_failure_and_uses_fallback(monkeypatch):
    calls = []

    def run(agent, backend):
        calls.append(agent["name"])
        if agent["name"] == "bad":
            raise subprocess.CalledProcessError(1, ["fake"])
        return "ok"

    monkeypatch.setattr(subagent_runner, "run_agent", run)
    result = subagent_runner.execute({
        "backend": "opencode",
        "agents": [{"name": "bad", "model": "m"}],
        "judge": {"name": "judge", "model": "j"},
        "fallback": {"name": "fallback", "model": "f"},
    })
    assert result == ["ok"]
    assert "judge" not in calls
    assert calls[-1] == "fallback"


def test_judge_formats_successful_agent_outputs_and_is_optional(monkeypatch, capsys):
    calls = []

    def run(agent, backend):
        calls.append(agent.copy())
        if agent["name"] == "judge":
            raise RuntimeError("judge unavailable")
        return "agent result"

    monkeypatch.setattr(subagent_runner, "run_agent", run)
    result = subagent_runner.execute({
        "backend": "opencode",
        "agents": [{"name": "agent", "model": "m", "prompt": "task"}],
        "judge": {"name": "judge", "model": "j", "prompt": "Choose from:\n{outputs}"},
    })
    assert result == ["agent result"]
    assert calls[1]["prompt"] == "Choose from:\nagent result"
    assert "judge unavailable" in capsys.readouterr().err


def test_missing_cli_fails_clearly(monkeypatch):
    monkeypatch.setattr(subagent_runner.shutil, "which", lambda executable: None)
    with pytest.raises(RuntimeError, match="not found"):
        subagent_runner.run_agent({"model": "m", "prompt": "p"}, "opencode")


def test_run_agent_invokes_explicit_model(monkeypatch):
    calls = []
    monkeypatch.setattr(subagent_runner.shutil, "which", lambda executable: executable)
    monkeypatch.setattr(subprocess, "run", lambda args, **kwargs: calls.append((args, kwargs)) or subprocess.CompletedProcess(args, 0, stdout="done"))
    assert subagent_runner.run_agent({"model": "alpha/model", "prompt": "task"}, "opencode") == "done"
    assert calls[0][0][calls[0][0].index("--model") + 1] == "alpha/model"


def test_run_agent_isolates_config_and_streams_stderr(monkeypatch):
    calls = []
    monkeypatch.setattr(subagent_runner.shutil, "which", lambda executable: executable)
    monkeypatch.setattr(subprocess, "run", lambda args, **kwargs: calls.append((args, kwargs)) or subprocess.CompletedProcess(args, 0, stdout="done"))
    monkeypatch.setenv("OPENCODE_CONFIG", "parent.json")
    subagent_runner.run_agent({"model": "m", "prompt": "one", "config": "child.json"}, "opencode")
    subagent_runner.run_agent({"model": "m", "prompt": "two"}, "opencode")
    assert calls[0][1]["env"]["OPENCODE_CONFIG"] == "child.json"
    assert calls[1][1]["env"]["OPENCODE_CONFIG"] == "parent.json"
    assert "capture_output" not in calls[0][1]
    assert calls[0][1]["stdout"] == subprocess.PIPE
