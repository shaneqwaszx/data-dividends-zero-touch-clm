# UI V2 Final Independent Re-Quality Gate

## 1. Executive summary

**Result: FAIL.** The synchronized integration commit and its ancestry are correct, backend/security files retain exact material parity with `origin/main`, the prior F-01 through F-05 remediations independently re-gate cleanly, the scanner is strict, the frontend verification baseline is fully green, and the primary backend/API-driven UI paths remain truthful.

Three independently reproduced defects prevent approval:

1. **HIGH — Onboarded causes document-level horizontal overflow.** At 1024, 760, and 480 CSS-pixel viewport settings, the document was wider than its client width. At 480, the document measured 1030/465 pixels, producing a page-level horizontal scrollbar and a substantially clipped mobile layout. The wide table has an intended scroll wrapper, but its intrinsic width still expands the page.
2. **MEDIUM — the historical backend list-ordering failure remains intermittent.** Full backend run #1 passed with 711 tests and 11 skips. Full backend run #2 failed `test_repository_listing_is_empty_ordered_and_defensively_copied`, yielding 1 failed, 710 passed, and 11 skipped. Ten subsequent isolated reruns passed, but the required two consecutive full-suite passes were not achieved.
3. **MEDIUM — the supported Windows lifecycle cannot verify its own live session in this timezone.** Both recorded processes and both health endpoints remained live, but `demo_lifecycle.ps1 -Action Status` exited 1 and reported both roles as `MISMATCH`. `ConvertFrom-Json` returns the stored UTC timestamp as a `DateTime`; the later string cast drops `Z`, so the comparison reparses it as local time and introduces an eight-hour offset.

This was a review-only gate. No implementation, test, scanner, security, or dependency file was changed. The only repository file created by this gate is this report.

## 2. Reviewed branch/worktree

- Repository: `C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm`
- Branch: `integration/ui-v2-finalization`
- Worktree: the primary repository worktree listed by `git worktree list`
- Review mode: independent, read-only except for this report

The active branch and worktree matched the requested review target.

## 3. Current HEAD

`git rev-parse HEAD` returned:

`a1f83a3c2b52e4a163979b5d4fd076a4070cb6b0`

This exactly matches the expected synchronized HEAD. The commit is the synchronization merge and has checkpoint `c252e311eada8ebfbb71effc3fb8988b46dd268b` and authoritative main `74a5fd2f8bc8a37c02a24dadaaa32a895ce2ee93` as parents/ancestors. No later implementation commit exists on the branch.

## 4. Synchronization ancestry

Both required ancestry checks returned exit code 0:

- `git merge-base --is-ancestor c252e311eada8ebfbb71effc3fb8988b46dd268b HEAD`
- `git merge-base --is-ancestor origin/main HEAD`

The graph/log inspection showed:

- checkpoint commits expected/observed: **1 / 1**
- main synchronization merges expected/observed: **1 / 1**
- unexpected implementation commits after synchronization: **0**

The merge contains the UI checkpoint plus the authoritative main-side backend/security remediation. No post-merge implementation commit was found.

## 5. origin/main SHA

After `git fetch origin`, `git rev-parse origin/main` returned:

`74a5fd2f8bc8a37c02a24dadaaa32a895ce2ee93`

This exactly matches the required authoritative SHA.

## 6. origin/ui-edits-v2 SHA

After the same fetch, `git rev-parse origin/ui-edits-v2` returned:

`be6bf3fa6dc3f15230d196f0d9c84cf9ccc66814`

This exactly matches the required frontend reference SHA.

## 7. Working-tree state

The initial status contained the expected non-clean items:

- `scripts/check_secrets.py` and `tests/test_check_secrets.py` showed mixed-EOL/stat indications only;
- `.ai-pipeline/reports/UI_V2_MAIN_SYNCHRONIZATION.md` was intentionally untracked;
- the unrelated strange filename beginning `e workspace and multi-document intake` was present;
- inaccessible pytest-cache directories emitted access warnings during broad searches.

The scanner files had **no material diff** in all three required comparisons:

- `git diff -- scripts/check_secrets.py tests/test_check_secrets.py`
- `git diff --raw -- scripts/check_secrets.py tests/test_check_secrets.py`
- `git diff origin/main -- scripts/check_secrets.py tests/test_check_secrets.py`

Only LF/CRLF warnings appeared. The strange filename and inaccessible cache directories were not touched.

## 8. Source hierarchy

The review applied the requested hierarchy:

1. the ten attached original screenshots for layout, visual language, and product-language intent;
2. `origin/ui-edits-v2` for reusable frontend/component/style reference;
3. `origin/main` for backend, API, workflow, and security authority;
4. synchronized integration behavior for the implementation under review.

The prior screen contract, implementation, quality-gate, remediation, and synchronization reports were read as claims/evidence only. Runtime behavior, source inspection, diffs, and fresh test output determined this verdict.

## 9. Screenshot inventory

All ten supplied screenshots were inspected:

1. Confirm details
2. Registry unavailable
3. Registry extract and verify
4. New onboarding
5. Audit trail
6. Client record
7. Completed
8. Onboarded list
9. Corrections/resubmit dialog
10. Pipeline rerun/case detail

The comparison covered the Autoboard shell, primary navigation, operator/account area, header and active underline, intake, registry states, case list/detail, evidence, pipeline, dialogs, completed/client/onboarded views, audit, cards, tables, spacing, typography, and status wording.

## 10. Backend/security parity

All four required file comparisons against `origin/main` were materially empty:

- `apps/backend/app/connectors/acra_bizfile_sandbox.py`
- `apps/backend/tests/test_acra_bizfile_sandbox_connector.py`
- `scripts/check_secrets.py`
- `tests/test_check_secrets.py`

Composition inspection confirmed:

- speculative OAuth client-credentials behavior remains removed;
- the ACRA sandbox connector remains dormant/uncomposed;
- provider routing was not changed by the UI branch;
- Q-012 remains OPEN and is shown as pending sponsor confirmation.

Backend/security divergence from `origin/main`: **0**.

## 11. Secret scanner

Fresh results:

- `python scripts/check_secrets.py`: **PASS**
- `python -m unittest discover -s tests -p "test_check_secrets.py" -v`: **5 passed**

An independent in-memory adversarial probe, outside the repository and without a probe file, verified detection of all requested forms:

- literal client-secret assignment — detected as sensitive assignment;
- literal access-token assignment — detected as sensitive assignment;
- bearer-token literal — detected as bearer authorization;
- API-key-like assignment — detected as sensitive assignment;
- conversion-wrapped literal secret — detected as sensitive assignment.

The first attempt to execute the probe had a test-harness quoting syntax error; the corrected in-memory probe ran successfully. No scanner bypass or scanner failure occurred and no temporary probe remained.

## 12. F-01 registry stop

A synchronized-backend registry stop was independently reproduced with case `8f9d4321-d135-4d35-a294-09e8d682bcc2`:

- `POST /api/clm/zero-touch/cases` returned **201**;
- the exact case was immediately retained as `WAITING_FOR_REVIEW` at `REGISTRY`;
- the backend returned `JURISDICTION_CONFLICT`, with no registry route/provider selected;
- browser rendering showed **Registry unavailable** and **Attention required**;
- no document-intake POST occurred for that case;
- no intake-complete POST occurred for that case;
- no impossible `Targeted retry required` message appeared;
- the case appeared in Cases and reopened by exact case ID.

The backend log showed only create followed by list/detail/evidence GET requests for this case. It showed no intake or completion request. F-01 is resolved.

## 13. Normal intake

Normal synchronized-backend intake was independently exercised with case `4dfcd10a-0889-4b19-a56d-571359dd67d3`:

- create: **201**;
- document upload 1: **201**;
- independent document upload 2: **201** with a distinct document ID;
- explicit intake complete: **200**;
- final state: `COMPLETED`, stage `COMPLETE`.

The backend log recorded create → document 1 → document 2 → intake complete in that order.

A genuine invalid-document upload was exercised on retained case `3f2db4c0-3fab-4b52-ba5b-6190cf545459`:

- upload returned **422**;
- the same case remained `PENDING_INPUTS` at `DOCUMENT`;
- no intake-complete request followed;
- no successful outcome was fabricated.

Targeted retry behavior and exact case/document binding were additionally verified in the passing frontend suite and source. The in-app browser's file-chooser bridge timed out during direct physical upload attempts, so the runtime upload evidence was recorded from the synchronized backend and logs rather than from a browser file chooser.

## 14. F-03 reset

Source inspection confirmed `resetNewCasePresentation` clears:

- case summary and retained-created summary;
- selected documents/current intake file state;
- case ID, UEN, and jurisdiction input state;
- request errors and polling warning;
- upload/intake progress;
- submitting/resolving state.

`handleStartNewCase` invokes that reset. The 95-test frontend baseline includes reset coverage, and previously persisted backend cases remained queryable/reopenable from Cases during browser QA. No stale presentation owner was found. Direct browser upload-to-terminal-state setup was limited by the browser file-chooser bridge noted above; this is a tooling limitation, not an observed product failure.

## 15. F-04 registry semantics

The exact state model is `SUCCESS`, `PENDING`, `ATTENTION`, `UNAVAILABLE`, `NOT_SELECTED`, and `FAILED`. Source, rendered DOM, accessible names, and tests agreed:

- jurisdiction conflict renders `!`, visible `Status: attention`, and accessible `Jurisdiction status: attention`;
- registry route not selected renders `–`, visible `Status: not selected`, and matching accessible label;
- pending does not use a success checkmark;
- unavailable/failed have distinct non-colour cues;
- only success uses the success checkmark.

No misleading registry status icon remains.

## 16. F-05 Policy classifications

The rendered Policy page used exactly:

- `REAL`
- `DERIVED`
- `PENDING SPONSOR CONFIRMATION`
- `UNAVAILABLE`

Representative values from all four categories were observed. Q-012 and Q-015 were both visibly OPEN sponsor questions and both carried `PENDING SPONSOR CONFIRMATION`; neither appeared as REAL. All mapped Policy/runtime values carry one classification. F-05 is resolved.

## 17. Global visual parity

The synchronized UI retains the screenshot-defined design system and structure: Autoboard wordmark, serif-led typography, warm neutral palette, thin dividers, compact cards/tables, active gold underline, New onboarding, Cases, Onboarded, Audit, Policy, environment indicator, operator control, pipeline/evidence layouts, dialogs, and truthful status language.

Prototype-only production claims were replaced with explicit Mock/POC/unavailable wording where the authoritative backend does not support the concept. No old-main dashboard visual leakage was found. The one material visual difference is the independently reproduced mobile page-width failure on Onboarded, recorded in sections 18, 19, and 39.

## 18. Responsive QA

Cases, Onboarded, Audit, Client record, and Case Detail were inspected at 1280, 1024, 760, and 480 CSS-pixel viewport settings. Document width was compared with client width, and wide-table wrapper/table widths were measured.

Observed document/client widths:

| Viewport | Cases | Onboarded | Audit | Client record | Case Detail |
|---:|---:|---:|---:|---:|---:|
| 1280 | 1280/1280 | 1280/1280 | 1265/1265 | 1265/1265 | 1265/1265 |
| 1024 | 1024/1024 | **1044/1009** | 1009/1009 | 1009/1009 | 1009/1009 |
| 760 | 760/760 | **1034/745** | 745/745 | 745/745 | 745/745 |
| 480 | 465/465 | **1030/465** | 465/465 | 465/465 | 465/465 |

Cases uses a deliberate contained scroll region: at narrow widths its table remained approximately 980 pixels wide while the document stayed constrained. Audit, Client record, and Case Detail also stayed constrained. Onboarded did not.

At 480, Onboarded produced approximately 565 pixels of document overflow and a page-level horizontal scrollbar. The table's right-side columns and controls were materially clipped unless the entire document was scrolled. This is mobile-breaking and is classified HIGH as directed by the gate.

## 19. Onboarded-table overflow investigation

Onboarded uses `table-card table-scroll`, whose CSS specifies `max-width: 100%` and `overflow-x: auto`; the table itself has an intentional `min-width: 1100px`. Measurements nevertheless showed:

- 1280: wrapper about 1223, table about 1223, document 1280/1280;
- 1024: wrapper about 952, table 1100, document 1044/1009;
- 760: wrapper about 707, table 1100, document 1034/745;
- 480: wrapper about 435, table 1100, document 1030/465.

The wide table is therefore not fully contained at the page/flex-item boundary. The wrapper can scroll, but the Onboarded page's intrinsic width still expands the document. The defect is absent from Cases despite a similarly wide table, confirming this is not trivial browser rounding. No fix was made.

## 20. Account/operator

The account area remains visually present. At desktop width it includes `Signed in as` plus `Demo operator`; at narrow width it preserves the operator control while simplifying surrounding metadata.

Opening the control displayed:

- `Local POC operator`
- `Authentication not connected in current POC.`
- `No identity, reviewer role, or sign-out action is available.`

It did not log out, change identity, assign a role, imply PingFed application login, or imply RBAC.

## 21. Cases

Browser QA verified real backend-driven controls:

- typed status filter;
- jurisdiction filter;
- exact case/UEN/company search;
- row navigation and exact-ID reopen.

The registry-stop case was found by exact ID and reopened successfully. Jurisdiction came from exact-case detail enrichment. Assigned reviewer remained `—`; list metrics showed backend-authored active-exception and human-intervention counts. No enabled dead Cases control was found.

## 22. Case Detail

Backend-authored detail remained available for:

- registry result, issue, route, provider/environment, acquisition status, and provenance;
- documents, fields, confidence, provider, state, and supersession evidence;
- reconciliation observations, validity, confidence, provenance, decisions, and unresolved replacement requirement;
- ownership/readiness/target evidence when available and explicit unavailable states otherwise;
- blockers, warnings, run metrics, timeline, recovery, and technical-failure states.

A live low-confidence case `b2fdc261-03af-4d60-bbec-5e58188b898d` rendered a backend-authored `DOCUMENT_LOW_CONFIDENCE` exception, 40% document confidence, current document evidence, replacement requirement, blockers, warnings, NOT_ATTEMPTED target operations, and backend timeline. No browser-side source precedence, UBO calculation, target replay, or approval was found.

## 23. Review dialogs

The low-confidence backend case exposed two disclosure controls:

- `Assign reviewer · unavailable`
- `Return for rework · unavailable`

Both opened semantic labelled dialogs. Reviewer select/note and final Assign were disabled. Rework reason/comment/field controls and final Return for rework were disabled. Both displayed explicit `not available in current POC` messaging, while Cancel remained a real local presentation action.

The backend request log after these interactions contained only supported GET requests. It contained no `/api/reviewers`, `/assign`, `/return-for-rework`, or equivalent speculative mutation.

## 24. Completed

Completed state was observed from a real synchronized-backend Mock workflow completion. It described Mock zero-touch completion and used the exact allowed identifier label `Mock GoldTier party ID`.

The runtime did not label the result Production Client ID, Approved, Ready for Approval, production onboarded, or live GoldTier accepted. Readiness explicitly stated `Ready-for-Approval: NOT AVAILABLE` where applicable.

## 25. Onboarded

The Onboarded collection requested only `COMPLETED` cases and enriched each row from exact-case detail. The exercised row contained:

- a `Mock GoldTier party ID`;
- real case/registration/company/jurisdiction values;
- risk `—`;
- next review `—`;
- a disabled risk filter with explanatory POC text;
- functional search, jurisdiction filter, row navigation, and Open action.

No production client-master claim was made. Functional truth passes; responsive containment fails as documented above.

## 26. Client record

The completed Mock client record rendered real backend case evidence only: corporate particulars, source/provenance information, documents, ownership/readiness/target status, metrics, and timeline. Its identifier remained `Mock GoldTier party ID`.

Unsupported export and start-review actions were disabled. Raw document download was not offered. No production client approval or review-scheduler value was fabricated.

## 27. Audit

The Audit page rendered backend timeline events only. Actor and loop displayed `—` because the backend supplied neither. Export CSV was disabled and explanatory copy stated that CSV export is unavailable in the current POC; no compliance-grade global audit-service claim appeared.

Semantic filtering was exercised: the unfiltered view showed **18 entries**; selecting `target` produced exactly **3 entries** (`readiness_automated`, `mock_submission_started`, and `mock_submission_completed`). The filter is functional, not decorative.

## 28. API audit

Operational source and the fresh production bundle were searched for:

- `/api/cases`
- `/api/clients`
- `/api/audit`
- `/api/reviewers`
- `/api/policy`
- `/assign`
- `/return-for-rework`
- `/resubmit`

Zero prohibited operational references were found. The fresh bundle referenced supported `/api/clm/zero-touch/cases`, `/api/onboarding/cases/...`, `/api/system/execution-profile`, and explicitly demo-prefixed routes. Runtime logs showed only routes registered by the synchronized `origin/main`-authoritative backend. Unsupported endpoint calls: **0**.

## 29. Runtime mock audit

Production runtime inspection found:

- operational frontend mock fallbacks: **0**;
- frontend-created successful business outcomes: **0**;
- fake reviewer/client/audit/risk/policy records: **0**;
- fake successful actions: **0**.

The UI uses backend-supplied Mock connector outputs and labels them clearly. Demo endpoints are gated behind explicit demo controls and retain `/api/demo/...` routing. Ordinary runtime failures remain failures; no frontend success substitution was found.

## 30. Dead-control audit

Visible controls were classified as backend functions, local presentation functions, or truthfully disabled unsupported functions. Representative checks included navigation, filters, search, row/open actions, operator disclosure, audit filters, dialog Cancel, disabled review mutations, disabled export/start-review, and disabled risk filtering.

No enabled control was observed doing nothing or issuing an invented request. Dead enabled controls: **0**.

## 31. Frontend verification

Fresh frontend results:

- `npm ls --all`: **PASS**; only expected unmet optional peer/dependency entries were reported;
- `npm run typecheck`: **PASS**;
- `npm test`: **PASS — 95 tests** across 2 files (37 UI V2 integration, 58 App);
- `npm run build`: **PASS — 42 modules transformed**.

The sandbox initially denied child-process spawn for Vitest/Vite with `EPERM`; the same commands were rerun with permitted execution and passed. The production build output was directed outside the repository. Frontend failures: **0**.

## 32. Backend full run #1

First consecutive full-suite run:

`711 passed, 11 skipped, 4 warnings in 19.07s`

Result: **PASS**.

`PHASE12_MONGO_URI` was absent, so the 11 real-Mongo skips were expected and acceptable for this local gate.

## 33. Backend full run #2

Second consecutive full-suite run:

`1 failed, 710 passed, 11 skipped, 4 warnings in 19.17s`

Failed test:

`apps/backend/tests/test_pre_phase12_workspace_multidoc.py::test_repository_listing_is_empty_ordered_and_defensively_copied`

The test creates two cases consecutively and requires the second-created case before the first. `InMemoryZeroTouchAutomationRepository.list_records()` sorts descending by `(updated_at, str(case_id))`. When timestamps tie at the available clock resolution, the UUID string — unrelated to creation order — becomes the deciding key and can invert the expected order. This is consistent with the historical intermittent failure and the fresh recurrence.

Result: **FAIL**. The required two consecutive full-suite passes were not achieved.

## 34. Ordering test 10-run result

After the full-suite recurrence, the exact ordering test was run in isolation 10 consecutive times.

- passes: **10**
- failures: **0**
- result: **10/10 pass**

The isolated result does not erase the failure in full run #2. The issue is intermittent and remains reproducible under the required full-suite sequence.

## 35. Phase regressions

Fresh targeted phase results:

- Phase 09: **39 passed**
- Phase 10: **52 passed**
- Phase 11: **58 passed**
- Pre-Phase 12: **31 passed**
- Phase 12: **16 passed, 11 skipped**

The 11 Phase 12 skips were the expected real-Mongo tests with `PHASE12_MONGO_URI` absent. No targeted phase regression was found; the intermittent ordering failure is recorded separately as a full-suite stability failure.

## 36. Contracts/security/static checks

Fresh results:

- contract tests: **44 passed**;
- security/integration-security target: **200 passed**, with 3 expected warnings;
- GoldTier focused unit tests: **5 passed**;
- GoldTier validator: **19 VALID, 19 INVALID / QUARANTINED, 48 NOT VALIDATED**;
- Ruff: **PASS**;
- strict mypy: **PASS across 73 source files**;
- `pip check`: **PASS**;
- standalone secret scan and scanner tests: **PASS**.

Contract regressions: **0**.

## 37. Windows/browser lifecycle

A supported lifecycle session already existed before this gate:

- session: `5fe258f1-0fbc-4ef5-a812-ce1da48e13da`
- metadata status: `RUNNING`
- backend: recorded launcher/listener on port 8000;
- frontend: recorded launcher/listener on port 5173.

The gate reused this existing session, confirmed frontend-to-backend requests, and did not start a competing process. Both recorded launcher processes and the recorded backend listener still existed with matching executable paths and sub-millisecond raw creation-time differences; `http://127.0.0.1:8000/health` and `http://127.0.0.1:5173/` both returned 200.

However, the supported final status action exited **1** and reported:

- `backend: PID 27596 - MISMATCH`
- `frontend: PID 33808 - MISMATCH`

Root-cause inspection showed that `ConvertFrom-Json` deserializes `creation_time_utc` as a UTC `System.DateTime`, but `[string]$Record.creation_time_utc` drops the `Z`. `Test-SameCreationTime` then parses that zone-less value as Asia/Singapore local time and shifts it by eight hours, so the ownership check fails despite live matching processes. Because the same conversion path applies to listener timestamps, a verified stop is not safely demonstrable. The pre-existing session was therefore left untouched. Gate-created browser tabs were closed and the temporary viewport override was reset. This is a lifecycle regression finding, not an unrelated port conflict.

## 38. Git hygiene

Final hygiene checks confirmed:

- no implementation, frontend, backend, test, security, scanner, or dependency file was changed by this gate;
- no staged changes;
- `git diff --check` passed apart from pre-existing mixed-EOL warnings;
- `git diff --cached --check` passed;
- scanner files retained zero material diff;
- no temporary scanner probe or screenshot file exists in the repository;
- the build output and browser artifacts were outside the repository;
- no generated dependency tree or credential file was added;
- the unrelated strange filename and inaccessible pytest caches were untouched.

The only repository file created by this gate is `.ai-pipeline/reports/UI_V2_FINAL_REQUALITY_GATE.md`.

## 39. Findings

### HIGH — RQG-01 — Onboarded table expands the document at responsive widths

**Evidence:** Onboarded measured 1044/1009 at 1024, 1034/745 at 760, and 1030/465 at 480. At 480 the page itself gained approximately 565 pixels of overflow. The table wrapper has `overflow-x: auto`, but the document still expands; the issue was visible as a page-level scrollbar and materially clipped layout.

**Impact:** The Onboarded page is not practically usable as a normal mobile-width page and violates the explicit document-containment gate.

**Canonical remediation owner:** frontend responsive layout/table containment. The wide table may remain internally scrollable, but its page/flex ancestor must be allowed to shrink without changing the screenshot-authoritative desktop layout.

### MEDIUM — RQG-02 — Backend case-list ordering remains intermittent

**Evidence:** full backend run #2 failed `test_repository_listing_is_empty_ordered_and_defensively_copied`; full run #1 and 10 isolated reruns passed. The in-memory repository uses UUID text as the tie-breaker after `updated_at`, while the asserted contract is second-created/newest first.

**Impact:** required backend stability evidence is not reproducible; cases created within the same timestamp resolution can appear in an order unrelated to creation order.

**Canonical remediation owner:** backend repository ordering contract. Triage should establish a deterministic sequence/timestamp tie-breaker consistently across in-memory and durable persistence without modifying UI behavior.

### MEDIUM — RQG-03 — Windows lifecycle UTC ownership check fails outside UTC

**Evidence:** `scripts/demo_lifecycle.ps1 -Action Status` exited 1 and marked both live recorded roles `MISMATCH`. The stored timestamp is `2026-09-02T09:37:01...Z`; after `ConvertFrom-Json`, casting the UTC `DateTime` to string produces a zone-less `09/02/2026 09:37:01`. The comparison reparses it as +08:00 local time, producing an approximately 28,800,000 ms difference. Both health endpoints still returned 200 and executable paths matched.

**Impact:** the supported lifecycle cannot reliably establish ownership or demonstrate a safe clean stop in the project's Asia/Singapore environment. Runtime metadata is retained and processes can be stranded behind fail-closed ownership checks.

**Canonical remediation owner:** Windows lifecycle timestamp serialization/comparison. Preserve UTC kind/offset through comparison and cover a non-UTC timezone without weakening PID-reuse protections.

No Critical or Low finding was recorded.

## 40. Remaining limitations

- The in-app browser file chooser timed out during direct physical upload attempts. Runtime intake was therefore exercised against the same synchronized backend with real repository PDF fixtures and corroborated by backend request logs; file-selection presentation and retry bindings were covered by the 95-test frontend suite and source review.
- Eleven real-Mongo tests were skipped because `PHASE12_MONGO_URI` was absent. This was verified and reported, not treated as a pass against a real Mongo service.
- The existing lifecycle session was left running because the supported ownership check returned `MISMATCH`; invoking Stop would have been unsafe and contrary to the review-only, do-not-disrupt constraint.
- Local backend state is process-local in this execution profile and the test-created cases are non-production Mock/POC data.

None of these limitations changes the two reproduced defects or the FAIL verdict.

## 41. Final metrics

| Metric | Count |
|---|---:|
| Critical findings | 0 |
| High findings | 1 |
| Medium findings | 2 |
| Merge/history anomalies | 0 |
| Backend/security divergence from origin/main | 0 |
| Unresolved F-01 findings | 0 |
| Unresolved F-02 findings | 0 |
| Unresolved F-03 findings | 0 |
| Unresolved F-04 findings | 0 |
| Unresolved F-05 findings | 0 |
| Registry-stop compatibility failures | 0 |
| Impossible retry paths | 0 |
| Stale progress states | 0 |
| Misleading registry status icons | 0 |
| Unclassified Policy values | 0 |
| Security scanner weakening | 0 |
| Scanner bypasses | 0 |
| Secret-detection regressions | 0 |
| Secret scan failures | 0 |
| Missing screenshot-defined elements | 0 |
| Material screenshot-defined visual differences | 1 |
| Old-main visual leakage | 0 |
| Material responsive overflow defects | 1 |
| Frontend operational mock fallbacks | 0 |
| Fake successful actions | 0 |
| Dead enabled controls | 0 |
| Unsupported endpoint calls | 0 |
| Frontend failures | 0 |
| Backend full-suite failures | 1 |
| Ordering-test failures across 10 reruns | 0 |
| Contract regressions | 0 |

Every metric must be zero for PASS. Three required final-zero metrics are nonzero, and one High finding exists.

## 42. Final verdict

The synchronized integration is **not ready to push**. Synchronization, security parity, scanner behavior, F-01 through F-05, frontend verification, API truthfulness, normal intake, and targeted phase/contract/static checks pass. Approval is blocked by the HIGH Onboarded responsive overflow, the failed second full backend run demonstrating that the historical ordering instability remains reproducible, and the supported Windows lifecycle's failed ownership check in the project timezone. This independent gate made no remediation.

FAIL — UI V2 INTEGRATION REQUIRES REMEDIATION
