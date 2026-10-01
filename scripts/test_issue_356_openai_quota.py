"""Independent verification of bacluc-agent/agent-todo#356.

Deliberately unlike the builder's tests: no monkeypatching of os.path inside
emit_openai_state (a real HOME with a real auth.json is used), real HTTP for the
rejected/accepted refresh paths, and the workflow's fallback gating is evaluated
with GitHub's actual "if without a status function implies success()" rule
instead of a substring match.
"""

import http.server
import importlib.util
import json
import re
import subprocess
import threading
from pathlib import Path

import pytest

import model_availability

_spec = importlib.util.spec_from_file_location(
    "refresh_token_under_test", Path(__file__).with_name("refresh-token.py")
)
assert _spec and _spec.loader
refresh_token = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(refresh_token)

REPO = Path(__file__).parents[1]
WORKFLOW = REPO / ".github/workflows/refresh-chatgpt-auth.yml"

# Nothing in emit_openai_state's output may ever contain these.
ACCESS = "eyJhbGciOiJSUzI1NiIsImtpZCI6InNILUNyIn0.SECRET-ACCESS-TOKEN"
REFRESH = "rt-SECRET-REFRESH-TOKEN"
EXPIRES_MS = 1234567890000
AUTH = {
    "openai": {
        "type": "oauth",
        "access": ACCESS,
        "refresh": REFRESH,
        "expires": EXPIRES_MS,
    }
}
SECRETS = (ACCESS, REFRESH, str(EXPIRES_MS))


def write_auth_home(home: Path) -> Path:
    auth_json = home / ".local/share/opencode/auth.json"
    auth_json.parent.mkdir(parents=True, exist_ok=True)
    auth_json.write_text(json.dumps(AUTH))
    return auth_json


# --- (a) emit_openai_state against a real HOME ---------------------------------


def test_reports_present_credential_from_a_real_home(monkeypatch, capsys, tmp_path):
    home = tmp_path / "home-with-credential"
    home.mkdir()
    write_auth_home(home)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)

    model_availability.emit_openai_state(
        ["openai/gpt-5.6-luna", "openai/gpt-5.5", "big-pickle"],
        [
            "openai/gpt-5.6-luna",
            "openai/gpt-5.5",
            "openai/gpt-5.6-sol",
            "big-pickle",
        ],
    )

    out = capsys.readouterr().out
    assert "openai state: credential=present" in out
    # usable=2 of the 3 openai/* candidates; big-pickle must not be counted
    assert "openai models usable 2/3 candidates" in out
    # a usable openai/* model means the override hint must not be printed
    assert "auto-selection never picks" not in out
    for secret in SECRETS:
        assert secret not in out, f"secret material leaked: {secret[:6]}..."
    assert "access" not in out and "refresh" not in out


def test_reports_absent_credential_from_a_real_home(monkeypatch, capsys, tmp_path):
    home = tmp_path / "home-without-credential"
    (home / ".local/share/opencode").mkdir(parents=True)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)

    model_availability.emit_openai_state([], ["openai/gpt-5.6-luna"] * 3)

    out = capsys.readouterr().out
    assert "openai state: credential=absent" in out
    assert "openai models usable 0/3 candidates" in out
    assert "auto-selection never picks openai/*" in out
    assert "inputs.model=openai/<model>" in out


def test_counts_only_openai_prefixed_entries(monkeypatch, capsys, tmp_path):
    """A non-openai provider with the same model name must not inflate either count."""
    home = tmp_path / "home"
    home.mkdir()
    write_auth_home(home)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)

    model_availability.emit_openai_state(
        ["opencode/openai/gpt-5.6-luna".replace("/opencode", ""), "opencode-go-openai/gpt-5.6-luna"],
        ["openai/gpt-5.6-luna", "opencode-go-openai/gpt-5.6-luna"],
    )

    out = capsys.readouterr().out
    assert "openai models usable 0/1 candidates" in out


# --- (b) GITHUB_STEP_SUMMARY unset / set ---------------------------------------


def test_no_raises_when_step_summary_is_unset(monkeypatch, capsys, tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    write_auth_home(home)
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)

    model_availability.emit_openai_state([], ["openai/gpt-5.6-luna"])  # must not raise

    assert "openai state: credential=present" in capsys.readouterr().out


def test_appends_to_an_existing_step_summary(monkeypatch, capsys, tmp_path):
    home = tmp_path / "home"
    home.mkdir()
    write_auth_home(home)
    monkeypatch.setenv("HOME", str(home))
    summary = tmp_path / "step-summary.md"
    summary.write_text("# existing report\n")
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))

    model_availability.emit_openai_state([], ["openai/gpt-5.6-luna"])
    model_availability.emit_openai_state(["openai/gpt-5.6-luna"], ["openai/gpt-5.6-luna"])

    body = summary.read_text()
    assert body.startswith("# existing report\n"), "existing summary was clobbered"
    assert body.count("openai state:") == 2, "second call did not append"
    for secret in SECRETS:
        assert secret not in body
    assert capsys.readouterr().out.count("\n") == 2


# --- (c) refresh-token.py ------------------------------------------------------


def test_corrupt_json_reports_the_reason_on_stderr(monkeypatch, capsys):
    monkeypatch.setenv("OPENCODE_AUTH_CONTENT", '{"openai": {"type": "oauth",')
    assert refresh_token._current_auth() is None
    err = capsys.readouterr().err
    assert "OPENCODE_AUTH_CONTENT is not valid JSON" in err
    assert "Expecting" in err, "the json decoder's own reason is not surfaced"


@pytest.mark.parametrize("payload", ['["a"]', '"a-string"', "42", "true"])
def test_truthy_non_dict_json_exits_1_with_a_diagnosis(monkeypatch, capsys, payload):
    monkeypatch.setenv("OPENCODE_AUTH_CONTENT", payload)
    assert refresh_token.main() == 1
    err = capsys.readouterr().err
    assert "Traceback" not in err
    assert "AttributeError" not in err
    assert "No current OpenAI credential found" in err


def _serve(body: bytes, status: int):
    class Handler(http.server.BaseHTTPRequestHandler):
        def do_POST(self):  # noqa: N802 - http.server API
            self.rfile.read(int(self.headers.get("Content-Length") or 0))
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = http.server.HTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    return server


def test_rejected_credential_still_exits_1_after_retries(monkeypatch, capsys, tmp_path):
    """A real HTTP 400 (the quota wall) must still fail the refresh, twice, loudly."""
    server = _serve(b'{"error":"usage_limit_reached"}', 400)
    try:
        monkeypatch.setattr(refresh_token, "ISSUER", f"http://127.0.0.1:{server.server_port}")
        monkeypatch.setenv("OPENCODE_AUTH_CONTENT", json.dumps(AUTH))
        monkeypatch.setenv("HOME", str(tmp_path / "home"))
        assert refresh_token.main() == 1
    finally:
        server.shutdown()
        server.server_close()

    err = capsys.readouterr().err
    assert "Token refresh attempt 1 failed" in err
    assert "Token refresh failed after retries" in err
    assert "HTTP 400" in err
    assert not (tmp_path / "home/.local/share/opencode/auth.json").exists()


def test_refreshable_credential_still_succeeds(monkeypatch, capsys, tmp_path):
    """The happy path must be untouched: expired-but-refreshable still exits 0."""
    server = _serve(
        json.dumps({"access_token": "new-access", "refresh_token": "new-refresh", "expires_in": 3600}).encode(),
        200,
    )
    home = tmp_path / "home"
    try:
        monkeypatch.setattr(refresh_token, "ISSUER", f"http://127.0.0.1:{server.server_port}")
        monkeypatch.setenv("OPENCODE_AUTH_CONTENT", json.dumps(AUTH))
        monkeypatch.setenv("HOME", str(home))
        assert refresh_token.main() == 0
    finally:
        server.shutdown()
        server.server_close()

    written = json.loads((home / ".local/share/opencode/auth.json").read_text())
    assert written["openai"]["access"] == "new-access"
    assert written["openai"]["refresh"] == "new-refresh"
    assert json.loads(capsys.readouterr().out)["openai"]["expires"] > 0


def test_refresh_response_without_access_token_exits_1(monkeypatch, capsys, tmp_path):
    server = _serve(json.dumps({"refresh_token": "new-refresh"}).encode(), 200)
    try:
        monkeypatch.setattr(refresh_token, "ISSUER", f"http://127.0.0.1:{server.server_port}")
        monkeypatch.setenv("OPENCODE_AUTH_CONTENT", json.dumps(AUTH))
        monkeypatch.setenv("HOME", str(tmp_path / "home"))
        assert refresh_token.main() == 1
    finally:
        server.shutdown()
        server.server_close()
    assert "no access token" in capsys.readouterr().err


# --- (d) the workflow's fallback gating, evaluated the way GitHub evaluates it --

STATUS_FUNCTIONS = ("always()", "success()", "failure()", "cancelled()")


STEP_KEYS = ("name", "id", "if", "uses", "run")


def steps():
    """Minimal indentation-aware reader: name/id/if per step, in file order.

    Steps start at 6 spaces + "- "; their keys sit at 8 spaces. Reading `id` is
    what makes the implicit-success() simulation possible, so it must not be
    silently dropped.
    """
    found = []
    current = None
    for line in WORKFLOW.read_text().splitlines():
        if re.match(r"^ {6}- \S", line):
            current = {"name": None, "id": None, "if": None}
            found.append(current)
            body = line[8:]
        elif current is None or not re.match(r"^ {8}\S", line):
            continue
        else:
            body = line.strip()
        key, sep, value = body.partition(":")
        if sep and key in STEP_KEYS:
            if key == "name":
                current["name"] = value.strip()
            elif key in ("id", "if"):
                current[key] = value.strip()
    return [s for s in found if s["name"] and "{" not in s["name"]]


def test_the_reader_actually_reads_ids_and_conditions():
    """Guard against the mini-parser silently dropping `id:`/`if:` lines."""
    found = {s["name"]: s for s in steps()}
    assert found["Try token refresh (no browser)"]["id"] == "refresh"
    assert found["Validate refreshed token with opencode"]["id"] == "validate"
    assert found["Browser login (fallback)"]["id"] == "browser-login"
    assert found["Try token refresh (no browser)"]["if"] is None
    assert "refreshed == 'true'" in found["Set secret (refreshed token)"]["if"]


def evaluate(expression: str, scenario: dict, previous_ok: bool):
    """Translate a GitHub step `if` into Python and evaluate it.

    Implements the rule that made this bug invisible: when an `if` contains no
    status function, GitHub implicitly ANDs success() into it.
    """
    outcomes = {step_id: value[0] for step_id, value in scenario.items()}
    outputs = {step_id: value[1] for step_id, value in scenario.items()}
    python = expression.replace("&&", " and ").replace("||", " or ")
    python = re.sub(
        r"steps\.([\w-]+)\.outcome",
        lambda m: repr(outcomes.get(m.group(1), "skipped")),
        python,
    )
    python = re.sub(
        r"steps\.([\w-]+)\.outputs\.([\w-]+)",
        lambda m: repr(outputs.get(m.group(1), {}).get(m.group(2), "")),
        python,
    )
    for status in STATUS_FUNCTIONS:
        python = python.replace(status, "True" if status == "always()" else "False")
    if not any(f in expression for f in STATUS_FUNCTIONS):
        python = f"({python}) and {previous_ok}"
    return bool(eval(python, {"__builtins__": {}}, {}))  # noqa: S307 - fixed input from this repo


def selected_steps(scenario: dict):
    selected = []
    previous_ok = True
    for step in steps():
        runs = evaluate(step["if"] or "success()", scenario, previous_ok)
        if runs:
            selected.append(step["name"])
            own = scenario.get(step["id"] or step["name"], ("success", {}))[0]
            previous_ok = previous_ok and own == "success"
    return selected


REJECTED_TOKEN = {
    "refresh": ("success", {"refreshed": "true"}),
    "validate": ("failure", {}),
}
REFRESH_FAILED = {"refresh": ("success", {}), "validate": ("skipped", {})}
HEALTHY = {"refresh": ("success", {"refreshed": "true"}), "validate": ("success", {})}
BROKEN_BROWSER = dict(REJECTED_TOKEN, **{"browser-login": ("failure", {})})


def test_rejected_token_now_reaches_the_browser_login_fallback():
    selected = selected_steps(REJECTED_TOKEN)
    assert "Set secret (refreshed token)" not in selected, "secret must not be written from a rejected token"
    assert "Browser login (fallback)" in selected


def test_failed_refresh_token_reaches_the_browser_login_fallback():
    assert "Browser login (fallback)" in selected_steps(REFRESH_FAILED)


def test_a_healthy_credential_still_skips_every_fallback():
    selected = selected_steps(HEALTHY)
    assert "Set secret (refreshed token)" in selected
    assert "Browser login (fallback)" not in selected
    assert "Agent-usable primitives fallback (start/status/step)" not in selected


def test_primitives_fallback_runs_only_after_a_failed_browser_login():
    assert "Agent-usable primitives fallback (start/status/step)" in selected_steps(BROKEN_BROWSER)


def test_the_pre_change_condition_really_did_skip_the_fallback():
    """Proves the fix was necessary: the old bare `if` evaluates false when validate failed."""
    assert not evaluate(
        "steps.refresh.outputs.refreshed != 'true' || steps.validate.outcome != 'success'",
        REJECTED_TOKEN,
        previous_ok=False,
    )
    assert evaluate(
        "always() && (steps.refresh.outputs.refreshed != 'true' || steps.validate.outcome != 'success')",
        REJECTED_TOKEN,
        previous_ok=False,
    )


def test_both_fallbacks_are_pinned_with_always():
    fallbacks = [s for s in steps() if "fallback" in s["name"]]
    assert len(fallbacks) == 2, fallbacks
    for step in fallbacks:
        assert "always()" in (step["if"] or ""), f"{step['name']} can still be skipped by implicit success()"


def test_primitives_step_never_reports_a_refreshed_secret():
    body = WORKFLOW.read_text()
    assert "Agent primitives fallback attempted" not in body
    warning = "::warning::Agent primitives fallback ran but did not update OPENCODE_AUTH_JSON"
    assert warning in body
    # the primitives step must not call gh secret set: it has no credential to write
    primitives = body.split("Agent-usable primitives fallback", 1)[1]
    assert "gh secret set" not in primitives


# --- (d, second half) the edited shell in setup-opencode must still parse ------


def test_setup_opencode_auth_step_is_valid_shell():
    action = (REPO / ".github/actions/setup-opencode/action.yml").read_text()
    assert "opencode --help" not in action
    script = action.split("- name: Materialize OpenCode auth", 1)[1].split("- name:", 1)[0]
    script = "\n".join(
        line[10:] if line.startswith(" " * 10) else line for line in script.splitlines()
    )
    assert subprocess.run(["bash", "-n"], input=script, text=True, capture_output=True).returncode == 0