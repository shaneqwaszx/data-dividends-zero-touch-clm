# Phase 12 Remediation Report

## 1. Executive Summary

Phase 12 quality-gate findings PH12-QG-001, PH12-QG-002, and PH12-QG-003 have been remediated on branch `phase/12-durable-persistence-restart-recovery`. Durable case reads now fail closed unless MongoDB `_id` is the canonical string form of the embedded `case_id`; interrupted current document work now recovers to an explicit document re-upload state with a targeted same-case retry path; and the genuine-Mongo suite now covers the adverse persistence, recovery, CAS, and cross-repository atomicity paths identified by the gate.

No Phase 13 work was performed. Nothing was staged, committed, pushed, merged, rebased, stashed, reset, or cleaned.

## 2. Quality Gate Findings

- **PH12-QG-001 — HIGH:** a stored MongoDB document could be selected by `_id=A` while its decoded snapshot declared `case_id=B`, allowing an invalid durable identity to be accepted.
- **PH12-QG-002 — HIGH:** documents recovered from `UPLOADED` or `PROCESSING` became failed evidence, but the automation could remain beyond Document and ordinary intake could not safely complete the stranded case.
- **PH12-QG-003 — MEDIUM:** the real-Mongo suite did not exercise the gate's required adverse durability, recovery, CAS, and Phase 11 atomicity behavior.

## 3. PH12-QG-001 Root Cause

`MongoCaseStore._decode` removed MongoDB `_id` before schema validation and trusted the embedded `case_id`. Query selection and decoded domain identity were therefore not proven to describe the same case. The same decoder is shared by direct reads, initialization, list reads, submission lookup, and document lookup, so the defect affected every durable read path.

## 4. PH12-QG-001 Implementation Fix

`MongoCaseStore._decode` now retains and validates `_id` before decoding the envelope. It rejects missing, non-string, malformed UUID, non-canonical UUID, and `_id`/`case_id` mismatch states with `PersistenceDataInvalidError`. Validation occurs before any snapshot is returned or projected. The store does not repair, rewrite, delete, or silently normalize the corrupt record.

## 5. Identity Validation Contract

Every durable case record must satisfy:

`mongo_document["_id"] == str(validated_snapshot.case_id)`

The `_id` value must itself already be the lowercase canonical UUID string. The invariant applies uniformly to `initialize`, `get`, `list`, `find_by_submission`, and `find_by_document` because they all use the fail-closed decoder.

## 6. PH12-QG-001 Unit Tests

The adapter suite now covers missing `_id`, non-string `_id`, malformed UUID text, uppercase/non-canonical UUID text, a valid but mismatched UUID, and the exact-match success case. It also confirms the invalid identity is rejected rather than returned under either case identity.

Result: `apps/backend/tests/test_phase12_persistence.py` — **14 passed**.

## 7. PH12-QG-001 Genuine Mongo Tests

The real-Mongo suite inserts a record with `_id=A` and embedded `case_id=B`, then proves that direct read, list, document lookup, and application initialization fail closed, `get(B)` does not project the corrupt record, and the record is not exposed as either case. This test was collected but skipped locally because `PHASE12_MONGO_URI` was unavailable.

## 8. PH12-QG-002 Root Cause

Restart recovery correctly marked an interrupted current document as failed, but did not realign the automation to a resumable Document-stage state. The normal intake endpoint also treated a replacement as unrelated fresh intake, leaving no explicit, constrained path to repair the interrupted evidence without creating a new case or replaying already completed providers.

## 9. Interrupted Document Recovery State

For a current document recovered from `UPLOADED` or `PROCESSING`, the document becomes `FAILED` with safe code `DOCUMENT_REUPLOAD_REQUIRED`. When no higher-priority uncertain target-delivery recovery applies, the automation becomes `PENDING_INPUTS` at `DOCUMENT`, completed stages are reduced to Registry, technical failure metadata is cleared, open document-stage exceptions are cancelled, and a typed `DOCUMENT_REUPLOAD_REQUIRED` partial event is recorded.

The transition is deterministic, versioned, validated, and durable. Completed structured documents remain unchanged and reusable.

## 10. Targeted Re-upload Behavior

The existing document retry operation is the sole repair path. It targets the failed current document within the same case, creates the replacement revision through the normal supersession rules, and reuses completed upstream evidence. It does not create a second case and does not replay Registry, Ownership, or GoldTier merely to replace interrupted document evidence.

## 11. Multiple Interrupted Documents

Recovery handles every interrupted current document independently. If documents A and B both require re-upload, retrying A does not hide B: ordinary intake and case start remain blocked until B is also retried. Each targeted retry preserves its own source lineage and supersession history. A previously completed current document C remains current, completed, and structurally unchanged.

## 12. Intake Guard Behavior

Ordinary document intake now fails with safe request code `ZERO_TOUCH_DOCUMENT_REUPLOAD_REQUIRED` whenever any current document is marked `DOCUMENT_REUPLOAD_REQUIRED`. This prevents accidental unrelated intake from bypassing the explicit recovery contract. Case start remains fail closed while any required re-upload is outstanding.

## 13. PH12-QG-002 Unit Tests

Adapter and orchestration tests cover both `UPLOADED` and `PROCESSING` restart recovery, the exact automation transition, event and exception behavior, ordinary-intake rejection, same-case targeted retry, two simultaneous interrupted documents, staged retries, supersession/source history, and preservation of completed document evidence.

Result: focused Phase 12 adapter suite — **14 passed**.

## 14. PH12-QG-002 Genuine Mongo Tests

The real-Mongo interrupted-document composition test persists a case containing interrupted documents A and B plus completed document C, restarts the application, verifies the durable recovery state, rejects ordinary intake, retries the exact failed documents, and asserts provider call deltas. It was collected but skipped locally because MongoDB was unavailable.

## 15. PH12-QG-003 Coverage Added

`apps/backend/tests/test_phase12_real_mongo.py` now contains 11 genuine-Mongo tests covering successful composition, corrupt identity, interrupted-document recovery, safe technical failure, uncertain target recovery, replacement/stale decisions, stale-envelope CAS, cross-repository lost updates, Phase 11 atomic success, stale-CAS rollback, and injected pre-commit rollback.

The module continues to use a unique test database per run and removes only that owned database during teardown.

## 16. Genuine Mongo CAS Test

Two independent store instances read the same envelope. Writer A persists successfully; writer B then receives the expected concurrency conflict from the stale version. The final durable record contains only A's mutation.

## 17. Real Mongo Phase 11 Atomicity Test

The successful `USE_DOCUMENT_VALUE` path proves that the canonical legal-name change and the decision resolution commit together. Separate adverse tests prove that a stale CAS conflict and an injected pre-commit fault leave neither atomic half applied, while unrelated concurrently committed demo-section data remains intact.

## 18. Recovery-Pending Test

A persisted target delivery with `IN_PROGRESS` state and an attempted-send marker restarts as `RECOVERY_PENDING`. Explicit resume is required, and automatic startup does not replay the provider call.

## 19. Technical-Failure Test

A persisted `TECHNICAL_FAILURE` case restarts with its safe public error metadata, attempt counters, and terminal automation state preserved. Startup does not replay Registry, IDP, Ownership, or GoldTier providers.

## 20. Replacement and Stale-Decision Test

The real-Mongo suite persists A and B, replaces B with B2, restarts, and verifies A and B2 are current while B is superseded. Old source identifiers remain stale, an old decision request receives conflict, and restart produces no provider calls.

## 21. Cross-Repository Lost-Update Test

Independent document and automation repositories read the same case version. A document mutation commits; a stale automation mutation then fails CAS. The document update remains durable and the stale automation update does not overwrite it.

## 22. Provider Call Counts

Recovery assertions use explicit deltas. Restart performs zero automatic provider replays. Targeted interrupted-document retry increments IDP only for the replacement, with Registry, Ownership, and GoldTier unchanged. Completed-case, technical-failure, uncertain-delivery, and replacement restart scenarios also assert zero unexpected calls.

## 23. Security Review

The integration-security review found no new Critical or High issue in the remediation. Corrupt identity fails before cross-case projection; persistence errors remain safe and do not expose raw MongoDB data. Recovery stores safe codes and identifiers, not document bytes or provider payloads. The targeted retry remains inside the existing authenticated case/document boundary and does not introduce a new external connector path. No secret, token, credential, certificate, raw confidential artefact, or KYC/PII logging was added.

## 24. Documentation Corrected

The README, Phase 12 architecture, persistence/recovery contract, project context, security boundary, and POC regression catalogue now describe the canonical identity invariant, fail-closed corrupt-state behavior, exact interrupted-document transition, ordinary-intake guard, targeted retry, multi-document handling, and completed-evidence reuse.

## 25. Files Changed

Remediation changes:

- `.agents/skills/poc-regression-check/references/regression-catalogue.md`
- `.ai-pipeline/reports/PHASE_12_REMEDIATION.md`
- `README.md`
- `apps/backend/app/domain/zero_touch.py`
- `apps/backend/app/persistence/mongo_case_store.py`
- `apps/backend/app/services/zero_touch_orchestration.py`
- `apps/backend/tests/test_phase12_persistence.py`
- `apps/backend/tests/test_phase12_real_mongo.py`
- `docs/PROJECT_CONTEXT.md`
- `docs/architecture/PHASE_12_DURABLE_PERSISTENCE_RESTART_RECOVERY.md`
- `docs/contracts/PERSISTENCE_RECOVERY_PROFILE.md`
- `docs/security/POC_SECURITY_BOUNDARIES.md`

Pre-existing working-tree items were preserved: `.ai-pipeline/reports/PHASE_12_EXECUTION.md`, `.ai-pipeline/reports/PHASE_12_QUALITY_GATE.md`, the unrelated untracked filename beginning `e workspace and multi-document intake`, and inaccessible pytest-cache directories.

## 26. Phase 09 Regression

Phase 09 regression suite: **39 passed**.

## 27. Phase 10 Regression

Phase 10 regression suite: **52 passed**.

## 28. Phase 11 Regression

Phase 11 reconciliation and remediation suites: **58 passed**.

## 29. Pre-Phase 12 Regression

Pre-Phase 12 regression suite: **31 passed**.

## 30. Phase 12 Focused Verification

- Adapter/remediation tests: **14 passed**.
- Genuine-Mongo tests: **11 collected, 11 skipped** because `PHASE12_MONGO_URI` was not configured.
- Ruff on application and Phase 12 tests: **passed**.
- Strict mypy: **passed for 72 source files**.

## 31. Full Backend Verification

The CI-equivalent backend run from `apps/backend`, with the repository root on `PYTHONPATH`, collected 715 tests: **704 passed, 11 skipped**. The skips were exactly the genuine-Mongo tests.

An initial repository-root pytest attempt was not used as evidence because pytest encountered pre-existing inaccessible frontend/root cache directories during collection. It ran no tests. The scoped backend command above completed successfully.

## 32. Frontend, Contract, and Security Verification

- Frontend dependency tree: **passed** (`npm ls --all`; optional platform packages reported only).
- Frontend typecheck: **passed**.
- Frontend tests: **58 passed**.
- Frontend production build: **passed** (29 modules transformed).
- Contract tests: **44 passed**.
- Security tests: **5 passed**.
- GoldTier validator unit tests: **5 passed**.
- Secret scan: **clean**.
- Dependency consistency: **passed** (`pip check`: no broken requirements).
- Delivery asset tests: **4 passed**.
- Fixture validation: **19 valid, 19 invalid/quarantined, 48 not validated**, matching the configured classifications.
- Broad Ruff check over `apps/backend`, `scripts`, and `tests`: **passed**.
- `git diff --check`: **passed**; Git emitted line-ending conversion warnings only.

## 33. Windows Lifecycle Verification

The elevated Windows lifecycle suite passed **13 of 13 tests**. It exercised verified start, reset, stop, ownership mismatch refusal, occupied-port refusal, stale metadata handling, partial records, and unrelated-process protection. Final residue checks found:

- `.runtime/demo-processes.json`: absent
- listeners on ports 8000 and 5173: zero
- project-owned Python/Node processes: zero

The first sandboxed lifecycle attempt was invalid because Windows denied required process-tree termination and left partial launcher metadata. The exact project-owned partial session was stopped with the repository stop script before the suite was rerun outside the sandbox.

## 34. Local Mongo Availability

No local MongoDB URI was supplied through `PHASE12_MONGO_URI`. The real-Mongo module therefore performed its intentional module-level skip. No claim is made that the new genuine-Mongo assertions passed locally.

## 35. Current-Head CI Requirement

Prior `phase12-mongo` CI evidence belongs to commit `d2551e8` and cannot validate these uncommitted remediation changes. After the user reviews, commits, and pushes this working tree, the current commit must receive a successful `phase12-mongo` run. That run must show all 11 genuine-Mongo tests executing rather than skipping. The old green run must not be reused as remediation evidence.

## 36. Q-012 and Q-015

Q-012 (sponsor hosting/persistence constraints) and Q-015 (final MongoDB/transaction topology) remain open sponsor/environment questions. This remediation does not claim production topology approval. The genuine-Mongo tests require a replica-set-capable transaction environment, and the current implementation remains a POC durability design pending those answers.

## 37. Remaining Risks

- The 11 adverse real-Mongo tests are implementation-complete but unexecuted in this local environment.
- Current-head CI evidence does not exist until the remediation is committed and pushed by the user.
- Q-012 and Q-015 continue to limit production-readiness claims.
- The pre-existing inaccessible cache directories and unrelated untracked files were deliberately not modified.

No remaining local code, documentation, lint, type, frontend, contract, security, regression, or Windows lifecycle failure is known for the assigned remediation scope.

## 38. Readiness

The remediation is ready for user review and current-head genuine-Mongo CI verification. It is not a Phase 12 re-quality-gate result and does not authorize Phase 13. A new independent quality-gate run should occur only after the current-head `phase12-mongo` workflow passes.

READY FOR PHASE 12 REMEDIATION CI VERIFICATION
