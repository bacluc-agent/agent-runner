import json
import os
from pathlib import Path
import tempfile
import unittest

try:
    from http_guard import check_request
except ImportError:
    from scripts.http_guard import check_request


class HttpGuardTest(unittest.TestCase):
    def test_outsider_reads_allowed_and_mutations_denied(self):
        with tempfile.TemporaryDirectory() as directory:
            previous = os.environ.get("RUNNER_TEMP")
            os.environ["RUNNER_TEMP"] = directory
            self.addCleanup(lambda: os.environ.pop("RUNNER_TEMP", None) if previous is None
                            else os.environ.__setitem__("RUNNER_TEMP", previous))
            for method in ("GET", "OPTIONS"):
                check_request(method, "https://outside.example/path")
            for method in ("POST", "PUT", "PATCH", "DELETE"):
                with self.assertRaises(PermissionError):
                    check_request(method, "https://outside.example/path")
            events = [json.loads(line) for line in
                      (Path(directory) / "http-guard-denials.jsonl").read_text().splitlines()]
            self.assertEqual(events, [{"event": "denied_outsider_request", "method": "POST",
                                       "host": "outside.example"}])


if __name__ == "__main__":
    unittest.main()
