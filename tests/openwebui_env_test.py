import re
from pathlib import Path
from typing import Any

from group_data.all import openwebui
from operations.openwebui_env import env_lines

FILES = Path(__file__).parent.parent / "deploys" / "openwebui" / "files"

SECRETS: dict[str, Any] = {
    "opencode_api_key": "key-one",
    "opencode_api_key_2": "key-two",
    "opencode_api_key_3": "key-three",
    "opencode_base_url": "https://example.invalid/one",
    "requesty_api_key": "key-requesty",
    "requesty_base_url": "https://example.invalid/requesty",
    "cortecs_api_key": "key-cortecs",
    "cortecs_base_url": "https://example.invalid/cortecs",
    "openwebui_caller_key": "key-caller",
    "zen_model_chat": "model-chat",
    "zen_model_chat_thinking": "model-thinking",
    "zen_model_web_research": "model-research",
    "zen_model_fast": "model-fast",
    "requesty_model_chat": "model-requesty",
    "cortecs_model_chat": "model-cortecs",
    "extra_env": {"ENABLE_OPENAI_API": "true"},
}


def names(lines: list[str]) -> list[str]:
    return [line.partition("=")[0] for line in lines]


def values(lines: list[str]) -> dict[str, str]:
    return {name: value for name, _, value in (line.partition("=") for line in lines)}


def test_env_covers_every_interpolated_variable() -> None:
    used: set[str] = set()
    for name in ("docker-compose.yml", "resources.yaml", "aisix-config.yaml"):
        used |= set(re.findall(r"\$\{([A-Z0-9_]+)\}", (FILES / name).read_text()))
    missing = used - set(names(env_lines(openwebui)))
    assert not missing, f"missing from .env: {sorted(missing)}"


def test_openai_api_keys_carries_the_caller_key() -> None:
    written = values(env_lines(SECRETS))
    assert written["OPENWEBUI_CALLER_KEY"] == "key-caller"
    assert written["OPENAI_API_KEYS"] == "key-caller"


def test_openai_api_keys_is_not_duplicated_from_extra_env() -> None:
    with_dupe = {**SECRETS, "extra_env": {**SECRETS["extra_env"], "OPENAI_API_KEYS": "key-second"}}
    lines = env_lines(with_dupe)
    assert names(lines).count("OPENAI_API_KEYS") == 1
    assert values(lines)["OPENAI_API_KEYS"] == "key-caller"
