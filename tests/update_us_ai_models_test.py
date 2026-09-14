import importlib.util
import json
import os

_SCRIPT = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "scripts",
    "update-us-ai-models.py",
)
_spec = importlib.util.spec_from_file_location("update_us_ai_models", _SCRIPT)
assert _spec is not None
assert _spec.loader is not None
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)


def test_strip_jsonc_comments_removes_line_comments() -> None:
    text = '{\n  // hello\n  "x": 1\n}'
    assert mod.strip_jsonc_comments(text) == '{\n  \n  "x": 1\n}'


def test_strip_jsonc_comments_removes_block_comments() -> None:
    text = '{\n  /* block */\n  "x": 1\n}'
    assert mod.strip_jsonc_comments(text) == '{\n  \n  "x": 1\n}'


def test_strip_jsonc_comments_preserves_strings() -> None:
    text = '{"url": "http://example.com // not a comment"}'
    assert mod.strip_jsonc_comments(text) == text


def test_strip_jsonc_comments_preserves_escaped_quotes() -> None:
    text = '{"s": "say \\"hi\\" // still string"}'
    assert mod.strip_jsonc_comments(text) == text


def test_npm_name_unscoped() -> None:
    assert mod.npm_name("opencode-gemini-auth@1.4.9") == "opencode-gemini-auth"


def test_npm_name_scoped() -> None:
    assert mod.npm_name("@dietrichgebert/ponytail@4.8.4") == "@dietrichgebert/ponytail"


def test_npm_name_no_version() -> None:
    assert mod.npm_name("@scope/name") is None
    assert mod.npm_name("plain") is None


def test_oauth_openai_model_is_available_in_model_catalog() -> None:
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "deploys",
        "development_tools",
        "ai_agent_devcontainer",
        "files",
        "opencode",
        "opencode.jsonc",
    )
    with open(config_path) as config_file:
        config = json.loads(mod.strip_jsonc_comments(config_file.read()))

    assert config["provider"]["openai"]["models"]["gpt-5.6-luna"] == {"name": "gpt-5.6-luna"}
