# Phase 12 — Durable CLM Case Persistence & Restart Recovery — Execution Report

## 1. Executive Summary

Implemented explicit process-local memory and fail-closed Mongo persistence behind the
existing repository/service boundaries. Mongo uses one schema-versioned structured
case envelope, single-document revision compare-and-set, durable target checkpoints,
and conservative restart classification. Local non-Mongo verification remains green;
the local environment could not host Mongo because Docker Desktop's backend crashed
before its engine started. The required genuine-Mongo proof subsequently executed
successfully in GitHub Actions: the `phase12-mongo` job started a real `mongo:7`
service, waited for it to become healthy, and ran
`tests/test_phase12_real_mongo.py`, which passed without being skipped. Phase 12 is now
ready for independent Quality Gate review; that independent gate has not yet occurred.

## 2. Accepted Baseline

Preserved the Phase 09 jurisdiction gateway, Phase 10 four-operation Registry
acquisition, Phase 11 reconciliation/resume, and Pre-Phase 12 workspace/multi-document
flow. No ACRA, UBO, source-authority, GoldTier, or approval policy changed.

## 3. Process-Local State Inventory

Thirteen mutable maps were found: onboarding cases; document records; document
insertion sequence; ownership; reconciliation; CLM; automation; target ledger;
ownership-provider factories; demo scenarios; finalisation-fault counters; Mock
GoldTier external-key correlation; and per-case locks.

Authoritative items become durable or deterministically reconstructible in Mongo.
Per-process locks, consumed fault-injection counters, and connector-instance correlation
remain runtime-only; uncertain target execution blocks replay instead of depending on
connector memory.

## 4. Chosen Persistence Architecture

Business services still depend on repository interfaces. `PersistenceBundle` selects
existing in-memory repositories or Mongo adapters sharing one `MongoCaseStore`.
PyMongo collections never enter business services.

## 5. Why This Storage Design Was Chosen

One case envelope avoids multi-collection transactions, preserves case isolation, and
provides one atomic boundary for coordinated canonical/reconciliation state in the
bounded POC.

## 6. Mongo Configuration

Added `CLM_PERSISTENCE_MODE`, `MONGO_DATABASE`, and `MONGO_CASE_COLLECTION` alongside
backend-secret `MONGO_URI`. Memory is the explicit default. Mongo mode requires a URI,
pings/validates during composition, and never falls back to memory.

## 7. Persistence DTO / Schema Version

`DurableCaseSnapshot` is strict and explicit, with `schema_version=1`, bounded nested
sections, controlled UUID/Decimal/UTC datetime serialization, and cross-record case/
submission binding validation. Unknown versions and malformed envelopes fail closed.

## 8. Optimistic Concurrency

All Mongo replacements filter on `_id` plus expected envelope `revision`, then increment
the revision. Aggregate expected versions remain enforced for Ownership,
Reconciliation, CLM, and Automation. Stale writes do not become last-write-wins.

## 9. Atomicity Model

The Mongo reconciliation unit of work validates current fingerprints/version and writes
the canonical legal-name candidate plus decision in one envelope CAS. A conflict or
pre-commit failure writes neither half. Memory mode retains the accepted shared-lock
rollback unit of work.

## 10. Onboarding Persistence

Case identity, requested UEN, jurisdiction observations/resolution, canonical entity,
Registry acquisition, events, safe errors, state, and timestamps are in the envelope.

## 11. Registry Evidence Persistence

The normalized four-operation acquisition bundle, statuses, bounded parties/
relationships, safe provenance, issues, and timestamps persist. Raw Registry responses
and authorization do not.

## 12. Document Evidence Persistence

Ordered records retain display/media/size metadata, structured fields, confidence,
provenance, review events/decisions, and replacement/supersession links.

## 13. Reconciliation / Decision Persistence

Observations, outcomes, discrepancies, actions, fingerprints, decisions, source
document IDs, versions, status, and history persist and revalidate on reconstruction.

## 14. Ownership Persistence

Parties, relationships, exact Decimal paths/aggregates, provisional classifications,
issues, state, versions, and timestamps persist.

## 15. CLM / Automation Persistence

Readiness, warnings, immutable submission snapshot, CLM status/events, automation stage,
status, exceptions, metrics, timeline, technical failure, and checkpoints persist.

## 16. Target Execution Ledger Persistence

Immutable input/idempotency bindings, ordered attempted operations, safe target outcome,
and receipt now use a repository and persist in the case envelope.

## 17. Provider / Demo Binding Persistence

Automation stores stable opaque binding IDs that reconstruct only the configured
Registry provider or a known Mock ownership scenario. Safe demo scenario selection is
durable. Provider objects and credentials are never stored.

## 18. Raw Document Retention Boundary

Raw PDF/DOCX/TXT bytes, OOXML bodies, and full extracted text are absent. Completed
structured evidence survives; an `UPLOADED`/`PROCESSING` record at restart becomes
`DOCUMENT_REUPLOAD_REQUIRED` because its bytes cannot be recovered.

## 19. Startup / Restart Behavior

Mongo startup pings, creates bounded non-TTL indexes, validates every envelope, and
classifies interrupted document/target state. It performs no automatic workflow run.

## 20. PENDING_INPUTS Recovery

Reconstructs with the same ID, Registry evidence, completed document evidence, and
intake state. Adapter composition-A/B test passed.

## 21. WAITING_FOR_REVIEW Recovery

Reconstructs in history and backend-derived Review queue with stable evidence. Adapter
composition-A/B test passed.

## 22. COMPLETED Recovery

Reconstructs the completed automation, documents, ownership, CLM, and finalized target
ledger. Adapter composition-A/B and full serialization round trip passed.

## 23. TECHNICAL_FAILURE Recovery

The typed automation/onboarding error and status are part of the strict envelope and do
not transform on read/startup. DTO/domain round-trip coverage passes. The dedicated
real-Mongo restart proof exercises completed, pending-input, and waiting-review cases;
it does not add a separate real-Mongo technical-failure case.

## 24. RECOVERY_PENDING Recovery

Automation status and retained target outcome/receipt state persist. Existing explicit
finalisation-only recovery remains the progression authority.

## 25. Interrupted Operation Recovery

An `IN_PROGRESS` target entry with an attempted marker is retained and startup projects
RUNNING/RESUMING Mock-target automation to `RECOVERY_PENDING` with
`RECOVERY_STATE_UNCERTAIN`. Direct recovery-classification coverage passes.

## 26. Side-Effect Replay Prevention

Target intent and each ordered operation marker persist before the call. Safe terminal
outcome persists before rich receipt finalisation. An uncertain attempted operation is
not replayed; explicit resume retains recovery pending.

## 27. Case History / Review Queue Durability

Both derive from authoritative automation/onboarding records. No duplicate frontend
queue is persisted.

## 28. Frontend Durability Disclosure

Execution profile now reports `Process-local` or `Mongo-backed durable POC`. Dashboard
and Review describe restart behavior accurately and deny production audit claims.

## 29. Real Mongo Integration

Added `test_phase12_real_mongo.py` with isolated `clm_phase12_test_<uuid>` cleanup. It
creates completed, pending-input, and waiting-review cases in composition A, creates
composition B against the same Mongo data, verifies evidence/status/history/review,
and asserts provider counters do not change on read.

- Local: **SKIPPED** because no working Mongo server was available.
- GitHub CI: `phase12-mongo` used an isolated real `mongo:7` service and ran
  `tests/test_phase12_real_mongo.py`: **1 passed, 1 warning in 2.38s**. The test was not
  skipped.

The mandatory genuine-Mongo verification requirement is satisfied through CI. This was
an isolated CI integration environment, not a production Mongo deployment.

## 30. CI Changes

Added `phase12-mongo` using `mongo:7`, health checks, isolated test execution, and
`PHASE12_MONGO_URI`. Normal backend tests remain Mongo-independent. GitHub Actions
subsequently executed the job successfully: **`phase12-mongo = PASS`**. It started the
Mongo service, waited until it was healthy, and actually executed
`python -m pytest tests/test_phase12_real_mongo.py`; it did not merely compile or
collect the test. The broader PR checks were also green at verification time.

## 31. Security Review

No active Critical/High code finding was identified. URI is a `SecretStr`; namespace
settings are bounded; errors contain safe classes/codes only; no URI/database/credential
is exposed in health/profile/browser DTOs; raw upload/full text/raw external payloads are
not serialized; no TTL/purge/migration exists. Accepted limitations: local POC Mongo is
not application-layer encrypted compliance storage, production HA, or a regulatory
retention solution. Q-015 governs those production decisions.

## 32. Files Changed

- Pipeline/config: `.ai-pipeline/001_planner/PHASE_12_DURABLE_PERSISTENCE_RESTART_RECOVERY.md`,
  `.ai-pipeline/reports/PHASE_12_EXECUTION.md`, `.env.example`, `.github/workflows/ci.yml`,
  `README.md`.
- Backend: `app/persistence/{__init__,errors,models,mongo_case_store,repositories,composition}.py`,
  `app/services/target_execution_repository.py`, plus `composition.py`, `config.py`,
  `main.py`, `connectors/mock_ownership.py`, `demo/{scenarios,zero_touch_control}.py`,
  `domain/zero_touch.py`, and the affected onboarding/CLM/reconciliation/zero-touch
  service/repository/binding modules.
- Tests/UI: `test_phase12_persistence.py`, `test_phase12_real_mongo.py`, updated exact
  execution-profile backend tests, and frontend `App.tsx`, `App.test.tsx`, `types.ts`.
- Documentation: project context; architecture baseline/index/new Phase 12 document;
  contract index/new persistence profile; configuration; D-033; Q-015 note; demo
  runbook; security boundary; and the repository regression catalogue.

## 33. Exact Phase 12 Tests

- Local Phase 12: **5 passed, 1 genuine-Mongo skipped**. Passing coverage includes
  memory independence, missing-URI fail-closed, unknown schema, controlled DTO round
  trip/raw-data exclusion, adapter composition-A/B completed/pending/review
  reconstruction, private binding/fingerprint serialization, and uncertain target
  recovery classification.
- Genuine Mongo CI: **1 passed**. This was the previously skipped test executing against
  the healthy `mongo:7` service.

## 34. Real Restart Demonstration

The genuine restart proof executed through GitHub Actions. The test used an isolated
`clm_phase12_test_<uuid>` database, created application state through composition A,
closed that application, and created a fresh composition B against the same Mongo
store. Composition B reconstructed the durable completed, pending-input, and
waiting-review case state and verified restart-visible case history, completed-case
detail, three document records, the review queue, and the Mongo-backed execution
profile. It also executed the test's zero-provider-replay assertion for the
composition-B reads and dropped only its isolated test database in cleanup.

The same test remained skipped locally because the local Mongo/Docker runtime was not
available; the successful CI execution supplies the genuine-Mongo proof.

## 35. Provider Call Counts Before / After Restart

Before restart, the real-Mongo test asserts aggregate counts of Registry `8` (four
operations for each of the completed and pending-input cases), IDP `3`, Ownership `1`,
and Mock GoldTier `4` (`SEARCH`, `SHELL`, `POLICY`, and `AMEND` once for the completed
case). It snapshots those counters before composition B, then performs case list,
completed-case detail, document list, review-queue, and execution-profile reads and
asserts the complete counter dictionary remains unchanged.

Executed post-restart/read evidence is therefore:

- additional Registry calls: **0**;
- additional IDP calls: **0**;
- additional Ownership calls: **0**;
- additional GoldTier calls: **0**.

This exact counter proof passed in genuine-Mongo CI. Existing Pre-Phase 12 call-count
regressions also pass.

## 36. Phase 09 Regression

**39 passed.** Jurisdiction unresolved/conflict/provider-not-implemented/identifier-
ineligible still stop downstream calls.

## 37. Phase 10 Regression

**52 passed.** Four-operation Registry semantics and `1/1/1/1` normal calls preserved.

## 38. Phase 11 Regression

**58 passed.** False-clear, stale decision, legal-name atomicity, actionless unusable
evidence, replacement, and idempotent resume preserved.

## 39. Pre-Phase 12 Regression

**31 passed.** History/queue, PDF/DOCX/TXT routing, bounded intake, hostile document
protection, reconciliation, replacement, and call stopping preserved.

## 40. Full Backend / Frontend Verification

- Local backend: **696 collected; 695 passed, 1 genuine-Mongo skipped**.
- Dedicated genuine-Mongo CI integration: **1 passed**; the test executed rather than
  skipped.
- Ruff: pass. mypy strict: pass, 72 source files.
- Frontend: **58 passed**; typecheck and production build pass.
- `pip check`: pass. `npm ls --all`: exit 0 (platform/feature optional dependencies
  remain reported as optional).
- Contract: 44 passed. Delivery assets: 4 passed.
- Secret tests: 5 passed; repository secret scan clean.
- GoldTier validator tests: 5 passed; fixtures remain 19 valid, 19 quarantined, 48 not
  validated.

## 41. Windows Lifecycle

**13/13 passed in 155.309s.** Afterwards runtime metadata was absent, ports 8000/5173
had zero listeners, and the elevated process check found zero project-owned Python/Node
processes.

## 42. Documentation Updated

Updated every planner-required file plus Phase 12 architecture and persistence/recovery
profile, security boundary, demo runbook, contract index, and regression catalogue.

## 43. Sponsor Dependencies

Q-012 remains OPEN for authoritative ACRA APIs. Q-015 remains OPEN for source/reviewer
authority, durable audit/retention, RBAC, and production restart policy.

## 44. Non-Goals Confirmation

No live ACRA/ACRA+, foreign registry, real GoldTier/PingFed, related-party write,
GridFS/raw KYC retention, RBAC, notification/SLA, purge/TTL, migration platform,
distributed worker/lock/queue, HA, new UBO/source policy, or Ready-for-Approval claim.

## 45. Remaining Risks

1. Mongo persistence is intentionally single-instance; concurrent active nodes are not
   supported even though stale envelope CAS is detected.
2. The POC does not provide distributed exactly-once execution, distributed locks or
   workers, or production high availability.
3. The passing isolated CI integration is not a production Mongo deployment, production
   backup/restore exercise, or regulatory storage certification.
4. Q-015 remains open for source/reviewer authority, retention, deletion, encryption,
   backup, audit governance, and production restart policy.
5. Q-012 remains open for the authoritative live ACRA contract, access, authentication,
   and sandbox verification.

## 46. Readiness

The implementation is unchanged. Local verification remains green apart from the
environment-dependent genuine-Mongo skip, and the mandatory real-Mongo evidence has now
been satisfied by the successful `phase12-mongo` GitHub Actions execution against a
healthy `mongo:7` service. The real restart and zero-additional-provider-call assertions
executed and passed. The independent Phase 12 Quality Gate has not yet been performed.

READY FOR PHASE 12 QUALITY GATE
