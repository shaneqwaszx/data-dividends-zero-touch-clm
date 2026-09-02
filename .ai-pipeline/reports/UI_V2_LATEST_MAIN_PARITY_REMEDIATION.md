# UI V2 + Latest Main Parity Remediation

## 1. Executive summary

The frontend now preserves the raw `ui-edits-v2` visual system and component composition while consuming latest-main FastAPI contracts through real adapters and view models. Browser QA against a backend launched from the detached latest-main worktree covered profile discovery, case creation, TXT intake, explicit completion, list/detail, bounded reconciliation, replacement/supersession, recovery without target replay, technical failure, completed/client-record projection, and audit.

All parity metrics are zero. Overall readiness is nevertheless **NOT READY** because latest `origin/main` itself fails the repository secret scan in the only post-base change, the dormant `acra_bizfile_sandbox.py` connector. No credential literal was found, but the guardrail flags its plain `client_secret` and `access_token` assignments. The reference worktree was not modified.

## 2. Integration SHA/state

- Branch: `integration/ui-edits-v2-backend`
- HEAD: `bc51b78bbca0b208a7a17c607eac498dbe6b65af`
- Requested frontend/report changes remain unstaged.
- No stage, commit, push, merge, rebase, reset, or clean was performed.
- Pre-existing inaccessible pytest-cache directories and the unrelated untracked filename beginning `e workspace and multi-document intake` were untouched.

## 3. ui-edits-v2 SHA

`be6bf3fa6dc3f15230d196f0d9c84cf9ccc66814`

Reference: `C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm-ui-baseline` (detached/read-only).

## 4. latest origin/main SHA

`b196d887964f0d93b93dfd2d39c271195eb19af9`

Reference: `C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm-main-baseline` (detached/read-only).

## 5. Three-way comparison method

The pass fetched and resolved all refs; diffed the integration base to latest main; inspected latest routes, DTOs, composition, repositories, configuration, and tests; inventoried the raw UI; compared every PR component and CSS; ran the raw and integrated frontends side by side; routed the integrated dev server to a latest-main backend; and ran frontend, backend, phase, contract, static, dependency, GoldTier, browser, and security checks.

## 6. origin/main drift since integration base

`git diff --name-status bc51b78bbca0b208a7a17c607eac498dbe6b65af..origin/main` reports one addition:

- `apps/backend/app/connectors/acra_bizfile_sandbox.py`

No route, API model, workflow service, persistence service, composition root, test, script, contract, architecture, decision, sponsor-question, or pipeline file changed. The connector is not imported or composed on latest main.

## 7. Main-change impact matrix

| Main change | Backend files | API/DTO impact | Frontend impact | Integrated already? | Action required |
|---|---|---|---|---|---|
| Bizfile Marketplace Mock connector, decoders, optional OAuth authorizer | `apps/backend/app/connectors/acra_bizfile_sandbox.py` | None | NO FRONTEND IMPACT | N/A | Document dormant contract/security limits; invent no UI state |

The connector maps two sample shapes, leaves ownership percentages unset, fails closed for relationships, labels the source `MOCK`, and is explicitly unconfirmed. Its standby token URL validation is less strict than its base URL validation and should be hardened before composition.

## 8. Full latest backend API inventory

| Area | Current latest-main operations | UI mapping / disposition |
|---|---|---|
| System | `GET /health`; `GET /api/system/execution-profile`; `GET /api/onboarding/mock-scenarios` | Health is operations-only; profile is in the existing pill/Policy model; scenarios are demo-gated |
| Onboarding | `POST /api/onboarding/cases`; `GET /api/onboarding/cases/{case_id}` | Retained staged/legacy API support |
| CLM | `POST /api/clm/cases`; `GET /api/clm/cases/{case_id}`; `POST .../readiness/evaluate`; `GET .../submission-plan`; `POST .../submit` | Retained staged CLM/readiness/target support; plan is backend-authored |
| Zero-touch intake | `POST .../{case_id}/intake/documents`; demo equivalent; `POST .../{failed_document_id}/retry`; demo equivalent; `POST .../intake/complete`; demo equivalent | Home independent upload, exact retry, explicit completion; demo variants gated |
| Zero-touch cases | `POST /api/clm/zero-touch/cases`; `GET /api/clm/zero-touch/cases`; demo create; `GET .../{case_id}` | Home create, Cases/Onboarded list, Home/Case/Client/Audit reads |
| Evidence | `GET /api/demo/clm/zero-touch/cases/{case_id}/uat-evidence` | Gated evidence export |
| Documents | Legacy zero-touch attach; replacement; legacy demo attach; onboarding attach/list/exact-read/review; demo attach | Canonical UI uses intake; case/client evidence; exact replacement/version; legacy/demo retained/gated |
| Workflow | `POST .../{case_id}/start`; `POST .../{case_id}/resume` | Start is compatibility/manual; normal UI uses intake-complete; resume is explicit recovery |
| Decisions | exception resolve; reconciliation discrepancy resolve | Only server-advertised actions; version/evidence/fingerprint binding |
| Ownership/UBO | ownership load/demo load/analyze/read; UBO candidates | Server-side deterministic analysis; case/client projection; no client arithmetic |

The exact route set inspected was:

```text
GET  /health
GET  /api/system/execution-profile
GET  /api/onboarding/mock-scenarios
POST /api/onboarding/cases
GET  /api/onboarding/cases/{case_id}
POST /api/clm/cases
GET  /api/clm/cases/{case_id}
POST /api/clm/cases/{case_id}/readiness/evaluate
GET  /api/clm/cases/{case_id}/submission-plan
POST /api/clm/cases/{case_id}/submit
POST /api/clm/zero-touch/cases/{case_id}/intake/documents
POST /api/demo/clm/zero-touch/cases/{case_id}/intake/documents
POST /api/clm/zero-touch/cases/{case_id}/intake/documents/{failed_document_id}/retry
POST /api/demo/clm/zero-touch/cases/{case_id}/intake/documents/{failed_document_id}/retry
POST /api/clm/zero-touch/cases/{case_id}/intake/complete
POST /api/demo/clm/zero-touch/cases/{case_id}/intake/complete
POST /api/clm/zero-touch/cases
GET  /api/clm/zero-touch/cases
POST /api/demo/clm/zero-touch/cases
GET  /api/clm/zero-touch/cases/{case_id}
GET  /api/demo/clm/zero-touch/cases/{case_id}/uat-evidence
POST /api/clm/zero-touch/cases/{case_id}/documents
POST /api/clm/zero-touch/cases/{case_id}/documents/{document_id}/replacement
POST /api/demo/clm/zero-touch/cases/{case_id}/documents
POST /api/clm/zero-touch/cases/{case_id}/start
POST /api/clm/zero-touch/cases/{case_id}/resume
POST /api/clm/zero-touch/cases/{case_id}/exceptions/{exception_id}/resolve
POST /api/clm/zero-touch/cases/{case_id}/reconciliation/discrepancies/{discrepancy_id}/resolve
POST /api/onboarding/cases/{case_id}/ownership/load
POST /api/demo/onboarding/cases/{case_id}/ownership/load
POST /api/onboarding/cases/{case_id}/ownership/analyze
GET  /api/onboarding/cases/{case_id}/ownership
GET  /api/onboarding/cases/{case_id}/ubo-candidates
POST /api/onboarding/cases/{case_id}/documents
GET  /api/onboarding/cases/{case_id}/documents
POST /api/demo/onboarding/cases/{case_id}/documents
GET  /api/onboarding/cases/{case_id}/documents/{document_id}
POST /api/onboarding/cases/{case_id}/documents/{document_id}/reviews
```

## 9. Full UI control inventory

| Screen | Controls / interactions | Classification and mapping |
|---|---|---|
| Global | Home, Cases, Onboarded, Audit, active underline, environment pill | B/C; exact raw order/labels; real profile |
| Start onboarding | Jurisdiction, UEN, drop/browse, folder select, file rows/remove, Create onboarding, Start a new case | A/C; create/intake/complete within raw layout |
| Start progress | Stage rail, status, warnings, failure detail, targeted Retry, recovery action | A/B/C |
| Registry/confirm | acquisition/progress, canonical fields, observations, reconciliation, ownership, unavailable placeholders | B/C; backend data only |
| Cases | status and jurisdiction filters, search, clickable rows | A; real list only |
| Case detail | Back, stage rail, exception actions, dialog launch, retry/replace, reconciliation decisions, resume | A/B/C/D per server support |
| Assign reviewer | reviewer select, note, Cancel, Assign | D; original dialog, disabled mutation, explanation |
| Return for rework | reason, comment, field chips, Cancel, Return for rework | D; original dialog, disabled mutation, explanation |
| Onboarded | jurisdiction/risk filters, search, clickable rows | A/B; completed cases; unsupported values `—` |
| Client record | Back, Audit trail, disabled file download, Export record, disabled Start a review | A/B/D; no fake success |
| Audit | clear case, action chips, disabled Export CSV, real timeline | A/B/D; no fake actor/loop |
| Policy | read-only rules/profile/persistence | B/C; hidden exactly as raw branch; no editing |
| Demo | gated scenario select/run | A; no normal-runtime fallback |

## 10. Master UI ↔ Backend Functional Parity Matrix

| UI screen/control | UI behavior | Latest main capability/endpoint | Result |
|---|---|---|---|
| Global navigation | Raw route switching | Presentation | Exact raw chrome restored; Policy hidden |
| Profile pill | Environment truth | `GET /api/system/execution-profile` | Real and compact |
| Home jurisdiction/UEN | Case identity | `POST /api/clm/zero-touch/cases` | Real |
| Browse/drop/folder | PDF/DOCX/TXT, dedupe, limits | intake document POST | Real |
| Create onboarding | Early create, independent uploads, explicit complete | create/intake/complete | Real; same case survives partial failure |
| Retry failed file | Exact failed-document retry | targeted retry POST | Real |
| Progress | Poll running/resuming only | exact case GET | Real; no invented terminal state |
| Cases filters/search/row | Real list/detail | zero-touch list/read | Real |
| Case pipeline/header | Present current state | exact case projection | Raw structure restored; unavailable loop is `—` |
| Exception decision | Advertised mutation only | exception resolve | Version/evidence-bound |
| Reconciliation | Advertised decision only | reconciliation resolve | Version/fingerprint-bound; 409 refresh |
| Replace/retry | Exact document/event binding | replacement/retry | Real; PDF/DOCX/TXT |
| Recovery | Explicit resume | resume POST | Real; browser never replays target |
| Assignment/rework | Original dialog | No route | Disabled and explained |
| Generic resubmit | Raw richer concept | No route/status | No speculative call |
| Onboarded/client | Completed projection | list/read/documents/ownership | Real with truthful gaps |
| Client export | Download sanitized view model | Presentation | Real; no raw provider payload |
| File download/review | Raw locations | No retained bytes/review route | Disabled and explained |
| Audit timeline/filter | Backend events | case reads | Real; actor/loop `—` |
| Audit CSV | Raw placement | No endpoint | Disabled and explained |
| Policy | Read-only profile/boundaries | profile GET | Real/display-only; Q-012/Q-015 open |
| Demo scenarios | Deterministic runs | `/api/demo/...` | Gated; never fallback |

Every user-relevant route is visible, handled, or deliberately classified as legacy, internal, or gated demo/test behavior.

## 11. Visual baseline

Raw facts verified in source and browser: brand `CLM Onboarding`; visible nav `Home`, `Cases`, `Onboarded`, `Audit`; Policy is a valid hidden tab; Home title `Start onboarding`; and the execution-profile pill is part of the raw nav. The illustrative `Autoboard` / `New onboarding` wording is absent from the raw branch and was not used.

## 12. Global chrome comparison

Brand, tab labels/order, divider, underline, typography, header height, and profile-pill placement match raw. The integration no longer exposes `Audit trail` or `Policy and rules` as top-level tabs.

## 13. CSS comparison

`design-system.css` is byte-for-byte equal to raw. No CSS redesign was introduced; raw responsive rules remain authoritative.

## 14. New onboarding comparison

Raw heading, subtitle, two-card layout, fields, drop zone, rows, and button styling remain. Required functional differences are limited to PDF/DOCX/TXT wording, folder selection, count/byte feedback, and safe retry/recovery. Limits: 20 files, 5 MiB/file, 25 MiB total, with deduplication.

## 15. Registry extract comparison

Existing stage/progress patterns receive current registry acquisition state. Only ACRA Mock/Singapore is presented as implemented. No ASIC behavior, timer, retry schedule, or snapshot policy is invented.

## 16. Registry unavailable comparison

Unavailable/provider-not-implemented state uses raw banner/progress patterns. Missing fields show `—` or `Not available in current POC`; downstream work is not fabricated.

## 17. Confirm details comparison

Canonical identity, observations, reconciliation fields/outcomes, actions, provenance, and ownership flow through selectors into existing PR cards/tables. No old-main reconciliation panel was inserted.

## 18. Cases comparison

Raw table/search/filter composition is preserved. Rows come only from latest-main list data. Actual statuses include `RUNNING`, `WAITING_FOR_REVIEW`, `RECOVERY_PENDING`, `TECHNICAL_FAILURE`, and `COMPLETED`; missing timestamps, assignment, or jurisdiction are not fabricated.

## 19. Case Detail comparison

The raw 260px rail, Back action, stages, divider, loop location, identity header, exception cards, particulars, and directors layout were restored. Latest documents, reconciliation, ownership/UBO, readiness, target state, recovery, technical failure, and timeline use the same PR table/card vocabulary below that structure. Because the latest DTO has no loop count, the retained location truthfully shows `Loop —`.

## 20. Rework/resubmit comparison

Assignment and rework dialogs retain original shape and labels. Submit controls are disabled and explain backend unavailability. No reviewer, rework, or generic resubmit endpoint is called.

## 21. Completed comparison

Completed Mock state is separated from production Ready-for-Approval. Backend completion, target result, ownership, and timeline are shown; production client ID, risk, approval, reviewer, screening, and scheduler values are not invented.

## 22. Onboarded comparison

The raw table uses completed backend cases only. Unsupported client ID, risk, and next-review values are `—`; copy states this is not a production client master/scheduler.

## 23. Client Record comparison

Raw side panel, schedule/document locations, two-column layout, tables, and header actions remain. Identity, registry, documents, directors, ownership paths/candidates, workflow, checks, timing, and timeline are real. Raw download and Start a review are disabled. Export downloads only the sanitized view model.

## 24. Audit comparison

Raw header, filters, columns, and table remain. Entries use backend timeline events. Actor/loop are `—`; CSV export is disabled with an unavailable tooltip.

## 25. Policy comparison

Policy is read-only and maps execution profile/persistence. Unsupported scheduler/RBAC/editing values are unavailable. Q-012 and Q-015 remain OPEN. Its nav item stays hidden because raw explicitly hides it.

## 26. Dialog comparison

Both PR dialogs preserve backdrop, dimensions, fields, buttons, and labels. Unsupported submits retain original labels while disabled, with explanations/tooltips.

## 27. Multi-document parity

Frontend and latest-main tests verify PDF, DOCX, UTF-8 TXT, multiple files, folder input, 20-file/5 MiB/25 MiB limits, dedupe, provenance, explicit complete, partial intake, failed-document metadata, targeted retry, replacement, supersession, and safe media/path handling. Live compatibility exercised TXT and PDF; replacement yielded one current and one superseded document on the same case.

## 28. Reconciliation parity

The UI handles `MATCH`, `MISSING_IN_SOURCE`, `CONFLICT`, `UNVERIFIABLE`, and `INVALID` for all four accepted fields. It binds server versions/fingerprints/actions, refreshes after 409, and performs no client-side source precedence.

## 29. Persistence/recovery parity

Memory/Mongo labels map from profile. Phase 12 tests cover restart reconstruction, interrupted documents, `DOCUMENT_REUPLOAD_REQUIRED`, completed restart, uncertain target work, recovery pending, and explicit resume. Eleven genuine-Mongo tests skipped because `PHASE12_MONGO_URI` is absent. Live recovery changed `RECOVERY_PENDING` to `COMPLETED` while target calls remained exactly `SEARCH,SHELL,POLICY,AMEND`.

## 30. Ownership/UBO parity

Parties, relationships, direct/indirect/effective ownership, paths, threshold, provisional candidates, cycle/incomplete warnings, and provenance are backend projections. There is no client-side calculation or final legal UBO decision.

## 31. Error/failure parity

Tests cover network and 400/409/422/500 without fallback success. Live invalid PDF returned safe 422 `DOCUMENT_STRUCTURE_INVALID`. A deterministic technical failure rendered `TECHNICAL_FAILURE` / `IDP_PROCESSING_FAILED`, zero business exceptions, failed-document Retry, and no target attempts.

## 32. Demo-controls parity

Accepted demo scenarios remain available only with `VITE_DEMO_CONTROLS_ENABLED=true`. Normal runtime does not import `mockData`, call speculative UI endpoints, or use demo routes as fallback.

## 33. Unsupported functionality

Reviewer assignment, return-for-rework, generic resubmit, production screening/approval/risk/scheduler, raw file download, audit CSV, and policy editing have no latest-main route. Original visual locations remain where present, but controls are disabled and explained.

## 34. Old-main visual leakage audit

Rendered routes use PR pages and raw CSS. Latest DTOs flow through `api.ts` and `viewModels.ts`; no historical main panel was inserted. Legacy exported helpers retained for existing tests do not render in the route tree.

## 35. Latest-main compatibility QA

- Backend: latest-main worktree on `127.0.0.1:8010`.
- Integrated UI: `127.0.0.1:5175`, same-origin `/api` proxy to 8010.
- Raw runtime: `127.0.0.1:5174`.
- Exercised: profile, create, intake, complete, list, detail, reconciliation action, replacement/supersession, recovery/resume/no-replay, technical failure, completed/onboarded, client, ownership/UBO, audit.
- No frontend contract mismatch or fallback occurred.

`vite.config.ts` accepts `VITE_BACKEND_PROXY_TARGET` while retaining port 8000 by default, allowing local compatibility tests without enabling permissive backend CORS.

## 36. Frontend tests

| Check | Result |
|---|---|
| `npm.cmd ls --all` | PASS; expected optional platform/feature dependencies only |
| `npm.cmd run typecheck` | PASS |
| `npm.cmd test -- --run` | PASS; 73/73 (58 App + 15 integration) |
| production build to task artifact directory | PASS; 41 modules |
| `git diff --check` | PASS; line-ending warnings only |

Coverage includes raw navigation/pages, adapters, create/intake/complete, formats/folder/limits/dedupe, list/detail, reconciliation/stale 409, replacement/retry binding, ownership, persistence, recovery/technical states, demo gating, unavailable backend, 400/409/422/500, no mock fallback, and disabled unsupported operations.

## 37. Backend regressions

| Latest-main check | Result |
|---|---|
| Full backend | PASS; 706 passed, 11 skipped, 4 warnings |
| Phase 09 + 10 + 11 focused | PASS; 149 passed |
| Pre-Phase 12 + Phase 12 | PASS; 47 passed, 11 live-Mongo skips |
| Contracts | PASS; 44 passed |
| Ruff `--no-cache` | PASS |
| strict mypy with external cache | PASS; 73 source files |
| Secret-scanner unit tests from writable integration copy | PASS; 5/5 |
| GoldTier validator unit tests from writable integration copy | PASS; 5/5 |
| GoldTier `--if-present` | PASS/NOT VALIDATED; sponsor archives absent, no private file read |
| `pip check` | PASS |
| Latest-main repository secret scan | **FAIL**; two matches in the new dormant connector |

Initial read-only-worktree Ruff/mypy/temp-writing test attempts hit expected cache/temp restrictions; cache-free/external-cache and writable-copy reruns separated those environment failures from the genuine scanner finding.

## 38. Security

Frontend review found no raw document storage, local/session business persistence, raw provider payload rendering, secret exposure, unsafe HTML, raw stack trace, client source precedence, client UBO decision, target replay, fake reviewer authority, fake approval, or operational mock fallback.

Latest-main blocker:

- `apps/backend/app/connectors/acra_bizfile_sandbox.py:157` stores `client_secret` as a plain string attribute.
- `apps/backend/app/connectors/acra_bizfile_sandbox.py:213` assigns `access_token` directly.
- The repository scanner flags both as `sensitive-assignment`.
- No literal credential was found and the module is not composed, but the failed guardrail blocks readiness.
- The optional token URL validator should also reject userinfo, query, and fragment before future wiring.

## 39. Files changed

Current unstaged integration output:

- `apps/frontend/src/App.tsx`, `App.test.tsx`, `api.ts`, `main.tsx`, `types.ts`
- `apps/frontend/src/UiV2Integration.test.tsx`, `design-system.css`, `shared.ts`, `viewModels.ts`
- `apps/frontend/src/pages/AssignReviewerDialog.tsx`, `AuditTrail.tsx`, `CaseDetail.tsx`, `CaseQueue.tsx`, `ClientDetail.tsx`, `HomeOnboarding.tsx`, `OnboardedClients.tsx`, `PolicyRules.tsx`, `ReturnForReworkDialog.tsx`
- `apps/frontend/vite.config.ts`
- `.ai-pipeline/reports/UI_V2_BACKEND_INTEGRATION_V2.md`
- `.ai-pipeline/reports/UI_V2_LATEST_MAIN_PARITY_REMEDIATION.md`

No backend file was changed.

## 40. Remaining gaps

No visual or frontend/latest-main compatibility gap remains. Readiness is blocked by latest-main's secret-scan failure. The 11 genuine-Mongo skips are expected until `PHASE12_MONGO_URI` is supplied; non-live recovery coverage passed.

Recommended next step: remediate the connector's secret handling/scanner compatibility on main and harden its optional token URL validation, rerun security checks, then run the independent parity quality gate. Do not update this integration branch against main until that gate is green.

## 41. Readiness

**NOT READY** for the independent quality gate because a required latest-main security check fails, despite zero parity gaps.

Material visual differences: 0

Unapproved visible design changes: 0

Old-main visual component leakage: 0

Missing UI-branch functionality: 0

Missing user-facing latest-main functionality: 0

Unhandled origin/main changes: 0

Frontend operational mock fallbacks: 0

Fake successful actions: 0

Dead interactive controls: 0

Unmapped backend operations: 0

Latest-main compatibility failures: 0
