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

## Testing .github changes

When you change files under `.github/`, `.opencode/`, or `AGENTS.md`:

1. **Decide** which workflow(s) exercise the changed code path — do NOT blanket-trigger all workflows.
2. **Trigger** each via `gh workflow run <name> --ref <branch>`.
3. **Poll** `gh run list` for the run URL.
4. **Include** those URLs in your PR description.

Push-triggered runs (via `paths:` filters) provide automatic coverage; the
manual step above targets specific workflows the agent identifies as relevant.

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
