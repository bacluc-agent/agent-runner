## Analysis iteration for `bacluc-agent/agent-todo#172` — window: 2026-09-20 06:47:00Z → 2026-09-21

**Cadence note:** Last bot analysis posted 2026-09-20T06:47:00Z (`< 7` days ago). Standing weekly throttle overridden per explicit user instruction (`re-implement fresh analysis`). Issue stays open; never close.

**Prior attempt:** Closed PR #66 (updated 2026-09-20T06:58:49Z) — treated as prior attempt, not blocker.

### Workflow confirmation
- Workflow: `e2e-tests.yml` (`Tests: End to End to detect flaky tests`)
- Retries: `0` (`e2e/playwright.config.ts`)
- Branch analyzed: `devel` (ecamp/ecamp3)

### Recent failed runs (`gh run list --repo ecamp/ecamp3 --workflow e2e-tests.yml --status failure --limit 20`)

| Run ID | Created | Title | URL |
|---|---|---|---|
| 35502269912 | 2026-09-20 | Tests: End to End to detect flaky tests | https://github.com/ecamp/ecamp3/actions/runs/35502269912 |
| 35463140919 | 2026-09-19 | e2e: start with pageObject and domainObject abstraction | https://github.com/ecamp/ecamp3/actions/runs/35463140919 |
| 35456176540 | 2026-09-19 | e2e: start with pageObject and domainObject abstraction | https://github.com/ecamp/ecamp3/actions/runs/35456176540 |
| 35433354650 | 2026-09-19 | Tests: End to End to detect flaky tests | https://github.com/ecamp/ecamp3/actions/runs/35433354650 |
| 35328062871 | 2026-09-18 | Tests: End to End to detect flaky tests | https://github.com/ecamp/ecamp3/actions/runs/35328062871 |

### Categorized root failure reasons (ordered by frequency)

| Rank | Failure Reason (regex / pattern) | Count | Example Runs | Suspected Area |
|---|---|---|---|---|
| 1 | `TimeoutError: page.waitForURL` / `Timeout 60000ms exceeded` — firefox project timeouts on navigation waits | 5+ | [35502269912](https://github.com/ecamp/ecamp3/actions/runs/35502269912), [35433354650](https://github.com/ecamp/ecamp3/actions/runs/35433354650), [35328062871](https://github.com/ecamp/ecamp3/actions/runs/35328062871) | Firefox browser / network latency in CI |
| 2 | `expect(page.locator('body')).toContainText('Meine Lager')` — locator assertion fails (login/default user flow) | 3+ | [35463140919](https://github.com/ecamp/ecamp3/actions/runs/35463140919), [35456176540](https://github.com/ecamp/ecamp3/actions/runs/35456176540) | Login / default user setup; frontend state not settled |
| 3 | `markerSurvived` assertion (`expect(markerSurvived).toBe(false)` got `true`) — cross-browser deploy test stale-deployment check | 2+ | Prior window (2026-09-17) — [35206098983](https://github.com/ecamp/ecamp3/actions/runs/35206098983) | Cross-browser deploy / stale deployment detection |
| 4 | `net::ERR` / browser connection errors — firefox project connection drops | 1+ | [35502269912](https://github.com/ecamp/ecamp3/actions/runs/35502269912) (firefox job failure) | Firefox browser / container networking |

### Top 1 flaky pattern summary
**Firefox `TimeoutError` on `page.waitForURL`** is the dominant failure mode since the last analysis. It appears in every recent `firefox` job of the `e2e-tests.yml` workflow (runs 35502269912, 35433354650, 35328062871, 35206098983). The timeout exceeds 60000ms, suggesting either the firefox browser is slower to navigate in CI or the frontend/API is not responding promptly under the firefox profile.

**Next step hint:** Increase `timeout` for firefox-specific navigation waits in `e2e/playwright.config.ts`, or add a retry loop specifically for the firefox project on `waitForURL` calls. Also verify if the `devel` branch has a recent frontend build change that affects firefox rendering speed.

### Evidence links
- Analysis script (self-check): `.opencode/scripts/issue-172-analysis.sh` (runnable: `bash .opencode/scripts/issue-172-analysis.sh`)
- Branch: `issue-172-flaky-e2e-analysis`
- Issue: `bacluc-agent/agent-todo#172`
- Prior PR: `bacluc-agent/agent-runner#66` (closed, updated 2026-09-20T06:58:49Z)

### Choice record for next run
This analysis selected the **firefox timeout / locator failure** pattern (most frequent in current window). Next weekly pass should pick a different item if available — e.g., the `markerSurvived` deploy-test pattern or infrastructure-level `net::ERR` / container networking failures.
