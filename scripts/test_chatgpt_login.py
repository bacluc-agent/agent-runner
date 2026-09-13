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
        def new_context(self):
            return FakeContext()

        def close(self):
            pass

    class FakeChromium:
        def launch(self, headless=True):
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
