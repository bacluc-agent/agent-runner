# Agent Runner Repo

This repo allows to run agents in github actions. The issues to implement are in a todo repository.

## Referencing issues and PR

ALWAYS REFERENCE ISSUES, PR AND ACTION RUNS WITH THEIR ABSOLUTE PATH.
We work with multiple repos, so single issue numbers are ambiguous.

## Testing

ALL PULL REQUEST DESCRIPTIONS HAVE TO CONTAIN LINKS TO ACTION RUNS WITH THE PROBLEMS THEY FIX IF THEY FIX A BUG.
Features don't need that.

ALL PULL REQUESTS DESCRIPTIONS MUST LINK TO ACTION RUNS THAT SHOW THAT THE CHANGE WORKS.
ALL CHANGED CODE PATHS HAVE TO BE COVERED BY THE LINKED ACTION RUNS.

/completion-check-command

```bash
./scripts/completion-check
```

## ACI edit tools

When working in this repo, prefer the project tools in `.opencode/tool/`:

- `edit_file` for targeted search/replace edits instead of rewriting whole files.
- `navigate_repo` to list tracked files before opening individual files.
- `run_tests` to run the test command and close the edit loop.

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
