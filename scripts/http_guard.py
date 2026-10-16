#!/usr/bin/env python3
import json
import os
from pathlib import Path
import re
from urllib.parse import urlparse

OWNED_ORGS = {"bacluc", "bacluc-agent", "bacluc-agent-org"}
READ_METHODS = {"GET", "HEAD", "OPTIONS"}
ALLOWED_HOSTS = {"github.com", "api.github.com", "uploads.github.com"}
FORK_PATH = re.compile(r"^/repos/[^/]+/[^/]+/forks/?$", flags=re.IGNORECASE)


def _deny(method, url):
    log = Path(os.environ.get("RUNNER_TEMP") or "/tmp") / "http-guard-denials.jsonl"
    with log.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps({"method": method, "url": url, "decision": "deny"}) + "\n")
    raise PermissionError(f"http guard denied {method} {url}")


def check_request(method, url):
    method = method.upper()
    if method in READ_METHODS:
        return
    parsed = urlparse(url)
    if (parsed.hostname or "").lower() not in ALLOWED_HOSTS:
        _deny(method, url)
    if method == "POST" and FORK_PATH.fullmatch(parsed.path):
        return
    parts = [part for part in parsed.path.split("/") if part]
    if (
        len(parts) < 3
        or parts[0].lower() != "repos"
        or parts[1].lower() not in OWNED_ORGS
        or parts[2] in {".", ".."}
    ):
        _deny(method, url)
