Standing issue #165 — tested renovate/api-platform-json-schema-4.x (ecamp/ecamp3#10098) — PASS. Related to ecamp/ecamp3#10098. Ref #165.

# Test result: renovate/api-platform-json-schema-4.x (ecamp/ecamp3#10098)

## Summary

- **Branch tested:** `renovate/api-platform-json-schema-4.x` @ `89ebcc4` (base `devel` @ `8b7e43d`)
- **Change:** `api-platform/json-schema` 4.3.10 → 4.3.18 (only `api/composer.json` + `api/composer.lock`; lock reference `b9749137` = v4.3.18 tag)
- **Verdict: PASS** — the only PR-caused CI failure is the OpenAPI snapshot test, which fails because the generated OpenAPI document changed as intended by the upstream fixes. All other tests pass; runtime API behavior is identical to devel.
- **Next action:** merge this PR, then a separate devel PR regenerating the OpenAPI snapshot (`ResponseSnapshotTest__testOpenApiSpecMatchesSnapshot__1.yml`) is required to make CI green.

## CI results (PR branch)

| Job | PR branch | Devel baseline | Note |
|---|---|---|---|
| Tests: API | FAIL — [push run 34901339216 job 104167839446](https://github.com/ecamp/ecamp3/actions/runs/34901339216/job/104167839446), [PR run 34901342970 job 104168475560](https://github.com/ecamp/ecamp3/actions/runs/34901342970/job/104168475560) | SUCCESS — [run 34901095010](https://github.com/ecamp/ecamp3/actions/runs/34901095010) | 1 failure: `ResponseSnapshotTest::testOpenApiSpecMatchesSnapshot` (2773 tests, 6412 assertions, 1 failure). Devel success proves the failure is PR-caused. |
| API: validate migrations | FAIL — [run 34901338848 job 104167753461](https://github.com/ecamp/ecamp3/actions/runs/34901338848/job/104167753461), [run 34901342765 job 104167766410](https://github.com/ecamp/ecamp3/actions/runs/34901342765/job/104167766410) | FAIL — [run 34901094421 job 104166967324](https://github.com/ecamp/ecamp3/actions/runs/34901094421/job/104166967324) | **Pre-existing**, identical error on devel: `CampRootContentNode#rootContentNode` mapping invalid (many-to-one association is sole identifier). Not caused by this PR. |
| workflow-success | FAIL (cascade of Tests: API) | — | Cascades from the snapshot failure. |
| Api Platform check dependencies | PASS — [run 34901338824 job 104167753286](https://github.com/ecamp/ecamp3/actions/runs/34901338824/job/104167753286), [run 34901342853 job 104167766838](https://github.com/ecamp/ecamp3/actions/runs/34901342853/job/104167766838) | — | |
| Check format | PASS — [job 104167754741](https://github.com/ecamp/ecamp3/actions/runs/34901339216/job/104167754741), [job 104167767759](https://github.com/ecamp/ecamp3/actions/runs/34901342970/job/104167767759) | — | |
| Lint: API php-cs-fixer | PASS — [job 104167839529](https://github.com/ecamp/ecamp3/actions/runs/34901339216/job/104167839529), [job 104168475501](https://github.com/ecamp/ecamp3/actions/runs/34901342970/job/104168475501) | — | |
| Lint: API phpstan | PASS — [job 104167753244](https://github.com/ecamp/ecamp3/actions/runs/34901339216/job/104167753244), [job 104167766900](https://github.com/ecamp/ecamp3/actions/runs/34901342970/job/104167766900) | — | |
| Lint: API psalm | PASS — [job 104167753515](https://github.com/ecamp/ecamp3/actions/runs/34901339216/job/104167753515), [job 104167766720](https://github.com/ecamp/ecamp3/actions/runs/34901342970/job/104167766720) | — | |
| Lint: Print ESLint | PASS — [job 104167754746](https://github.com/ecamp/ecamp3/actions/runs/34901339216/job/104167754746), [job 104167767623](https://github.com/ecamp/ecamp3/actions/runs/34901342970/job/104167767623) | — | |
| Lint: e2e ESLint | PASS — [job 104167754758](https://github.com/ecamp/ecamp3/actions/runs/34901339216/job/104167754758), [job 104167767631](https://github.com/ecamp/ecamp3/actions/runs/34901342970/job/104167767631) | — | |

## Local verification

Environment: docker compose stack (api + database + frontend), `DB_CPU_LIMIT=4`, `USER_ID=1001` (runner has 4 CPUs, host files owned by uid 1001), JWT keys chowned to 1001:1001. API port 3001 is not published to the host, so requests were made against the api container IP (`http://172.18.0.x:3001`).

- `composer validate -n --no-check-all --no-check-publish --strict` → exit 0, "./composer.json is valid"
- `composer test tests/Api/SnapshotTests/ResponseSnapshotTest.php` → Tests: 63, Assertions: 239, **Failures: 1** (`testOpenApiSpecMatchesSnapshot`, "Failed asserting that two strings are equal") — matches CI exactly. 1 deprecation (doctrine/orm 3.7.0 `ASC` order-by direction, from #10774 already in devel — pre-existing, not from this PR).
- `composer test tests/Api/ContentNodes/ColumnLayout/` → OK (87 tests, 231 assertions)
- `composer test tests/Api/Periods/` → OK (87 tests, 203 assertions)
- `composer test tests/Api/MaterialItems/` → OK (105 tests, 216 assertions; 1 warning from sentry serializer on an intentional INF test — unrelated)

## Snapshot diff analysis (categories A–F)

The snapshot diff (41866 lines, from CI log) was analyzed against the source and the upstream `api-platform/json-schema` git history (4.3.10..4.3.18 = #8272, #8289, #8294, #8362, #8485, #8480; core PRs #8277, #8306, #8321, #8313, #8386, #8360 — all task-listed PRs confirmed in the exact version range).

- **A — 619 auto-generated embedded schema definitions removed** (e.g. `Activity-read_Camp.Periods_Period.Days_...`, `Activity.html-read_...`, `Activity.jsonld-read_...`). These were auto-generated per-relation embedded schemas; they no longer exist because relations are now inlined (B).
- **B — relations inlined as IRI strings with metadata preserved.** Old: `camp: $ref: '#/components/schemas/Camp.html-read_...'` (full object schema). New: `camp: {description: 'The camp to which this activity belongs.', example: /camps/1a2b3c4d, format: iri-reference, readOnly: true, type: string}`. Metadata (description/example/format/readOnly/type) is preserved on the reference schemas — upstream #8480 "keep property metadata on reference schemas".
- **C — attribute removals: `supportedSlotNames`, `periodMaterialItems`, `daysSorted`, `endOfLastDay`, `firstDayNumber`, `periodLength`.** Verified in source: none of these have `#[Groups]`/`#[ApiProperty]` (`Period::$periodMaterialItems` Period.php:115-116, `MaterialItem::$periodMaterialItems` MaterialItem.php:103-104, `getDaysSorted()` Period.php:223, `getPeriodLength()` 335, `getFirstDayNumber()` 348, `getEndOfLastDay()` 372, `getSupportedSlotNames()` ContentNode.php:257). Runtime verification: these attributes are NOT serialized in API responses on either devel or PR branch — the schema previously documented attributes that were never returned; the new schema matches actual runtime behavior. `periodMaterialItems` (relation to non-resource `PeriodMaterialItem`) is no longer embedded in output schemas (upstream #8294/#8362 behavior for non-resource relation targets).
- **D — `moveScheduleEntries` becomes `writeOnly: true`** in the `Period.jsonapi` attributes schema. Source: `#[ApiProperty(example: true)] #[Groups(['write'])]` (Period.php:180-182) — write-only property now correctly marked. Runtime: PATCH `{"moveScheduleEntries": false}` → 200 on both branches.
- **E — ColumnLayout `data` default preserved.** `default: '{"columns":[{"slot":"1","width":6},{"slot":"2","width":6}]}'` exists in both old snapshot and new output (source: `ColumnLayout.php:82 DATA_DEFAULT`, `getData()` `#[ApiProperty(default: ...)]`). The `+ default:` diff lines belong to inlined schemas (category B) carrying the default with them. Runtime: POST without `data` → 201 with the default applied, identical on both branches.
- **F — OpenAPI document integrity.** `docs.jsonopenapi` → 200, valid OpenAPI 3.1.0, info "eCamp v3", 80 paths, 399 schemas, 2207 internal `$ref`s, **0 dangling references**.

## Smoke tests (PR branch vs devel — identical)

| # | Request | PR branch | devel (4.3.10) |
|---|---|---|---|
| 1 | GET /docs.jsonopenapi | 200 | 200 |
| 2 | GET / | 200 | 200 |
| 3 | GET /camps | 200 (7 camps) | 200 |
| 4 | GET /periods?camp=/camps/0969e3c95dfc | 200, C-attrs absent | 200, C-attrs absent |
| 5 | GET /material_items?camp=/camps/0969e3c95dfc | 200, periodMaterialItems absent | 200 |
| 6 | GET /content_node/column_layouts?camp=/camps/0969e3c95dfc | 200, supportedSlotNames absent | 200 |
| 7 | POST /content_node/column_layouts (valid data) | 201 | 201 |
| 8 | POST /content_node/column_layouts (no data) | 201, default applied | 201, default applied |
| 9 | POST /content_node/column_layouts (widths sum 11) | 422 "Expected column widths to sum to 12" | 422 |
| 10 | PATCH /periods/{id} {"moveScheduleEntries": false} | 200 | 200 |
| 11 | PATCH /periods/{id} (end before start) | 422 "less than or equal" | 422 |

Notes: routes are `/content_node/column_layouts` (singular), not `/content_nodes/...`; `material_items` and `column_layouts` collections require `camp`/`period`/`root` filters; invalid payloads return 422 (validation violations), not 400. POST requires a `parent` (root node creation is not allowed) and `slot` matching the parent's supported slots.

## Deprecations

1 deprecation in the snapshot test run: doctrine/orm 3.7.0 "Using 'ASC' as an order by direction is deprecated" (`Day::dayResponsibles`). Pre-existing — doctrine/orm 3.7.0 is identical on devel and PR branch (merged via #10774 before this PR). Not introduced by this change.

## Recommendation

- **Merge** `renovate/api-platform-json-schema-4.x` (PR #10098) — the change is safe; the snapshot failure is the expected consequence of the upstream OpenAPI generation fixes.
- **Follow-up (required for green CI):** a separate devel PR regenerating the OpenAPI snapshot (`api/tests/Api/SnapshotTests/__snapshots__/ResponseSnapshotTest__testOpenApiSpecMatchesSnapshot__1.yml`) — e.g. run `composer test tests/Api/SnapshotTests/ResponseSnapshotTest.php -- --update-snapshots` (or the project's snapshot update mechanism) and commit the updated snapshot. Not created as part of this test run.
- The pre-existing `API: validate migrations` failure (`CampRootContentNode#rootContentNode`) is unrelated and should be tracked separately.
