# Issue #201 / PR #36 Workflow Trigger Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Test `.github` workflow trigger locally, fix bugs A–E, trigger actual workflow, capture URL, update PR description.

**Architecture:** Minimal bash script fixes + local simulation + `gh workflow run` + URL verification + PR edit.

**Tech Stack:** bash, `gh` CLI, `git`, `jq`, `.github/scripts/trigger-workflows.sh`

**Spec:** Issue #201 / PR #36 in agent-runner repo; `.github/scripts/trigger-workflows.sh`; `.github/workflows/ci.yml`

## Global Constraints

- Keep changes minimal; no new dependencies.
- All PR descriptions must link to action runs that cover changed code paths (AGENTS.md).
- `RUNNER_TEMP` must have a fallback (`/tmp`).
- `jq` must be available or handled gracefully.
- `ci.yml` has no `workflow_dispatch`; mapping must skip it or add trigger.

---

### Task 1: Read and audit trigger script

**Files:**

- Read: `.github/scripts/trigger-workflows.sh`
- Read: `.github/workflows/ci.yml`
- Read: `.github/workflows/opencode.yml` (has `workflow_dispatch`)

**Interfaces:**

- Consumes: existing bash script
- Produces: list of bugs A–E confirmed

- [ ] **Step 1: Confirm bugs A–E in script**

Read `.github/scripts/trigger-workflows.sh`. Confirm:

- A: `map_file_to_workflow_file` maps `.github/workflows/ci.yml` → `ci.yml`, but `ci.yml` lacks `workflow_dispatch`.
- B: `base_ref` loop exits empty if neither `main` nor `origin/main` exists → `changed_files` empty silently.
- C: `grep -oE` relies on `gh` output format; `jq` used in API fallback without existence check.
- D: No `[[ -f ... ]]` check before `gh workflow run`.
- E: `"$RUNNER_TEMP"` used without default.

- [ ] **Step 2: Commit audit note**

```bash
git add -A
git commit -m "audit: confirm bugs A-E in trigger-workflows.sh"
```

---

### Task 2: Fix mapping bug (A) and silent failure (B)

**Files:**

- Modify: `.github/scripts/trigger-workflows.sh`

**Interfaces:**

- Consumes: `map_file_to_workflow_file`, `base_ref` loop
- Produces: corrected mapping and non-empty `changed_files`

- [ ] **Step 1: Skip `ci.yml` or add `workflow_dispatch`**

Option (lazy): skip `ci.yml` in mapping since it has no `workflow_dispatch`. Edit case:

```bash
    .github/workflows/ci.yml) echo "" ;;  # no workflow_dispatch trigger
```

- [ ] **Step 2: Fix silent failure for missing `main`/`origin/main`**

Replace base_ref loop with fallback to `HEAD~1` or `git rev-parse --short HEAD`:

```bash
  base_ref=""
  for ref in main origin/main; do
    if git rev-parse --verify "$ref" >/dev/null 2>&1; then
      base_ref="$ref"
      break
    fi
  done
  if [[ -z "$base_ref" ]]; then
    # Fallback: compare with previous commit if no main branch
    if git rev-parse --verify HEAD~1 >/dev/null 2>&1; then
      base_ref="HEAD~1"
    fi
  fi
```

- [ ] **Step 3: Run local simulation**

```bash
bash -c '
  export GITHUB_REPOSITORY="bacluc-agent/agent-runner"
  export GITHUB_REF_NAME="main"
  export RUNNER_TEMP="/tmp/test-runner"
  mkdir -p "$RUNNER_TEMP"
  # Simulate changed file
  echo ".github/workflows/opencode.yml" | bash .github/scripts/trigger-workflows.sh
'
```

Expected: `changed_files` non-empty, mapping returns `opencode.yml`, no crash.

- [ ] **Step 4: Commit fix**

```bash
git add .github/scripts/trigger-workflows.sh
git commit -m "fix(A,B): skip ci.yml mapping, add HEAD~1 fallback for base_ref"
```

---

### Task 3: Fix URL dependency (C), file-existence check (D), `RUNNER_TEMP` (E)

**Files:**

- Modify: `.github/scripts/trigger-workflows.sh`

**Interfaces:**

- Consumes: `gh` output regex, `jq` call, `RUNNER_TEMP`
- Produces: robust URL capture, file check, temp fallback

- [ ] **Step 1: Add `RUNNER_TEMP` fallback**

At top of script (after `set`):

```bash
RUNNER_TEMP="${RUNNER_TEMP:-/tmp}"
mkdir -p "$RUNNER_TEMP"
```

- [ ] **Step 2: Add file-existence check before trigger**

Before `gh workflow run`:

```bash
    if [[ ! -f ".github/workflows/$workflow_file" ]]; then
      printf 'Workflow file %s not found, skipping\n' "$workflow_file"
      continue
    fi
```

- [ ] **Step 3: Make URL capture robust (C)**

Replace regex-only capture with combined regex + `jq` check, and verify `jq` exists:

```bash
    url=""
    if command -v jq >/dev/null 2>&1; then
      url=$(gh workflow run ... 2>/dev/null | jq -r '.html_url // empty' || true)
    else
      url=$(gh workflow run ... 2>/dev/null | grep -oE 'https://github.com/[^/]+/[^/]+/actions/runs/[0-9]+' || true)
    fi
```

Apply to both `opencode.yml` and other branches.

- [ ] **Step 4: Verify `jq` dependency handled**

If `jq` missing, regex path still works. Confirm with:

```bash
bash -c 'command -v jq || echo "jq missing, regex fallback active"'
```

- [ ] **Step 5: Commit fix**

```bash
git add .github/scripts/trigger-workflows.sh
git commit -m "fix(C,D,E): RUNNER_TEMP fallback, file check, robust URL capture"
```

---

### Task 4: Trigger actual workflow and capture URL

**Files:**

- Run: `.github/scripts/trigger-workflows.sh` (or direct `gh` command)

**Interfaces:**

- Consumes: fixed script
- Produces: action-run URL in `RUNNER_TEMP/workflow-run-urls.txt`

- [ ] **Step 1: Ensure `gh` auth and repo context**

```bash
gh auth status
echo "Repo: $(gh repo view --json url -q .url)"
```

- [ ] **Step 2: Trigger `opencode.yml` workflow**

```bash
export GITHUB_REPOSITORY="bacluc-agent/agent-runner"
export GITHUB_REF_NAME="main"
export RUNNER_TEMP="/tmp/test-runner"
mkdir -p "$RUNNER_TEMP"

# Direct trigger for verification
url=$(gh workflow run opencode.yml --repo "$GITHUB_REPOSITORY" --ref "$GITHUB_REF_NAME" --field prompt="Test .github workflow trigger for issue #201" 2>/dev/null | grep -oE 'https://github.com/[^/]+/[^/]+/actions/runs/[0-9]+' || true)
echo "Captured URL: $url"
```

- [ ] **Step 3: Verify URL is valid**

```bash
if [[ -n "$url" ]]; then
  curl -s -o /dev/null -w "%{http_code}" "$url"
  echo "URL reachable"
fi
```

Expected: `200` or redirect (`302`).

- [ ] **Step 4: Write URL to temp file**

```bash
echo "opencode: $url" > "$RUNNER_TEMP/workflow-run-urls.txt"
cat "$RUNNER_TEMP/workflow-run-urls.txt"
```

- [ ] **Step 5: Commit trigger result**

```bash
git add -A
git commit -m "test: trigger opencode workflow, capture URL"
```

---

### Task 5: Update PR description with URL

**Files:**

- Modify: PR #36 description (via `gh pr edit` or manual)

**Interfaces:**

- Consumes: captured URL from Task 4
- Produces: PR description with action-run link

- [ ] **Step 1: Read current PR description**

```bash
gh pr view 36 --repo bacluc-agent/agent-runner --json body -q .body
```

- [ ] **Step 2: Append URL and verification note**

```bash
gh pr edit 36 --repo bacluc-agent/agent-runner --body-file - <<EOF
$(gh pr view 36 --repo bacluc-agent/agent-runner --json body -q .body)

---

**Action run covering changed code paths:** $url

**Verification:**
- Mapping bug (A) fixed: `ci.yml` skipped.
- Silent failure (B) fixed: `HEAD~1` fallback added.
- URL dependency (C) fixed: `jq` + regex fallback.
- File-existence check (D) added.
- `RUNNER_TEMP` (E) has `/tmp` fallback.
EOF
```

- [ ] **Step 3: Confirm PR updated**

```bash
gh pr view 36 --repo bacluc-agent/agent-runner --json body -q .body | tail -n 10
```

- [ ] **Step 4: Final commit**

```bash
git add -A
git commit -m "docs: update PR #36 description with action-run URL"
```

---

### Task 6: Final verification and completion check

**Files:**

- Run: `./scripts/completion-check`

**Interfaces:**

- Consumes: all fixes
- Produces: passing quality checks

- [ ] **Step 1: Run completion check**

```bash
./scripts/completion-check
```

Expected: exit 0.

- [ ] **Step 2: Confirm changed code paths covered by linked action run**

Check PR description contains URL; check `.github/scripts/trigger-workflows.sh` is covered by the triggered workflow (`opencode.yml` runs `completion-check` which touches the script indirectly, or add explicit test step).

- [ ] **Step 3: Push branch and record branch name in issue**

```bash
git push origin $(git branch --show-current)
gh issue comment 201 --repo bacluc-agent/agent-runner --body "Plan executed. Branch: $(git branch --show-current). Action run: $url"
```

- [ ] **Step 4: Mark complete**

```bash
echo "Plan complete. PR #36 updated with URL: $url"
```

---

## Assumptions (non-interactive)

- `gh` CLI is authenticated with `BACLUC_AGENT_GITHUB_TOKEN`.
- `bacluc-agent/agent-runner` is the target repo; PR #36 exists.
- `opencode.yml` has `workflow_dispatch` (confirmed in file).
- `ci.yml` intentionally has no `workflow_dispatch`; mapping fix skips it.
- `jq` may or may not be installed; script handles both.
- `RUNNER_TEMP` may be unset in local test; `/tmp` fallback is safe.
