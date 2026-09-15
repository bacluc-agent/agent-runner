# Verification notes for issue #201 (.github workflow trigger fix)

- Read `.github/scripts/trigger-workflows.sh`: broken API fallback removed; mapping logic intact.
- Read `.github/workflows/ci.yml`: `workflow_dispatch:` added.
- Triggered `ci.yml` on branch `issue-201`: https://github.com/bacluc-agent/agent-runner/actions/runs/34999497782
- Triggered `opencode.yml` with prompt "Test .github workflow trigger for issue #201": https://github.com/bacluc-agent/agent-runner/actions/runs/34999500141
- Verified both runs in `gh run list`.
- Posted comment to issue #201 in bacluc-agent/agent-todo: https://github.com/bacluc-agent/agent-todo/issues/201#issuecomment-5684627038
- Updated PR #36 description with new URLs.
- Run link: $GITHUB_SERVER_URL/$GITHUB_REPOSITORY/actions/runs/$GITHUB_RUN_ID
