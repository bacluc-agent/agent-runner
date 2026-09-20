Standing issue #165 — tested renovate/typescript-7.x (ecamp/ecamp3#10638) — FAIL (blocked upstream: typescript-eslint has no TS 7 support). Related to ecamp/ecamp3#10638. Ref #165.

# Test result: renovate/typescript-7.x (ecamp/ecamp3#10638)

## Summary

- **Run URL:** https://github.com/bacluc-agent/agent-runner/actions/runs/35536590038
- **Branch tested:** `renovate/typescript-7.x` — PR [ecamp/ecamp3#10638](https://github.com/ecamp/ecamp3/pull/10638)
- **Change:** `typescript` 6.0.3 → 7.0.2 (only `e2e/package.json`; `e2e/package-lock.json` NOT updated) — a genuine MAJOR bump
- **Verdict: FAIL** (approved by review) — PR as-is is unmergeable, and the upgrade is blocked upstream even with a regenerated lockfile
- **Next action:** wait for typescript-eslint TS 7 support (none exists, not even canary), then retry; no fix PR opened because the blocker is upstream and a partial tsconfig fix would still fail CI
- **Note:** the pick for this run was corrected from #10557 (phpunit, minor not major) and #10627 (symfony, patch not major) to #10638 (typescript, genuine major)

## CI results (PR branch)

All failing checks on #10638 are caused by the stale lockfile (`npm ci` EUSAGE) or the upstream typescript-eslint blocker. Only `API: validate migrations` also fails pre-existing on devel.

| Job                                  | PR branch                                                                                                                                                                                  | Devel baseline                                                                     | Note                                                                                                              |
| ------------------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ---------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------- |
| renovate/artifacts                   | FAIL — Renovate's own check                                                                                                                                                                | —                                                                                  | Lockfile not regenerated: `e2e/package-lock.json` still has typescript 6.0.3.                                     |
| Lint: e2e (ESLint)                   | FAIL — [run 105932938407](https://github.com/ecamp/ecamp3/actions/runs/105932938407)                                                                                                       | —                                                                                  | `npm ci` EUSAGE: `lock file's typescript@6.0.3 does not satisfy typescript@7.0.2`.                                |
| Tests: End-to-end run (all browsers) | FAIL — behavior [run 105936644691](https://github.com/ecamp/ecamp3/actions/runs/105936644691), merge-reports [run 105940798278](https://github.com/ecamp/ecamp3/actions/runs/105940798278) | —                                                                                  | Install failure (same EUSAGE), not test failures.                                                                 |
| Merge e2e reports                    | FAIL (cascade) — [run 105940798278](https://github.com/ecamp/ecamp3/actions/runs/105940798278)                                                                                             | —                                                                                  | Cascades from the failing e2e run jobs.                                                                           |
| workflow-success                     | FAIL (cascade)                                                                                                                                                                             | —                                                                                  | Cascades from the failing jobs above.                                                                             |
| API: validate migrations             | FAIL                                                                                                                                                                                       | FAIL — [run 34901094421](https://github.com/ecamp/ecamp3/actions/runs/34901094421) | **Pre-existing**, identical on devel (`CampRootContentNode#rootContentNode` mapping invalid, doctrine/orm 3.7.0). |

## Root cause: upstream typescript-eslint has no TS 7 support

- Even with a regenerated lockfile the upgrade is blocked upstream: `typescript-eslint@8.70.0` peer requires typescript `>=4.8.4 <6.1.0` — `npm ci` ERESOLVE, reproduced in the `playwright:v1.63.0-noble` container (npm 11.19.0).
- typescript-eslint hard-refuses TS 7.0: "typescript-eslint does not support TS 7.0" (maintainer: "there is no TS 7 API at this time"; tracking issue typescript-eslint#12518; eslint/eslint#21070 blocked on it). Latest stable 8.70.0 peer excludes TS 7; 8.70.1 is only alpha.
- TS 7 removed `baseUrl` (TS5102) and non-relative paths (TS5090), breaking `tsc --noEmit` with the current `e2e/tsconfig.json`. Fixable: remove `baseUrl` + `./` prefix — typecheck passes after the fix. Devel with TS 6.0.3 passes `tsc` with the same tsconfig, proving this is TS 7-caused, not pre-existing.

## E2E tests themselves pass

Playwright has its own transpiler, so the tests are unaffected by the TS 7 upgrade:

- behavior-tests: 64 passed / 1 flaky-retry-pass / 1 skipped
- chromium: 8/8, firefox: 7/1 (staleDeployment environmental — needs production build), webkit: 6/2

## Recommendation

- **Do not merge** #10638 as-is — the lock is stale and `npm ci` fails.
- **Do not open a fix PR** — the blocker is upstream (typescript-eslint has no TS 7 support, not even canary); a partial tsconfig fix would still fail CI (eslint crash + npm ci ERESOLVE).
- **Wait** for typescript-eslint TS 7 support, then retry the Renovate branch.
- The pre-existing `API: validate migrations` failure is unrelated and should be tracked separately.
