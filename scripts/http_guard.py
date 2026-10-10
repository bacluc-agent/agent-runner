import json
import os
from pathlib import Path
from urllib.parse import urlsplit


def check_request(method, url):
    method = method.upper()
    host = urlsplit(url).hostname
    if not host:
        raise ValueError("request URL must include a hostname")
    if host.lower() in {"github.com", "api.github.com"} or method in {"GET", "OPTIONS"}:
        return
    if method == "POST":
        directory = Path(os.environ["RUNNER_TEMP"])
        directory.mkdir(parents=True, exist_ok=True)
        with (directory / "http-guard-denials.jsonl").open("a") as log:
            log.write(json.dumps({"event": "denied_outsider_request", "method": method, "host": host}) + "\n")
    raise PermissionError(f"{method} to outsider host {host} is denied")
