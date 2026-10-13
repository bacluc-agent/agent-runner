#!/usr/bin/env python3
import json
from http.server import BaseHTTPRequestHandler, HTTPServer
import re
from urllib.parse import urlsplit


def allowed(method, url):
    if method in {"GET", "HEAD", "OPTIONS"}:
        return True
    if method not in {"POST", "PUT", "PATCH", "DELETE"}:
        return False
    parsed = urlsplit(url)
    match = re.fullmatch(r"/repos/([^/]+)/([^/]+)(?:/.*)?", parsed.path)
    return (
        parsed.scheme == "https"
        and parsed.hostname == "api.github.com"
        and parsed.port in {None, 443}
        and parsed.username is None
        and parsed.password is None
        and bool(
            match
            and match.group(1).lower() in {"bacluc", "bacluc-agent"}
            and match.group(2) not in {".", ".."}
            and re.fullmatch(r"[A-Za-z0-9_.-]+", match.group(2))
        )
    )


class PolicyHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/check":
            self.send_error(404)
            return
        try:
            request = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            method, url = request["method"], request["url"]
            if not isinstance(method, str) or not isinstance(url, str):
                raise ValueError("method and url must be strings")
            status = 200 if allowed(method.upper(), url) else 403
        except (KeyError, TypeError, ValueError, json.JSONDecodeError):
            status = 400
        self.send_response(status)
        self.send_header("Content-Length", "0")
        self.end_headers()

    def log_message(self, *_):
        pass


if __name__ == "__main__":
    HTTPServer(("127.0.0.1", 18736), PolicyHandler).serve_forever()
