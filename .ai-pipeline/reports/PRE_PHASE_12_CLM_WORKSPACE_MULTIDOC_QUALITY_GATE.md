# Pre-Phase 12 CLM Workspace / Multi-Document Quality Gate

Date: 2026-08-30  
Branch: `phase/pre-12-clm-workspace-multidoc`  
HEAD: `8a969e1 Phase 11: Multi-source reconciliation and review resume (#17)`  
Mode: independent, report-only review

## 1. Verdict

**FAIL.** The refinement has strong workflow, regression, and UI coverage, but two mandatory hostile-media acceptance criteria are not met. A DOCX containing a Windows-rooted archive member is accepted, and a plainly non-PDF body framed only with `%PDF-` / `%%EOF` reaches the IDP path instead of being rejected as malformed media. The Windows lifecycle suite also was not independently pass-confirmed: its sandbox run is invalid because the sandbox cannot terminate test-owned process trees, while the escalated runner cleaned up successfully but did not return its final unittest summary to this reviewer.

## 2. Scope Reviewed

Reviewed the execution report; README; project context; UI, architecture, intake-profile, decision, and configuration documents; Phase 09--11 final gate evidence; all listed frontend/backend implementation files; the full unstaged working-tree diff; and the relevant test suites. Applied the project quality-gate, integration-security, and POC-regression checklists. No implementation, test, configuration, staging, commit, push, merge, or Phase 12 work occurred.

## 3. Working-Tree / Diff Assessment

The working tree is on the expected branch with the intended Pre-Phase 12 implementation and documentation changes, all unstaged. No staged files were present. `git diff --check` and cached-diff check passed apart from CRLF notices. Scope review found no MongoDB application persistence, live registry/GoldTier integration, reviewer RBAC, ZIP ingestion, OCR claim, Phase 12 functionality, or source-precedence change.

## 4. Heading / Landing Page

**PASS.** `App.tsx` renders `Client Lifecycle Management (CLM) Onboarding`, initializes `activeTab` as `start`, and preserves the sidebar order Dashboard, Start onboarding, Review, Logs, Account info.

## 5. Start Progress / Duplicate Protection

**PASS.** The Start workflow immediately enters Creating, then Uploading, Starting analysis, Processing, Waiting/Completed/Failed safely states through an accessible live-status panel. The submit action is disabled while submitting and `beginJourney` also has an in-process guard. The created case summary is saved before upload, so case ID, UEN, and status remain visible after a later upload failure.

## 6. Case History Repository

**PASS.** `InMemoryZeroTouchAutomationRepository.list_records()` returns deep copies, is read-only, and sorts by updated time then case ID. The focused test directly verifies returned-record mutation cannot alter stored state.

## 7. Case List API

**PASS.** `GET /api/clm/zero-touch/cases` has typed optional `status` filtering and emits only bounded case summary fields. It does not expose document bytes/text, registry payloads, credentials, stack traces, or internal evidence bodies.

## 8. Review Queue / Cross-Case Isolation

**PASS.** Backend-filtered `WAITING_FOR_REVIEW` cases feed the queue. Focused tests create two review cases, resolve one, and confirm the other remains unchanged. The UI makes no authenticated reviewer or durable assignment claim.

## 9. Process-Local Boundary

**PASS.** README, UI portfolio, queue, and architecture documentation clearly say cases/history/queue are process-local and cleared by backend restart. No durable production-work-queue wording was found.

## 10. Multi-File / Folder Intake

**PASS WITH ONE UI FIX REQUIRED.** The UI accepts multiple individual or browser-folder `File` objects through one validation path, lists/removes selected files, and the backend never receives a path. Count and limit validation is present on both client and server. However, the selected-files panel displays only the count, not the selected total size required by the brief; see P12-QG-003.

## 11. Intake Limits

**PASS.** Server limits are 20 current files, 5 MiB each, and 25 MiB total. Tests cover count and total limits; service code recomputes the current evidence set on each upload/replacement, preventing sequential bypass and avoiding superseded-document double counting.

## 12. PDF Validation

**FAIL -- P12-QG-002.** `DocumentMediaRouter` accepts any nonempty byte sequence that begins `%PDF-` and ends `%%EOF` (lines 74--80). Probe `b"%PDF-1.4\\nplain text\\n%%EOF"` passed that router and reached the local PDF provider; the intake endpoint returned `503 IDP_PROCESSING_FAILED` while the case stayed `PENDING_INPUTS`. This is safe call-stopping, but it is not the specified safe rejection of an obvious PDF masquerade and incorrectly classifies malformed client input as an IDP infrastructure failure.

## 13. DOCX Security / Extraction

**FAIL -- P12-QG-001.** The router rejects POSIX traversal and leading-slash entries, encryption, macros, embedded objects, ActiveX, excessive entries/expanded size, and malformed XML. However, the name checks at `document_media.py:101-118` use only POSIX semantics and do not reject Windows drive-rooted names. An in-memory DOCX containing `C:/evil.txt` plus required OOXML files was accepted by the router and by `POST .../intake/documents` (`201 REVIEW_REQUIRED`). The code currently extracts in memory, so this did not write a file or reach later workflow; it nevertheless violates the explicit hostile-DOCX rule requiring absolute-path-like archive entries to be safely rejected.

## 14. TXT Validation

**PASS.** UTF-8 and UTF-8 BOM input are supported. Invalid UTF-8, NUL/binary/control content, empty values, and configured size limits are rejected. Extracted bodies are transient.

## 15. Unsupported Media

**PASS.** Frontend and backend restrict intake to matching PDF/DOCX/TXT extension/MIME combinations. Unsupported image/archive inputs receive controlled safe errors; no OCR/image-analysis claim is made.

## 16. Intake Completion Boundary

**PASS.** New intake uploads process one document only and leave automation `PENDING_INPUTS`. Completion requires at least one current document, matching expected count, and no current failed document. The maintained legacy single-document auto-start route is explicitly documented as compatibility-only; the new browser uses intake completion.

## 17. Partial Upload / Retry

**PASS.** Successful uploads remain attached after a later failed upload; final progression does not begin; the created case remains visible and retry stays on that case. Failed provider processing creates a retryable document record, and request-validation failures can be retried through the same case workflow.

## 18. Multi-Document Evidence Aggregation

**PASS.** Each current supported document is processed independently. Reconciliation retains document ID/display-name provenance for each document observation and uses every current document, not just the first or last.

## 19. Reconciliation Semantics

**PASS.** Tests and code confirm missing evidence in one document cannot erase another usable value; equal values match; document-vs-document conflicts block; invalid/unverifiable evidence remains visible; and neither registry, document order, confidence, nor recency becomes an automatic winner. `USE_DOCUMENT_VALUE` remains legal-name-only and requires one unique usable document candidate.

## 20. Replacement Behavior

**PASS.** Replacing B leaves A current, preserves B as superseded, processes B2 only, and rebuilds reconciliation from A+B2 without another registry acquisition. Failed replacement-chain logic keeps one current retry target.

## 21. Registry / IDP Call Counts

**PASS.** Independently executed focused test evidence confirms normal three-document flow: Registry entity/officers/ownership parties/relationships = `1/1/1/1`; IDP = `3`; Ownership = `1`; GoldTier SEARCH/SHELL/POLICY/AMEND = `1/1/1/1`.

## 22. Ownership / GoldTier Call-Stopping

**PASS.** A blocked two-document conflict records Registry `1/1/1/1` and IDP `2`, with Ownership `0` and all GoldTier operations `0`. Invalid intake/failed completion remains before downstream progression.

## 23. Read-Only History / Queue Call Counts

**PASS.** Focused counted-provider tests show repeated list/filter calls add Registry `0`, IDP `0`, Ownership `0`, and GoldTier `0`; no automation state advances.

## 24. Frontend Assessment

**PASS WITH P12-QG-003.** The UI gives immediate truthful progress, supports same-case retry, exposes early identity, shows queue/history correctly, and passes typecheck, 56 tests, and production build. The only observed current UX gap is absence of a selected total-size indicator.

## 25. API / Browser / Logging Security

**FAIL.** Safe browser projections, bounded request bodies, safe error models, process-local retention, mock labeling, and secret checks are good. P12-QG-001 and P12-QG-002 are active input-validation defects at the document trust boundary. No secret, token, raw uploaded body, raw IDP text, or confidential sponsor artefact was found newly tracked.

## 26. Phase 09 Regression

**PASS.** The focused Phase 09 jurisdiction suite passed. Accepted jurisdiction blockers continue to stop Registry, IDP, Ownership, and GoldTier work.

## 27. Phase 10 Regression

**PASS.** The focused Phase 10 acquisition suite passed. Normal Singapore acquisition remains four registry operations once per case.

## 28. Phase 11 Regression

**PASS.** The focused Phase 11 reconciliation/remediation suites passed. Source-neutral decisions, stale rejection, false-clear prevention, and legal-name-only document selection remain intact.

## 29. Full Backend / Frontend / Static Results

| Check | Independent result |
| --- | --- |
| Focused Pre-Phase 12 + document + Phase 09--11 backend suites | PASS |
| Full backend pytest suite | PASS, 675; existing Starlette/httpx deprecation and three known Pydantic serializer warnings |
| Ruff | PASS |
| strict mypy | PASS, 65 source files |
| Contract tests | PASS, 44 |
| Secret unit tests / repository scan | PASS, 5 / clean |
| `pip check` | PASS |
| Frontend typecheck | PASS |
| Frontend tests | PASS, 56 |
| Frontend production build | PASS, 29 modules |

The initial frontend test/build attempt was blocked by sandbox child-process `EPERM`; an approved out-of-sandbox rerun passed.

## 30. Lifecycle / Cleanup

**UNVERIFIED FOR PASS.** The sandbox lifecycle invocation produced 13 setup failures because it was denied permission to terminate test-owned child process trees; this is an environment restriction, not a product assertion. The approved out-of-sandbox invocation started, health-checked, and stopped test-owned demo processes; its process tree later exited with runtime metadata absent and ports 8000/5173 not listening. Its final unittest summary/exit status was not captured by the runner, so the execution report's `13 passed` claim is not treated as independently demonstrated here. Re-run the full lifecycle suite in a normal Windows host and retain its complete final output before a PASS gate.

## 31. Documentation / Sponsor Boundaries

**PASS.** Documentation correctly labels the implementation Mock and process-local, keeps Q-012 (live ACRA contract/access) and Q-015 (review authority, durable audit/persistence) open, and does not claim real ACRA/GoldTier or Ready-for-Approval readiness.

## 32. Findings by Severity

### Critical

None.

### High

- **P12-QG-001 -- DOCX absolute-path-like entry accepted.** `apps/backend/app/services/document_media.py:101-118`. Reject drive-qualified and other Windows absolute/path-like archive member names before any OOXML read. Add endpoint-level regression probes for `C:/evil.txt`, `C:\\evil.txt`, and related path forms.
- **P12-QG-002 -- Obvious PDF masquerade is delegated to IDP.** `apps/backend/app/services/document_media.py:74-80`. Strengthen the media boundary so malformed/truncated PDF bytes receive a document-structure request error rather than a provider `503`; retain bounded parsing and add valid/masquerade/truncated tests.

### Medium

- **P12-QG-003 -- Selected total size is not displayed.** `apps/frontend/src/App.tsx:2711-2721`. Show the actual selected byte total (and ideally the 25 MiB limit) next to the count, with a frontend test.
- **P12-QG-004 -- Lifecycle PASS not independently captured.** No product defect is established, but the mandatory lifecycle PASS criterion remains unverified in this review. Re-run and retain a complete clean-host `13/13` result after P12-QG-001/002 remediation.

## 33. Remaining Technical Debt

Accepted, documented POC limitations remain: process-local state, no production RBAC/reviewer authority, no durable audit/restart recovery, no malware scanning/CDR, local deterministic extraction rather than OCR, live ACRA blocked by Q-012, and real GoldTier/governance blocked by Q-015. The Starlette/httpx deprecation and provider-conformance serializer warnings remain non-blocking but should be addressed separately. These do not excuse the active media-boundary findings.

## 34. Next-Development Readiness

Not ready for merge or Phase 12 planning. Remediate P12-QG-001 and P12-QG-002, add adversarial regression coverage, add the selected-total-size display, and obtain a complete lifecycle pass from a normal Windows host. Then rerun this independent gate. This result does not change Q-012/Q-015: live ACRA and real GoldTier remain separately not ready.

FAIL — PRE-PHASE 12 REMEDIATION REQUIRED
