## Analysis iteration for bacluc-agent/agent-todo#172 — window: 2026-09-17T09:06:42Z → 2026-09-20

Standing issue stays open (never close). Previous analysis: https://github.com/bacluc-agent/agent-todo/issues/172#issuecomment-5657504027 (window 2026-09-17 09:06:42Z → 2026-09-17 09:37, run 35206098983). This iteration extends to 2026-09-20.

### Workflow confirmation

- Workflow file: `Tests: End to End to detect flaky tests` (workflow id 76561500, `e2e-tests.yml`)
- Retries: `0` (`e2e/playwright.config.ts` line 15)
- Playwright image: `mcr.microsoft.com/playwright:v1.63.0-noble` (`docker-compose.yml`)
- Spec file: `e2e/tests/5-cross-browser-tests/staleDeployment.spec.ts:54`

### Failed runs examined (window 2026-09-17 09:06:42Z → 2026-09-20)

| Run ID                                                                  | Date             | Branch                 | Project | Failure snippet                                                      |
| ----------------------------------------------------------------------- | ---------------- | ---------------------- | ------- | -------------------------------------------------------------------- |
| [35206098983](https://github.com/ecamp/ecamp3/actions/runs/35206098983) | 2026-09-17 09:37 | `devel`                | firefox | `expect(markerSurvived).toBe(false)` at `staleDeployment.spec.ts:54` |
| [35328062871](https://github.com/ecamp/ecamp3/actions/runs/35328062871) | 2026-09-18 09:09 | `devel`                | firefox | `expect(markerSurvived).toBe(false)` at `staleDeployment.spec.ts:54` |
| [35433354650](https://github.com/ecamp/ecamp3/actions/runs/35433354650) | 2026-09-19 08:56 | `devel`                | firefox | `expect(markerSurvived).toBe(false)` at `staleDeployment.spec.ts:54` |
| [35463140919](https://github.com/ecamp/ecamp3/actions/runs/35463140919) | 2026-09-19 19:03 | `e2e-show-pageObjects` | firefox | `expect(markerSurvived).toBe(false)` at `staleDeployment.spec.ts:54` |

Note: [35456176540](https://github.com/ecamp/ecamp3/actions/runs/35456176540) (`e2e-show-pageObjects`, 2026-09-19 16:49) also failed but log-failed produced no snippet; excluded from ranking due to missing evidence.

### Ranking by frequency (devel branch only, 4 runs × 10 attempts = 40 attempts)

| Rank | Reason                                                                                                                       | Count             | Example runs                                                                                                                                                                                                                                                                                       | Typical log snippet                                                                               |
| ---- | ---------------------------------------------------------------------------------------------------------------------------- | ----------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------- |
| 1    | `5-cross-browser-tests/staleDeployment.spec.ts` firefox: `expect(markerSurvived).toBe(false)` fails (marker survives reload) | 4 / 4 runs (100%) | [35206098983](https://github.com/ecamp/ecamp3/actions/runs/35206098983), [35328062871](https://github.com/ecamp/ecamp3/actions/runs/35328062871), [35433354650](https://github.com/ecamp/ecamp3/actions/runs/35433354650), [35463140919](https://github.com/ecamp/ecamp3/actions/runs/35463140919) | `Error: expect(received).toBe(expected) // Object.is equality` at `staleDeployment.spec.ts:54:26` |

Earlier candidates (`TimeoutError: page.waitForURL 60000ms` PDF download; `expect(body).toContainText('Meine Lager')`) did **not** appear in this window.

### Root-cause analysis (dominant reason — same as previous)

The dominant failure (`staleDeployment` firefox) **persists unchanged** since the previous analysis.

- **Root cause**: Playwright 1.63.0 (Firefox 155) retries `route.abort('failed')` for `CampCreate-*.js` chunks (commit `337a77a5`, PR ecamp/ecamp3#10692, image `mcr.microsoft.com/playwright:v1.63.0-noble`). The `route.abort('failed')` on the first chunk request does not trigger the expected page reload in Firefox 155; the `__noReload` marker survives (`markerSurvived` remains `true`), so `expect(markerSurvived).toBe(false)` fails.
- **Config**: `retries: 0` (`e2e/playwright.config.ts`) — no retry mitigation.
- **Image**: `mcr.microsoft.com/playwright:v1.63.0-noble` (`docker-compose.yml`) — same version as previous analysis; no upgrade.
- **Spec**: `e2e/tests/5-cross-browser-tests/staleDeployment.spec.ts:54` — unchanged.

No new root cause identified; previous root-cause note remains valid.

### Local reproduction attempt

Attempted per issue instructions: `CI=true docker compose up -d --force-recreate frontend` (root README). **Reproduction failed** — `ecamp/ecamp3` repository not cloned in this workspace (`agent-runner` repo only); no `docker-compose.yml` for ecamp3 present locally. No reproduction logs available.

### Summary

- Window: 2026-09-17T09:06:42Z → 2026-09-20
- Total `devel` failed runs examined: 4
- Total attempts (4 runs × 10 attempts): 40
- Dominant failure (`staleDeployment` firefox `markerSurvived`) persists at 100% frequency.
- Previous dominant failure: **persists** (same root cause, same Playwright 1.63.0 / Firefox 155, same `retries: 0`).
- Issue remains open (standing / never-close).
