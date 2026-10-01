import importlib.util
import json
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "refresh_token", Path(__file__).with_name("refresh-token.py")
)
assert spec and spec.loader
refresh_token = importlib.util.module_from_spec(spec)
spec.loader.exec_module(refresh_token)

WORKFLOW = Path(__file__).parents[1] / ".github/workflows/refresh-chatgpt-auth.yml"

VALID_AUTH = {
    "openai": {"type": "oauth", "access": "acc", "refresh": "ref", "expires": 1234567890000}
}


def test_parses_valid_env_json(monkeypatch):
    monkeypatch.setenv("OPENCODE_AUTH_CONTENT", json.dumps(VALID_AUTH))
    assert refresh_token._current_auth() == VALID_AUTH


def test_corrupt_env_json_reports_and_returns_none(monkeypatch, capsys):
    monkeypatch.setenv("OPENCODE_AUTH_CONTENT", "{not json")
    assert refresh_token._current_auth() is None
    assert "OPENCODE_AUTH_CONTENT is not valid JSON" in capsys.readouterr().err


def test_list_valued_env_json_exits_1_without_traceback(monkeypatch, capsys):
    monkeypatch.setenv("OPENCODE_AUTH_CONTENT", json.dumps(["not", "a", "dict"]))
    assert refresh_token.main() == 1
    assert "AttributeError" not in capsys.readouterr().err


class TestChatGPTRefreshFallbacksRun:
    def test_both_fallbacks_run_even_after_a_failing_step(self):
        content = WORKFLOW.read_text()
        assert (
            "if: always() && (steps.refresh.outputs.refreshed != 'true' "
            "|| steps.validate.outcome != 'success')" in content
        )
        assert "if: always() && steps.browser-login.outcome == 'failure'" in content

    def test_primitives_step_does_not_claim_a_refreshed_secret(self):
        content = WORKFLOW.read_text()
        assert "Agent primitives fallback attempted" not in content
        assert (
            "::warning::Agent primitives fallback ran but did not update OPENCODE_AUTH_JSON"
            in content
        )
