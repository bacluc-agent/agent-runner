# Agent Runner Repo

This repo allows to run agents in github actions. The issues to implement are in a todo repository.

## Referencing issues and PR

ALWAYS REFERENCE ISSUES, PR AND ACTION RUNS WITH THEIR ABSOLUTE PATH.
We work with multiple repos, so single issue numbers are ambiguous.

## Testing

ALL PULL REQUEST DESCRIPTIONS MUST LINK TO ACTION RUNS THAT SHOW THE CHANGE WORKS — include bug-repro runs when fixing a bug, and ensure all changed code paths are covered. When you change files under `.github/`, `.opencode/`, or `AGENTS.md`, trigger only the workflow(s) that exercise the changed code path — never all of them — via `gh workflow run <name> --ref <branch>`, poll `gh run list` for the run URL, and link it in the PR description; push-triggered runs (via `paths:` filters) provide automatic coverage for the workflows whose files you touched.

/completion-check-command

```bash
./scripts/completion-check
```

## Renovate

Renovate must be able to update all dependencies.
For that we use a regex pattern where we have the renovate instructions in a comment above, and all versions
are assigned to an env variable, and have a renovate comment on top.

```json
{
  "customType": "regex",
  "fileMatch": [".*"],
  "matchStrings": [
    "# renovate: datasource=(?<datasource>[^\\s]+) depName=(?<depName>[^\\s]+)\\n[A-Z_]+=(?<currentValue>[0-9][\\w.-]*)"
  ]
}
```

```bash
# renovate: datasource=docker depName=ghcr.io/bacluc/prettier-image/prettier-image
PRETTIER_VERSION=3.9.4

# renovate: datasource=docker depName=rhysd/actionlint
ACTIONLINT_VERSION=1.7.12
```
