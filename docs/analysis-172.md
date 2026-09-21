## Analysis iteration for bacluc-agent/agent-todo#172 — window: 2026-09-20T06:47:00Z → 2026-09-21

Standing issue stays open (never close). Previous analysis: https://github.com/bacluc-agent/agent-todo/issues/172#issuecomment-5742904305 (window 2026-09-19 15:10Z → 2026-09-20 06:47, run 35492093815). This iteration extends to 2026-09-21.

Candidate line: `[PR: closed #66] [last-human-feedback:none]` — PR #66 (updated 2026-09-20T06:58:49Z) treated as evidence, not blocker; fresh analysis implemented.

### Workflow confirmation

- Workflow file: `Tests: End to End to detect flaky tests` (workflow id 76561500, `e2e-tests.yml` / `e2e-tests-all.yml`)
- Retries: `0` (`e2e/playwright.config.ts` line 15)
- Playwright image: `mcr.microsoft.com/playwright:v1.63.0-noble` (`docker-compose.yml`)
- Spec file: `e2e/tests/5-cross-browser-tests/staleDeployment.spec.ts:54`

### Failed runs examined (window 2026-09-20 06:47 → 2026-09-21)

| Run ID                                                                  | Date             | Branch  | Project | Failure snippet                                                      |
| ----------------------------------------------------------------------- | ---------------- | ------- | ------- | -------------------------------------------------------------------- |
| [35502269912](https://github.com/ecamp/ecamp3/actions/runs/35502269912) | 2026-09-20 09:25 | `devel` | firefox | `expect(markerSurvived).toBe(false)` at `staleDeployment.spec.ts:54` |

Note: [35456176540](https://github.com/ecamp/ecamp3/actions/runs/35456176540) (`e2e-show-pageObjects`, 2026-09-19 16:49) previously failed but produced no extractable snippet; excluded from ranking due to missing evidence.

### Ranking by frequency (all failed runs since last analysis)

| Rank | Reason                                                                                                                       | Count                | Example runs                                                            | Typical log snippet                                                                               |
| ---- | ---------------------------------------------------------------------------------------------------------------------------- | -------------------- | ----------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------- |
| 1    | `5-cross-browser-tests/staleDeployment.spec.ts` firefox: `expect(markerSurvived).toBe(false)` fails (marker survives reload) | 1 / 1 new run (100%) | [35502269912](https://github.com/ecamp/ecamp3/actions/runs/35502269912) | `Error: expect(received).toBe(expected) // Object.is equality` at `staleDeployment.spec.ts:54:26` |

Earlier candidates (`TimeoutError: page.waitForURL 60000ms` PDF download; `expect(body).toContainText('Meine Lager')`) did **not** appear in this window.

### Root-cause analysis (dominant reason — same as previous)

The dominant failure (`staleDeployment` firefox) **persists unchanged** since the previous analysis.

- **Root cause**: Playwright 1.63.0 (Firefox 155) retries `route.abort('failed')` for `CampCreate-*.js` chunks (commit `337a77a5`, PR ecamp/ecamp3#10692, image `mcr.microsoft.com/playwright:v1.63.0-noble`). The `route.abort('failed')` on the first chunk request does not trigger the expected page reload in Firefox 155; the `__noReload` marker survives (`markerSurvived` remains `true`), so `expect(markerSurvived).toBe(false)` fails.
- **Config**: `retries: 0` (`e2e/playwright.config.ts`) — no retry mitigation.
- **Image**: `mcr.microsoft.com/playwright:v1.63.0-noble` (`docker-compose.yml`) — same version as previous analysis; no upgrade.
- **Spec**: `e2e/tests/5-cross-browser-tests/staleDeployment.spec.ts:54` — unchanged.

No new root cause identified; previous root-cause note remains valid.

### Additional observations from run 35502269912

- Firefox jobs (10 attempts): 10 failures, all with same `staleDeployment.spec.ts:54` assertion error.
- Varnish/http-cache warning observed: `mlock() of VSM failed: Cannot allocate memory (12)` (`ecamp3-http-cache` container).
- App startup retries observed: repeated `curl --fail http://localhost:3000/api` and `http://localhost:3000/print/health` before Playwright execution.
- No new failure signatures (timeout, locator not found, network/DOM flake, app error, infra runner) detected beyond the persistent `staleDeployment` assertion failure.

### Local reproduction attempt

Attempted per issue instructions: `CI=true docker compose up -d --force-recreate frontend` (root README). **Reproduction failed** — `ecamp/ecamp3` repository not cloned in this workspace (`agent-runner` repo only); no `docker-compose.yml` for ecamp3 present locally. No reproduction logs available.

### Summary

- Window: 2026-09-20T06:47:00Z → 2026-09-21
- Total failed runs examined: 1 new (`35502269912`) + 4 prior (`35206098983`, `35328062871`, `35433354650`, `35463140919`) = 5 total since 2026-09-17
- Total attempts (new run: 10 firefox attempts): 10
- Dominant failure (`staleDeployment` firefox `markerSurvived`) persists at 100% frequency in new run.
- Previous dominant failure: **persists** (same root cause, same Playwright 1.63.0 / Firefox 155, same `retries: 0`).
- Issue remains open (standing / never-close).
- PR #66 (updated 2026-09-20T06:58:49Z, last-human-feedback none) treated as evidence; fresh analysis implemented independently.
