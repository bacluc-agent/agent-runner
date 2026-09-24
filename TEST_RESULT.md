Standing issue #165 — tested renovate/emoji-regex-11.x (ecamp/ecamp3#10822) — PASS (CI fully green; no direct emoji-regex usage in frontend source; local build/unit/lint pass). Related to ecamp/ecamp3#10822. Ref #165.

# Test result: renovate/emoji-regex-11.x (ecamp/ecamp3#10822)

## Summary

- **Run URL:** (local verification; CI evidence below)
- **Branch tested:** `renovate/emoji-regex-11.x` — PR [ecamp/ecamp3#10822](https://github.com/ecamp/ecamp3/pull/10822)
- **Change:** `emoji-regex` 10.6.0 → 11.0.0 (frontend/package.json + package-lock.json only) — genuine MAJOR bump
- **Verdict: PASS** — upgrade safe; no fixes needed; Renovate PR unchanged
- **Next action:** ready for maintainer review/merge; no separate fix PR required

## CI results (PR branch)

All checks PASS (2 runs, latest 2026-09-22):

| Job                                | State | Evidence                                                                                                      |
| ---------------------------------- | ----- | ------------------------------------------------------------------------------------------------------------- |
| Lint: Frontend (ESLint)            | PASS  | [run 35788903579/job/106952794695](https://github.com/ecamp/ecamp3/actions/runs/35788903579/job/106952794695) |
| Tests: Frontend                    | PASS  | [run 35788903579/job/106952794636](https://github.com/ecamp/ecamp3/actions/runs/35788903579/job/106952794636) |
| Tests: End-to-end (behavior-tests) | PASS  | [run 35788903579/job/106954585688](https://github.com/ecamp/ecamp3/actions/runs/35788903579/job/106954585688) |
| Tests: End-to-end (chromium)       | PASS  | [run 35788903579/job/106954585724](https://github.com/ecamp/ecamp3/actions/runs/35788903579/job/106954585724) |
| Tests: End-to-end (firefox)        | PASS  | [run 35788903579/job/106954585602](https://github.com/ecamp/ecamp3/actions/runs/35788903579/job/106954585602) |
| Tests: End-to-end (webkit)         | PASS  | [run 35788903579/job/106954585617](https://github.com/ecamp/ecamp3/actions/runs/35788903579/job/106954585617) |
| workflow-success                   | PASS  | [run 35788908235/job/106958085563](https://github.com/ecamp/ecamp3/actions/runs/35788908235/job/106958085563) |
| renovate/stability-days            | PASS  | [docs link](https://docs.renovatebot.com/key-concepts/minimum-release-age/)                                   |

No PR-caused failures. `API: validate migrations` and `Tests: API` are skipped (expected for frontend-only PR). `renovate/artifacts` passes (lockfile updated by Renovate).

## Local verification

- Clone: `/tmp/opencode/ecamp3-10822` on `renovate/emoji-regex-11.x` (`37e30d907`)
- `npm ci` (frontend): PASS (845 packages)
- `npm run build`: PASS (18.00s)
- `npm run test:unit`: PASS — 64 files, 1275 tests, 0 failures
- `npm run lint:check`: PASS (ESLint + Prettier clean)

## emoji-regex impact assessment

- `frontend/src/` search: **no direct import** of `emoji-regex`
- `frontend/src/plugins/veeValidate/oneEmojiOrTwoCharacters.js`: uses native `\p{Extended_Pictographic}` regex, not `emoji-regex`
- `emoji-regex` appears only as a direct dependency in `frontend/package.json` and resolved in `package-lock.json`; likely consumed by transitive dependencies (`cliui`, `wrap-ansi`)
- v11 updates the regex pattern for newer Unicode emoji; since ecamp3 frontend does not invoke the library directly, the pattern change has **no direct impact** on application behavior

## Verdict

PASS — the upgrade is safe. CI fully green; local build/unit/lint pass; no source-level dependency on the changed regex. The Renovate PR (#10822) remains untouched (no commits pushed to it). No separate fix PR needed.
