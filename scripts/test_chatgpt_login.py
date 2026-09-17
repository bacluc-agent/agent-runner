import importlib.util
import json
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "chatgpt_login", Path(__file__).with_name("chatgpt-login.py")
)
assert spec and spec.loader
chatgpt_login = importlib.util.module_from_spec(spec)
spec.loader.exec_module(chatgpt_login)


def test_build_auth_json_shape():
    auth = chatgpt_login.build_auth_json("acc", "ref", 1234567890000)
    assert auth == {
        "openai": {"type": "oauth", "access": "acc", "refresh": "ref", "expires": 1234567890000}
    }


def test_build_auth_json_rejects_empty_access():
    with pytest.raises(ValueError):
        chatgpt_login.build_auth_json("", "ref", 1)


def test_build_auth_json_rejects_empty_refresh():
    with pytest.raises(ValueError):
        chatgpt_login.build_auth_json("acc", "", 1)


def test_build_auth_json_rejects_non_int_expires():
    with pytest.raises(ValueError):
        chatgpt_login.build_auth_json("acc", "ref", "123")
    with pytest.raises(ValueError):
        chatgpt_login.build_auth_json("acc", "ref", 12.3)


def test_write_auth_file_explicit_path(tmp_path):
    dest = tmp_path / "nested" / "dir" / "auth.json"
    auth = chatgpt_login.build_auth_json("a", "r", 999)
    assert chatgpt_login.write_auth_file(auth, dest) == dest
    assert dest.parent.is_dir()
    assert json.loads(dest.read_text(encoding="utf-8")) == auth


def test_write_auth_file_default_path(tmp_path, monkeypatch):
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    auth = chatgpt_login.build_auth_json("a", "r", 999)
    dest = chatgpt_login.write_auth_file(auth)
    assert dest == tmp_path / ".local" / "share" / "opencode" / "auth.json"
    assert json.loads(dest.read_text(encoding="utf-8")) == auth