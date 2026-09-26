# Issue 274 Analysis: 2026-09-25 Agent-Runner Workflow Failures

## Summary
Analyzed 24 failed workflow runs in `bacluc-agent/agent-runner` between 2026-09-25T02:20Z and 2026-09-25T10:20Z. Identified 5 distinct root-cause patterns.

## Failure Patterns

### 1. GitHub API Rate Limit (HTTP 403) — 5 runs
**Error**: `HTTP 403: API rate limit exceeded for user ID 325194408` when calling `gh api /repos/bacluc-agent/agent-todo/labels`

**Affected Runs**:
- 36088974574 (Hourly issue runner — select job)
- 36089855518 (Refine issues — refine job)
- 36091159175 (Hourly issue runner — select job)
- 36098043021 (Refine issues — refine job)
- 36099393486 (Hourly issue runner — select job)

**Files to Fix**:
- `.github/workflows/hourly-issue-runner.yml` — select job label fetching
- `.github/workflows/refine-issues.yml` — refine job label fetching

**Root Cause**: The `select` and `refine` jobs fetch all labels from `agent-todo` repo on every run. With hourly runs, this exhausts the GitHub API rate limit (5000 requests/hour for authenticated user).

**Fix Approach**: Cache labels, use conditional requests (ETag/If-None-Match), or reduce fetch frequency.

---

### 2. OpenCode "Unexpected Server Error" — 1 run (30+ occurrences)
**Error**: Repeated `Unexpected server error. Check server logs for details.` with ref IDs like `err_db87bfff`, `err_e325419d`

**Affected Run**:
- 36091159175 (Hourly issue runner — select job)

**Files to Fix**:
- `.github/workflows/hourly-issue-runner.yml` — select job OpenCode invocation
- `.opencode/agent/issue-selector.md` — agent prompt/model configuration

**Root Cause**: OpenCode agent coordinator encounters upstream model provider errors when invoking models (qwen3.6-plus, qwen3.8-max, etc.) during issue selection.

**Fix Approach**: Add model fallback logic, increase timeout/retry, or catch and handle provider errors gracefully.

---

### 3. CI Completion-Check False Failure — 1 run
**Error**: All tests pass (14 opencode tool tests + 153 pytest tests) but process exits with code 1

**Affected Run**:
- 36089108323 (CI workflow — completion-check job on branch `agent-run/219-36065843274`)

**Files to Fix**:
- `.github/workflows/ci.yml` — completion-check job
- `scripts/completion-check` — test runner script

**Root Cause**: Post-test cleanup or reporting step fails, or test runner returns non-zero despite all tests passing.

**Fix Approach**: Debug the completion-check script to find the failing step after tests pass.

---

### 4. OpenCode "retry_limit" Fatal Error — 3 runs
**Error**: `Run ❌ fatal error: retry_limit` when running prompt-generator agent

**Affected Runs**:
- 36101507293 (Hourly issue runner — run job, model: `openrouter/dots-studio/dots-3-note-preview:free`)
- 36101683733 (Hourly issue runner — run job, model: `openrouter/cohere/north-mini-code:free`)
- 36102033658 (Hourly issue runner — select job, same branch `issue-238-prompt-generator-concise-test`)

**Files to Fix**:
- `.github/workflows/hourly-issue-runner.yml` — run job model selection
- `.opencode/agent/prompt-generator.md` — agent configuration
- Model availability/fallback logic

**Root Cause**: Free-tier models on OpenRouter hit rate limits or return errors, exhausting the agent's retry attempts.

**Fix Approach**: Use more reliable models, increase retry limits, add model health checks before dispatch.

---

### 5. Coordinator Exit Failure (False Failure) — 4 runs
**Error**: Workflow marked "failed" with "Run ⚠️ failed (coordinator exit failure)" despite agent completing work and posting comments

**Affected Runs**:
- 36093032188 (Hourly issue runner — issue #219 table generation completed)
- 36111112547 (Hourly issue runner — issue #269 research completed)
- 36116566897 (Hourly issue runner — issue #269 final setup completed)
- 36114594253 (Review fixes runner — PR review completed)

**Files to Fix**:
- `.github/workflows/hourly-issue-runner.yml` — run job exit code handling
- `.github/workflows/review-fixes-runner.yml` — run job exit code handling
- OpenCode agent runner wrapper script

**Root Cause**: OpenCode agent returns non-zero exit code even after successful completion (posting comments, creating branches, etc.).

**Fix Approach**: Ensure the agent runner script returns 0 on successful completion, or handle specific exit codes that indicate "work done but not an error".

---

## Created Issues in bacluc-agent/agent-todo

| Pattern | Issue | URL |
|---------|-------|-----|
| GitHub API Rate Limit | #303 | https://github.com/bacluc-agent/agent-todo/issues/303 |
| OpenCode Unexpected Server Error | #304 | https://github.com/bacluc-agent/agent-todo/issues/304 |
| CI False Failure | #305 | https://github.com/bacluc-agent/agent-todo/issues/305 |
| OpenCode retry_limit | #306 | https://github.com/bacluc-agent/agent-todo/issues/306 |
| Coordinator Exit Failure | #307 | https://github.com/bacluc-agent/agent-todo/issues/307 |

## Summary Comment on Issue 274
https://github.com/bacluc-agent/agent-todo/issues/274#issuecomment-5846511866

## Next Steps
Each issue should be addressed independently. Priority order suggested:
1. #303 (rate limit) — affects most runs, blocks issue selection/refinement
2. #305 (CI false failure) — blocks CI pipeline reliability
3. #307 (coordinator exit failure) — creates noise, masks real failures
4. #304 (unexpected server error) — intermittent but blocks selection
5. #306 (retry_limit) — specific to prompt-generator test branch