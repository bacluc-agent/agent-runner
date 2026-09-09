# agent-runner

Agent-run todo repository: scheduled issue runner and OpenCode workflows.

## Two-repository setup

The agent system is split across two public repositories:

- [`bacluc-agent/agent-todo`](https://github.com/bacluc-agent/agent-todo) — holds the issues.
- [`bacluc-agent/agent-runner`](https://github.com/bacluc-agent/agent-runner) — runs the GitHub Actions workflows.

The runner repository reads issues from the todo repository through the
`ISSUE_REPOSITORY` repository variable (set to `bacluc-agent/agent-todo` there).

## Provenance

The workflows in this repository were moved from
[`bacluc-agent/agent-todo`](https://github.com/bacluc-agent/agent-todo) in
[PR #170](https://github.com/bacluc-agent/agent-todo/pull/170), implementing
[issue #42](https://github.com/bacluc-agent/agent-todo/issues/42) ("Move the
github action run to a second repository").

## Repository variables

Set these in Settings → Secrets and variables → Actions → Variables:

| Variable                         | Description                                                    | Default             |
| -------------------------------- | -------------------------------------------------------------- | ------------------- |
| `ISSUE_REPOSITORY`               | Repository for issue tracking and cache (format: `owner/repo`) | `github.repository` |
| `MODEL_AVAILABILITY_CACHE_ISSUE` | Issue number used as the model-availability cache              | auto-detected       |

## Secrets

| Secret                      | Description                                         |
| --------------------------- | --------------------------------------------------- |
| `BACLUC_AGENT_GITHUB_TOKEN` | PAT for issue/PR operations and workflow dispatches |
| `OPENCODE_GO_API_KEY`       | API key for the first OpenCode Go provider          |
| `OPENCODE_GO_2_API_KEY`     | API key for the second OpenCode Go provider         |

## Completion check

Run `./scripts/completion-check` before pushing. It runs all quality checks (Prettier formatting check and actionlint) in Docker and exits non-zero if any check fails. `.github/workflows/ci.yml` runs the same script on every push and pull request.
