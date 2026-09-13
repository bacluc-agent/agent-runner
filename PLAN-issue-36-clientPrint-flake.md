# Plan — Fix `Client print test › downloads PDF` flake (bacluc-agent/agent-todo#36)

> Planner-only. Ponytail full. Shortest diff that fixes root cause for all 35 callers, not just `clientPrint.spec.ts:14`.

## 1. Context & confirmed root causes

- Failing spec: `e2e/tests/5-cross-browser-tests/clientPrint.spec.ts:14` — `TimeoutError: page.waitForURL: Timeout 60000ms exceeded` on all three projects (webkit/firefox/chromium). Mirrors login-flake `Tests: End to End to detect flaky tests` scheduled run `34107232508` (all webkit).
- `retries: 0` in `e2e/playwright.config.ts:13` is the flake detector — **must not change**.
- Helpers: `loginAndSetCookie` called in 35 places, 8 `waitForURL` sites repo-wide (grep: `helpers.ts:34,179,209`, `oauthHelpers.ts:12,14`, `clientPrint.spec.ts:16`, `zz-createCamp.spec.ts:40`, `zzz-changePassword.spec.ts:36,42`).
- Root causes (from refiner + code read):

  1. **Racy `page.waitForURL('/camps')` as exact string** — not auto-retrying, misses redirect if navigation already happened. `page.goto('/')` then sequential `waitForURL` is a classic race (goto resolves before navigation commits). String `'/camps'` also fails when URL is `http://localhost:3000/camps` with trailing `?`/`/`/query.
  2. **Missing web-first assertions before clicks** on `GRGR`/`Admin`/`Drucken` — locator clicked before visible/attached.
  3. **Download listener already correct** (`waitForEvent('download')` before click) but issue body suggests adding `waitForResponse` on print API _before_ PDF assertions where applicable. For **client** print there is no API (pdf generated in worker via `file-saver`); adding a response wait would be wrong abstraction — leave download pattern as-is, only ensure the button was enabled/visible first.

- Constraint: `bacluc-agent/agent-todo#36` **stays open** (standing checklist, one fix per iteration). Last runner picks `14,123`; avoid `138,42,157,161,143,124,139,135,14,123`. Do not close tracker, only comment.

## 2. Solution approaches considered

| Approach                                                                      | Change                                                                                                                                      | Pros                                                                                                                                                                                                                                         | Cons                                                                                                                                              | Verdict                                                                                             |
| ----------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------- |
| **A — Central guard in `helpers.ts:34` (chosen)**                             | Replace `page.waitForURL('/camps')` with `expect(page).toHaveURL(/\/camps/)` inside `loginAndSetCookie` (and keep `Promise.all` click race) | One-line, fixes 35 callers; `expect.toHaveURL` is auto-retrying (Playwright best practice), handles `http://…/camps*`, no new helper; matches `login.spec.ts:20` existing pattern (`expect(page).toHaveURL(url => url.pathname==='/camps')`) | Touches shared code — regression risk if regex too loose                                                                                          | **Pick — ponytail ladder rungs 2 & 3: reuse existing expectation, stdlib regex, native Playwright** |
| B — Patch single caller `clientPrint.spec.ts:16` only                         | `await page.goto('/'); await expect(page).toHaveURL(/\/camps/)` just in that spec                                                           | Minimal blast radius                                                                                                                                                                                                                         | Leaves 34 callers still flaky; violates “one guard where all callers route through” — lazy fix is root-cause fix in shared helper, not per-caller | Reject                                                                                              |
| C — New helper `waitForCamps()` abstraction                                   | Wrap expect in utility, call from all specs                                                                                                 | DRY in theory                                                                                                                                                                                                                                | Unrequested abstraction (ponytail: no interface with one implementation), adds file, adds indirection for a one-liner                             | Reject                                                                                              |
| D — Keep `waitForURL` but switch to regex/glob `**/camps` or increase timeout | `page.waitForURL('**/camps', {timeout:90s})`                                                                                                | Small edit                                                                                                                                                                                                                                   | `waitForURL` still not auto-retrying; timeout bump hides race, doesn't fix; glob `**/camps` still flaky on query strings                          | Reject                                                                                              |
| E — Fix all 8 `waitForURL` sites at once                                      | Patch every file                                                                                                                            | Thorough                                                                                                                                                                                                                                     | Out-of-scope for “one test per iteration”; larger diff, higher review burden, hides incremental verification per #36 contract                     | Defer — note in tracker, do helpers.ts + clientPrint only now                                       |

## 3. Minimal plan — files to touch (fewest, shortest diff)

### 3.1 `e2e/utils/helpers.ts` — the shared guard (highest leverage)

**Current `23-36`:**

```ts
export async function loginAndSetCookie(
  page: Page,
  _: unknown,
  user: string,
  password = "test",
) {
  await page.goto("/");
  await page.locator('[type="email"]').fill(user);
  await page.locator('[type="password"]').fill(password);
  await Promise.all([
    page.locator('[type="submit"]').click(),
    page.waitForURL("/camps", { timeout: 60000 }),
  ]);
}
```

**Change to (1 logical line, keep Promise.all race):**

```ts
export async function loginAndSetCookie(
  page: Page,
  _: unknown,
  user: string,
  password = "test",
) {
  await page.goto("/");
  await page.locator('[type="email"]').fill(user);
  await page.locator('[type="password"]').fill(password);
  await Promise.all([
    page.locator('[type="submit"]').click(),
    expect(page).toHaveURL(/\/camps/),
  ]);
}
```

- `expect` already imported in file.
- Use regex `/\/camps/` (or `/\/camps(\/|$|\?)/` if want stricter) — aligns with `oauthHelpers.ts:14` and `deleteCampViaUI:209` (`/\/camps$/`) and `login.spec.ts:20` pathname check. Prefer `/\/camps/` for minimal change; it matches `http://localhost:3000/camps` + `?query` + `/`.
- Timeout now comes from `playwright.config.ts` `expect.timeout:15000`; do not pass explicit timeout unless flake persists — then consider `{timeout: 30000}` as second iteration.
- **Do not** change `retries:0`.

> Ponytail: If 15s proves too tight on CI cold start, upgrade path is `expect(page).toHaveURL(/\/camps/, {timeout: 60000})` — add explicit timeout only when measured.

Optionally also fix `helpers.ts:179` (`await page.waitForURL('**/admin/info')` → `await expect(page).toHaveURL(/\/admin\/info/)`) and `209` already regex — but **skip for this iteration** per “one test per iteration”; note in tracker as future candidate.

### 3.2 `e2e/tests/5-cross-browser-tests/clientPrint.spec.ts` — spec-local race + web-first assertions

**Current `14-24`:**

```ts
test('downloads PDF', async ({ page }) => {
  await page.goto('/')
  await page.waitForURL('/camps')
  await page.locator('a:has-text("GRGR")').click()
  await page.locator('a:has-text("Admin")').click()
  await page.locator('a:has-text("Drucken")').click()
  const downloadPromise = page.waitForEvent('download')
  await page.locator('button:has-text("PDF herunterladen (Layout #2)")').click()
  const download = await downloadPromise
```

**Change to:**

```ts
test('downloads PDF', async ({ page }) => {
  await page.goto('/')
  await expect(page).toHaveURL(/\/camps/)

  const grgrLink = page.getByRole('link', { name: 'GRGR' })
  await expect(grgrLink).toBeVisible()
  await grgrLink.click()

  const adminLink = page.getByRole('link', { name: 'Admin' })
  await expect(adminLink).toBeVisible()
  await adminLink.click()

  const druckenLink = page.getByRole('link', { name: 'Drucken' })
  await expect(druckenLink).toBeVisible()
  await druckenLink.click()

  const downloadButton = page.getByRole('button', { name: 'PDF herunterladen (Layout #2)' })
  await expect(downloadButton).toBeVisible()
  await expect(downloadButton).toBeEnabled()
  const downloadPromise = page.waitForEvent('download')
  await downloadButton.click()
  const download = await downloadPromise
```

- Rationale: `beforeEach` already logged in via `loginAndSetCookie` (now auto-retrying). `page.goto('/')` when authenticated redirects to `/camps`; `expect.toHaveURL` auto-retries until redirect settles — fixes the sequential `goto`→`waitForURL` race.
- `getByRole` preferred over `a:has-text` (web-first, accessibility, matches `persistDashboardFilter.spec.ts:8` pattern already in repo). Reuse existing pattern — no new util.
- Keep download pattern “listener before click” (already correct per #36 How-to). No `waitForResponse` needed — client PDF uses `generatePdf()` worker + `file-saver`, no print API. Adding `page.waitForResponse(/.*\/print.*/)` would be speculative. If reviewer insists, add `// ponytail: client pdf has no API response to wait for; add waitForResponse only for nuxtPrint.spec.ts server pdf` comment.
- Imports: `expect` already imported.

### 3.3 Files NOT to touch this iteration

- `e2e/playwright.config.ts` — leave `retries:0`, `expect.timeout:15000`, `trace: 'retain-on-failure'`.
- `e2e/utils/oauthHelpers.ts` (`waitForURL(/\/mock-auth\//)` is already regex — fine), `zzz-changePassword.spec.ts`, `zz-createCamp.spec.ts`, `staleDeployment.spec.ts` — defer to tracker comment.
- `frontend/` — no frontend fix needed unless trace shows genuine app race; keep test strict.

## 4. Order of operations (build agent checklist)

1. **Branch & fork prep**
   - `gh auth login` / `gh auth status` with `BACLUC_AGENT_GITHUB_TOKEN` (PAT). `echo $BACLUC_AGENT_GITHUB_TOKEN | gh auth login --with-token` if needed.
   - Check fork exists: `gh repo view bacluc-agent/ecamp3 --json parent` → parent `ecamp/ecamp3`. Also `bacluc/ecamp3` exists. Per #36 “open PR against branch pointing to same commit as ecamp/ecamp3 devel (you might need to create that) in bacluc/ecamp3”. Prefer `bacluc-agent/ecamp3` fork for agent, but verify workflow target: `gh api repos/ecamp/ecamp3 --jq .default_branch` → `devel` (confirmed). Branch base is `devel` (= `main` in issue text means default branch).
   - Ensure local clone: `git clone https://github.com/bacluc-agent/ecamp3 /tmp/ecamp3` or `gh repo fork ecamp/ecamp3 --clone` if missing.
   - `git remote add upstream https://github.com/ecamp/ecamp3.git; git fetch upstream devel; git checkout -b issue-36 upstream/devel` — branch name `issue-36` per task.

2. **Edit `e2e/utils/helpers.ts` first** (shared guard), commit.

3. **Edit `e2e/tests/5-cross-browser-tests/clientPrint.spec.ts`**, commit.

4. **No new deps, no formatting drift**

5. **Push** `git push -u origin issue-36` (origin = fork). Record branch name for issue comment.

6. **Verify** (see §5), then open PR `gh pr create --repo bacluc/ecamp3 --base devel --head bacluc-agent:issue-36 --label 'test-flaky-e2e!' --title 'Fix clientPrint flake: toHaveURL + web-first assertions (agent-todo#36)'` . If `bacluc/ecamp3` requires fork `bacluc-agent/ecamp3`, push there and PR across forks: `--repo ecamp/ecamp3` vs `bacluc/ecamp3` — follow #36 exact: “in bacluc/ecamp3”. Check `gh repo view bacluc/ecamp3`. If push to `bacluc-agent/ecamp3`, create PR via `gh pr create -R bacluc/ecamp3`.

7. **Tracker comment** on `bacluc-agent/agent-todo#36` (stay open): fixed test, root cause, PR link, plus new checklist from `gh run list --repo ecamp/ecamp3 --workflow e2e-tests.yml --status failure --limit 20` + `gh run view <id> --log-failed | grep -E "✘|TimeoutError|failed"`.

## 5. Verification steps (must pass before PR)

Simulate CI (production frontend build) per #36 §2:

```bash
CI=true docker compose up -d --force-recreate frontend
# loop failing spec 20×, retries 0, each browser that runs 5-cross-browser-tests
for i in $(seq 20); do
  docker compose --profile e2e run --rm e2e npx playwright test tests/5-cross-browser-tests/clientPrint.spec.ts --project=webkit --retries=0
done
# repeat for firefox, chromium (matrix is 4-project but this spec only in multipleBrowserTests)
docker compose --profile e2e run --rm e2e npx playwright test tests/5-cross-browser-tests/clientPrint.spec.ts --project=firefox --retries=0
docker compose --profile e2e run --rm e2e npx playwright test tests/5-cross-browser-tests/clientPrint.spec.ts --project=chromium --retries=0
# lint
docker compose --profile e2e run --rm e2e npx playwright test --lint   # or `npm run lint` inside e2e container per e2e/README.md
```

Local fallback (no docker):

```bash
npx playwright test tests/5-cross-browser-tests/clientPrint.spec.ts --project=webkit --retries=0
npx playwright test tests/5-cross-browser-tests/clientPrint.spec.ts --project=chromium --retries=0
```

Exit code must be 0 for 20 consecutive runs. If still flaky, pull trace: `docker compose --profile e2e run --rm e2e npx playwright show-trace <trace.zip> --host=localhost --port=8080` (trace retain-on-failure).

Also verify not broke other callers:

```bash
docker compose --profile e2e run --rm e2e npx playwright test tests/5-cross-browser-tests/login.spec.ts --project=webkit --retries=0
```

## 6. Risk mitigations

- **Shared helper regression:** Regex `/\/camps/` is slightly looser than exact `'/camps'` but correct — Playwright best practice is auto-retrying `toHaveURL` with regex; matches `/camps`, `/camps/`, `/camps?foo`. Strict alternative `/\/camps\/?(\?|$)/` available if false-positive observed. Mitigation: keep `expect.timeout` default 15s; only bump if cold-start CI shows timeout (upgrade path comment).
- **Retries stay 0:** Do not add `test.slow()`/`test.retry` or `waitForTimeout`. No `test.skip`.
- **Web-first assertions:** `toBeVisible` + `toBeEnabled` are web-first and auto-retry, they don't weaken assertion; they replace racy `click()` without guard.
- **Branch target:** Base is `devel` (default_branch). Verify before PR: `gh api repos/bacluc/ecamp3 --jq .default_branch` → `devel`. Use `upstream/devel` as point-in-time base (same commit as ecamp/ecamp3 devel).
- **Fork handling:** If `bacluc-agent/ecamp3` fork missing or stale, `gh repo fork` or `git remote` push with PAT `BACLUC_AGENT_GITHUB_TOKEN`. Post run link + model as first issue comment (workflow already does, but build agent should ensure).
- **Issue stays open:** Comment but never `gh issue close 36`. Tracker is standing checklist.
- **Avoided issues:** Do not pick `138,42,157,161,143,124,139,135,14,123` as next candidate if expanding checklist.

## 7. What was skipped (ponytail)

- Skipped fixing all 8 `waitForURL` sites → add when next iteration picks that spec (e.g., `staleDeployment › reloads when chunk missing` is next recurrent). Add when trace shows same race there.
- Skipped `waitForResponse` on client PDF → add when server-side print test (`nuxtPrint › downloads PDF for whole camp`) flakes and trace shows network wait needed (`page.waitForResponse(/\/api\/.*/)`).
- Skipped new `waitForCamps` helper abstraction → add when helper grows beyond one-liner.

## 8. References (for build agent)

- `e2e/playwright.config.ts:13` retries 0, expect timeout 15s, projects chromium/firefox/webkit + behavior-tests.
- `e2e/tests/5-cross-browser-tests/clientPrint.spec.ts:16` exact line to replace.
- `e2e/utils/helpers.ts:34` exact line to replace; `e2e/utils/oauthHelpers.ts:12,14` already regex (reference).
- `e2e/tests/5-cross-browser-tests/login.spec.ts:20-21` correct pattern to copy: `expect(page).toHaveURL(...)+expect(getByRole...).toBeVisible()`.
- `e2e/README.md` docker compose commands for CI reproduction.
- Workflow `.github/workflows/e2e-tests.yml` triggered by `test-flaky-e2e!` label, runs matrix 10×.

---

Pass context to build agent: `agent-run 14,123` last picks, avoided list above, token `BACLUC_AGENT_GITHUB_TOKEN`, branch `issue-36` off `upstream/devel`.
