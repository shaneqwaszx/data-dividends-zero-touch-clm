# UI V2 Final Independent Quality Gate

**Gate date:** 2 September 2026
**Gate role:** Independent final quality gate
**Scope:** Uncommitted UI V2 integration on `integration/ui-v2-finalization`
**Result:** **FAIL — remediation required**

## 1. Executive summary

The UI V2 integration is substantially implemented and is much stronger than a visual-only prototype. The operational production bundle uses the current backend APIs, the tested straight-through and review-required workflows preserve backend truth, responsive layouts avoid document-level horizontal overflow, and the current and latest-main automated suites pass.

The gate nevertheless fails because two High-severity defects remain:

1. A registry-stage stop created by the latest-main backend is retained correctly by the backend but is not transitioned to the Registry unavailable UI during new onboarding. The user remains on the intake page and is told to retry a document intake operation that cannot be accepted for that case state.
2. The modified secret scanner treats any sensitive assignment whose right-hand side begins with a small set of conversion calls as safe. An independent adversarial probe demonstrated that a conversion-wrapped literal secret is not detected. This is a scanner weakening, a bypass, and a secret-detection regression.

Three Medium findings also remain: stale processing state after starting a new case, success checkmarks on registry conflict/not-selected states, and incomplete explicit REAL/DERIVED/PENDING/UNAVAILABLE classification on the Policy page.

No implementation fixes were made during this review. This report is the only repository file created by the gate.

## 2. Reviewed branch/worktree

- Repository: `data-dividends-zero-touch-clm`
- Worktree: `C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm`
- Branch: `integration/ui-v2-finalization`
- Reviewed HEAD: `b196d887964f0d93b93dfd2d39c271195eb19af9`
- Review mode: unstaged/uncommitted integration worktree; no commit, push, merge, rebase, reset, clean, or implementation edit was performed.

## 3. Working-tree state

The worktree was intentionally dirty before the gate. Modified and untracked UI V2 integration files were reviewed in place. Nothing was staged. A pre-existing unrelated untracked file whose name begins `e workspace and multi-document intake` was not opened, changed, removed, or included in the integration assessment.

The repository emitted access warnings for pre-existing pytest cache directories during status checks. Those directories were not modified. A pre-existing demo lifecycle session remained active on ports 8000 and 5173 and was not stopped or altered.

## 4. origin/main SHA

- `origin/main`: `74a5fd2f8bc8a37c02a24dadaaa32a895ce2ee93`
- Subject: `fix: defer speculative ACRA OAuth handling (#21)`
- Commit date: `2026-09-01T23:54:14+08:00`

The remote reference was fetched immediately before review. Latest-main tests and runtime checks used the detached latest-main worktree, not the older integration base.

## 5. origin/ui-edits-v2 SHA

- `origin/ui-edits-v2`: `be6bf3fa6dc3f15230d196f0d9c84cf9ccc66814`
- Subject: `ui edits v2`

This reference was treated as the implementation/design baseline below the supplied screenshots and below current sponsor/project decisions.

## 6. Diff inventory

### Frontend implementation

- Modified: `apps/frontend/src/App.tsx`, `apps/frontend/src/api.ts`, `apps/frontend/src/main.tsx`, `apps/frontend/src/types.ts`, `apps/frontend/vite.config.ts`
- Added: `apps/frontend/src/design-system.css`, `apps/frontend/src/shared.ts`, `apps/frontend/src/viewModels.ts`
- Added pages/components: `AssignReviewerDialog.tsx`, `AuditTrail.tsx`, `CaseDetail.tsx`, `CaseQueue.tsx`, `CaseStatePanels.tsx`, `ClientDetail.tsx`, `HomeOnboarding.tsx`, `OnboardedClients.tsx`, `PolicyRules.tsx`, `ReturnForReworkDialog.tsx`

### Frontend tests

- Modified: `apps/frontend/src/App.test.tsx`
- Added: `apps/frontend/src/UiV2Integration.test.tsx`

### Security tooling and tests

- Modified: `scripts/check_secrets.py`
- Modified: `tests/test_check_secrets.py`

### Integration documentation present in the worktree

- `.ai-pipeline/reports/UI_V2_BACKEND_INTEGRATION_V2.md`
- `.ai-pipeline/reports/UI_V2_FINAL_IMPLEMENTATION.md`
- `.ai-pipeline/reports/UI_V2_LATEST_MAIN_PARITY_REMEDIATION.md`
- `.ai-pipeline/reports/UI_V2_SCREEN_FUNCTION_CONTRACT.md`

### Backend implementation

No backend implementation, service, domain, connector, or API source files are changed by this integration.

Tracked diff statistics before this report were 428 insertions and 1,281 deletions across six files; untracked files are not represented in that statistic.

## 7. Screenshot inventory

Ten supplied screenshots were treated as the highest visual authority. They depict an approximately 1024-pixel application canvas inside a dark browser/artboard frame and collectively define these states:

1. `photo_2026-09-01_17-53-33.jpg` — Registry unavailable: outage summary, retry attempts, cached snapshot, stale-field provenance, policy card, Retry now and Continue actions.
2. `photo_2026-09-01_17-53-31.jpg` — Registry extract and verify: vertical progress, reconciliation card, registry-unavailable escape and Review and confirm action.
3. `photo_2026-08-31_22-13-21.jpg` — New onboarding: jurisdiction/registration fields, multi-document upload rows, progress/removal controls, primary/cancel actions.
4. `photo_2026-08-31_22-13-21 (2).jpg` — Confirm details: provenance-labelled corporate fields, reconciliation chips, relationship input, and open-item panel.
5. `photo_2026-08-31_22-13-22.jpg` — Audit trail: event filters, timestamp/action/actor/change/loop table, Export CSV.
6. `photo_2026-09-01_17-53-20.jpg` — Client record: client summary, documents, corporate particulars, onboarding record, completion checks, export/review actions.
7. `photo_2026-09-01_17-53-16.jpg` — Onboarded list: jurisdiction/risk/search controls, client rows, dates, Open actions.
8. `photo_2026-09-01_17-53-14.jpg` — Completed: four-stage record, client record card, Onboarded and audit actions.
9. `photo_2026-09-01_17-53-10.jpg` — Pipeline re-run: loop history, stage rail, re-run comparison, loop metadata and completion control.
10. `photo_2026-09-01_17-53-05.jpg` — Corrections and resubmit: corrections table and resubmission dialog with restart/re-run/reviewer/loop details.

Australia/ASIC content in the prototype screenshots was not treated as a business requirement because current project authority limits the live POC registry to Singapore ACRA. Truthful ACRA/mock/unsupported-jurisdiction labels therefore are not unapproved visual changes.

## 8. Review methodology

The assessment combined:

- governing project context, decision logs, open questions, security boundaries, architecture, API handoff, and prior quality-gate reports;
- complete working-tree inventory and source/diff inspection;
- screenshot-by-screenshot component and state comparison;
- production-bundle endpoint and mock-fallback audit;
- isolated runtime against the latest `origin/main` backend;
- browser exercise of straight-through, low-confidence, registry-stop, list, detail, completed, client, audit, policy, unavailable-backend, keyboard, dialog, and responsive paths;
- current-worktree and latest-main backend tests, frontend tests/build/type checks, contract checks, lint/type checks, package checks, GoldTier validation, scanner tests, standalone scanner, and an independent adversarial scanner probe;
- final status, staged-state, diff-whitespace, listener, and process-lifecycle checks.

Source authority was applied in this order: supplied screenshots for visual intent; direct sponsor/project decisions for business truth; corrected contracts and latest main for API behavior; `origin/ui-edits-v2` for design implementation context; then the integrated worktree. Observed runtime behavior overrides claims in implementation reports.

## 9. Global shell

The integrated shell materially matches the supplied design language: Autoboard wordmark, restrained serif typography, thin rules, warm neutral palette, compact navigation, active gold underline, content-width discipline, and a top-right operator control.

Navigation labels are exactly New onboarding, Cases, Onboarded, Audit, and Policy. Active state, hierarchy, focus styling, and responsive wrapping were observed. No legacy dashboard navigation or unsupported production feature was exposed in the operational runtime.

## 10. Account/operator

The account disclosure truthfully identifies a local POC operator and states that authentication is not connected. It does not fabricate identity management, reviewer authority, sign-out, or a production session. Mutation controls that would imply connected identity/reviewer services remain absent or disabled.

Result: **PASS**.

## 11. Design-system parity

The design-system stylesheet consistently supplies the screenshot family’s typography, borders, cards, tables, status chips, controls, overlays, spacing, and focus treatments. The implementation is visually coherent across pages and viewports.

Material parity exceptions are recorded in Findings: the missing immediate registry-unavailable transition and misleading checkmarks on registry conflict/not-selected progress items. Extra truthful detail on completed/client screens is acceptable functional enrichment rather than old-main leakage.

Result: **PASS WITH FINDINGS**.

## 12. New onboarding

The page supports jurisdiction selection, registration identifier entry, multi-document selection, per-document listing/removal, accepted-type guidance, and a single create-and-process action. Uploads use actual backend document intake and preserve backend errors. Unsupported jurisdictions are not presented as live registry integrations.

The straight-through workflow successfully created a case, uploaded a real repository fixture, completed the backend workflow, and displayed a truthful Mock GoldTier party ID plus a prominent mock-completion caveat. It did not claim production onboarding or Ready-for-Approval.

Two defects affect this page: registry-stage stop routing is broken, and Start a new case leaves stale processing text visible. See Findings F-01 and F-03.

Result: **FAIL**.

## 13. Registry progress

The UI represents registry progress, unavailable/conflict states, jurisdiction, registry routing, provider/result details, and links into the case state. It derives these from actual case and timeline data rather than timers or browser storage.

However, fixed jurisdiction/registry progress rows inherit the stylesheet’s default checkmark even when their text is `Jurisdiction Conflict` or `Registry Route Not Selected`. This undermines non-colour status communication and conflicts with the screenshot’s attention-state language. See F-04.

Result: **PASS WITH FINDING**.

## 14. Registry unavailable

The Case Detail implementation contains a truthful Registry unavailable/conflict panel and displays backend-supplied registry routing state without inventing cached snapshots, retry attempts, or policy allowances that latest main does not provide.

The required transition from new onboarding does not work. In the exercised jurisdiction-conflict case, case creation returned 201 and retained the case, document intake returned 409 because intake was not open, and the UI remained on Start onboarding with `Targeted retry required`. Repeating the enabled create action cannot advance that retained case. The Registry unavailable screen was reachable only by manually navigating through Cases.

Result: **FAIL — High finding F-01**.

## 15. Confirm details

The low-confidence path rendered Confirm details with backend-derived required fields, separate registry/document observations, confidence and validity, source/provenance disclosure, match/unverifiable outcomes, and no invented resolution action. In the exercised case it showed three matches and one unverifiable item.

The page does not permit unsupported direct data mutation. Review and return controls open informational dialogs whose unavailable mutations are disabled.

Result: **PASS**.

## 16. Cases

The Cases page uses the real collection endpoint and enriches rows only with bounded detail calls. Status, jurisdiction, and search controls work; keyboard Enter opens a row. The table becomes an internally scrollable region at narrow widths rather than expanding the document.

No fake pagination, reviewer, risk, or unsupported backend state is introduced.

Result: **PASS**.

## 17. Case Detail

Case Detail renders backend stage/timeline/document/ownership/target-operation truth, including waiting-for-review, completed, registry conflict, and retry/replacement contexts. It does not calculate UBO/source authority in the client. It exposes no speculative reviewer, return, or resubmit endpoint.

The registry conflict display is truthful once reached, subject to the progress-icon issue in F-04.

Result: **PASS WITH FINDING**.

## 18. Document interruption

Source and tests preserve case identity during document interruption and use the latest-main retry/replacement operations. The integration does not offer a generic reset or speculative resubmit mutation. Backend regression tests cover duplicate/stale/replacement/retry and recovery behavior.

No contradiction was found between UI action availability and the latest-main recovery contract, except the earlier registry-stage stop transition described in F-01.

Result: **PASS**.

## 19. Review dialogs

Assign reviewer and Return for rework dialogs are semantic modal dialogs with labelled fields, visible focus handling, safe dimensions, and explicit unavailable-state messaging. Final mutation actions are disabled because latest main has no corresponding API; Cancel remains functional. Runtime logs confirmed that opening and using these dialogs made no speculative endpoint calls.

Result: **PASS**.

## 20. Corrections/recovery

The integration maps actual timeline/document recovery evidence into correction and re-run views. It avoids claiming the screenshot prototype’s reviewer notifications, loop mechanics, or automatic stage reset where those capabilities are not supplied by latest main. The real recovery APIs and state transitions are covered by backend and integration tests.

Result: **PASS**.

## 21. Completed

The exercised straight-through case completed through the backend and displayed the four-stage record, elapsed time, human touches, target operations, documents, corporate data, and a truthful mock-party identifier. Mock completion is explicitly distinguished from production onboarding and Ready-for-Approval.

Result: **PASS**.

## 22. Onboarded

Only completed cases are listed. Jurisdiction and search work; unsupported risk and scheduling data are shown as unavailable rather than fabricated, and the risk filter is disabled. Rows use real detail enrichment and open the corresponding client record by mouse or keyboard.

Result: **PASS**.

## 23. Client record

The client record safely presents actual entity, registry, document, director, ownership-candidate, target-operation, and timeline data. Export record and Start review are disabled because no supported API exists. No production client ID, risk rating, review schedule, or screening result is fabricated.

Result: **PASS**.

## 24. Audit

The Audit page uses the real case timeline. In the exercised case, all 12 events appeared, and semantic filters produced the expected target and document subsets. Unavailable actor and loop data remain `—`; Export CSV is disabled rather than faked.

Result: **PASS**.

## 25. Policy

The Policy page is read-only, records open sponsor questions such as Q-012 and Q-015, and labels provisional/pending/unavailable content. It does not permit edits or present unresolved rules as sponsor-confirmed.

It does not, however, consistently expose the required explicit value classifications `REAL`, `DERIVED`, `PENDING SPONSOR CONFIRMATION`, and `UNAVAILABLE`. Browser inspection found no REAL or DERIVED classifications and only prose-equivalent pending language. See F-05.

Result: **PASS WITH FINDING**.

## 26. Responsive QA

Browser checks were performed at 1280, 1024, 760, and 480 CSS pixels.

- No document-level horizontal overflow occurred.
- The global navigation wraps deliberately at narrower widths.
- The 480-pixel shell retains account access while reducing the environment label.
- Wide tables use contained horizontal scrolling; at 480 pixels, the Cases table measured approximately 980 pixels inside a 451-pixel scroll container while the document remained 480 pixels wide.
- Review dialogs fit within the 480-by-760 viewport; the measured dialog was approximately 445 by 547 pixels.
- Cards and primary actions remain readable and operable at all tested sizes.

Result: **PASS**.

## 27. Accessibility

The integration uses semantic `main`, navigation, headings, tables, labels, buttons, and modal-dialog roles. Focus-visible styling is present, table rows are keyboard operable, disabled actions use native disabled semantics, and most status information is communicated by text as well as colour.

The registry conflict/not-selected checkmarks are an accessibility regression because the non-colour icon cue says success while the text says attention or absence. See F-04.

Result: **PASS WITH FINDING**.

## 28. API audit

The production bundle contains calls only to registered latest-main routes under:

- `/api/clm/zero-touch/...`
- `/api/demo`
- `/api/onboarding/cases/{id}/documents`
- ownership endpoints
- `/api/system/execution-profile`

No operational bundle call was found for speculative `/api/reviewers`, assign, return-for-rework, resubmit, clients, audit, or policy endpoints. Legacy helpers remain in source but are tree-shaken from the production operational bundle.

- Unsupported endpoint calls: **0**
- Missing runtime endpoint registrations: **0**

Result: **PASS**.

## 29. Runtime mock audit

No `mockData`, localStorage, sessionStorage, or operational client-side mock fallback appears in the production bundle. The demo uses the backend’s explicit demo controls and labels resulting target operations as mock. Foreign/unsupported cases do not masquerade as live ACRA results.

- Frontend operational mock fallbacks: **0**
- Fake successful actions: **0**

Result: **PASS**.

## 30. Error handling

With the isolated backend unavailable, a Cases request produced the safe user-facing message `Application API request failed (500).` No raw response body, stack trace, credential, or internal exception was projected. The frontend does not silently replace failed API calls with fixture data or success.

Backend tests cover validation errors, stale conflicts, technical 500/503 responses, retry, replacement, recovery, and state conflicts. The registry-stop error is safe but its UX transition is incorrect, as described in F-01.

Result: **PASS WITH FINDING**.

## 31. Latest-main compatibility

The frontend was run against an isolated backend from the fetched `origin/main` SHA. Straight-through and low-confidence workflows, lists, exact details, documents, ownership, target operations, timeline, and execution-profile calls were exercised successfully.

The registry-stage stop exposed one compatibility failure: latest main can retain a non-intake case immediately after creation, while the integrated onboarding controller assumes it can always proceed to document intake before storing/navigating to the returned case summary.

- Latest-main compatibility failures: **1**
- Missing latest-main user-facing functionality: **1**

Result: **FAIL — High finding F-01**.

## 32. Security-tooling review

The scanner change in `scripts/check_secrets.py` adds a broad right-hand-side prefix exemption for sensitive Python assignments beginning with `str(`, `bytes(`, `float(`, `int(`, or `bool(`. The exemption is broader than the narrow false-positive condition it intends to solve.

The scanner’s own six tests pass, and the standalone scan reports success. An independent temporary-fixture probe also confirmed detection of ordinary literal client-secret, access-token, bearer-token, API-key, and JKS cases, plus acceptance of safe annotations and token conversions. Critically, the same probe demonstrated that a sensitive assignment containing a literal secret wrapped in a conversion call is not detected.

The standalone green scan is therefore not sufficient evidence of scanner integrity.

- Scanner weakenings: **1**
- Scanner bypasses: **1**
- Secret-detection regressions: **1**

Result: **FAIL — High finding F-02**.

## 33. Security review

No new credential, token, certificate, private key, confidential sponsor artifact, or raw KYC/PII logging was found in the reviewed UI integration. The frontend masks document numbers, avoids raw backend bodies, keeps mock/live status explicit, and does not create a new authorization boundary. No speculative privileged mutation endpoint is invoked.

Security is not approved overall because the committed scanner behavior would allow a reproducible false negative. The finding concerns defensive tooling; no actual secret was found in the UI V2 files.

Result: **FAIL due to F-02**.

## 34. Frontend verification

| Check | Result |
|---|---|
| `npm ls --all` | PASS; only expected optional platform-package notices |
| `npm run typecheck` | PASS |
| Vitest | PASS — 84 tests across 2 files (58 + 26) |
| Production build | PASS — 42 modules; CSS 54.02 kB; JS 228.38 kB |
| Production bundle endpoint/mock audit | PASS with 0 unsupported calls and 0 operational mock fallbacks |
| Latest-main isolated browser workflow | PASS WITH HIGH FINDING F-01 |
| Responsive browser QA | PASS |

The build and Vitest initially encountered a Windows sandbox `spawn EPERM`; each was rerun with the required execution permission and then passed. This was an execution-environment constraint, not a product failure.

## 35. Backend verification

### Current worktree

| Check | Result |
|---|---|
| Phase 09 targeted suite | PASS — 39 |
| Phase 10 targeted suite | PASS — 52 |
| Phase 11 reconciliation/remediation | PASS — 58 |
| Pre-12 + Phase 12 + real-Mongo suite | PASS — 47 passed, 11 skipped |
| Full backend suite | PASS |
| Contract suite | PASS — 44 |
| Ruff | PASS |
| Strict mypy | PASS — 73 source files |
| `pip check` | PASS |
| GoldTier validator unit suite | PASS — 5 |
| GoldTier examples | 19 valid; 19 invalid/quarantined; 48 not validated |

### Fetched latest main

| Check | Result |
|---|---|
| Full backend suite with detached-main `PYTHONPATH` | PASS — 711 passed, 11 skipped, 4 warnings |
| Contract suite | PASS — 44 |
| Ruff `--no-cache` | PASS |
| Strict mypy with isolated cache | PASS — 73 source files |
| `pip check` | PASS |

The first detached-main run accidentally imported the editable current-worktree backend. Module-path inspection identified the contamination, and the run was repeated with an absolute detached-main `PYTHONPATH`; only the corrected 711/11 result is used for the gate. Real-Mongo tests were skipped because `PHASE12_MONGO_URI` was not supplied, in accordance with their configured conditional behavior.

- Backend regressions: **0**
- Contract regressions: **0**

## 36. Windows/browser lifecycle

The repository’s pre-existing lifecycle session remained active on backend port 8000 and frontend port 5173. It was not adopted or terminated by this gate.

Review servers were isolated on 8001 and 5175. They were stopped after browser QA. Final listener checks confirmed 8001 and 5175 closed while the pre-existing 8000 and 5173 listeners remained active. No orphaned gate-owned browser/backend/frontend process was left running.

Result: **PASS**.

## 37. Git hygiene

- No stage, commit, push, merge, rebase, reset, checkout-revert, or clean operation was performed.
- `git diff --check`: PASS.
- `git diff --cached --check`: PASS; nothing staged.
- Existing unrelated and inaccessible files were preserved.
- The only file created by this gate is `.ai-pipeline/reports/UI_V2_FINAL_QUALITY_GATE.md`.

Result: **PASS**.

## 38. Visual parity matrix

| Screenshot state | Integrated representation | Functional truth | Verdict |
|---|---|---|---|
| New onboarding | Jurisdiction, identifier, multi-document intake, progress/removal and create action | Real create/intake/complete calls | PASS WITH F-03 |
| Registry extract & verify | Registry progress and backend state represented in Case Detail | Real detail/timeline data | PASS WITH F-04 |
| Registry unavailable | Component exists and is truthful once opened through Cases | Backend retains registry-stop case | **FAIL: direct transition missing (F-01)** |
| Confirm details | Provenance, observations, confidence/validity, unmatched state | Real low-confidence case data | PASS |
| Cases | Filters, search, table, keyboard navigation | Real collection/detail data | PASS |
| Case detail / pipeline | Stage rail, timeline, documents, target/ownership state | Real workflow state; no fake loops | PASS WITH F-04 |
| Review dialogs | Modal structure and unavailable-state controls | Speculative mutations disabled | PASS |
| Corrections/resubmit | Actual recovery/replacement evidence; no invented reviewer mutation | Real latest-main recovery operations | PASS |
| Completed | Stage record, mock completion, client summary | Real backend completion; mock clearly labelled | PASS |
| Onboarded | Completed-only list and detail navigation | Real completed cases | PASS |
| Client record | Corporate, document, ownership, target and timeline sections | Real detail data; unsupported actions disabled | PASS |
| Audit | Filters and event table | Real timeline; export disabled | PASS |
| Policy | Read-only policy/open-question presentation | No invented decisions | PASS WITH F-05 |

Prototype Australia/ASIC labels, reviewer identities, risk values, schedules, cached-snapshot policy, CSV/export behavior, and production client IDs were deliberately not copied where latest main or sponsor authority does not support them. Those are truthful differences, not parity failures.

## 39. Bidirectional functional parity

### Screenshot-to-implementation

All major screenshot families have corresponding integrated pages or components. Their principal information architecture, controls, tables, dialogs, state hierarchy, and restrained design system are represented. The one missing point-of-flow state is the immediate Registry unavailable transition after a registry-stage stop.

### Implementation-to-latest-main

Every operational network call in the production bundle maps to a registered latest-main route. Collections and details derive from backend state; mock completion is labelled; unavailable mutations remain disabled; ownership and source authority are displayed rather than recomputed; and technical errors are safely projected.

The new-onboarding controller is not bidirectionally compatible with a case that latest main retains before document intake opens. That creates the sole runtime API/state-machine compatibility failure.

Result: **FAIL due to F-01**.

## 40. Findings

### F-01 — High — Registry-stage stop is stranded on New onboarding

**Evidence:** `apps/frontend/src/App.tsx` creates a local case summary and immediately performs document intake. It stores the summary/navigates only after successful completion. In an exercised jurisdiction-conflict case, create returned 201, document intake correctly returned 409, and the UI remained on New onboarding with a retry instruction. The retained case’s Registry unavailable state was visible only after manually opening Cases.

**Impact:** The screenshot-defined Registry unavailable workflow is absent at the exact point it is required; the enabled retry path cannot succeed while intake remains closed; and a latest-main state is not surfaced to the operator. This can strand a case and misdirect the user.

**Required remediation:** Preserve the created summary immediately, route retained pre-intake terminal/attention states to the corresponding case/registry panel, and ensure retry language/actions are state-valid. Add an integration test for create-success followed by intake-not-open/registry-stop behavior.

### F-02 — High — Secret scanner conversion allowlist creates a false-negative path

**Evidence:** `scripts/check_secrets.py` exempts sensitive Python assignments based on broad conversion-call prefixes. An independent temporary fixture proved that ordinary literals are detected while a literal wrapped by an allowed conversion is not. Existing tests cover benign conversions but not the adversarial literal-wrapping case.

**Impact:** A secret can be committed while the scanner and CI report success. This weakens a repository security control and violates the rule that scanner exceptions must be narrower than the protected condition.

**Required remediation:** Parse or narrowly match the intended dynamic-conversion forms without exempting literal-bearing calls, add adversarial regression tests for every allowed conversion prefix, and rerun the full scanner/security suite.

### F-03 — Medium — Start a new case retains stale processing state

**Evidence:** After completing a low-confidence workflow and selecting Start a new case, the intake form reset but `Processing case…` remained visible although no case or upload was active. The reset handler clears summary, documents, identifiers, and errors but not intake progress.

**Impact:** The operator receives a false ongoing-work signal and may avoid starting a legitimate new case.

**Required remediation:** Clear intake progress and any pending-stage presentation in the new-case reset path; add a test covering the transition from terminal/review-required state back to blank intake.

### F-04 — Medium — Registry conflict/not-selected rows display success checkmarks

**Evidence:** Fixed progress list items for jurisdiction and registry route do not supply a non-success state attribute, so the stylesheet’s default `::before` checkmark appears beside `Jurisdiction Conflict` and `Registry Route Not Selected`.

**Impact:** The icon contradicts the text and weakens non-colour status interpretation, visual parity, and accessibility.

**Required remediation:** Bind icon/state styling to actual registry/jurisdiction status and test success, pending, conflict, unavailable, and not-selected variants.

### F-05 — Medium — Policy value classifications are not explicit or complete

**Evidence:** The Policy page contains provisional, pending, and unavailable prose, but browser inspection found no explicit REAL or DERIVED labels and no consistent four-class treatment for policy/runtime values.

**Impact:** Operators cannot reliably distinguish backend facts, UI-derived presentation, sponsor-pending rules, and unavailable data using the required classification vocabulary.

**Required remediation:** Apply the four explicit classifications consistently to applicable policy/value rows without upgrading unresolved decisions to confirmed rules.

## 41. Remaining limitations

- Real-Mongo checks were not run because `PHASE12_MONGO_URI` was absent; 11 tests were skipped by design.
- Browser QA used the latest-main mock/demo execution profile, not sponsor ACRA, PingFed, or GoldTier sandboxes.
- Review assignment, return-for-rework mutation, CSV/export, policy editing, risk/scheduling, and production client-review actions remain unavailable because latest main does not expose supporting contracts. The UI correctly disables or omits them.
- The screenshot prototype includes Australia/ASIC and richer reviewer/risk/scheduler data outside current live POC authority; these were assessed for layout and interaction intent only.
- The secret scan currently reports green but cannot be relied upon as final assurance until F-02 is remediated and independently re-probed.

## 42. Final metrics

| Metric | Count |
|---|---:|
| Critical findings | 0 |
| High findings | 2 |
| Medium findings | 3 |
| Missing screenshot-defined UI elements/states | 1 |
| Material visual differences | 2 |
| Unapproved visual changes | 0 |
| Old-main visual leakage | 0 |
| Missing UI-defined functions | 1 |
| Missing latest-main user-facing functionality | 1 |
| Frontend operational mock fallbacks | 0 |
| Fake successful actions | 0 |
| Dead/misleading interactive controls | 1 |
| Unsupported endpoint calls | 0 |
| Latest-main compatibility failures | 1 |
| Scanner weakenings | 1 |
| Scanner bypasses | 1 |
| Secret-detection regressions | 1 |
| Backend regressions | 0 |
| Contract regressions | 0 |

## 43. Final verdict

**FAIL.** The integration is not eligible for final approval while either High finding remains. F-01 blocks a required latest-main registry-stop workflow, and F-02 weakens a security control with a demonstrated false negative. After targeted remediation, the gate should be rerun independently, including the adversarial scanner probe, the registry-stop browser scenario, the stale-reset transition, registry status icons, the explicit Policy classifications, and the full verification matrix above.

FAIL — UI V2 FINAL REMEDIATION REQUIRED
