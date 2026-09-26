#!/usr/bin/env python3
import json
import os
import sys
import time
import urllib.error
import urllib.request

AISIX = "http://aisix:3000"
AISIX_COMPLETIONS = f"{AISIX}/v1/chat/completions"
OPENWEBUI = "http://127.0.0.1:8080"
OPENWEBUI_COMPLETIONS = f"{OPENWEBUI}/openai/chat/completions"
MODEL = os.environ.get("PROVE_MODEL", "chat")
QUESTION = os.environ.get("PROVE_QUESTION", "What color is the sky on a clear day? Answer in at most three words.")
TIMEOUT = int(os.environ.get("PROVE_TIMEOUT", "120"))


def extract_text(payload: dict[str, object]) -> str:
    choices = payload.get("choices")
    if not isinstance(choices, list) or not choices:
        return ""
    first_choice = choices[0]
    if not isinstance(first_choice, dict):
        return ""
    message = first_choice.get("message")
    if isinstance(message, dict):
        content = message.get("content")
        if isinstance(content, str):
            return content.strip()
    text = first_choice.get("text")
    if isinstance(text, str):
        return text.strip()
    return ""


def request(
    method: str,
    url: str,
    body: dict[str, object] | None = None,
    headers: dict[str, str] | None = None,
    timeout: int = TIMEOUT,
) -> tuple[int, dict[str, object]]:
    data = None if body is None else json.dumps(body).encode()
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    for key, value in (headers or {}).items():
        req.add_header(key, value)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as response:
            raw = response.read().decode()
            status = response.status
    except urllib.error.HTTPError as error:
        raw = error.read().decode(errors="replace")
        status = error.code
    except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as error:
        return 0, {"_error": f"{type(error).__name__}: {error}"}
    try:
        return status, json.loads(raw)
    except json.JSONDecodeError:
        return status, {"_raw": raw}


def wait_ready(url: str, attempts: int = 90) -> bool:
    for _ in range(attempts):
        status, _ = request("GET", url, timeout=10)
        if status == 200:
            return True
        time.sleep(2)
    return False


def complete(url: str, token: str, label: str) -> bool:
    status, payload = request(
        "POST",
        url,
        {"model": MODEL, "messages": [{"role": "user", "content": QUESTION}], "max_tokens": 64},
        {"Authorization": f"Bearer {token}"},
    )
    model = payload.get("model", MODEL)
    text = extract_text(payload)
    ok = status == 200 and bool(text)
    print(f"{label} http={status} model={model} text={text!r}", flush=True)
    if not ok:
        print(f"{label}_FAILED payload={json.dumps(payload)[:600]}", flush=True)
    return ok


def prove(caller_key: str, label: str) -> bool:
    if not wait_ready(f"{AISIX}/readyz"):
        print(f"{label}_FAILED aisix /readyz never became ready", flush=True)
        return False
    if not complete(AISIX_COMPLETIONS, caller_key, f"{label}_AISIX_DIRECT"):
        return False

    if not wait_ready(f"{OPENWEBUI}/health"):
        print(f"{label}_FAILED openwebui /health never became ready", flush=True)
        return False
    status, signin = request("POST", f"{OPENWEBUI}/api/v1/auths/signin", {"email": "", "password": ""})
    token = signin.get("token")
    if not token or not isinstance(token, str):
        print(f"{label}_FAILED openwebui signin http={status} {json.dumps(signin)[:300]}", flush=True)
        return False
    return complete(OPENWEBUI_COMPLETIONS, token, f"{label}_OPENWEBUI")


def main() -> int:
    caller_key = os.environ.get("OPENWEBUI_CALLER_KEY") or os.environ.get("OPENAI_API_KEYS", "")
    label = sys.argv[1] if len(sys.argv) > 1 else "PROVIDE"
    if not caller_key:
        print("OPENWEBUI_CALLER_KEY is empty", file=sys.stderr)
        return 2
    if not prove(caller_key, label):
        return 1
    print("BOTH_PROOFS_OK", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
