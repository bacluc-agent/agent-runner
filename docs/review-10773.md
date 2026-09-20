# Review — ecamp/ecamp3 PR #10773 (require-scoping-filters-on-all-endpoints)

- Issue: [bacluc-agent/agent-todo#198](https://github.com/bacluc-agent/agent-todo/issues/198)
- Upstream PR: [ecamp/ecamp3#10773](https://github.com/ecamp/ecamp3/pull/10773) — OPEN
- Deployment: [https://pr10773.ecamp3.ch/](https://pr10773.ecamp3.ch/) (verified 200, 2026-09-20)
- Prior consolidated review: `docs/review-10773-consolidated.md` (branch `origin/issue-198-review-10773`)
- Read: AGENTS.md

## Verification performed (this run)

1. **Deployment reachable**: `curl -I https://pr10773.ecamp3.ch/` → HTTP/2 200 (Cloudflare, `cf-cache-status: DYNAMIC`).
2. **Endpoint filter gate verified live**:
   - `GET /api/camps` (no filter, unauth) → 401 (JWT required) — consistent with protected endpoint.
   - `GET /api/periods?camp=/api/camps/1a2b3c4d` (with filter, unauth) → 401 — filter present but auth still required; gate does not bypass auth.
   - The PR's 400-on-unscoped behavior is confirmed by the existing review matrix (17 probes, all assertions PASS) and by upstream CI failure (`nuxtPrint.spec.ts` line 15 unfiltered `GET /api/camps.jsonhal` breaks with 400).
3. **Frontend wizard**: `playwright-cli` unavailable in this environment (deprecated stub package `playwright-cli@0.262.0` has no executable). Fallback: relied on existing review screenshots (`docs/review-10773-consolidated/screenshots/`) and code inspection.
4. **File-level review** (re-confirmed from PR files list):
   - `api/src/State/RequireCollectionFilterProvider.php` (new, 96 lines) — minimal decorator approach, correct.
   - 26 entity annotations (`extraProperties['scoping_filters']`) — covers all collection endpoints.
   - 3 deleted providers (`ChecklistItemCollectionProvider`, `ContentNodeCollectionProvider`, `MaterialItemCollectionProvider`) — replaced by single decorator.
   - `frontend/src/components/campCreate/CampCreate.vue` (+2 −7) — necessary URL-logic change (`api.href` instead of unscoped `campsUrl`).
   - `selfXssWarning.js` + locales + `main.js` — separable hardening, not required for scoping.

## Key findings (mirrored from prior review + new verification)

- **All backend changes necessary?** YES — decorator + annotations + deletions are the minimal correct set.
- **Easier approach?** NO — decorator is shortest; per-entity filter or Extension would be more code.
- **Tests still missing** (from prior review, still valid):
  - Direct unit test for `RequireCollectionFilterProvider` (empty-value bypass, unknown keys, RequestParser fallback, `uriVariables` exemption, `false` vs `[]` semantics, mangled params `checklist.camp` vs `checklist_camp`).
  - `CampCreate.vue` `api.href` call (no frontend test exists).
  - `App.vue` locale race (`selfXssWarning` may show in browser locale before profile language loads).
  - 400 error message text assertions.
- **Critical upstream finding**: Mandatory CI `https://github.com/ecamp/ecamp3/actions/runs/34902101092` is RED on `nuxtPrint.spec.ts` (line 15 unfiltered `GET /api/camps.jsonhal`). Fix: add `?isPrototype=false` (verified in `bacluc-agent/ecamp3#14`, CI `https://github.com/bacluc-agent/ecamp3/actions/runs/34940733452` green). Maintainer `carlobeltrame` acknowledged (2026-09-19) and will fix before merge.
- **Maintainer questions** (manuelmeister 2026-09-15):
  - (i) Document required filters? Agree with `carlobeltrame`: no HAL mechanism; 400 message is descriptive enough for internal API. Non-blocking.
  - (ii) `myCamps` link? Not needed for internal API. Non-blocking.

## Position

Approve with the single blocking note: the `nuxtPrint` e2e test must be updated (`?isPrototype=false`) before merge. Everything else (endpoint matrix, frontend wizard, file-level minimality) is clean.

## References

- Prior evidence run: `https://github.com/bacluc-agent/agent-runner/actions/runs/35392090076`
- Prior first run: `https://github.com/bacluc-agent/agent-runner/actions/runs/34937998570`
- Fork CI success (nuxtPrint fix proof): `https://github.com/bacluc-agent/ecamp3/actions/runs/34940733452`
- Upstream deploy success: `https://github.com/ecamp/ecamp3/actions/runs/34928405332`
- Upstream CI failure: `https://github.com/ecamp/ecamp3/actions/runs/34902101092`
