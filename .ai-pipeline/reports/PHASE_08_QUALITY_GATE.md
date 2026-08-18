# Phase 08 Independent Remediation Re-Gate

**Gate date:** 2026-08-19

**Branch:** `phase/08-evidence-driven-demo`

**HEAD:** `9baafd9b2520f45b4fabb1140617d1070b22e1f8`

**Scope:** independent remediation re-gate of P08-QG-001, P08-QG-002, P08-QG-003, and the complete Phase 01–08 accepted regression

## Executive Result

**PASS**

All three previous High findings are independently closed. The actual supported
`scripts/start_demo_windows.bat` composition started from free ports, reported and ran
`LOCAL_PDF_TEXT`, served both backend and frontend, and produced distinct outcomes from
the actual bytes of clean, address-mismatch, and low-confidence PDFs for the same UEN.
Misleading filenames and byte-identical renames did not change extracted evidence or
semantic results.

Sponsor evidence now follows the server-authored case revision, retains explicit
current/superseded document history, and exposes minimized document, ownership,
readiness, and Mock GoldTier operation evidence. Live replacement, sequential
document/ownership blocking, stale-token, cycle, and existing-party probes passed.

The maintained Windows lifecycle suite passed 13/13 and repository discovery passed
71/71. Full backend, Phase 01–08 focused groups, contracts, frontend, static,
dependency, security, GoldTier, delivery-asset, recovery, and whitespace checks passed.
No current Critical, High, Medium, or required-fix Low finding remains.

## Previous High-Finding Closure

### P08-QG-001

**CLOSED**

Independent evidence:

- `scripts/demo_lifecycle.ps1` sets `IDP_CONNECTOR_MODE=local_pdf_text`; Settings default
  and composition select `LocalPdfTextIdpProvider`, while the Mock provider remains an
  explicit developer/test override.
- Actual `scripts/start_demo_windows.bat` output reported `IDP LOCAL_PDF_TEXT (Local
  POC)`. Live `/api/system/execution-profile` reported `idp_environment=LOCAL` and
  `idp_provider=LOCAL_PDF_TEXT`; backend and frontend returned HTTP 200.
- Through that same launched application and UEN `202400001A`:
  `clean-company-profile.pdf` completed with zero interventions;
  `address-mismatch.pdf` stopped at `DOCUMENT_SOURCE_CONFLICT`; and
  `low-confidence.pdf` stopped at `DOCUMENT_LOW_CONFIDENCE`.
- Clean bytes uploaded as `low_confidence.pdf` stayed clean; mismatch bytes uploaded as
  `clean.pdf` stayed mismatched; two uploads of identical clean bytes under different
  names produced equal field values, confidence, comparisons, and completion.
- Source inspection confirmed that the local provider reads a bounded `BytesIO` through
  `pypdf`, then parses labelled extracted text. It does not receive a filename, UAT ID,
  expected result, scenario, or desired state.

### P08-QG-002

**CLOSED**

Independent evidence:

- `SponsorDocumentEvidence` and `SponsorOwnershipEvidence` refetch on a key composed of
  authoritative case ID, automation version, and updated timestamp. Effect cleanup
  prevents an earlier empty response from overwriting a later revision.
- The normal Start flow exposes the created case before attachment, then replaces it
  with the attachment/automation response; the changed revision retriggers evidence
  retrieval without changing case ID.
- A live A blocked → B blocked → C clean sequence retained three records in order:
  A `SUPERSEDED`, B `SUPERSEDED`, C `CURRENT`. B remained
  `WAITING_FOR_REVIEW`; C automatically resumed and completed. Extraction history was
  not rewritten or deleted.
- Resolving A's pre-replacement exception after C was current returned HTTP 409
  `ZERO_TOUCH_EXCEPTION_STALE`.
- Live APIs returned the exact registry/document values, POC confidence, comparison,
  supersession links, ownership parties/relationships/issues/path evidence, readiness
  stage statuses/blockers, and server-authored target operation statuses consumed by
  the sponsor components.
- Frontend tests passed 40/40 and specifically rendered CURRENT/SUPERSEDED document
  evidence, ownership arithmetic/cycle issues, readiness, target operations, and the
  truthful Local POC provider label.

### P08-QG-003

**CLOSED**

Independent evidence:

- Direct Start from verified free ports succeeded, captured structurally valid backend
  and frontend launcher/listener identities, and reached backend/frontend HTTP 200.
- Direct Stop removed only the verified owned trees, removed runtime metadata, and left
  both ports free.
- Direct Reset changed the session, removed all three recorded old launcher/listener
  PIDs, returned the old process-local case as HTTP 404, and left a new healthy RUNNING
  backend/frontend pair. Final Stop passed.
- The maintained suite passed **13/13 in 176.815 seconds**, including occupied unowned
  ports, ownership mismatch, failed fresh Start, incomplete roles, stale state,
  repeated lifecycle, reset, and unrelated-process safety.
- Repository discovery independently reran the same lifecycle coverage and passed
  **71/71 in 168.825 seconds**.
- PATH normalization is process-scoped, case-insensitive, removes duplicate effective
  names, retains the selected inherited path value, writes one process `PATH`, and does
  not modify user or machine environment variables.

An initial sandboxed Start reached backend launch but Vite's esbuild child process was
denied with `spawn EPERM`; the launcher's exact cleanup initially required the normal
child/process-inspection permission. The supported Stop then verified and removed the
partial owned tree. The same unmodified Start/Stop/Reset scripts and both complete
lifecycle runs passed with the required local child-process permission. This was an
execution-sandbox restriction, not a reproduced lifecycle product failure.

## Supported Sponsor Composition

| Boundary | Runtime truth |
|---|---|
| Registry | ACRA `MOCK` |
| IDP | `LOCAL_PDF_TEXT` / `LOCAL` / Local POC |
| Ownership | `MOCK`, UEN-keyed bounded synthetic data |
| Target | GoldTier `MOCK` |

The frontend fetches the public execution profile and renders
`IDP Local POC (LOCAL_PDF_TEXT)` rather than a hard-coded Mock IDP claim. Developer
controls are separately gated and do not replace the normal composition.

## Input Causality Review

**PASS.** Actual PDF bytes caused the supported-path results. For one UEN, clean,
address-mismatch, and ambiguous/low-confidence content produced completion,
`DOCUMENT_SOURCE_CONFLICT`, and `DOCUMENT_LOW_CONFIDENCE` respectively. Filename
swaps and identical-byte renames preserved semantics. Generic orchestration contains no
branch on a synthetic UEN, scenario, filename, expected result, or desired final state.
UEN-specific fictional state exists only in Mock/input-provider data layers.

## PDF Extraction / Confidence Review

**PASS.** Independent live and focused probes covered clean four-field extraction;
field-specific address mismatch; ambiguous labelled values at deterministic confidence
`0.40`; missing country at `0.00`; a valid no-text PDF with no fabricated value;
structurally invalid input; and a signature/EOF-valid but parser-malformed document.
The latter persisted a sanitized `FAILED` document and
`TECHNICAL_FAILURE / IDP_PROCESSING_FAILED`, with no target operation.

Confidence is deterministic parser evidence (`0.97`, `0.90`, `0.40`, `0.00`) and is
consistently labelled project-defined/POC, not calibrated ML, AI certainty, production
OCR confidence, or sponsor-approved policy. Scanned/no-text PDFs remain unsupported as
an accepted limitation.

## Sponsor Evidence Refresh Review

**PASS.** The evidence fetch lifecycle is keyed to authoritative automation revision,
not just case ID. Initial attachment/processing and each replacement change version and
timestamp, forcing case-bound refetches. Older in-flight requests are invalidated. Live
evidence APIs and the passed frontend rendering suite confirmed safe causal values and
truthful provider/status presentation.

An interactive in-app-browser control surface could not be initialized in this agent
runtime. The live frontend itself returned HTTP 200; runtime profile, application API,
component fetch/effect wiring, static rendering, typecheck, Vitest, and production build
were verified independently. Browser E2E/Playwright absence is an explicitly accepted
gate limitation and is not represented as executed.

## Replacement / Supersession Review

**PASS.** Replacement parses new bytes, is limited to the active same-case document
review, requires the current document event count, records bidirectional supersession,
retains history, excludes superseded evidence from readiness, and automatically
re-enters orchestration. A blocked replacement remained blocked. A clean replacement
resumed without a manual Continue action. Stale, superseded, cross-case, and terminal
requests fail safely; post-target replacement cannot replay target operations.

## Ownership Evidence Review

**PASS.** Delivered `cycle-uen-clean.pdf` passed the document stage for `202400006F`;
the independent UEN-keyed ownership provider then produced `OWNERSHIP_CYCLE` with three
parties, three relationships, explicit owner-to-owned percentages, and
`CYCLE_DETECTED`, with zero target operations. The existing multiple-path fixture
rendered backend-authored calculations including `40% x 50% = 20%` plus direct and
aggregated results. React displays those calculations and does not recompute ownership.

## Readiness Evidence Review

**PASS.** The sponsor view consumes `summary.clm.readiness` directly and renders
server-authored Registry, Documents, Ownership, Target readiness, and active blockers.
It does not infer stage readiness in React.

## Mock GoldTier Evidence Review

**PASS.** A normal clean no-match case exposed:
`SEARCH -> NO_MATCH`, `SHELL -> CREATED`, `POLICY -> CREATED`, `AMEND -> SUCCESS`.
UEN `202400005E` with matching evidence exposed `SEARCH -> MATCH_FOUND`; Shell, Policy,
and Amend remained `NOT_ATTEMPTED`. The response/UI projection contains only operation
and bounded status, not payloads, responses, credentials, authorization headers,
endpoints, fingerprints, or idempotency internals.

## Sequential Pipeline Composition

**PASS.** `202400006F` plus an actual mismatch PDF stopped at Document first; the clean
cycle replacement auto-resumed and then stopped independently at Ownership cycle.
`202400005E` plus low-confidence/conflicting early evidence made no target call; its
matching clean replacement auto-resumed and later reached search-only
`MATCH_FOUND`. No global scenario change was used.

## Developer/Test Isolation Review

**PASS.** Developer/Test Controls remain subordinate in a collapsed `<details>`, are
labelled fault-injection/regression tooling, and require the backend demo gate. A
separate developer case did not change the normal case's version, timestamp, status,
or exception identity. Demo provider selection is passed only through dedicated demo
routes and case-bound controls.

## Windows Lifecycle Review

**PASS.** Direct Start, Stop, Reset, clean-port preconditions, structural runtime
metadata, health, old-case clearing, exact PID removal, occupied unowned ports,
ownership mismatch, failed Start cleanup, incomplete/stale state, repeated cycles, and
unrelated-process survival passed. No broad `taskkill /IM`, executable-name selection,
or blind port kill exists. Final runtime state contained no metadata and no listener on
8000 or 5173.

## UAT / Fixture Review

**PASS.** Phase 07 delivery assets passed 4/4. The manifest explicitly includes
`no-text.pdf` and `cycle-uen-clean.pdf`; the former remains valid and textless without
an internal synthetic marker, while every normal text-bearing fixture retains
`SYNTHETIC TEST DATA`. Unexpected additions remain rejected by the exact manifest.
The delivered cycle fixture was used in the live sponsor-path probe and its document
stage passed before the ownership-only cycle.

## Documentation / Runtime Truthfulness Review

**PASS.** README, sponsor script, runbook, Phase 08 UAT, integration handoff, provider
replacement guide, configuration reference, security boundaries, and `.env.example`
consistently define UEN + actual PDF + Start as the normal path and Local PDF Text as a
bounded POC provider. Scenario names occur only as Developer/Test fault-injection or
legacy regression material, not normal presenter instructions. Live execution-profile
truth matched launcher output and frontend types/rendering.

## Security Review

**PASS within the documented POC boundary.** The integration-security review verified:

- strict media type and safe display-name validation, upload streaming/size limit,
  PDF signature/EOF checks, parser page/text bounds, and no path use;
- in-memory, network-free parsing with no external retrieval;
- no retained/projected raw bytes, full extracted text, provider payload, stack, secret,
  auth header, endpoint, or private binding;
- sanitized parser errors and terminal state convergence without target progression;
- case/document and event-version replacement binding, safe stale/cross-case rejection,
  and revision-bound evidence refresh;
- minimized ownership/target evidence, gated developer APIs, and truthful labels; and
- secret tests 5/5 plus standalone scanner pass, with no tracked `private/` file.

The pre-existing inaccessible untracked directory
`apps/frontend/pytest-cache-files-89airr88/` still produces a permission warning, so
its contents could not be inspected. Tracked files and all 14 accessible untracked
files passed available scans. This is an audit-environment limitation, not a Phase 08
changed-path finding.

## Cross-Phase Regression

**PASS.** Results:

| Check | Result |
|---|---|
| Full backend pytest, cache disabled | PASS — 502/502 |
| Phase 01 focused | PASS — 28 |
| Phase 02 focused | PASS — 81 |
| Phase 03 focused | PASS — 59 |
| Phase 04 focused | PASS — 77 |
| Phase 05 focused | PASS — 61 |
| Phase 06 focused/provider conformance | PASS — 179 |
| Phase 07 focused | PASS — 9 |
| Phase 08 focused | PASS — 8 |
| Contract unittest discovery | PASS — 44/44 |
| Repository unittest discovery | PASS — 71/71 |
| Phase 07 delivery assets | PASS — 4/4 |
| Windows lifecycle suite | PASS — 13/13 |
| Phase 05 retained-outcome/replay safety focus | PASS — 6 |
| Ruff `--no-cache` | PASS |
| Strict mypy `--no-incremental` | PASS — 56 source files |
| `pip check` | PASS |
| Secret tests / standalone scanner | PASS — 5/5 / clean, subject to inaccessible-directory note |
| GoldTier validator tests | PASS — 5/5 |
| GoldTier normal / strict | PASS — 19 valid / 19 quarantined / 48 not validated; expected strict exit 1 |
| Frontend no-incremental typecheck | PASS |
| Frontend Vitest | PASS — 40/40; sandbox `spawn EPERM` rerun with required child-process permission |
| Frontend production build outside repository | PASS — 29 modules |
| `npm ls --all` | PASS — exit 0; expected optional platform/feature packages absent |
| Tracked and cached diff whitespace | PASS |
| Accessible untracked whitespace/final newline | PASS — 12 text files |

The upstream Starlette TestClient/httpx deprecation warning remains non-failing.

## Findings

### CRITICAL

None.

### HIGH

None. P08-QG-001, P08-QG-002, and P08-QG-003 are closed.

### MEDIUM

None.

### LOW

None requiring a Phase 08 fix. The inaccessible untracked directory and unavailable
interactive browser-control surface are validation-environment limitations recorded
above, not reproduced application defects.

## Accepted Limitations

- deterministic text extraction rather than OCR/ML; scanned PDFs unsupported;
- project-defined POC confidence and provisional document/source/UBO rules;
- Mock ACRA, synthetic/Mock ownership, Mock GoldTier, and process-local state;
- no production RBAC, durable workflow/storage/audit, malware CDR, retention,
  distributed idempotency, or browser E2E/Playwright;
- no live ACRA/hierarchy, real GoldTier/PingFed/TLS verification, related-party write,
  autonomous approval, or Ready-for-Approval transition.

## Remaining Sponsor Dependencies

- Sponsor-approved IDP document/profile/confidence/reviewer/source-authority policy:
  **NOT CONFIRMED** (Q-003/Q-005/Q-013/Q-014).
- Sponsor-approved UBO policy: **NOT CONFIRMED** (Q-004).
- Live ACRA: **BLOCKED** by Q-012 contract/access/auth/TLS inputs.
- Live hierarchy: **BLOCKED** by Q-002.
- Real GoldTier/PingFed: **NOT READY** under Q-008/D-018 and unresolved Singapore
  mappings/access/TLS verification.
- Ready-for-Approval/four-eye state: **NOT CONFIRMED** under Q-001.

D-027 remains a working project/security decision for a bounded synthetic POC, not a
sponsor-approved IDP, source-authority, confidence, or reviewer policy. No sponsor
authority was newly supplied or inferred during this gate.

## Required Fixes

**None for Phase 08.**

## Readiness

| Area | Decision |
|---|---|
| Overall result | **PASS** |
| P08-QG-001 | **CLOSED** |
| P08-QG-002 | **CLOSED** |
| P08-QG-003 | **CLOSED** |
| Phase 08 implementation | **READY** |
| Input-driven sponsor flow | **READY** |
| Supported sponsor IDP | **LOCAL_PDF_TEXT** |
| Actual PDF-derived assessment | **READY** |
| Happy-path interventions after Start | **0** |
| Document exception HITL | **READY** |
| Replacement remediation | **READY** |
| Automatic resume | **READY** |
| Ownership evidence visibility | **READY** |
| Readiness evidence visibility | **READY** |
| Mock GoldTier evidence visibility | **READY** |
| Developer scenario isolation | **READY** |
| Sponsor-facing demo | **READY** |
| Phase 01–07 regression | **PASS** |
| Windows lifecycle | **PASS** |
| Repository regression | **PASS** |
| Sponsor-approved IDP policy | **NOT CONFIRMED** |
| Sponsor-approved UBO policy | **NOT CONFIRMED** |
| Live ACRA | **BLOCKED** |
| Real GoldTier | **NOT READY** |
| Ready-for-Approval | **NOT CONFIRMED** |
| Next-phase/finalization readiness | **READY** |

This result authorizes no commit, push, merge, or next-phase start.

## Git Status

- Branch remained `phase/08-evidence-driven-demo`; HEAD remained
  `9baafd9b2520f45b4fabb1140617d1070b22e1f8`.
- Staged entries remained 0.
- Before this overwrite, the worktree contained 37 tracked modified files and 14
  accessible untracked files, plus the pre-existing inaccessible-directory warning.
- This gate overwrote only `.ai-pipeline/reports/PHASE_08_QUALITY_GATE.md` in the
  repository. It made no application, test, configuration, ordinary-documentation,
  contract-log, or supporting-report change.
- Frontend build output was written outside the repository. Lifecycle metadata/logs
  were Git-ignored; final metadata and port listeners were absent.
- Nothing was staged, committed, pushed, merged, or started as another phase.
