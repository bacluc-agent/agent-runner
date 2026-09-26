## Analysis iteration for bacluc-agent/agent-todo#172 — window: 2026-09-23T23:38Z → 2026-09-26T13:38Z

Standing issue stays open (never close). Previous analysis: https://github.com/bacluc-agent/agent-runner/issues/99 (window 2026-09-23T18:48:57Z → 2026-09-23T23:38Z). This iteration extends to 2026-09-26T13:38Z.

### Workflow confirmation

- e2e-tests.yml (id 76561500, "Tests: End to End to detect flaky tests"): cron '42 4 * * *', PR-only with label 'test-flaky-e2e!', workflow_dispatch with pr-number input, matrix 0..9 (10 attempts).
- retries: 0 (e2e/playwright.config.ts line 18); Playwright image mcr.microsoft.com/playwright:v1.63.0-noble; spec: e2e/tests/5-cross-browser-tests/staleDeployment.spec.ts.

### Failed runs examined (window 2026-09-23T23:38Z → 2026-09-26T13:38Z)

2 failed runs in e2e-tests.yml (both devel schedule runs). 0 failed runs in e2e-tests-all.yml.

| Run ID | Time | Branch | Result | Failures |
|--------|------|--------|--------|----------|
| 36120222300 | 2026-09-25T09:45:30Z | devel (`5203f90b`) | failure | 2 |
| 36232946407 | 2026-09-26T09:29:47Z | devel (`1aacb6d7`) | failure | 1 |

Raw `gh run list` output (commands re-run 2026-09-26T13:38Z):

```text
$ gh run list --repo ecamp/ecamp3 --workflow e2e-tests.yml --status failure --created ">=2026-09-23T23:38Z"
completed	failure	Tests: End to End to detect flaky tests	Tests: End to End to detect flaky tests	devel	schedule	36232946407	13m40s	2026-09-26T09:29:47Z
completed	failure	Tests: End to End to detect flaky tests	Tests: End to End to detect flaky tests	devel	schedule	36120222300	16m52s	2026-09-25T09:45:30Z

$ gh run list --repo ecamp/ecamp3 --workflow e2e-tests-all.yml --status failure --created ">=2026-09-23T23:38Z"
(no output — 0 failures)
```

### Ranking by frequency (updated)

| Rank | Reason | Count | Example runs | Typical log snippet |
| ---- | ------ | ----- | ------------ | ------------------- |
| 1 | behavior-tests hover/timeout race (comments.spec.ts delete-button) | 2 | [36232946407](https://github.com/ecamp/ecamp3/actions/runs/36232946407), [36120222300](https://github.com/ecamp/ecamp3/actions/runs/36120222300) | `Error: locator.click: Test timeout of 120000ms exceeded`, `Error: expect(locator).toBeVisible() failed` |
| 2 | login redirect timeout (chromium) — loginAndSetCookie waitForURL('/camps', {timeout:60000}) e2e/utils/helpers.ts:34 | 2 | [36120222300](https://github.com/ecamp/ecamp3/actions/runs/36120222300) | `TimeoutError: page.waitForURL` |
| 3 | DockerHub pull reset (infra) | 1 | (prior run) | `read tcp ... connection reset by peer` |
| 4 | staleDeployment firefox markerSurvived (FIXED upstream via ecamp/ecamp3#10775, merged 2026-09-22T18:46:50Z) | 0 | [35710417930](https://github.com/ecamp/ecamp3/actions/runs/35710417930) | expect(markerSurvived).toBe(false) got true |
| — | loginPage.spec.ts snapshot mismatch (PR-branch-only, PR #10459) | 30 in one run | (prior run) | snapshot mismatch |

### Root-cause analysis

**Cat1 (staleDeployment firefox markerSurvived)** — FIXED upstream via ecamp/ecamp3#10775 (merged 2026-09-22T18:46:50Z). No occurrences in this window. Demoted from rank 1.

**Cat2 (behavior-tests hover/timeout race)** — NEW dominant failure this window. Two runs failed with behavior-tests:
- Run 36120222300 (2026-09-25): 2 failures — `admin-tea-13b0b--by-name-and-uses-its-email-behavior-tests` (`TimeoutError: page.waitForURL: Timeout 60000ms exceeded`, `Error: expect(locator).toBeVisible() failed`, `Error: element(s) not found`) and `comments--eba5a--and-deletes-an-own-comment-behavior-tests` (`Error: expect(locator).toBeVisible() failed`).
- Run 36232946407 (2026-09-26): 1 failure — `comments--eba5a--and-deletes-an-own-comment-behavior-tests` (`Error: locator.click: Test timeout of 120000ms exceeded`).

The comments.spec.ts delete-button hover race was previously identified (rank 4, fix PR ecamp/ecamp3#10767 OPEN/DRAFT). The current failures appear to be the same hover race issue, now also affecting the admin-tea test with login redirect timeouts.

**Cat3 (login redirect timeout)** — Carried forward from previous analysis. 2 occurrences in run 36120222300.

**Cat4 (DockerHub pull reset)** — Carried forward from previous analysis. 1 occurrence in prior run.

### Local reproduction attempt

Not attempted this pass: 2 failed runs in window; behavior-tests failures are the dominant new issue. Prior local runs blocked by EACCES mkdir '/app/node_modules' (docker-compose user ${USER_ID:-1000}).

### Summary

Window 2026-09-23T23:38Z → 2026-09-26T13:38Z: 2 failed e2e runs in e2e-tests.yml, 0 in e2e-tests-all.yml. Dominant failure shifted from staleDeployment (Cat1, fixed) to behavior-tests hover/timeout race (Cat2). Issue remains open (standing / never-close).
