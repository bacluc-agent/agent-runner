/completion-check-command

```bash
./scripts/completion-check
```

Note: The harness (GitHub Actions workflow `.github/workflows/opencode.yml`)
reads this declaration and runs the command after the coordinator exits,
failing the job if the check fails. The `bacluc-opencode-completion-check-command`
plugin is no longer required; the harness enforces the check directly.

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
