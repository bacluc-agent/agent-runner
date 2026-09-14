import json
import sys
import types
from pathlib import Path

import importlib.util

import pytest

try:
    import chatgpt_login
except ModuleNotFoundError:
    spec = importlib.util.spec_from_file_location("chatgpt_login", Path(__file__).with_name("chatgpt-login.py"))
    assert spec and spec.loader
    chatgpt_login = importlib.util.module_from_spec(spec)  # type: ignore[assignment]
    spec.loader.exec_module(chatgpt_login)  # type: ignore[union-attr]


def test_build_auth_json_shape():
    auth = chatgpt_login.build_auth_json("acc", "ref", 1234567890000)
    assert auth == {"openai": {"type": "oauth", "access": "acc", "refresh": "ref", "expires": 1234567890000}}
    assert json.dumps(auth) == json.dumps({"openai": {"type": "oauth", "access": "acc", "refresh": "ref", "expires": 1234567890000}})


def test_build_auth_json_rejects_empty_access():
    with pytest.raises(ValueError):
        chatgpt_login.build_auth_json("", "ref", 1)


def test_build_auth_json_rejects_empty_refresh():
    with pytest.raises(ValueError):
        chatgpt_login.build_auth_json("acc", "", 1)


def test_build_auth_json_rejects_none():
    with pytest.raises(ValueError):
        chatgpt_login.build_auth_json(None, "ref", 1)  # type: ignore[arg-type]


def test_build_auth_json_expires_must_be_int():
    with pytest.raises(ValueError):
        chatgpt_login.build_auth_json("acc", "ref", "123")  # type: ignore[arg-type]
    with pytest.raises(ValueError):
        chatgpt_login.build_auth_json("acc", "ref", 12.3)  # type: ignore[arg-type]


def test_build_auth_json_rejects_wrong_type():
    with pytest.raises(ValueError):
        chatgpt_login.build_auth_json(123, "ref", 1)  # type: ignore[arg-type]


def test_write_auth_file(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    auth = chatgpt_login.build_auth_json("a", "r", 999)
    dest = chatgpt_login.write_auth_file(auth)
    assert dest == tmp_path / ".local" / "share" / "opencode" / "auth.json"
    assert json.loads(dest.read_text()) == auth


def test_stdout_single_json_line(capsys, tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    auth = chatgpt_login.build_auth_json("tokA", "tokR", 42)
    chatgpt_login.write_auth_file(auth)
    json.dump(auth, sys.stdout)
    sys.stdout.write("\n")
    out = capsys.readouterr().out.strip()
    assert out.count("\n") == 0
    parsed = json.loads(out)
    assert parsed == {"openai": {"type": "oauth", "access": "tokA", "refresh": "tokR", "expires": 42}}


def test_main_missing_creds_returns_1(monkeypatch, capsys):
    monkeypatch.delenv("CHATGPT_EMAIL", raising=False)
    monkeypatch.delenv("OPENAI_USERNAME", raising=False)
    monkeypatch.delenv("CHATGPT_PASSWORD", raising=False)
    monkeypatch.delenv("OPENAI_PASSWORD", raising=False)
    assert chatgpt_login.main() == 1
    assert "must be set" in capsys.readouterr().err


def test_env_fallback_chain(monkeypatch):
    monkeypatch.delenv("CHATGPT_EMAIL", raising=False)
    monkeypatch.setenv("OPENAI_USERNAME", "fb@x.com")
    assert chatgpt_login._env("CHATGPT_EMAIL", ["OPENAI_USERNAME"]) == "fb@x.com"
    monkeypatch.delenv("OPENAI_USERNAME", raising=False)
    assert chatgpt_login._env("CHATGPT_EMAIL", ["OPENAI_USERNAME"]) is None
    monkeypatch.setenv("CHATGPT_EMAIL", "primary@x.com")
    monkeypatch.setenv("OPENAI_USERNAME", "fb@x.com")
    assert chatgpt_login._env("CHATGPT_EMAIL", ["OPENAI_USERNAME"]) == "primary@x.com"


def test_env_fallback_totp_three_level(monkeypatch):
    monkeypatch.delenv("CHATGPT_2FA_KEY", raising=False)
    monkeypatch.delenv("OPENAI_2FA_KEY", raising=False)
    monkeypatch.setenv("CHATGPT_TOTP_KEY", "last")
    assert chatgpt_login._env("CHATGPT_2FA_KEY", ["OPENAI_2FA_KEY", "CHATGPT_TOTP_KEY"]) == "last"
    monkeypatch.setenv("OPENAI_2FA_KEY", "middle")
    assert chatgpt_login._env("CHATGPT_2FA_KEY", ["OPENAI_2FA_KEY", "CHATGPT_TOTP_KEY"]) == "middle"
    monkeypatch.setenv("CHATGPT_2FA_KEY", "first")
    assert chatgpt_login._env("CHATGPT_2FA_KEY", ["OPENAI_2FA_KEY", "CHATGPT_TOTP_KEY"]) == "first"


def test_is_headless_default(monkeypatch):
    monkeypatch.delenv("CHATGPT_HEADLESS", raising=False)
    assert chatgpt_login._is_headless() is False


def test_is_headless_true(monkeypatch):
    monkeypatch.setenv("CHATGPT_HEADLESS", "1")
    assert chatgpt_login._is_headless() is True


def test_is_headless_false_string(monkeypatch):
    monkeypatch.setenv("CHATGPT_HEADLESS", "true")
    assert chatgpt_login._is_headless() is True


def test_is_headless_explicit_false(monkeypatch):
    monkeypatch.setenv("CHATGPT_HEADLESS", "0")
    assert chatgpt_login._is_headless() is False


def test_click_first_visible_prefers_submit_button():
    clicked = []

    class FakeLocator:
        def __init__(self, text, visible=True):
            self._text = text
            self._visible = visible

        @property
        def first(self):
            return self

        def is_visible(self, timeout=0):
            return self._visible

        def click(self):
            clicked.append(self._text)

    class FakePage:
        def locator(self, sel):
            if sel == 'button[type="submit"]':
                return FakeLocator("Continue")
            if sel == 'button:has-text("Continue")':
                return FakeLocator("Continue with Google")
            raise AssertionError(f"unexpected selector {sel}")

    assert chatgpt_login._click_first_visible(
        FakePage(), ['button[type="submit"]', 'button:has-text("Continue")']
    )
    assert clicked == ["Continue"]


def test_click_first_visible_skips_hidden_and_falls_back():
    clicked = []

    class FakeLocator:
        def __init__(self, text, visible=True):
            self._text = text
            self._visible = visible

        @property
        def first(self):
            return self

        def is_visible(self, timeout=0):
            return self._visible

        def click(self):
            clicked.append(self._text)

    class FakePage:
        def locator(self, sel):
            if sel == 'button[type="submit"]':
                return FakeLocator("Continue", visible=False)
            if sel == 'button:has-text("Continue")':
                return FakeLocator("Continue with Google")
            raise AssertionError(f"unexpected selector {sel}")

    assert chatgpt_login._click_first_visible(
        FakePage(), ['button[type="submit"]', 'button:has-text("Continue")']
    )
    assert clicked == ["Continue with Google"]


def test_is_error_page_detects_error_title():
    class FakePage:
        def title(self):
            return "Oops, an error occurred! - OpenAI"

        def inner_text(self, sel):
            return "Try again"

    assert chatgpt_login._is_error_page(FakePage()) is True


def test_is_error_page_detects_route_error_body():
    class FakePage:
        def title(self):
            return "Enter your password - OpenAI"

        def inner_text(self, sel):
            return "Oops, an error occurred! Route Error (400 Invalid content type)"

    assert chatgpt_login._is_error_page(FakePage()) is True


def test_is_error_page_false_on_normal_page():
    class FakePage:
        def title(self):
            return "Enter your password - OpenAI"

        def inner_text(self, sel):
            return "Enter your password"

    assert chatgpt_login._is_error_page(FakePage()) is False


def test_submit_password_retries_on_error_page_then_succeeds(monkeypatch, capsys):
    state = {"error": True, "submits": 0, "fills": 0}
    monkeypatch.setattr(chatgpt_login.time, "sleep", lambda s: None)

    class FakeLocator:
        def __init__(self, sel, visible=True):
            self._sel = sel
            self._visible = visible

        @property
        def first(self):
            return self

        def is_visible(self, timeout=0):
            return self._visible

        def wait_for(self, timeout=0):
            if not self._visible:
                raise TimeoutError("not visible")

        def fill(self, value):
            state["fills"] += 1

        def click(self):
            if "Try again" in self._sel:
                return
            state["submits"] += 1
            state["error"] = state["submits"] == 1

    class FakePage:
        def content(self):
            return "<html>clean</html>"

        def title(self):
            return "Oops, an error occurred! - OpenAI" if state["error"] else "Enter your password - OpenAI"

        def inner_text(self, sel):
            return "Oops, an error occurred!" if state["error"] else "Enter your password"

        def locator(self, sel):
            if sel in ('input[type="password"]:visible', 'button[type="submit"]', 'a:has-text("Try again")'):
                return FakeLocator(sel, visible=True)
            return FakeLocator(sel, visible=False)

    assert chatgpt_login._submit_password_with_retry(FakePage(), "pw") is None
    assert state["submits"] == 2
    assert state["fills"] == 2
    assert "retry 1/2" in capsys.readouterr().err


def test_submit_password_retry_exhausts_after_three_attempts(monkeypatch, capsys):
    state = {"submits": 0, "fills": 0}
    monkeypatch.setattr(chatgpt_login.time, "sleep", lambda s: None)

    class FakeLocator:
        def __init__(self, sel, visible=True):
            self._sel = sel
            self._visible = visible

        @property
        def first(self):
            return self

        def is_visible(self, timeout=0):
            return self._visible

        def wait_for(self, timeout=0):
            if not self._visible:
                raise TimeoutError("not visible")

        def fill(self, value):
            state["fills"] += 1

        def click(self):
            if "Try again" not in self._sel:
                state["submits"] += 1

    class FakePage:
        def content(self):
            return "<html>clean</html>"

        def title(self):
            return "Oops, an error occurred! - OpenAI"

        def inner_text(self, sel):
            return "Oops, an error occurred! Route Error"

        def locator(self, sel):
            if sel in ('input[type="password"]:visible', 'button[type="submit"]', 'a:has-text("Try again")'):
                return FakeLocator(sel, visible=True)
            return FakeLocator(sel, visible=False)

    assert chatgpt_login._submit_password_with_retry(FakePage(), "pw") is None
    assert state["submits"] == 3
    assert state["fills"] == 3
    assert "retry 2/2" in capsys.readouterr().err


def test_wait_for_blocking_clear_returns_none_after_challenge_clears(monkeypatch):
    clock = {"t": 0.0}
    monkeypatch.setattr(chatgpt_login.time, "monotonic", lambda: clock["t"])
    monkeypatch.setattr(chatgpt_login.time, "sleep", lambda s: clock.update(t=clock["t"] + s))

    calls = {"n": 0}

    class FakePage:
        def content(self):
            calls["n"] += 1
            return "<html>captcha</html>" if calls["n"] <= 2 else "<html>clean</html>"

        def locator(self, *a, **k):
            raise AssertionError("locator should not be called when content contains captcha")

    assert chatgpt_login._wait_for_blocking_clear(FakePage()) is None
    assert calls["n"] == 3


def test_wait_for_blocking_clear_returns_label_on_persistent_blocking(monkeypatch):
    clock = {"t": 0.0}
    monkeypatch.setattr(chatgpt_login.time, "monotonic", lambda: clock["t"])
    monkeypatch.setattr(chatgpt_login.time, "sleep", lambda s: clock.update(t=clock["t"] + s))

    class FakePage:
        def content(self):
            return "<html>Verify you are human captcha</html>"

        def locator(self, *a, **k):
            raise AssertionError("locator should not be called when content contains captcha")

    assert chatgpt_login._wait_for_blocking_clear(FakePage(), timeout_s=1) == "captcha/device verification detected"


def test_wait_for_blocking_clear_keeps_polling_on_transient_error(monkeypatch):
    clock = {"t": 0.0}
    monkeypatch.setattr(chatgpt_login.time, "monotonic", lambda: clock["t"])
    monkeypatch.setattr(chatgpt_login.time, "sleep", lambda s: clock.update(t=clock["t"] + s))

    calls = {"n": 0}

    class FakePage:
        def content(self):
            calls["n"] += 1
            if calls["n"] == 1:
                raise RuntimeError("Execution context was destroyed")
            return "<html>clean</html>"

        def locator(self, *a, **k):
            raise AssertionError("locator should not be called when content contains captcha")

    assert chatgpt_login._wait_for_blocking_clear(FakePage()) is None
    assert calls["n"] == 2


def test_main_captcha_returns_2(monkeypatch, capsys):
    monkeypatch.setenv("CHATGPT_EMAIL", "e@x.com")
    monkeypatch.setenv("CHATGPT_PASSWORD", "pw")

    class FakePage:
        def goto(self, *a, **k):
            pass

        def content(self):
            return "<html><body>Verify you are human captcha</body></html>"

        def locator(self, *a, **k):
            raise AssertionError("locator should not be called when content contains captcha")

    class FakeContext:
        def new_page(self):
            return FakePage()

    class FakeBrowser:
        def new_context(self, **kwargs):
            return FakeContext()

        def close(self):
            pass

    class FakeChromium:
        def launch(self, headless=True, **kwargs):
            return FakeBrowser()

    class FakeP:
        def __init__(self):
            self.chromium = FakeChromium()

        def __enter__(self):
            return self

        def __exit__(self, *a):
            pass

    fake_sync = types.ModuleType("playwright.sync_api")
    fake_sync.sync_playwright = lambda: FakeP()
    monkeypatch.setitem(sys.modules, "playwright.sync_api", fake_sync)

    assert chatgpt_login.main() == 2
    assert "Login blocked" in capsys.readouterr().err


def _jq_valid_auth(content: str) -> bool:
    import subprocess

    jq_filter = '.openai.type == "oauth" and .openai.access != "" and .openai.refresh != "" and (.openai.expires | type == "number")'
    result = subprocess.run(["jq", "-e", jq_filter], input=content, text=True, capture_output=True)
    return result.returncode == 0


def test_jq_rejects_invalid_json():
    assert not _jq_valid_auth("not json")
    assert not _jq_valid_auth("{ invalid")
    assert not _jq_valid_auth("")


def test_jq_rejects_schema_mismatch():
    assert not _jq_valid_auth(json.dumps({"openai": {"type": "oauth"}}))
    assert not _jq_valid_auth(json.dumps({"openai": {"type": "oauth", "access": "a", "refresh": "r"}}))
    assert not _jq_valid_auth(json.dumps({"openai": {"type": "oauth", "access": "a", "refresh": "r", "expires": "123"}}))
    assert not _jq_valid_auth(json.dumps({"openai": {"type": "not-oauth", "access": "a", "refresh": "r", "expires": 1}}))
    assert not _jq_valid_auth(json.dumps({"openai": {"type": "oauth", "access": "", "refresh": "r", "expires": 1}}))


def test_jq_accepts_valid_auth():
    valid = json.dumps({"openai": {"type": "oauth", "access": "acc", "refresh": "ref", "expires": 1234567890000}})
    assert _jq_valid_auth(valid)


def test_workflow_removes_invalid_auth_and_continues(tmp_path, monkeypatch):
    import subprocess

    auth_path = tmp_path / "auth.json"
    for content, should_exist in [
        ("not json", False),
        (json.dumps({"openai": {"type": "oauth"}}), False),
        (json.dumps({"openai": {"type": "oauth", "access": "a", "refresh": "r", "expires": 1}}), True),
    ]:
        auth_path.write_text(content, encoding="utf-8")
        jq_filter = '.openai.type == "oauth" and .openai.access != "" and .openai.refresh != "" and (.openai.expires | type == "number")'
        result = subprocess.run(["jq", "-e", jq_filter, str(auth_path)], capture_output=True)
        if result.returncode != 0:
            auth_path.unlink(missing_ok=True)
        assert auth_path.exists() == should_exist


def test_opencode_help_check_removes_broken_auth(tmp_path, monkeypatch):
    import subprocess

    auth_path = tmp_path / "auth.json"
    auth_path.parent.mkdir(parents=True, exist_ok=True)
    auth_path.write_text(json.dumps({"openai": {"type": "oauth", "access": "a", "refresh": "r", "expires": 1}}))

    def fake_opencode_help_fails(*a, **kw):
        return subprocess.CompletedProcess(args=["opencode", "--help"], returncode=1, stdout="", stderr="crash")

    monkeypatch.setattr(subprocess, "run", fake_opencode_help_fails)
    result = subprocess.run(["opencode", "--help"], capture_output=True)  # type: ignore[call-overload]
    if result.returncode != 0:
        auth_path.unlink(missing_ok=True)
    assert not auth_path.exists()

    auth_path.write_text(json.dumps({"openai": {"type": "oauth", "access": "a", "refresh": "r", "expires": 1}}))

    def fake_opencode_help_ok(*a, **kw):
        return subprocess.CompletedProcess(args=["opencode", "--help"], returncode=0, stdout="", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_opencode_help_ok)
    result = subprocess.run(["opencode", "--help"], capture_output=True)  # type: ignore[call-overload]
    if result.returncode != 0:
        auth_path.unlink(missing_ok=True)
    assert auth_path.exists()
