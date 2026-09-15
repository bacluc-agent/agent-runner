# Issue #201 Workflow Trigger Test Results

Branch: issue-201
Repo: bacluc-agent/agent-runner

## Changed .github/ paths (vs origin/main)
- .github/scripts/trigger-workflows.sh
- .github/workflows/opencode.yml

## Mapping verification (from .github/scripts/trigger-workflows.sh)
- .github/workflows/opencode.yml → opencode.yml
- .github/scripts/trigger-workflows.sh → opencode.yml (default *)
Both correctly map to opencode workflow.

## Triggered workflows (using file-name syntax per fix 36b24d7)
1. opencode.yml (with prompt input)
   URL: https://github.com/bacluc-agent/agent-runner/actions/runs/34998898340
   Status: queued / triggered via workflow_dispatch
2. refine-issues.yml (no input)
   URL: https://github.com/bacluc-agent/agent-runner/actions/runs/34998913927
   Status: queued / triggered via workflow_dispatch

## PR description coverage
opencode.yml lines 545-547 embed `trigger-workflows.outputs.workflow_urls`.
Script writes `opencode: <url>` format (workflow_file stripped of .yml).
This covers both changed paths since both map to opencode.

## Fix verification
Commit 36b24d7 changed `gh workflow run` to use file names (`opencode.yml` instead of `opencode`).
Trigger succeeded with file name; previous name-based approach would fail for workflows where file name != workflow name (e.g., refine-issues.yml file vs "Refine Issues" name).

## Failures / issues
None. Both triggers returned valid run URLs.
