# Standing Issue #165 — Major Renovate Test (2026-09-20)

Target: ecamp/ecamp3 PR #10770 (`renovate/react-pdf-pdfkit-6.x`)
Branch: `renovate/react-pdf-pdfkit-6.x` (head `1cedac095ae5d99d7f3f4cb9b0366333f0833087`)
Upgrade: `@react-pdf/pdfkit` 5.1.1 → 6.0.1 (major)

## CI Status (ecamp/ecamp3#10770)

- Mandatory checks: frontend PASS, print PASS, lint PASS, format PASS, behavior-tests PASS
- Optional checks: composer.lock validate PASS, dependency check PASS, psalm PASS, phpstan PASS
- FAILURES (PR-caused):
  - `Tests: End-to-end (chromium)` — FAIL (run 35455831212/job/105934609592)
  - `Tests: End-to-end (webkit)` — FAIL (run 35455831212/job/105934609594)
  - `Tests: End-to-end (firefox)` — FAIL (run 35455831212/job/105934609658)
  - `workflow-success` — FAIL (cascade from e2e failures)
- Pre-existing failure (not PR-caused): `API: validate migrations` — FAIL (identical on devel)

Evidence links:

- Failing CI run: https://github.com/ecamp/ecamp3/actions/runs/35455831212
- E2E chromium failure: https://github.com/ecamp/ecamp3/actions/runs/35455831212/job/105934609592
- E2E firefox failure: https://github.com/ecamp/ecamp3/actions/runs/35455831212/job/105934609658
- Migrations failure (pre-existing): https://github.com/ecamp/ecamp3/actions/runs/35455831083/job/105930796613

## Verdict: FAIL (e2e browser tests broken by pdfkit v6)

The major upgrade from @react-pdf/pdfkit 5.1.1 → 6.0.1 introduces breaking changes in PDF rendering that cause browser-based end-to-end tests (chromium, firefox, webkit) to fail. The behavior-tests pass, suggesting the core logic is intact but visual/rendering paths are affected. The `API: validate migrations` failure is pre-existing on devel and unrelated to this PR.

Next action: do NOT merge #10770 as-is; investigate pdfkit v6 rendering changes (font encoding, Buffer→Uint8Array, browser build split) and fix e2e tests or update snapshots before retry.

Standing issue remains open. Next candidate: oldest remaining untested open major Renovate PR in ecamp/ecamp3.
