# Flaky e2e analysis for #172

Analysis window: 2026-09-13 17:03:42Z (last completed run) → 2026-09-14 00:45:02Z (current run start)
Branch: issue-172
Repo: ecamp/ecamp3 (target), bacluc-agent/agent-todo (tracking)

Playwright retries: 0 (e2e/playwright.config.ts)

## Failure frequency (most frequent first)

| Rank | Reason                                                                                                                                                                                                | Count                       | Example runs                                                    | Typical log snippet                                                                                                                                                |
| ---- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------- | --------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 1    | Cross-browser deploy test: `markerSurvived` assertion fails (`expect(markerSurvived).toBe(false)` expected false, got true) in `5-cross-browser-tests-stal-de078-k-is-missing-after-a-deploy-firefox` | 5                           | 34786202794, 34774912717, 34774119305, 34772549771, 34771096781 | `Error: expect(received).toBe(expected) // Object.is equality` `Expected: false` `> 54                                                                             | expect(markerSurvived).toBe(false)`            |
| 2    | Locator visibility timeout (`expect(locator).toBeVisible()` failed, timeout 30000ms) for `[data-testid="create-camp-title-input"] input`                                                              | 2                           | 34653025387 (2026-09-11), 34447705270 (2026-09-10)              | `Error: expect(locator).toBeVisible() failed` `Locator: locator('[data-testid="create-camp-title-input"] input')` `Timeout: 30000ms` `Error: element(s) not found` |
| 3    | TimeoutError: `page.waitForURL` exceeded 60000ms (PDF download / login redirect) — from 2026-09-07 scheduled run                                                                                      | 2                           | 34107232508 (2026-09-07) — webkit project                       | `TimeoutError: page.waitForURL: Timeout 60000ms exceeded.` `> 34                                                                                                   | page.waitForURL('/camps', { timeout: 60000 })` |
| 4    | Setup/network: `curl --fail` retries to `localhost:3000/api` and `/print/health` before test start; `digest-mismatch: error` on `e2e-tests-images` cache                                              | Multiple (every failed run) | All recent runs (34786202794, 34774912717, etc.)                | `digest-mismatch: error` `- e2e-tests-images` `+ curl --output /dev/null --silent --fail http://localhost:3000/api` (repeated)                                     |

## Notes

- The dominant recent failure (5/5 recent `Tests: All End-to-End` runs) is the same cross-browser deploy test (`stal-de078-k-is-missing-after-a-deploy`) failing on firefox with `markerSurvived` assertion. This suggests a persistent state/deploy timing issue rather than random flakiness.
- Retries are set to 0 (`retries: 0` in playwright.config.ts), so any failure is final.
- The 2026-09-07 scheduled run (id 34107232508) showed different webkit failures (PDF download timeout, login redirect timeout) — these have not recurred in the recent window but remain known candidates.
