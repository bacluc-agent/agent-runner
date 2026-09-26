from typing import Any


def env_lines(openwebui: dict[str, Any]) -> list[str]:
    return [
        f"OPENCODE_API_KEY={openwebui['opencode_api_key']}",
        f"OPENCODE_API_KEY_2={openwebui['opencode_api_key_2']}",
        f"OPENCODE_API_KEY_3={openwebui['opencode_api_key_3']}",
        f"OPENCODE_BASE_URL={openwebui['opencode_base_url']}",
        f"REQUESTY_API_KEY={openwebui['requesty_api_key']}",
        f"REQUESTY_BASE_URL={openwebui['requesty_base_url']}",
        f"CORTECS_API_KEY={openwebui['cortecs_api_key']}",
        f"CORTECS_BASE_URL={openwebui['cortecs_base_url']}",
        f"OPENWEBUI_CALLER_KEY={openwebui['openwebui_caller_key']}",
        f"OPENAI_API_KEYS={openwebui['openwebui_caller_key']}",
        f"ZEN_MODEL_CHAT={openwebui['zen_model_chat']}",
        f"ZEN_MODEL_CHAT_THINKING={openwebui['zen_model_chat_thinking']}",
        f"ZEN_MODEL_WEB_RESEARCH={openwebui['zen_model_web_research']}",
        f"ZEN_MODEL_FAST={openwebui['zen_model_fast']}",
        f"REQUESTY_MODEL_CHAT={openwebui['requesty_model_chat']}",
        f"CORTECS_MODEL_CHAT={openwebui['cortecs_model_chat']}",
        *[f"{k}={v}" for k, v in openwebui["extra_env"].items() if k != "OPENAI_API_KEYS"],
    ]
