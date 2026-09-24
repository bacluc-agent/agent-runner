#!/usr/bin/env python3
"""Verify archive issues #266/#267/#268 contain every #76 comment verbatim."""
import json
import subprocess
import sys

REPO = "bacluc-agent/agent-todo"
ISSUES = {1: 266, 2: 267, 3: 268}
EXPECTED_COUNTS = {1: 5, 2: 6, 3: 9}

with open("/tmp/opencode/issue76/comments.json") as f:
    comments = json.load(f)
assert len(comments) == 20

def gh_issue(number):
    out = subprocess.run(
        ["gh", "api", f"repos/{REPO}/issues/{number}", "--jq", "{state, body, title}"],
        capture_output=True, text=True, check=True,
    )
    return json.loads(out.stdout)

failures = []
for p, num in ISSUES.items():
    data = gh_issue(num)
    body = data["body"]
    if data["state"] != "closed":
        failures.append(f"#{num}: state={data['state']} (expected closed)")
    if len(body) >= 65536:
        failures.append(f"#{num}: body {len(body)} chars >= 65536")
    # count archived comment headers
    import re
    headers = re.findall(r"^\*\*Archived comment (\d+)/20\*\*", body, re.M)
    if len(headers) != EXPECTED_COUNTS[p]:
        failures.append(f"#{num}: {len(headers)} headers, expected {EXPECTED_COUNTS[p]}")
    # per-comment checks (only the comments belonging to this part)
    part_comments = comments[0:5] if p == 1 else comments[5:11] if p == 2 else comments[11:20]
    for i, c in enumerate(part_comments, start=1 if p == 1 else 6 if p == 2 else 12):
        expected_header = f"**Archived comment {i}/20**"
        expected_link = f"issuecomment-{c['id']}"
        if expected_header not in body:
            failures.append(f"#{num}: missing header for comment {i}")
        if expected_link not in body:
            failures.append(f"#{num}: missing link {expected_link}")
        if c["body"].rstrip("\n") not in body:
            failures.append(f"#{num}: comment {i} body NOT verbatim (len {len(c['body'])})")

if failures:
    print("FAIL:")
    for f_ in failures:
        print(" -", f_)
    sys.exit(1)
print("OK: all archive issues closed, bodies < 65536, all 20 comments verbatim (5/6/9)")