import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


SCRIPT = Path(__file__).with_name("network_policy_proxy.py")


def check(method, url, expected):
    request = urllib.request.Request(
        "http://127.0.0.1:18736/check",
        data=json.dumps({"method": method, "url": url}).encode(),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request) as response:
            result = response.status == 200
    except urllib.error.HTTPError as error:
        result = error.code == 200
    assert result is expected, (method, url, result)


def test_policy_proxy():
    process = subprocess.Popen([sys.executable, str(SCRIPT)], stdout=subprocess.DEVNULL)
    try:
        for _ in range(100):
            try:
                check("GET", "https://github.com/", True)
                break
            except (OSError, urllib.error.URLError):
                time.sleep(0.02)
        else:
            raise AssertionError("policy proxy did not start")
        for method in ("GET", "OPTIONS"):
            check(method, "https://outsider.example/issues", True)
        for method in ("POST", "PUT", "PATCH", "DELETE"):
            check(method, "https://outsider.example/issues", False)
            check(method, "https://api.github.com/repos/outsider/project/issues", False)
        for method in ("POST", "PATCH", "DELETE"):
            check(method, "https://api.github.com/repos/bacluc-agent/agent-runner/issues", True)
        check("GET", "https://api.github.com/repos/outsider/project/issues", True)
        for url in (
            "https://api.github.com:444/repos/bacluc/project/issues",
            "https://user@api.github.com/repos/bacluc/project/issues",
            "https://api.github.com/repos/bacluc/%2e%2e/issues",
        ):
            check("POST", url, False)
        check("CONNECT", "https://api.github.com/", False)
    finally:
        process.terminate()
        process.wait(timeout=5)
    print("Policy-proxy PoC: outsider mutations denied; owned GitHub mutations permitted")


if __name__ == "__main__":
    test_policy_proxy()
