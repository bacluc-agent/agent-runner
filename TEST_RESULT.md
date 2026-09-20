Standing issue #165 — tested renovate/major-vitest-monorepo (ecamp/ecamp3#10725) — FAIL (vitest 5 breaks frontend test). Related to ecamp/ecamp3#10725. Ref #165.

# Test result: renovate/major-vitest-monorepo (ecamp/ecamp3#10725)

## Summary

- **Branch tested:** `renovate/major-vitest-monorepo` @ `b1fcf05a99fc65daccbd87e108f20917c8b965f6` (base `devel`)
- **Change:** vitest monorepo 4.1.11 → 5.0.0 (`frontend/package.json`, `frontend/package-lock.json`, `print/package.json`, `print/package-lock.json`)
- **Verdict: FAIL** — vitest 5.0.0 breaks `frontend/src/plugins/__tests__/preferences.spec.js` (`TypeError: Cannot set property localStorage of [object Window] which has only a getter`). Direct `window.localStorage = ...` assignment no longer works in vitest 5 test env.
- **CI:** Tests: Frontend FAIL ([run 35518347610](https://github.com/ecamp/ecamp3/actions/runs/35518347610/job/106099440441), [run 35518350183](https://github.com/ecamp/ecamp3/actions/runs/35518350183/job/106098435796)); workflow-success FAIL (cascade); all other jobs PASS (API validate migrations, lint, e2e build/run, format, etc.).
- **Local verification:** Confirmed same `localStorage` error locally. Print `npm ci` has separate lock-file issue (`cac` missing); print test failure (`.nuxt/tsconfig.json`) is unrelated infra.
- **Next action:** Fix mock pattern (`Object.defineProperty` or `vi.stubGlobal`) in `frontend/src/plugins/__tests__/preferences.spec.js` before merge. No fixes pushed to Renovate branch.

## Root cause

- vitest 5 changed the test environment so `window.localStorage` is a getter-only property; direct assignment (`window.localStorage = ...`) throws `TypeError`.
- The failing test (`preferences.spec.js`) uses this pattern to mock localStorage.
- This is a real code/test compatibility issue caused by the major version bump, not an infra failure.

## Recommendation

- **Do not merge** #10725 as-is.
- Apply a mock-pattern fix (`Object.defineProperty(window, 'localStorage', { value: ... })` or `vi.stubGlobal('localStorage', ...)`) in the affected test file, then retry/rebase the Renovate branch.
- The print package lock-file issue (`cac` missing) is a separate infra/dependency resolution problem unrelated to vitest 5.

# ponytail: minimal verification only; no fixes applied; no renovate.json changes; no push to Renovate branch.
