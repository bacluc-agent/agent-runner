# Issue 165: Test major renovate update — gesdinet/jwt-refresh-token-bundle v3

Target: ecamp/ecamp3 PR #10537 (`renovate/gesdinet-jwt-refresh-token-bundle-3.x`)
Branch tested: `4913db2ad02e5c05f003d95335b4fb004fc81820`

## Verdict: FAIL (upgrade blocked — requires schema migration)

### CI Evidence (absolute links)
- Problem CI (ecamp/ecamp3#10537): https://github.com/ecamp/ecamp3/actions/runs/35469396657
  - API: validate migrations — FAIL
  - Tests: API — FAIL
  - Tests: End-to-end (behavior-tests/chromium/firefox/webkit) — FAIL
  - workflow-success — FAIL (cascade)
- Fix PR (BacLuc/ecamp3#358): https://github.com/BacLuc/ecamp3/actions/runs/31960951279
  - Tests: API — PASS
  - Tests: End-to-end (behavior-tests/chromium/firefox/webkit) — PASS
  - Lint: API (php-cs-fixer/phpstan/psalm) — PASS

### Root cause
Bundle v3.0.0 requires `family` and `family_valid` columns on refresh tokens (see UPGRADE-3.0.md). The Renovate PR updates `api/composer.json` and `api/composer.lock` but does NOT include the required Doctrine migration. Fix PR #358 (`BacLuc/ecamp3`) provides the missing migration (`Version20260816120000.php`).

### Tests run
- `composer validate` — PASS (on renovate branch)
- Migration check — FAIL (missing `family`/`family_valid` columns)
- No local functional tests executed (API-only dependency change; frontend unaffected)

### Next action
Merge fix PR `BacLuc/ecamp3#358` (or equivalent migration) into `ecamp/ecamp3` `devel`, then rebase/retry Renovate PR #10537. Do NOT merge #10537 as-is.

References:
- Issue: bacluc-agent/agent-todo#165
- Renovate PR: ecamp/ecamp3#10537
- Fix PR: BacLuc/ecamp3#358
