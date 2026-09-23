## Analysis iteration for bacluc-agent/agent-todo#172 — window: 2026-09-23T18:48:57Z → 2026-09-23T23:38Z

Standing issue stays open (never close). Previous analysis: https://github.com/bacluc-agent/agent-todo/issues/172#issuecomment-5800876242 (window 2026-09-22T23:45Z → 2026-09-23T16:20Z). This iteration extends to 2026-09-23T23:38Z.

### Workflow confirmation

- e2e-tests.yml (id 76561500, "Tests: End to End to detect flaky tests"): cron '42 4 * * *', PR-only with label 'test-flaky-e2e!', workflow_dispatch with pr-number input, matrix 0..9 (10 attempts).
- retries: 0 (e2e/playwright.config.ts line 18); Playwright image mcr.microsoft.com/playwright:v1.63.0-noble; spec: e2e/tests/5-cross-browser-tests/staleDeployment.spec.ts.

### Failed runs examined (window 2026-09-23T18:48:57Z → 2026-09-23T23:38Z)

None — 0 failed runs in window (both e2e workflows). Context: last pre-fix failure https://github.com/ecamp/ecamp3/actions/runs/35710417930 (2026-09-22T09:26:47Z, devel, firefox); first post-fix full-matrix success https://github.com/ecamp/ecamp3/actions/runs/35843270702 (2026-09-23T09:29:47Z).

Raw `gh run list` output (commands re-run 2026-09-23T23:38Z):

```text
$ gh run list --repo ecamp/ecamp3 --workflow e2e-tests.yml --status failure --created ">=2026-09-23T18:48:57Z"
(no output — 0 failures)

$ gh run list --repo ecamp/ecamp3 --workflow e2e-tests-all.yml --status failure --created ">=2026-09-23T18:48:57Z"
(no output — 0 failures)

$ gh run list --repo ecamp/ecamp3 --workflow e2e-tests.yml --created ">=2026-09-23T18:48:57Z"
completed	action_required	fix(#7426): Simplified Rename and Delete Buttons for Material Lists	Tests: End to End to detect flaky tests	issue-7426-fix	pull_request	35919199018	0s	2026-09-23T20:55:49Z

$ gh run list --repo ecamp/ecamp3 --workflow e2e-tests-all.yml --created ">=2026-09-23T18:48:57Z"
(no output — 0 runs)
```

The single e2e-tests.yml run in the window (35919199018) is a PR check for ecamp/ecamp3#10742 (`issue-7426-fix`) in `action_required` state (waiting for the 'test-flaky-e2e!' label) — not a failure. Other window runs are non-e2e: CD cleanup https://github.com/ecamp/ecamp3/actions/runs/35920697619 (success), PR checks 35919198631/35919198680/35919198772/35919199018/35919199105 (action_required), CD https://github.com/ecamp/ecamp3/actions/runs/35919196982 (skipped).

### Ranking by frequency (carried forward; no new data this window)

| Rank | Reason                                                                                                              | Count         | Example runs                                                            | Typical log snippet                         |
| ---- | ------------------------------------------------------------------------------------------------------------------- | ------------- | ----------------------------------------------------------------------- | ------------------------------------------- |
| 1    | staleDeployment firefox markerSurvived (FIXED upstream via ecamp/ecamp3#10775, merged 2026-09-22T18:46:50Z)         | 0 this window | [35710417930](https://github.com/ecamp/ecamp3/actions/runs/35710417930) | expect(markerSurvived).toBe(false) got true |
| 2    | login redirect timeout (chromium) — loginAndSetCookie waitForURL('/camps', {timeout:60000}) e2e/utils/helpers.ts:34 | 2             | [35427168373](https://github.com/ecamp/ecamp3/actions/runs/35427168373) | TimeoutError: waitForURL                    |
| 3    | DockerHub pull reset (infra)                                                                                        | 1             | (prior run)                                                             | read tcp ... connection reset by peer       |
| 4    | comments.spec.ts delete-button hover race (fix PR ecamp/ecamp3#10767 OPEN/DRAFT)                                    | 1             | (prior run)                                                             | (hover race)                                |
| —    | loginPage.spec.ts snapshot mismatch (PR-branch-only, PR #10459)                                                     | 30 in one run | (prior run)                                                             | snapshot mismatch                           |

### Root-cause analysis

Cat1 root cause (from prior iterations, comment https://github.com/bacluc-agent/agent-todo/issues/172#issuecomment-5731656235): Playwright 1.63.0/Firefox re-fetches the aborted CampCreate chunk → no vite:preloadError → no reload → markerSurvived stays true. FIXED by ecamp/ecamp3#10775 (abort modulepreload + import re-fetch; assertion now at staleDeployment.spec.ts:61). devel head unchanged 44ea6ae8332131fb9ea7ed2417ac224de21fed21 (2026-09-23T05:10:11Z). Recommendation: demote/retire Cat1 from rank 1 if it stays at 0 through the next full analysis.

Fix confirmation (Step 2, re-run 2026-09-23T23:38Z):

```text
$ gh pr view 10775 -R ecamp/ecamp3 --json state,mergedAt,mergeCommit --jq '{state,mergedAt,mergeCommit:{oid:.mergeCommit.oid}}'
{"mergeCommit":{"oid":"ef903cfa04a917fe69e3daca276014fc531ebd5a"},"mergedAt":"2026-09-22T18:46:50Z","state":"MERGED"}

$ gh api repos/ecamp/ecamp3/commits/devel --jq '.sha, .commit.committer.date'
44ea6ae8332131fb9ea7ed2417ac224de21fed21
2026-09-23T05:10:11Z

$ gh api repos/ecamp/ecamp3/contents/e2e/playwright.config.ts --jq '.content' | base64 -d | grep -n "retries"
18:  retries: 0,
```

Post-fix runs all SUCCESS: full matrix https://github.com/ecamp/ecamp3/actions/runs/35843270702 (2026-09-23T09:29:47Z, incl. 10 firefox shards), e2e-tests-all https://github.com/ecamp/ecamp3/actions/runs/35831351826 (2026-09-23T07:22:16Z).

### Local reproduction attempt

Not attempted this pass: 0 new failures; Cat1 already reproduced + bisected (comment 5731656235); prior local runs blocked by EACCES mkdir '/app/node_modules' (docker-compose user ${USER_ID:-1000}).

### Summary

Window 2026-09-23T18:48:57Z → 2026-09-23T23:38Z: 0 failed e2e runs (e2e-tests.yml + e2e-tests-all.yml). Dominant failure (Cat1) fixed upstream. Issue remains open (standing / never-close).
