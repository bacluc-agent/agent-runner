# Consolidated Review — ecamp/ecamp3 PR #10773 "Require query param filters on all endpoints"

- Issue: [bacluc-agent/agent-todo#198](https://github.com/bacluc-agent/agent-todo/issues/198) (re-run; prior attempt [bacluc-agent/agent-todo#202](https://github.com/bacluc-agent/agent-todo/issues/202), closed 2026-09-16)
- Upstream PR: [ecamp/ecamp3#10773](https://github.com/ecamp/ecamp3/pull/10773) — OPEN, APPROVED by pmattmann 2026-09-17 ("very clean solution 👍"), MERGEABLE
- Head commit: `b6786bc769d34d99eeb7b2e20d129df7fdbc9768` (unchanged since 2026-09-15), base `devel`; 73 files changed (+588 −2840)
- Deployments: [https://pr10773.ecamp3.ch/](https://pr10773.ecamp3.ch/) (login `test@example.com` / `test`) and [https://dev.ecamp3.ch/](https://dev.ecamp3.ch/) — both HTTP 200
- This run: [https://github.com/bacluc-agent/agent-runner/actions/runs/35392090076](https://github.com/bacluc-agent/agent-runner/actions/runs/35392090076)
- Date: 2026-09-18
- Read: AGENTS.md

---

## 1. Deployment verification

Both deployments are up and reachable (HTTP 200). Login works on both:

- PR deployment: magic button `.dev-login-button` on the PR page.
- devel: no `.dev-login-button`; used the "Login" button in the dev alert.
- JWT user confirmed on both: `/api/users/9145944210a7`.

This run closes the gap of the prior attempt (bacluc-agent/agent-todo#202), where playwright-cli was unavailable. All testing below was done with playwright-cli 0.1.20.

## 2. Endpoint probe matrix

17 probes × 2 deployments, all status assertions PASS. Item counts drift vs the prior review because both deployments share test data that changes over time.

| #   | Endpoint                                                         | PR status/count/message                                                                                                                                                                                                                   | devel status/count/message |
| --- | ---------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | -------------------------- |
| 1   | `/api/camps` (no filter)                                         | 400 / 0 / "Filter on campCollaborator or isPrototype is required."                                                                                                                                                                        | 200 / 9                    |
| 2   | `/api/camps?campCollaborator=$USER`                              | 200 / 5                                                                                                                                                                                                                                   | 200 / 7                    |
| 3   | `/api/camps?isPrototype=false`                                   | 200 / 5                                                                                                                                                                                                                                   | 200 / 7                    |
| 4   | `/api/camps?campCollaborator=` (empty)                           | 400 / 0 / "No resource associated to \"\"."                                                                                                                                                                                               | 400 / 0 / same             |
| 5   | `/api/periods` (no filter)                                       | 400 / 0 / "Filter on camp or campCollaborator is required."                                                                                                                                                                               | 200 / 11                   |
| 6   | `/api/periods?camp=$CAMP`                                        | 200 / 1                                                                                                                                                                                                                                   | 200 / 1                    |
| 7   | `/api/activities` (no filter)                                    | 400 / 0 / "Filter on camp is required."                                                                                                                                                                                                   | 200 / 143                  |
| 8   | `/api/activities?camp=$CAMP`                                     | 200 / 18                                                                                                                                                                                                                                  | 200 / 18                   |
| 9   | `/api/content_types` (exempt `false`)                            | 200 / 11                                                                                                                                                                                                                                  | 200 / 11                   |
| 10  | `/api/camps/$CAMP/activities` (sub-resource uriVariables exempt) | 200 / 18                                                                                                                                                                                                                                  | 200 / 18                   |
| 11  | unauth `/api/camps`                                              | 401 / 0 / "JWT Token not found"                                                                                                                                                                                                           | 401 / 0 / same             |
| 12  | `/api/periods?camp=` (empty value)                               | 200 / 0 — value-blind gate                                                                                                                                                                                                                | 200 / 0                    |
| 13  | `/api/periods?camp[]=x` (array)                                  | 200 / 0 — value-blind gate                                                                                                                                                                                                                | 200 / 0                    |
| 14  | `/api/camps?camp=` (unknown key)                                 | 400 / 0 / "Filter on campCollaborator or isPrototype is required." (key-based gate)                                                                                                                                                       | 200 / 9                    |
| 15  | `/api/checklist_items?checklist.camp=$CAMP` (dotted)             | 200 / 0                                                                                                                                                                                                                                   | 200 / 0                    |
| 16  | `/api/checklist_items?checklist_camp=$CAMP` (underscore)         | 400 / 0 / "Filter on checklist or checklist.camp is required."                                                                                                                                                                            | 200 / 2282                 |
| 17  | root GET `/api`                                                  | 200 — with Accept: application/ld+json no `_links` key (with application/hal+json it has templated `_links` only); collection search IriTemplates mark all filters `required:false` — the API does not document required filters anywhere | 200 — identical            |

### Key interpretations

- **Rows 12/13 — the gate is VALUE-BLIND.** It checks key presence only. Empty (`?camp=`) and array (`?camp[]=x`) values pass the gate but return 0 items — no data leak, but the gate does not validate that the filter value is meaningful.
- **Row 14 — key-based gate.** An unknown key (`?camp=` on `/api/camps`) does not satisfy the required-filter check and yields 400.
- **Row 16 — underscore-mangled behavior change.** The old provider on devel checked PHP-mangled query names (`checklist_camp`), so the literal underscore form silently bypassed the filter and returned **2282 unfiltered items**. The new provider parses the raw query string, so `?checklist_camp=` now 400s on PR while `?checklist.camp=` works. This is a real behavior improvement.
- **Row 17 — the API does NOT document required filters anywhere.** Root GET `/api` with Accept: application/ld+json has no `_links` key (with application/hal+json it has templated `_links` only) and all collection search IriTemplates mark filters `required:false`. This directly answers maintainer question (i) — see section 8.

## 3. Frontend testing with playwright-cli

Commands used: `open`, `snapshot`, `click`, `goto`, `fill`, `console`, `eval`, `resize`, `screenshot`.

### Console findings

- PR wizard load: **0 errors / 0 warnings**.
- `selfXssWarning` present on PR only — German variant ("%cStopp!" + "%cDiese Browser-Konsole ist für Entwickler*innen gedacht…"). Locale-dependent; the prior review saw the English variant. devel: 0 messages.
- No 400 errors on either deployment during the wizard flow.
- Only 401 seen: benign pre-login `/api/token/refresh` race on initial page load (PR).

### Wizard avoided unfiltered GET /api/camps

Performance entries show ONLY the filtered call `https://pr10773.ecamp3.ch/api/camps?campCollaborator=%2Fusers%2F9145944210a7` (same on devel). The frontend never issues an unscoped collection GET — the CampCreate change (section 4) works.

### End-to-end camp creation (bonus)

Completed the wizard end-to-end on PR: title "Testlager PR10773 Review", dates 01.08.2027–07.08.2027, template "Keine Vorlage" → camp created and visible in the camps list (API count 5 → 6). The POST path is unaffected by the collection-GET filter gate.

### Screenshots

Committed at `docs/review-10773-consolidated/screenshots/`:

| File                  | Size    | md5       |
| --------------------- | ------- | --------- |
| pr-wizard.png         | 31455 B | a551d269… |
| dev-wizard.png        | 31295 B | 1c8fa684… |
| pr-wizard-mobile.png  | 24210 B | 42279ae6… |
| dev-wizard-mobile.png | 24210 B | 42279ae6… |
| pr-camps-mobile.png   | 34139 B | a319de42… |
| dev-camps-mobile.png  | 41693 B | 68adaaa5… |

![pr-wizard](./screenshots/pr-wizard.png)
![dev-wizard](./screenshots/dev-wizard.png)
![pr-wizard-mobile](./screenshots/pr-wizard-mobile.png)
![dev-wizard-mobile](./screenshots/dev-wizard-mobile.png)
![pr-camps-mobile](./screenshots/pr-camps-mobile.png)
![dev-camps-mobile](./screenshots/dev-camps-mobile.png)

**The wizard-mobile pair is byte-identical (md5 42279ae6… both) — a GENUINE finding, not a test bug.** The wizard FORM components (CampCreateStep1/2.vue) are untouched and CampCreate.vue's change is URL-logic only, so at 390×844 the dialog fills the viewport and no differing background is visible. The prior review's "invalid comparison" verdict was actually correct behavior.

**The camps-mobile pair DIFFERS** (a319de42… vs 68adaaa5…) — that comparison exercises the filtered API call and shows deployment-specific data, so it is the meaningful mobile comparison.

## 4. File-level review conclusions

### Backend — minimal and correct

- `api/config/services.yaml`: replaces 3 CollectionProvider services with a single decorator `RequireCollectionFilterProvider` decorating `api_platform.doctrine.orm.state.collection_provider` (`@.inner` + `@request_stack`); deletes `ContentNodeCollectionProvider`, `ChecklistItemCollectionProvider`, `MaterialItemCollectionProvider`.
- `api/src/State/RequireCollectionFilterProvider.php` (new, 96 lines, `final readonly`): `provide()` checks `CollectionOperationInterface && [] === uriVariables`; reads `extraProperties['scoping_filters']`; `false` → pass; missing/empty → 400 "This collection cannot be listed unfiltered."; otherwise requires any listed filter present in parsed query params (`RequestParser::parseRequestParams` + `_api_query_parameters`); throws `BadRequestHttpException`; sub-resources (`/camps/{id}/activities`) exempt via `uriVariables`; `getQueryParameters()` avoids PHP `checklist_camp` mangling by using `_api_query_parameters` or reparsing the raw query string.
  - NOTE: `_api_query_parameters` is never set anywhere in the project — the attribute branch is dead code in practice; the RequestParser path is the only live path. Minor cleanup opportunity, not a bug.
- 26 entities add `extraProperties['scoping_filters']`: Activity(camp), ActivityProgressLabel(camp), ActivityResponsible(activity, activity.camp), Camp(campCollaborator, isPrototype), CampCollaboration(camp), Category(camp), Checklist(camp, isPrototype), ChecklistItem(checklist, checklist.camp), Comment(camp, activity), ContentNode(+6 subtypes)(root, camp, period), ContentType(false), Day(period, period.camp), DayResponsible(day, day.period), MaterialItem(camp, period, materialList, materialNode), MaterialList(camp), Period(camp, campCollaborator), Profile(user, user.collaborations.camp, search), ScheduleEntry(period, activity), User(false).
  - The prior review's mention of an "Invitation" entity was inaccurate — no Invitation entity exists; `/invitations` is a DTO item endpoint.
- The 3 deleted providers each checked `$request?->query->has(...)` with PHP-mangled names (e.g. `checklist_camp`) and threw `BadRequestHttpException`. The new provider's raw-query-string parsing changes behavior: literal `?checklist_camp=` (underscore) now 400s (verified live, row 16) while `?checklist.camp=` works.

### Frontend

- `CampCreate.vue` (+2 −7): **NECESSARY** — drops computed `campsUrl` (`api.get().camps()._meta.self` → unscoped `/camps`) and uses `await api.href(api.get(), 'camps')` (matches existing `DialogPeriodCreate.vue` / `CollaboratorCreate.vue` patterns); removes `api.reload(campsUrl)`.
- `this.api.reload` removal is **SAFE** — no stale-camps-list regression: `frontend/src/views/Camps.vue` `mounted()` → `loadCamps()` → `this.api.reload(this.camps)` (now filtered with `campCollaborator`) + `this.api.reload(this.periods)` on EVERY visit; CampCreate navigates away via `$router.push(campRoute(camp, 'admin'))`; App.vue has no `<keep-alive>`, so Camps.vue unmounts and remounts on return → fresh reload. The removed reload was belt-and-suspenders.
- `selfXssWarning.js` (12 lines) + `__tests__/selfXssWarning.spec.js` (39 lines) + locales `{de,en,fr,it}.json` + `main.js` (production-gated `warnAboutSelfXss()`): **UNRELATED to scoping** — separable hardening, harmless, cleaner as a split PR (BacLuc suggested exactly that in review; carlobeltrame declined).
  - Known cosmetic issue: App.vue may commit the profile language asynchronously after `warnAboutSelfXss()` runs (`mounted()` awaits `loadUser` → profile → `setLanguage`), so the warning can appear in the initial/browser locale rather than the user-profile locale — confirmed live (German variant shown; user profile language may differ). Console-only, cosmetic.

## 5. Test coverage assessment

### Covered behaviorally (existing upstream tests)

- uriVariables exemption (sub-resource tests)
- 401-vs-400 ordering (17 List tests have both anonymous-401 and without-filter-400)
- `false` semantics (ListContentTypesTest 200 unfiltered)

### STILL MISSING (no direct unit test for RequireCollectionFilterProvider)

- empty-value bypass (`?camp=`) — live: passes gate, 200 with 0 items (no leak, but untested)
- unknown keys (`?camp[]`) — live: 200 with 0 items (untested)
- RequestParser fallback (`_api_query_parameters` null) — attribute never set anywhere; branch is dead code (untested)
- uriVariables non-empty exemption (unit-level)
- `false` vs `[]` semantics — `false` covered; `[]` (the "This collection cannot be listed unfiltered." message) untested
- mangled params `checklist.camp` vs `checklist_camp` (behavior change vs old provider, untested)
- CampCreate `api.href` call (no frontend test for CampCreate.vue exists)
- App.vue locale race (`selfXssWarning.spec.js` sets `i18n.global.locale.value` directly, bypassing the race; no test of `main.js` ordering)
- No test asserts the 400 error message text.

## 6. CRITICAL upstream finding — nuxtPrint e2e failure still latent

Upstream mandatory CI run [https://github.com/ecamp/ecamp3/actions/runs/34902101092](https://github.com/ecamp/ecamp3/actions/runs/34902101092) = **FAILURE** (never re-run): `e2e/tests/9-behavior-tests/nuxtPrint.spec.ts:15` calls unfiltered `GET /api/camps.jsonhal` and line 19 expects `body._embedded.items` — the PR's 400 breaks it, and the test was NOT updated.

The proven fix is adding `?isPrototype=false` (exactly what fork PR [bacluc-agent/ecamp3#14](https://github.com/bacluc-agent/ecamp3/pull/14) commit `2bb7db8d1` did; fork CI run [https://github.com/bacluc-agent/ecamp3/actions/runs/34940733452](https://github.com/bacluc-agent/ecamp3/actions/runs/34940733452) success).

The PR is APPROVED but its own mandatory CI is red on this — a heads-up before merge. Deploy run (success): [https://github.com/ecamp/ecamp3/actions/runs/34928405332](https://github.com/ecamp/ecamp3/actions/runs/34928405332).

## 7. Explicit answers

1. **All changes necessary?** Backend (services.yaml decorator + RequireCollectionFilterProvider + 26 entity annotations + 3 provider deletions) and CampCreate.vue: **YES** — minimal set that enforces scoping on all collection endpoints. selfXssWarning + locales + main.js: **NOT necessary** for scoping — separable hardening, harmless, cleaner as a split PR.
2. **Easier approach?** **No** — the decorator is the shortest correct approach: one file, no new dependency, reuses existing RequestParser. Alternatives (per-entity filter attribute, Extension, ApiFilter) would be more code/magic. `extraProperties` alone without the provider gives no enforcement.
3. **Which tests are still missing?** The list in section 5 (provider unit tests: empty-value bypass, unknown keys, RequestParser fallback, uriVariables exemption, false-vs-[] semantics, mangled params; CampCreate `api.href` test; App.vue locale race; 400 message text) PLUS the nuxtPrint e2e fix (`?isPrototype=false`) — the PR's own mandatory CI is red on it.

## 8. Position on the two maintainer questions

From the PR discussion: manuelmeister (2026-09-15) asked (i) whether the API should indicate which filters are required (root endpoint / OpenAPI docs) now that unscoped collection requests fail, and (ii) whether a `myCamps` link should be added. carlobeltrame (2026-09-15) replied there is no HAL built-in way to document required filters, the API isn't public and may never be published, he doesn't want to maintain docs for AI scripts, and "The error message when omitting the filter is clear enough IMO."

Our position (evidence-based):

- **(i) Agree with carlobeltrame.** Live probe (row 17) confirms neither the root Entrypoint nor the search IriTemplates indicate required-ness (all `required:false`), so the ONLY discoverable signal is the 400 error message, which IS descriptive ("Filter on campCollaborator or isPrototype is required."). For an internal API this is acceptable; if the API is ever published, `hydra:search` with `required:true` on the IriTemplate mappings would be the natural mechanism. **Non-blocking.**
- **(ii) myCamps link: not needed** for an internal API; the frontend already resolves the scoped camps URL via `api.href(api.get(), 'camps')` with `campCollaborator`. **Non-blocking.**

Approval has already been given; both questions are effectively resolved.

## 9. References

- [bacluc-agent/agent-todo#198](https://github.com/bacluc-agent/agent-todo/issues/198) (this issue)
- [bacluc-agent/agent-todo#202](https://github.com/bacluc-agent/agent-todo/issues/202) (prior attempt, closed)
- [ecamp/ecamp3#10773](https://github.com/ecamp/ecamp3/pull/10773) (upstream PR)
- [bacluc-agent/ecamp3#14](https://github.com/bacluc-agent/ecamp3/pull/14) (fork implementation proof)
- [https://github.com/bacluc-agent/agent-runner/actions/runs/35392090076](https://github.com/bacluc-agent/agent-runner/actions/runs/35392090076) (this run)
- [https://github.com/ecamp/ecamp3/actions/runs/34902101092](https://github.com/ecamp/ecamp3/actions/runs/34902101092) (upstream CI failure nuxtPrint)
- [https://github.com/ecamp/ecamp3/actions/runs/34928405332](https://github.com/ecamp/ecamp3/actions/runs/34928405332) (deploy success)
- [https://github.com/bacluc-agent/agent-runner/actions/runs/35009103759](https://github.com/bacluc-agent/agent-runner/actions/runs/35009103759) (prior evidence run)
- [https://github.com/bacluc-agent/agent-runner/actions/runs/34937998570](https://github.com/bacluc-agent/agent-runner/actions/runs/34937998570) (prior first run)
- [https://github.com/bacluc-agent/ecamp3/actions/runs/34940733452](https://github.com/bacluc-agent/ecamp3/actions/runs/34940733452) (fork CI success)
