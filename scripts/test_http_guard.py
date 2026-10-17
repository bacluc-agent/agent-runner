import json
import os
from pathlib import Path
import tempfile
import unittest

from http_guard import check_request


class HttpGuardTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.previous = os.environ.get("RUNNER_TEMP")
        os.environ["RUNNER_TEMP"] = self.temp.name
        self.addCleanup(self.restore)
        self.log = Path(self.temp.name) / "http-guard-denials.jsonl"

    def restore(self):
        if self.previous is None:
            os.environ.pop("RUNNER_TEMP", None)
        else:
            os.environ["RUNNER_TEMP"] = self.previous

    def test_allowed(self):
        for method in ("GET", "HEAD", "OPTIONS"):
            check_request(method, "https://outsider.example/x")
            check_request(method, "https://api.github.com/repos/ecamp/ecamp3/issues")
        for url in (
            "https://api.github.com/repos/bacluc-agent-org/r/issues",
            "https://api.github.com/repos/bacluc/r/pulls",
            "https://api.github.com/repos/octocat/Hello-World/forks",
            "https://uploads.github.com/repos/bacluc-agent/agent-runner/releases/1/assets",
        ):
            check_request("POST", url)
        self.assertFalse(self.log.exists())

    def test_denied(self):
        denied = [
            ("POST", "https://outsider.example/x"),
            ("PUT", "https://outsider.example/x"),
            ("PATCH", "https://outsider.example/x"),
            ("DELETE", "https://outsider.example/x"),
            ("POST", "https://api.github.com/repos/ecamp/ecamp3/issues"),
            ("POST", "https://api.github.com/repos/{owner}/{repo}/issues"),
            ("POST", "https://uploads.github.com/repos/octocat/Hello-World/releases/1/assets"),
        ]
        for method, url in denied:
            with self.assertRaises(PermissionError):
                check_request(method, url)
        lines = self.log.read_text().splitlines()
        self.assertEqual(len(lines), len(denied))
        for line, (method, url) in zip(lines, denied):
            self.assertEqual(json.loads(line), {"method": method, "url": url, "decision": "deny"})


if __name__ == "__main__":
    unittest.main()
