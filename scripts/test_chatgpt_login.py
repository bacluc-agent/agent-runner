import json
import sys
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
