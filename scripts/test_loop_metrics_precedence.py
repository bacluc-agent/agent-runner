"""Plain-assert precedence checks for loop_metrics.main().

Runnable with `python3 scripts/test_loop_metrics_precedence.py` (no framework)
and collected by pytest (pythonpath = scripts).
"""
import contextlib
import io
import json
import os
import tempfile

import loop_metrics

ARTIFACT = {
    "steps": 5,
    "tokenCostPerStep": 0.01,
    "convergenceRate": 2.5,
    "failureMode": "success",
    "terminatedAt": "2026-09-26T00:00:00+00:00",
}


def run_case(artifact_mode, env_mode):
    """Drive main() end-to-end in a fresh temp dir; return (artifact, summary, stdout)."""
    env_keys = ("LOOP_FAILURE_MODE", "GITHUB_STEP_SUMMARY", "GITHUB_OUTPUT")
    saved = {k: os.environ.get(k) for k in env_keys}
    old_cwd = os.getcwd()
    with tempfile.TemporaryDirectory() as tmp:
        try:
            os.chdir(tmp)
            with open("loop-metrics.json", "w") as f:
                json.dump({**ARTIFACT, "failureMode": artifact_mode}, f)
            os.environ["GITHUB_STEP_SUMMARY"] = os.path.join(tmp, "summary.md")
            os.environ["GITHUB_OUTPUT"] = os.path.join(tmp, "output.txt")
            if env_mode is None:
                os.environ.pop("LOOP_FAILURE_MODE", None)
            else:
                os.environ["LOOP_FAILURE_MODE"] = env_mode
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                assert loop_metrics.main() == 0
            with open("loop-metrics.json") as f:
                artifact = json.load(f)
            with open(os.environ["GITHUB_STEP_SUMMARY"]) as f:
                summary = f.read()
            print(summary)  # rendered table visible when run via `python3` (evidence)
            print(out.getvalue())
            return artifact, summary, out.getvalue()
        finally:
            os.chdir(old_cwd)
            for k, v in saved.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v


def test_env_timeout_beats_artifact_success():
    artifact, summary, out = run_case("success", "timeout")
    assert artifact["failure_mode"] == "timeout"
    assert "failure_mode=timeout (source=env); env=timeout" in out
    assert "| Mode source | env |" in summary
    assert "| Disagreement | env=timeout artifact=success |" in summary


def test_env_error_beats_artifact_success():
    artifact, summary, out = run_case("success", "error")
    assert artifact["failure_mode"] == "error"
    assert "failure_mode=error (source=env); env=error" in out
    assert "| Mode source | env |" in summary
    assert "| Disagreement | env=error artifact=success |" in summary


def test_env_unknown_loses_to_artifact():
    artifact, summary, out = run_case("max-steps", "unknown")
    assert artifact["failure_mode"] == "max-steps"
    assert "failure_mode=max-steps (source=artifact); env=unknown" in out
    assert "| Mode source | artifact |" in summary
    assert "Disagreement" not in summary


if __name__ == "__main__":
    for case in (
        test_env_timeout_beats_artifact_success,
        test_env_error_beats_artifact_success,
        test_env_unknown_loses_to_artifact,
    ):
        case()
        print(f"PASS {case.__name__}")
    print("all precedence checks passed")
