# Pre-Phase 12 — CLM Workspace, Case History/Queue and Multi-Document Intake Execution

## 1. Executive Summary

Pre-Phase 12 is implemented on `phase/pre-12-clm-workspace-multidoc` without staging, committing, pushing, merging, or beginning Phase 12. The local POC now opens on a truthful CLM Start workspace, creates and exposes a case identifier before document intake completes, supports bounded PDF/DOCX/TXT multi-document intake, aggregates all current document evidence with provenance, and provides backend-authored process-local case history and a multi-case review queue.

All repository-correct required checks pass. The full backend is `675 passed`, the frontend is `56 passed`, and the Windows lifecycle suite is `13 passed` with clean post-run ownership state.

## 2. Accepted Baseline

The repository's final Phase 11 quality gate records the executable pre-change baseline as Phase 11 `58`, Phase 10 `52`, Phase 09 `39`, POC/provider `197`, full backend `658`, frontend `52`, contract `44`, and Windows lifecycle `13/13`. The planner's `706` backend figure was approximate and did not match the checked-in final Phase 11 evidence; this execution uses the repository evidence rather than silently changing the baseline.

The accepted Phase 11 reconciliation, deterministic ownership, Registry four-operation acquisition, and Mock GoldTier `SEARCH -> SHELL -> POLICY -> AMEND` behavior remain intact.

## 3. Scope Implemented

Implemented only the assigned refinement:

- CLM product heading and Start-first landing page;
- visible, accessible case-creation/upload/start progress;
- read-only backend case portfolio and review-queue projections;
- bounded multi-file and folder-derived intake for PDF, DOCX, and TXT;
- explicit intake-completion boundary;
- multi-document reconciliation/provenance and replacement isolation;
- focused backend/frontend, call-count, security, and regression coverage;
- architecture, contract, decision, configuration, quick-start, and regression documentation.

## 4. Product Heading / Landing Page

The product H1 is exactly `Client Lifecycle Management (CLM) Onboarding`. The initial active workspace is `Start onboarding`; the existing sidebar order remains Dashboard, Start onboarding, Review, Logs, Account info. Dashboard and Review remain available navigation destinations rather than being rendered as the initial landing page.

## 5. Start Feedback UX

Submitting is duplicate-guarded. The Start workspace immediately enters `Creating case…`, retains the backend-created case ID and UEN, then shows per-file `Uploading documents… (n/total)`, `Starting analysis…`, `Processing…`, and a terminal `Completed`, `Waiting for review`, or `Failed safely` state through an accessible `role=status`/`aria-live=polite` region.

A failed upload leaves the created case and successful earlier documents intact. `Retry this case` continues the same case and failed-document chain. The selected document set is locked once case creation begins. Completed and waiting cases expose `Start another case`, which clears only the Start form state; backend-authored history remains visible.

## 6. Case History Architecture

`InMemoryZeroTouchRepository.list_records()` returns sorted defensive copies of all process-local automation records. `GET /api/clm/zero-touch/cases` projects only safe portfolio fields and performs no Registry, IDP, ownership, or GoldTier work. Dashboard renders the returned collection and opens the exact selected case through the existing case-detail endpoint.

The case list is backend-authored; it is not reconstructed from React state or browser storage.

## 7. Review Queue Architecture

Review uses the same backend portfolio endpoint filtered by typed `WAITING_FOR_REVIEW` status and renders every waiting case. Queue rows carry the legal name or UEN, case ID, stage, blocker count, and last-updated time. Opening and resolving one item fetches/mutates only that case; another waiting case remains independently present.

The queue does not create reviewer authority. Actions continue to come exclusively from backend-authored `allowed_actions` and evidence-version controls.

## 8. Process-Local Persistence Boundary

History and review state live only in the backend process's in-memory repository. Restarting or resetting the local demo clears them. No MongoDB, browser persistence, durable queue, transaction log, production restart/resume guarantee, or cross-process coordination is claimed. The UI, README, architecture notes, and contract profile label this boundary explicitly.

## 9. Multi-Document Intake

One case can hold up to 20 current documents. Each accepted file creates an independent document-processing record with its own ID, safe display name, media type, size, provider evidence, events, fields, and reconciliation provenance. Files are uploaded sequentially to the already-created case; one file never overwrites another.

The default total current intake bound is 25 MiB, with the existing 5 MiB per-file bound retained. Current documents, rather than superseded history, determine the active count and total.

## 10. Folder Selection

The Start form provides a multiple-file input and a `webkitdirectory` folder input. Folder-derived files pass through the same deduplication, filename, extension/MIME, per-file, count, and total-size validation as individually selected files. Unsupported folder contents are rejected visibly and are not silently discarded or submitted.

## 11. Supported File Types

The supported media profile is deliberately narrow:

- `.pdf` with `application/pdf`;
- `.docx` with `application/vnd.openxmlformats-officedocument.wordprocessingml.document`;
- `.txt` with `text/plain` and valid UTF-8/UTF-8 BOM text.

ZIP files, images, legacy `.doc`, macros, arbitrary XML, and other media are not claimed as analysed.

## 12. Media Validation / Security

The backend revalidates all client claims. It enforces safe display names, exact extension/MIME pairs, non-empty and bounded bodies, PDF header/trailer structure, DOCX ZIP/XML structure, and UTF-8 TXT content. DOCX validation limits entry count and expanded bytes; rejects traversal-like names, encrypted entries, macros, embedded objects, and ActiveX content; and reads only the required package parts. TXT rejects decoding errors, NULs, and unsupported control content.

Raw upload bytes and extracted text are passed transiently to the selected IDP provider and are not stored in the case/document repository or normal logs. API errors expose controlled codes, safe messages, correlation IDs, case IDs, and document IDs only.

## 13. Document Extraction Routing

`DocumentMediaRouter` owns format validation and extraction. PDF bytes continue through the existing local PDF-text provider path. DOCX text is extracted from `word/document.xml`; TXT is decoded as UTF-8. Both supply transient extracted text to the replaceable IDP interface, preserving the connector boundary and avoiding format logic in orchestration/business rules.

## 14. Evidence Aggregation

Reconciliation builds observations from Registry evidence plus every current, successfully processed document. Every document observation carries its document record ID and safe display name. Browser projections expose the safe document ID/name provenance needed to explain which file contributed each value; superseded documents remain auditable history but do not contribute current evidence.

## 15. Multi-Document Reconciliation Semantics

A missing field in one document does not produce a false `MISSING` outcome when another current document supplies usable evidence. All matching current values may proceed. Conflicting usable values remain one blocked field discrepancy containing all observations; there is no source, confidence, recency, or document-order winner.

`USE_DOCUMENT_VALUE` for legal name remains possible only when current usable document observations resolve to one unique normalized value. Ambiguous document values expose no document winner. Invalid or unverifiable evidence remains visible and blocked even when other evidence is usable.

## 16. Intake Completion / Start Boundary

`POST .../intake/documents` is intake-only and never starts the downstream workflow. `POST .../intake/complete` requires at least one current document, an expected count matching the current set, and no current failed document. Only that explicit boundary starts reconciliation and downstream readiness processing. A partial or failed upload therefore cannot accidentally start ownership or GoldTier work.

Existing completed-start idempotency remains intact; repeated terminal start/complete attempts do not repeat downstream calls.

## 17. Replacement Behavior

Replacement targets exactly one current failed/reviewed document. Document A remains current when B is replaced; B is retained as superseded; B2 becomes current; only B2 is newly analysed; and reconciliation rebuilds from A plus B2. Old evidence versions and fingerprints remain stale and are rejected by existing optimistic-concurrency controls.

If B2 itself fails safely, B is still linked to B2 so there remains exactly one current record in that replacement chain, permitting bounded same-case retry without accumulating multiple current failed documents.

## 18. Registry / IDP / Ownership / GoldTier Call Counts

The focused three-document test proves:

| Boundary | Calls |
| --- | ---: |
| Registry entity | 1 |
| Registry officers | 1 |
| Registry ownership parties | 1 |
| Registry relationships | 1 |
| IDP/document analysis | 3 |
| Ownership after reconciliation clears | 1 |
| GoldTier search/shell/policy/amend | 1 each |

Read-only list/filter calls add zero connector calls. A blocked two-document reconciliation produces Registry `1/1/1/1`, IDP `2`, ownership `0`, and GoldTier `0`.

## 19. API Changes

Added:

- `GET /api/clm/zero-touch/cases` with optional typed status filtering;
- normal and demo `POST /api/clm/zero-touch/cases/{case_id}/intake/documents`;
- normal and demo `POST /api/clm/zero-touch/cases/{case_id}/intake/documents/{document_id}/retry`;
- normal and demo `POST /api/clm/zero-touch/cases/{case_id}/intake/complete`.

Document responses now include media type and safe size metadata. Reconciliation browser observations include optional document provenance. The existing single-document attachment/start routes remain compatible for accepted regressions.

## 20. Frontend Changes

The React client now provides the Start-first workspace, file/folder selection, visible validation and selection/removal, early case identity, upload/start progress, safe same-case retry, start-another-case reset, backend portfolio, multi-case review queue, and per-document reconciliation provenance. Replacement controls accept the same supported PDF/DOCX/TXT profile and allow the operator to select the exact current document being replaced.

## 21. Files Changed

Backend implementation and tests:

- `apps/backend/app/api_models.py`
- `apps/backend/app/composition.py`
- `apps/backend/app/config.py`
- `apps/backend/app/connectors/idp.py`
- `apps/backend/app/connectors/local_pdf_idp.py`
- `apps/backend/app/domain/documents.py`
- `apps/backend/app/domain/reconciliation.py`
- `apps/backend/app/main.py`
- `apps/backend/app/services/document_media.py`
- `apps/backend/app/services/document_processing.py`
- `apps/backend/app/services/reconciliation.py`
- `apps/backend/app/services/zero_touch_orchestration.py`
- `apps/backend/app/services/zero_touch_repository.py`
- `apps/backend/tests/test_document_processing.py`
- `apps/backend/tests/test_pre_phase12_workspace_multidoc.py`

Frontend implementation and tests:

- `apps/frontend/src/App.tsx`
- `apps/frontend/src/App.test.tsx`
- `apps/frontend/src/api.ts`
- `apps/frontend/src/styles.css`
- `apps/frontend/src/types.ts`

Documentation/configuration:

- `.agents/skills/poc-regression-check/references/regression-catalogue.md`
- `.env.example`
- `README.md`
- `docs/PROJECT_CONTEXT.md`
- `docs/UI_DEMO_QUICK_START.md`
- `docs/architecture/ARCHITECTURE.md`
- `docs/architecture/PRE_PHASE_12_CLM_WORKSPACE_MULTIDOC.md`
- `docs/architecture/README.md`
- `docs/contracts/MULTI_DOCUMENT_INTAKE_PROFILE.md`
- `docs/decisions/DECISION_LOG.md`
- `docs/integration/CONFIGURATION_REFERENCE.md`
- `.ai-pipeline/reports/PRE_PHASE_12_CLM_WORKSPACE_MULTIDOC_EXECUTION.md`

## 22. Exact Test Results

| Check | Exact result |
| --- | --- |
| New Pre-Phase 12 backend focus | `16 passed` |
| Focused new/existing document, orchestration, Phase 11 set | `135 passed` |
| Full backend | `675 passed`, 4 existing warnings |
| Ruff | Passed |
| strict mypy, no incremental cache | Passed, 65 source files |
| Contract tests | `44 passed` |
| Frontend typecheck | Passed |
| Frontend tests | `56 passed` |
| Frontend production build | Passed, 29 modules transformed |
| Secret unit tests | `5 passed` |
| Repository secret scan | Clean |
| Repository Python dependencies | `No broken requirements found` |
| Frontend dependency tree | Passed; platform/tooling optional dependencies reported as optional only |
| GoldTier validator unit tests | `5 passed` |
| GoldTier examples | `VALID=19`, `INVALID_QUARANTINED=19`, `NOT_VALIDATED=48`, exit 0 |
| Delivery assets | `4 passed` |
| Windows lifecycle | `13 passed` in 143.963 seconds |
| Post-lifecycle ownership audit | runtime metadata false; listeners 0; project processes 0 |
| `git diff --check` | Passed; line-ending notices only |
| `git diff --cached --check` | Passed |
| Staging area | Empty |

The first sandboxed frontend build and lifecycle attempt could not spawn/inspect child processes (`EPERM`/`Access denied`). The required approved out-of-sandbox reruns passed. A machine-wide `pip check` reports an unrelated global `python-telegram-bot`/`httpx` conflict; the repository-owned `.venv` dependency check is clean and is the result used for project readiness.

## 23. Phase 09–11 Regression

- Phase 11 reconciliation/remediation: `58 passed`, 1 existing Starlette/httpx deprecation warning.
- Phase 10 Registry acquisition: `52 passed`, 1 existing warning.
- Phase 09 jurisdiction gateway: `39 passed`, 1 existing warning.
- Accepted zero-touch/UAT/input/provider regression: `197 passed`, 4 existing warnings.

No Phase 09–11 assertion was removed or weakened. Singapore Registry acquisition remains four operations once per case, and blocked paths retain zero downstream ownership/GoldTier calls.

## 24. Security Review

Result: no Critical, High, or Medium finding.

The integration-security checklist was applied to upload/media parsing, external connector boundaries, safe API projection, error handling, logging, credentials, and PII/KYC treatment. No credential/authentication path, TLS behavior, outbound endpoint, GoldTier payload contract, or log sink was changed. New content is bounded and parsed before the IDP connector; raw bodies/extracted text are not persisted or logged; filenames and API errors are sanitized; no secrets are introduced.

Accepted Low/POC limitations: the UI/API is a local synthetic demonstration without production authentication/authorization, the queue is process-local, and the upstream Starlette/httpx deprecation warning remains. Production reviewer authority, durable audit/persistence, malware scanning, and operational document-retention controls remain outside this phase and depend on Q-015 governance.

## 25. Documentation Updated

Updated the project README, context, UI quick start, architecture index/current architecture, configuration reference, decision log, environment example, and POC regression catalogue. Added a dedicated Pre-Phase 12 architecture note and a multi-document intake contract/profile. All documentation labels the implementation Mock/process-local and avoids durable or production-ready claims.

## 26. Sponsor Dependencies Preserved

- Q-012 remains OPEN for authoritative subscribed ACRA endpoint/schema/authentication/error/rate-limit details and authorized sandbox access.
- Q-015 remains OPEN for production evidence precedence, reviewer authority, conflict governance, durable audit, persistence, and restart/resume semantics.

No sponsor answer was invented. Registry and Document conflicts remain human-review blockers without automatic precedence.

## 27. Non-Goals Confirmation

This execution did not add live ACRA/ACRA+, foreign Registry integration, MongoDB, `createRelationship`, multi-level GoldTier hierarchy creation, production reviewer authorization, a full compliance/risk engine, autonomous approval, ML UBO decisions, a production workflow engine, a full Exception Workbench, or Phase 12 functionality. Existing ownership/UBO and GoldTier business behavior was not redesigned.

## 28. Remaining Risks

- Case history, the queue, intake records, evidence, and review state are lost on process restart by design.
- Q-012 prevents live ACRA interoperability claims.
- Q-015 prevents production authority, evidence-governance, durable-audit, and restart/resume claims.
- DOCX/TXT support is deterministic text extraction for the local POC, not OCR, malware detection, or production document forensics.
- The known Starlette/httpx deprecation and provider-conformance serialization warnings remain non-blocking technical debt.

## 29. Readiness

The explicitly assigned Pre-Phase 12 refinement is implemented and verified. No Critical or High issue remains. The result is ready for an independent Pre-Phase 12 quality gate; this execution did not perform that gate and did not begin Phase 12.

READY FOR PRE-PHASE 12 QUALITY GATE
