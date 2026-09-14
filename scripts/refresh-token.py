#!/usr/bin/env python3
"""Renew the opencode OpenAI (ChatGPT) OAuth credential via the refresh token.

No browser needed: POST grant_type=refresh_token to auth.openai.com/oauth/token
and write the rotated tokens to ~/.local/share/opencode/auth.json.

The current credential is read from OPENCODE_AUTH_CONTENT (the workflow passes
the OPENCODE_AUTH_JSON secret) or from the auth.json file.

Exit codes: 0 success, 1 refresh failed (caller should fall back to a full
browser login).
"""
import json
import os
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

CLIENT_ID = "app_EMoamEEZ73f0CkXaXp7hrann"
ISSUER = "https://auth.openai.com"
TOKEN_PATH = "/oauth/token"


def build_auth_json(access: str, refresh: str, expires: int) -> dict:
    if not isinstance(access, str) or not access:
        raise ValueError("access must be a non-empty string")
    if not isinstance(refresh, str) or not refresh:
        raise ValueError("refresh must be a non-empty string")
    if not isinstance(expires, int):
        raise ValueError("expires must be an int (millisecond epoch)")
    return {"openai": {"type": "oauth", "access": access, "refresh": refresh, "expires": expires}}


def write_auth_file(auth: dict, path: Path | None = None) -> Path:
    dest = path or Path.home() / ".local" / "share" / "opencode" / "auth.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(auth), encoding="utf-8")
    return dest


def _current_auth() -> dict | None:
    content = os.environ.get("OPENCODE_AUTH_CONTENT")
    if content:
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            return None
    path = Path.home() / ".local" / "share" / "opencode" / "auth.json"
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def refresh_tokens(refresh_token: str) -> dict:
    body = urllib.parse.urlencode({
        "grant_type": "refresh_token",
        "refresh_token": refresh_token,
        "client_id": CLIENT_ID,
    }).encode()
    req = urllib.request.Request(
        f"{ISSUER}{TOKEN_PATH}",
        data=body,
        headers={"Content-Type": "application/x-www-form-urlencoded", "User-Agent": "opencode/refresh"},
    )
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.load(resp)


def main() -> int:
    auth = _current_auth()
    if not auth or not isinstance(auth.get("openai"), dict):
        print("No current OpenAI credential found (OPENCODE_AUTH_CONTENT or auth.json)", file=sys.stderr)
        return 1
    refresh = auth["openai"].get("refresh")
    if not refresh:
        print("No refresh token in current credential", file=sys.stderr)
        return 1

    try:
        tokens = refresh_tokens(refresh)
    except Exception as e:
        print(f"Token refresh failed: {e}", file=sys.stderr)
        return 1

    access = tokens.get("access_token", "")
    new_refresh = tokens.get("refresh_token", "")
    expires_in = tokens.get("expires_in") or 3600
    if not access or not new_refresh:
        print("Token refresh returned no access/refresh token", file=sys.stderr)
        return 1

    try:
        auth = build_auth_json(access, new_refresh, int(time.time() * 1000) + int(expires_in) * 1000)
    except ValueError as e:
        print(str(e), file=sys.stderr)
        return 1

    write_auth_file(auth)
    json.dump(auth, sys.stdout)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())