# Refinement: issue-201 Native Triggers

**Branch:** `issue-201-native-triggers`
**Parent issue:** bacluc-agent/agent-todo#201
**Previous attempt:** PR bacluc-agent/agent-runner#36 (closed — overengineered custom script)

## Summary

Replace the custom `.github/scripts/trigger-workflows.sh` approach with:

1. Native `on: push: paths:` triggers on each workflow
2. Agent-decided workflow selection via `gh workflow run` (in AGENTS.md + issue-refiner.md)
3. Cascade guard: opencode.yml's push-triggered run only validates, never runs the agent

---

## 1. Exact final content for each workflow file

### 1.1 ci.yml

**Full file** (23 lines → 23 lines, only `on:` block changes):

```yaml
name: CI

on:
  push:
    paths:
      - ".github/workflows/ci.yml"
      - ".github/actions/**"
      - "scripts/**"
      - "AGENTS.md"
  pull_request:

permissions:
  contents: read

jobs:
  completion-check:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - name: Check out repository
        uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1

      - name: Install uv
        run: pip install --quiet uv

      - name: Run completion check
        run: ./scripts/completion-check
```

**Change:** `branches: [main]` removed, `paths:` added. `pull_request:` unchanged (no filter = all PRs).

### 1.2 opencode.yml

**`on:` block** (lines 3–62 become):

```yaml
on:
  push:
    paths:
      - ".github/workflows/opencode.yml"
      - ".github/actions/**"
      - ".opencode/**"
      - "AGENTS.md"
      - "README.md"
  workflow_dispatch:
    inputs:
      prompt:
        description: Task for OpenCode
        required: true
        type: string
      model:
        description: "Exact model override (provider/model, for example opencode-go-openai/glm-5.2). Wins over the dropdown; leave empty for automatic discovery."
        required: false
        type: string
      model_choice:
        description: Preferred model from the dropdown. Ignored when 'model' is filled in.
        required: false
        type: choice
        default: auto
        options:
          - auto
          - opencode/big-pickle
          - opencode/mimo-v2.5-free
          - opencode/nemotron-3-ultra-free
          - opencode/nemotron-3.5-lightning-free
          - opencode/muse-spark-1.3-contributor-free
          - opencode/ling-3.0-flash-fin-free
          - opencode-go-openai/qwen3.8-max
          - opencode-go-openai/qwen3.8-flash
          - opencode-go-openai/glm-5.3
          - opencode-go-openai/kimi-k3
          - opencode-go-openai/hy4-preview
          - opencode-go-openai/gpt-5.6-luna
          - opencode-go-openai/minimax-m2.5
          - opencode-go-openai-2/qwen3.8-max
          - opencode-go-openai-2/qwen3.8-flash
          - opencode-go-openai-2/glm-5.3
          - opencode-go-openai-2/kimi-k3
          - opencode-go-openai-2/hy4-preview
          - opencode-go-openai-2/gpt-5.6-luna
          - opencode-go-openai-2/minimax-m2.5
          - openai/gpt-5.6-luna
          - openai/gpt-4o-mini
      timeout_minutes:
        description: Job timeout in minutes
        required: false
        type: number
        default: 120
  workflow_call:
    inputs:
      prompt:
        description: Task for OpenCode
        required: true
        type: string
      model:
        description: "Exact model override (provider/model, for example opencode-go-openai/glm-5.2). Wins over the dropdown; leave empty for automatic discovery."
        required: false
        type: string
      timeout_minutes:
        description: Job timeout in minutes
        required: false
        type: number
        default: 120
```

**New `validate` job** (insert before the existing `run` job at line 73):

```yaml
jobs:
  validate:
    if: github.event_name == 'push'
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - name: Check out repository
        uses: actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1 # v7.0.1

      - name: Run completion check
        run: ./scripts/completion-check

  run:
    if: github.event_name != 'push'
    runs-on: ubuntu-latest
    timeout-minutes: 130
    env:
      # ... (unchanged from line 78 onward)
```

**Key changes to `run` job:**

- Add `if: github.event_name != 'push'` at line 74 (job level, before `runs-on`)
- Everything else in `run` job stays identical

### 1.3 hourly-issue.yml

**Full `on:` block** (lines 3–11 become):

```yaml
on:
  schedule:
    - cron: "24 * * * *"
  workflow_dispatch:
    inputs:
      selection_prompt:
        description: Optional override for the selection instruction tail (the candidate list is always prepended)
        required: false
        type: string
  push:
    paths:
      - ".github/workflows/hourly-issue.yml"
      - ".github/actions/**"
      - ".opencode/**"
```

**Jobs:** unchanged.

### 1.4 refine-issues.yml

**Full `on:` block** (lines 3–6 become):

```yaml
on:
  schedule:
    - cron: "7 * * * *"
  workflow_dispatch:
  push:
    paths:
      - ".github/workflows/refine-issues.yml"
      - ".github/actions/**"
      - ".opencode/**"
```

**Jobs:** unchanged.

### 1.5 review-fixes.yml

**Full `on:` block** (lines 3–17 become):

```yaml
on:
  schedule:
    - cron: "32 */4 * * *" # Every 4 hours at :32
  workflow_dispatch:
    inputs:
      prompt:
        description: >-
          Optional override prompt for all PRs (leave empty for
          auto-generation).
        required: false
        type: string
      model:
        description: Optional OpenCode model override (e.g. opencode-go-openai/glm-5.2)
        required: false
        type: string
  push:
    paths:
      - ".github/workflows/review-fixes.yml"
      - ".github/actions/**"
      - ".opencode/**"
```

**Jobs:** unchanged.

---

## 2. Exact text to add to AGENTS.md

Insert after the existing `## Testing` section (after line 16), before `## Renovate`:

```markdown
## Testing .github changes

When you change files under `.github/`, `.opencode/`, or `AGENTS.md`:

1. **Decide** which workflow(s) exercise the changed code path — do NOT blanket-trigger all workflows.
2. **Trigger** each via `gh workflow run <name> --ref <branch>`.
3. **Poll** `gh run list` for the run URL.
4. **Include** those URLs in your PR description.

Push-triggered runs (via `paths:` filters) provide automatic coverage; the
manual step above targets specific workflows the agent identifies as relevant.
```

---

## 3. Exact text to add to .opencode/agent/issue-refiner.md

Insert as a new bullet point after the existing "Do NOT include any step to run `./scripts/completion-check`" bullet (after line 18):

```markdown
- If the implementation changes files under `.github/`, `.opencode/`, or
  `AGENTS.md`, include a step in `## How to implement` that instructs
  the agent to trigger the relevant workflow(s) via
  `gh workflow run <name> --ref <branch>`, poll `gh run list` for the
  run URL, and include those URLs in the PR description. Do NOT instruct
  the agent to trigger all workflows — only the ones relevant to the
  changed files.
```

This instruction is validator-safe:

- No `BEGIN_PROMPT` / `END_PROMPT` / `SELECTED_ISSUE:` markers
- No "ignore previous instructions" phrasing
- No API key patterns
- No new `## ` headings (it's a bullet in the agent instructions, not a heading in the refined body)
- The step it tells the refiner to add is a numbered item within `## How to implement`, not a new section

---

## 4. Answers to questions A–F

### A. ci.yml: removing `branches: [main]`

**Is it correct and safe?** Yes.

- The current `push: branches: [main]` means CI only runs on pushes to main. Agents work on feature branches, so CI never runs on their pushes.
- Removing `branches: [main]` and adding `paths:` means CI runs on pushes to ANY branch that change the specified files. This is the desired behavior.
- The `pull_request:` trigger (no filter) already triggers on all PRs regardless of base branch, so PR-level CI coverage is unchanged.
- **Implication:** pushes to feature branches that change `scripts/**`, `.github/actions/**`, etc. will now trigger CI. This is correct — those changes should be validated.
- **Exact YAML:** See section 1.1 above.

### B. opencode.yml: validate job and run job gate

**Where does the `validate` job go?** Before the `run` job (first job in the `jobs:` block). It has no dependency on other jobs.

**What permissions/steps does it need?**

- Permissions: inherits the workflow-level permissions (broad: `actions: write`, `contents: write`, etc.). The `validate` job only uses `contents: read` implicitly via `actions/checkout`. Having broader permissions is acceptable — the job doesn't use them.
- Steps: checkout + `./scripts/completion-check`. The script handles Docker (prettier, actionlint), node (plugin tests), and pytest (with uv/pip fallback). Ubuntu-latest has node and python3 pre-installed.

**What is the minimal `if:` gate for the `run` job?**

- `if: github.event_name != 'push'` at the job level (line 74, before `runs-on`).
- This prevents the `run` job from executing on push events entirely.

**Does the `run` job reference `inputs.*` that would be empty on push?**

- Yes: `inputs.prompt` (lines 96, 124, 306, 333), `inputs.model` (lines 97, 125), `inputs.model_choice` (line 98), `inputs.timeout_minutes` (lines 99, 335).
- On push, all `inputs.*` resolve to empty strings.
- The gate `if: github.event_name != 'push'` prevents the job from running on push, so empty inputs are never evaluated. **Safe.**

**Does the workflow-level `permissions` block apply to the validate job?**

- Yes, workflow-level permissions apply to all jobs. The `validate` job inherits the broad permissions but only needs `contents: read`. This is acceptable — the job doesn't escalate privileges.

### C. Dispatch workflows: inputs.* safety on push

**hourly-issue.yml:**

- `inputs.selection_prompt` used at line 63: `SELECTION_PROMPT: ${{ inputs.selection_prompt }}`
- On push, `SELECTION_PROMPT` is empty.
- Step handles it: `tail_instruction="${SELECTION_PROMPT:-$default_tail}"` (line 147). Falls back to `scripts/issue-selection-tail.txt`. **Safe.**
- The `run` job uses `${{ needs.select.outputs.prompt }}` (not inputs). **Safe.**

**refine-issues.yml:**

- `workflow_dispatch:` has NO inputs defined (line 6).
- The `refine` job does not reference `inputs.*` anywhere. **Safe.**

**review-fixes.yml:**

- `inputs.prompt` used at line 51: `OVERRIDE_PROMPT: ${{ inputs.prompt }}`
  - On push, `OVERRIDE_PROMPT` is empty.
  - Step handles it: `if [[ -n "${OVERRIDE_PROMPT:-}" ]]; then ... else ... fi` (line 103). Falls back to auto-generated prompt. **Safe.**
- `inputs.model` used at line 145: `model: ${{ inputs.model }}`
  - On push, `inputs.model` is empty.
  - Passed to opencode.yml as optional `model` input. opencode.yml's `select-model` step handles empty model via auto-discovery. **Safe.**

### D. Cascade analysis

**Push changes `.github/actions/**` triggers ALL 5 workflows.** Yes, this is the intended behavior per the task (`.github/actions/**` is in all five path lists).

**Residual cascade risk:**

1. **Push → hourly-issue.yml → select → dispatch opencode.yml (workflow_call) → agent job runs → agent pushes → push → all 5 workflows again.**
   - The cascade guard (opencode.yml push trigger only runs `validate`) prevents the most direct cascade: push → opencode.yml → agent → push.
   - But hourly-issue.yml on push CAN dispatch an agent via workflow_call (since workflow_call is not push, the `run` job gate passes).
   - If that agent changes `.github/` files and pushes, the cycle repeats.
   - **Likelihood:** Low. The agent dispatched by hourly-issue works on a specific issue, not on `.github/` changes. The cycle would stop when the agent stops changing `.github/` files.

2. **Push → review-fixes.yml → find-prs → process-prs → dispatch opencode.yml (workflow_call) → agent job runs → agent pushes → push → all 5 workflows again.**
   - Same analysis as above. Low likelihood.

3. **Push → refine-issues.yml → refine job → modifies issue bodies only → no code changes → no cascade.**
   - **No risk.** Refinement only modifies issue bodies, not code files.

**Does the task's cascade-guard scope (opencode.yml only) cover it?**

- The task's cascade guard prevents the most dangerous cascade: push → opencode.yml → agent → push → opencode.yml → agent → ...
- The residual risk from hourly-issue/review-fixes is acknowledged and accepted. The agents dispatched by these workflows work on specific issues/PRs, not on `.github/` changes. The probability of an infinite loop is negligible.

### E. Verification strategy

**Automatic coverage (push triggers):**

- Pushing the implementation branch triggers all 5 workflows (paths match `.github/actions/**` etc.).
- ci.yml: runs completion-check (cheap).
- opencode.yml: runs validate job only (cheap).
- hourly-issue.yml: runs full select + dispatch (expensive).
- refine-issues.yml: runs full refinement (expensive).
- review-fixes.yml: runs find-prs + dispatch (expensive if PRs exist).

**Manual coverage (agent-decided triggers):**

- The agent should trigger specific workflows via `gh workflow run` to verify the changed code paths.
- For the initial implementation push, the automatic push triggers already cover all 5 workflows.
- The agent should include the push-triggered run URLs in the PR description.

**Cheapest verification covering every changed path:**

- ci.yml: push-triggered run covers `scripts/**`, `.github/actions/**`, `AGENTS.md`, `.github/workflows/ci.yml`. **Cheap.**
- opencode.yml: push-triggered validate run covers `.github/workflows/opencode.yml`, `.github/actions/**`, `.opencode/**`, `AGENTS.md`, `README.md`. **Cheap.**
- hourly-issue.yml: push-triggered run covers `.github/workflows/hourly-issue.yml`, `.github/actions/**`, `.opencode/**`. **Expensive** (dispatches real agent).
- refine-issues.yml: push-triggered run covers `.github/workflows/refine-issues.yml`, `.github/actions/**`, `.opencode/**`. **Expensive** (refines real issues).
- review-fixes.yml: push-triggered run covers `.github/workflows/review-fixes.yml`, `.github/actions/**`, `.opencode/**`. **Expensive** (dispatches real agents if PRs exist).

**Recommendation:** The push triggers provide automatic coverage. The agent should link the push-triggered run URLs in the PR description. For the expensive workflows (hourly-issue, refine-issues, review-fixes), the push-triggered runs are sufficient — no need for additional manual `gh workflow run` triggers unless the agent wants to test a specific scenario.

However, per AGENTS.md: "ALL CHANGED CODE PATHS HAVE TO BE BE COVERED BY THE LINKED ACTION RUNS." The push-triggered runs cover all changed paths. The agent should link them.

### F. Prettier/actionlint compatibility

**Prettier:**

- 2-space indent (consistent with existing files).
- YAML style matches existing workflow files.
- No trailing whitespace, no mixed indent.
- The `paths:` lists use the same format as existing `branches:` lists (YAML sequence).
- **Compatible.**

**Actionlint:**

- `if:` expressions: `github.event_name == 'push'` and `github.event_name != 'push'` are valid GitHub Actions expressions.
- `paths:` filters: valid syntax, actionlint supports them.
- `push:` with `paths:` alongside other triggers: valid, actionlint handles multi-trigger `on:` blocks.
- No reference to `inputs.*` in push-triggered jobs (the `run` job is gated).
- **Compatible.**

**Existing actionlint warnings:** The repo has pre-existing SC2015 info warnings in some shell scripts. These are unrelated to the proposed changes.

---

## 5. Risks and edge cases for the planner/builder

1. **Push to `.github/actions/**` triggers all 5 workflows, including expensive ones (hourly-issue, refine-issues, review-fixes).** This is the intended design per the task. The planner should note this in the PR description.

2. **hourly-issue.yml on push may dispatch a real agent.** If the `select` job picks an issue, it dispatches opencode.yml via workflow_call. The agent works on the issue. This is the normal behavior of hourly-issue.yml. The planner should note that push-triggered hourly-issue runs are not just validation — they run the full workflow.

3. **review-fixes.yml on push may dispatch real agents.** If `find-prs` finds PRs with review comments, `process-prs` dispatches opencode.yml for each PR. Same caveat as hourly-issue.

4. **refine-issues.yml on push runs full refinement.** The `refine` job processes up to 2 unrefined issues. This modifies issue bodies in the todo repo. The planner should note this side effect.

5. **Cascade risk from hourly-issue/review-fixes dispatching agents that change `.github/` files.** Low probability but theoretically possible. The cascade guard on opencode.yml only prevents the direct push → opencode.yml → agent cascade. The residual risk from other workflows is accepted.

6. **`validate` job in opencode.yml needs Docker for prettier and actionlint.** The `completion-check` script runs Docker commands. The ubuntu-latest runner has Docker pre-installed. No issue.

7. **`validate` job needs node for plugin tests.** Ubuntu-latest has node pre-installed. The `completion-check` script runs `node --test .opencode/plugin/*.test.mjs`. No issue.

8. **`validate` job needs python3/pytest.** Ubuntu-latest has python3. The `completion-check` script falls back to `python3 -m pip install --quiet pytest && python3 -m pytest -q` if uv is not available. This works but is slower. The planner could add `pip install --quiet uv` before completion-check for speed, but it's not required.

9. **Issue-refiner.md instruction must not trip the validator.** The proposed phrasing is validator-safe (no hostile markers, no extra headings). The planner should verify this by running `python3 scripts/validate_refined_issue.py` on a sample refined body that includes the conditional step.

10. **AGENTS.md section must be concise.** The existing Testing section is brief. The new section should match the style. The proposed text is 8 lines.

11. **The `pull_request` trigger on ci.yml has no branch filter.** This means PRs to any branch trigger CI. This is the existing behavior and is unchanged. The planner should not add a branch filter to `pull_request`.

12. **The `push` trigger on ci.yml without `branches:` filter means pushes to any branch trigger CI (when paths match).** This is the desired behavior for agent feature branches. The planner should not add a `branches:` filter to `push`.

13. **Prettier formatting.** The YAML changes must be prettier-formatted. The `completion-check` script runs `prettier --check .` via Docker. The builder should run prettier locally before pushing.

14. **Actionlint validation.** The YAML changes must pass actionlint. The `completion-check` script runs actionlint. The builder should run actionlint locally before pushing.

15. **No CLAUDE.md exists in this repo.** Verified. Only AGENTS.md is present.
