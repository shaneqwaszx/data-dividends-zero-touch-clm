# Phase 12 — Independent Quality Gate

Date: 2026-08-31
Branch: `phase/12-durable-persistence-restart-recovery`
HEAD / PR #19 head: `d2551e827de736b82540e0e644e106895f73d95d`
Review mode: independent, report-only combined quality gate

## 1. Verdict

**FAIL.** Phase 12 has genuine current-head Mongo restart evidence and its principal
repository/CAS/replay-prevention design is sound, but two High defects violate mandatory
acceptance criteria:

1. a persisted Mongo `_id` that disagrees with the envelope `case_id` is silently accepted;
2. an interrupted document is classified as `DOCUMENT_REUPLOAD_REQUIRED` while its
   automation remains `RUNNING`, leaving every available re-upload/retry path blocked.

Phase 12 is not safe to merge. PR #19 must remain draft/not-ready, and Phase 13 planning is
not authorized by this gate.

## 2. Scope Reviewed

Reviewed `AGENTS.md`, project context, the Phase 12 planner and execution report, final
accepted Phase 09/10/11 and Pre-Phase 12 gates, reviewer/tester/contract/security roles,
the repository quality/security/regression skills and checklists, the complete
`main...HEAD` diff, all changed implementation/tests/UI/CI/documentation, and current PR
checks/logs. No implementation, test, CI, configuration, or ordinary documentation fix
was made.

## 3. Git / Branch / PR State

- Branch and local HEAD match the expected Phase 12 branch and remote PR #19 head exactly.
- PR #19 is open and draft against `main`.
- Current-head GitHub jobs `backend`, `frontend`, `phase12-mongo`,
  `demo-lifecycle-windows`, and `security` are green. Two event-triggered runs are shown;
  both sets are green.
- Pre-existing local state was preserved: modified regression catalogue, modified Phase 12
  execution report, inaccessible frontend pytest-cache directory, and the pre-existing
  oddly named untracked file.
- No file was staged, committed, pushed, merged, rebased, stashed, reset, or cleaned.

## 4. Accepted Baseline

Phase 09 call-stopping, Phase 10 four-operation Registry acquisition, Phase 11 no-source-
precedence/decision/atomicity invariants, and the Pre-Phase 12 workspace, history, review
queue, safe PDF/DOCX/TXT multi-document behavior remain accepted. Focused regression
suites all pass in this review. No Phase 13 implementation or prohibited live-integration
scope was found.

## 5. Phase 12 Architecture

**PASS with the findings below.** Business services consume repository interfaces.
`PersistenceBundle` selects memory repositories or Mongo adapters sharing one
`MongoCaseStore`; PyMongo collections do not enter business services. One case envelope
provides a coherent bounded persistence and atomic-update boundary.

## 6. Process-Local State Inventory Review

**PASS.** Independent searches reproduced the reported 13 holders: onboarding, documents,
document insertion order, ownership, reconciliation, CLM, automation, target ledger,
provider factories, demo scenarios, fault counters, Mock GoldTier correlation, and case
locks. Items required for restart are durable or safely reconstructed. Fault counters,
connector correlation, and process locks are legitimately runtime-only; configuration
cache and function-local ownership traversal maps are not authoritative case state.

## 7. Memory/Mongo Mode Review

**PASS.** `memory` does not construct/contact Mongo and remains process-local. `mongo`
selects only Mongo repositories and exposes the bounded `Mongo-backed durable POC` label.
There is no fallback branch from Mongo to memory.

## 8. Mongo Fail-Closed Behavior

**PARTIAL / FAIL for corrupt identity.** Missing URI raises
`PERSISTENCE_CONFIGURATION_INVALID`. An independent unreachable-server probe raised the
message-free `PersistenceUnavailableError / PERSISTENCE_UNAVAILABLE`; no memory fallback
occurred. Unknown schema versions and extra nested fields are rejected. However,
PH12-QG-001 proves that one class of corrupt persisted identity is accepted rather than
failing closed.

## 9. Genuine Mongo CI Evidence

**PASS.** Current PR head `d2551e8` was checked out through merge ref `c689076`. The job
started official `mongo:7`, waited for `mongosh ... ping` health to report healthy, and ran
`python -m pytest tests/test_phase12_real_mongo.py`. Result: **1 passed, 1 warning in
2.38s**. It executed; it was not skipped.

## 10. Genuine Mongo Test Quality

**Meaningful but incomplete.** It creates a unique
`clm_phase12_test_<uuid>` namespace, uses real PyMongo, creates state with composition A,
closes it, creates composition B against the same store, checks completed/pending/review
visibility and zero read-triggered provider calls, then drops only its own namespace. It
does not reuse one repository object and is not ceremonial. It does not cover the two
High counterexamples or most adverse recovery/CAS/atomicity cases; see PH12-QG-003.

## 11. Persistence Envelope / Schema Version

**FAIL.** The DTO is explicit, `extra="forbid"`, schema-versioned, bounded, and validates
nested case/submission bindings. Future schema version and unknown-field probes fail
safely. But `MongoCaseStore._decode` copies the Mongo document and removes `_id` before
validation without comparing it with `case_id` (`mongo_case_store.py:168-177`). A direct
probe changed only `_id`; decode succeeded with `mongo_id_matches_case_id=False`.

## 12. Serialization Fidelity

**PASS for declared values.** The serializer uses strings for UUID/Decimal, UTC ISO-8601
for datetimes, enum values, and recursive declared fields. Full completed adapter-envelope
round trip preserved nested reconciliation, ownership Decimal evidence, document links,
automation, and target state. No binary floating-point conversion is used.

## 13. Optimistic Concurrency

**PASS by implementation; real-Mongo stale-writer test absent.** Every replacement filters
on `_id` plus expected envelope `revision`, increments revision, and treats a zero match as
`PersistenceConflictError`. Aggregate repositories retain expected-version checks. There
is no unconditional last-write-wins path.

## 14. Shared-Envelope Lost-Update Review

**PASS for the supported single-instance model.** Each logical repository reloads the
current envelope while holding the shared process lock, modifies one section, and CAS
replaces the envelope. A cross-process stale snapshot loses the CAS rather than another
section. This is not active-active/distributed locking, and no such claim is made.

## 15. Phase 11 Atomicity Under Mongo

**PASS by code boundary, with coverage debt.** `MongoReconciliationUnitOfWork` validates
current reconciliation version and onboarding/entity fingerprints, then writes canonical
and reconciliation candidates in one envelope CAS. Conflict or injected pre-commit fault
writes neither half. The Phase 11 58-test baseline remains green; a genuine-Mongo
atomic-fault test is not present.

## 16. Onboarding / Registry Persistence

**PASS.** Identity, jurisdiction/resolution, canonical entity, normalized four-operation
Registry acquisition, safe errors/events, and timestamps are in the envelope. The normal
real-Mongo path produced eight Registry calls for two eligible cases before restart and
zero after composition-B reads.

## 17. Document Persistence / Raw-Data Boundary

**PASS for completed evidence; FAIL for interruption recovery.** Ordered bounded document
records, structured fields, provenance, decisions, events, and supersession links persist.
No upload bytes, OOXML members, complete TXT/DOCX/PDF body, or raw IDP payload is a
document-record field. PH12-QG-002 blocks the promised interrupted-document re-upload.

## 18. Reconciliation / Decision Persistence

**PASS.** Observations, raw/normalized bounded field values, outcomes, discrepancy IDs,
actions, fingerprints, decisions, source-document versions, and history serialize. An
independent composition-A/B conflict probe retained `WAITING_FOR_REVIEW` and an identical
reconciliation projection. No automatic Registry/Document/confidence/recency winner was
introduced.

## 19. Ownership Persistence

**PASS.** Parties, relationships, exact Decimal paths/aggregates, issues, classifications,
versions, and timestamps persist. The existing deterministic ownership engine remains the
sole calculator.

## 20. CLM / Automation Persistence

**PARTIAL.** Readiness, immutable submission snapshot, CLM events/status, automation
metrics/events/checkpoints, typed review/technical state, and opaque ownership binding are
durable. Terminal and normal states reconstruct. Interrupted document automation is not
coordinated with the recovered document state; see PH12-QG-002.

## 21. Target Execution Ledger

**PASS.** Immutable input and idempotency bindings, ordered attempted-operation prefix,
safe target outcome, and receipt are durable. Model validation enforces
`IN_PROGRESS -> TARGET_OUTCOME_RECORDED -> FINALIZED` shapes and exact ordered prefixes.

## 22. Interrupted Side-Effect Recovery

**PASS.** Each target marker is persisted before its side-effecting call. An attempted
`IN_PROGRESS` operation with no retained outcome is uncertain and is not deleted or
replayed. Startup projects an active Mock-GoldTier automation to `RECOVERY_PENDING`;
explicit progression encounters `CLM_TARGET_OUTCOME_UNCERTAIN` and returns the retained
recovery state. A retained outcome finalizes without another connector call.

## 23. Provider / Demo Binding Persistence

**PASS.** Durable bindings are deterministic SHA-256 IDs for only the Registry acquisition
provider or enumerated Mock ownership scenarios. Unknown IDs resolve to none; no user
module/class path, dynamic import, provider object, or credential is persisted. Demo
scenario conversion uses a closed enum.

## 24. PENDING_INPUTS Restart

**PASS.** Real-Mongo composition A/B retained the pending case and Registry state, with no
provider call on list/open. Completed structured documents, when present, are stored rather
than reprocessed.

## 25. WAITING_FOR_REVIEW Restart

**PASS with test-depth limitation.** Real Mongo retained a Registry-stage review case.
An independent full-envelope composition A/B probe retained a document conflict with the
same reconciliation projection. The genuine test does not assert two discrepancy-bearing
review cases or cross-case resolution isolation.

## 26. COMPLETED Restart

**PASS.** Genuine Mongo reconstructed the completed case, three documents, automation,
and target result in a new composition. Case/list/document reads added Registry 0, IDP 0,
Ownership 0, and GoldTier 0 calls.

## 27. TECHNICAL_FAILURE Restart

**PASS by strict serialization/terminal invariants; genuine-Mongo case absent.** Automation
technical failure and safe error are declared envelope state, and the terminal transition
table forbids transformation into success/review/pending. The dedicated real-Mongo test
does not create this case.

## 28. RECOVERY_PENDING Restart

**PASS by implementation/round trip; genuine-Mongo case absent.** Automation recovery
status and target outcome/ledger state persist. Finalization-only recovery consumes a
retained outcome; uncertain `IN_PROGRESS` remains blocked and is not automatically replayed.

## 29. Document Reupload Boundary

**FAIL — PH12-QG-002 (High).** `MongoCaseStore._recover_interrupted` rewrites
`UPLOADED/PROCESSING` to `FAILED / DOCUMENT_REUPLOAD_REQUIRED`
(`mongo_case_store.py:189-226`) but changes automation only for uncertain Mock GoldTier
(`:243-271`). The case therefore remains `RUNNING` at Document. `retry_intake_document`
requires `PENDING_INPUTS` (`zero_touch_orchestration.py:380-385`), ordinary start/resume
rejects the failed current document (`:444-448`), and general replacement requires
`WAITING_FOR_REVIEW` (`:484-498`). The independent executable probe returned:

- document `FAILED / DOCUMENT_REUPLOAD_REQUIRED`;
- automation `RUNNING`;
- `/resume` 409 `ZERO_TOUCH_INTAKE_INCOMPLETE`;
- intake retry 409 `ZERO_TOUCH_INTAKE_NOT_OPEN`.

The documented explicit retry/re-upload path does not exist for the recovered state.

## 30. Replacement / Supersession Restart

**PASS by envelope model and prior behavior, with Phase 12 coverage debt.** Both directional
replacement IDs, timestamps, complete document history, reconciliation source-document
IDs/counts, and decision fingerprints persist. Current-evidence selection continues to
exclude superseded records. No dedicated Phase 12 restart test exercises `A, B -> B2` or
post-restart stale decision replay.

## 31. Case History Durability

**PASS.** Real Mongo retained three independently created cases across composition A/B;
list/open remained side-effect free. Store ordering is deterministic by `updated_at`, then
`case_id`, descending. The genuine test checks membership/status but not exact order.

## 32. Review Queue Durability

**PASS with limited genuine coverage.** Queue derivation uses durable automation state,
and the real test returned only the waiting case, excluding pending/completed. It tests one
waiting case rather than the requested two-review-case isolation scenario.

## 33. Provider Call Counts Before / After Restart

Genuine Mongo composition A recorded Registry **8**, IDP **3**, Ownership **1**, and Mock
GoldTier **4**. After composition B list/detail/document/review/profile reads, additional
calls were Registry **0**, IDP **0**, Ownership **0**, GoldTier **0**.

## 34. Startup Behavior

**PASS for provider side effects; partial for state recovery.** Startup pings Mongo, creates
indexes, validates envelopes, and performs bounded interrupted-state classification. It
does not run workflows or call providers. Its document classification is internally
incomplete as described in PH12-QG-002.

## 35. Indexes / Retention

**PASS.** Indexes cover unique `case_id`, automation status plus update time, target
submission, and document lookup. No TTL, purge, GridFS, wildcard cleanup, automatic
migration, or sponsor-undefined deletion was introduced.

## 36. API / Secret / Logging Security

**FAIL for cross-case identity integrity; otherwise PASS.** `MONGO_URI` is `SecretStr`,
namespace names are grammar/length bounded, normal APIs accept typed IDs rather than query
documents, and URI/database/raw PyMongo errors are absent from health/profile/browser
models. Secret tests and scan are clean. PH12-QG-001 could project the wrong case beneath a
requested Mongo key after corruption and is therefore also a security/isolation defect.

## 37. Frontend Durability Disclosure

**PASS.** Memory is described as cleared by restart. Mongo is labelled durable POC and
explicitly not a production audit repository; assignment remains session-only. No HA,
regulatory-retention, bank-grade, live-interoperability, or Ready-for-Approval claim was
found. Typecheck, tests, and build pass.

## 38. Phase 09 Regression

**PASS — 39 passed, 1 existing warning.** Jurisdiction unresolved/conflict/provider-not-
implemented/identifier-ineligible still stop Registry, IDP, Ownership, and GoldTier.

## 39. Phase 10 Regression

**PASS — 52 passed, 1 existing warning.** Normal Registry operation counts and mandatory
ownership evidence invariants remain accepted.

## 40. Phase 11 Regression

**PASS — 58 passed, 1 existing warning.** No precedence, false-clear prevention, stale
decision protection, legal-name-only document selection, atomic process-local behavior,
multiple blockers, and replacement behavior remain green.

## 41. Pre-Phase 12 Regression

**PASS — 31 passed, 1 existing warning.** History/queue, PDF/DOCX/TXT/folder intake,
strict PDF/DOCX protection, multi-document reconciliation, replacement, and call stopping
remain green.

## 42. Phase 12 Focused Tests

Local result: **5 passed, 1 skipped, 1 warning**. The skipped test is the genuine-Mongo
test because `PHASE12_MONGO_URI` is not configured locally; it executed in current-head CI
and passed. The five-test focused suite does not cover the two High counterexamples.

## 43. Full Backend / Static Checks

- Repository-correct local backend: **743 passed, 1 skipped, 4 warnings in 49.75s**.
- Current-head isolated CI backend: **695 passed, 1 skipped, 4 warnings in 22.87s**.
- Ruff: **PASS**.
- Strict mypy: **PASS, 72 source files**.
- The first local full-suite command omitted repository-root `PYTHONPATH` and had two
  collection import errors; it was corrected and rerun successfully as required.

The difference in local versus CI collection totals is reported rather than normalized;
both completed green apart from the expected local/normal-job real-Mongo skip.

## 44. Frontend / Contract / Security Checks

- Frontend: `npm ls --all` exit 0 (platform/feature packages reported only as optional),
  typecheck PASS, **58 tests passed**, build PASS with **29 modules transformed**.
- Contract tests: **44 passed**.
- Secret tests / repository scan: **5 passed / clean**.
- GoldTier validator tests: **5 passed**; fixtures **19 valid, 19 quarantined, 48 not
  validated**.
- Delivery assets: **4 passed**.
- Local `pip check`: **FAIL** because the shared host has unrelated
  `python-telegram-bot 20.7` requiring older `httpx`; current-head isolated CI `pip check`
  says **No broken requirements found**. This is local environment contamination, not a
  project dependency defect.

## 45. Windows Lifecycle

**PASS — 13/13 in 152.988s.** Post-run checks: `.runtime/demo-processes.json` absent;
ports 8000 and 5173 have zero listeners; project-owned Python/Node process count is zero.
Current-head CI independently passed 13/13 in 123.017s.

## 46. CI Review

**Green but insufficient to override reproduced defects.** For the exact remote head:
backend, frontend, phase12-mongo, demo-lifecycle-windows, and security all succeeded.
Mongo executed rather than skipped. Existing CI lacks adversarial cases for mismatched
Mongo identity and interrupted-document re-upload, so green CI does not establish those
acceptance criteria.

## 47. Documentation Accuracy

**FAIL on one material claim.** README, project context, architecture, persistence profile,
configuration, security, decision D-033, and open questions otherwise match the implemented
bounded POC. The Phase 12 architecture/profile claim that interrupted processing permits
explicit retry/re-upload is false for the actual recovered automation state (PH12-QG-002).

## 48. Q-012 / Q-015

**PASS.** Q-012 remains explicitly OPEN for authoritative/live ACRA contract/access. Q-015
remains explicitly OPEN for source/reviewer authority, audit/retention/deletion/encryption/
backup policy, reviewer governance, and production restart semantics. Phase 12 does not
claim to close either question.

## 49. Findings by Severity

### Critical

None.

### High

- **PH12-QG-001 — Mongo key/envelope identity mismatch is accepted.** Evidence:
  `apps/backend/app/persistence/mongo_case_store.py:168-177`. Consequence: corrupt durable
  data under `_id=A` can decode as case B, so `get(A)` can return B while `get(B)` cannot
  find it, violating corrupt-data fail-closed behavior and cross-case isolation. Required:
  reject any missing/noncanonical/mismatched `_id` before returning a snapshot and add
  startup/get/list adversarial tests against genuine Mongo.
- **PH12-QG-002 — interrupted documents cannot be retried after restart.** Evidence:
  `mongo_case_store.py:189-226,243-271` and
  `zero_touch_orchestration.py:380-385,444-448,484-498`. Consequence: the case advertises
  re-upload required but is stranded in `RUNNING`; all progression/re-upload routes reject
  it. Required: recover automation and document into one truthful retryable state, expose
  only the bounded affected-document retry, and prove composition A/B recovery with zero
  unrelated provider replay.

### Medium

- **PH12-QG-003 — mandatory adverse restart coverage is materially incomplete.** The real
  test proves completed/pending/one review read durability, but not technical failure,
  recovery pending, interrupted documents, replacement/stale decisions, stale Mongo CAS,
  cross-repository lost-update, or Mongo Phase 11 atomic fault paths. The focused suite's
  five passing tests did not catch PH12-QG-001/002. Add bounded real-Mongo and adapter
  tests for these acceptance cases; do not merely assert DTO presence.

### Low

- Existing Starlette/httpx deprecation and deliberate malformed-provider serializer
  warnings remain non-blocking.
- Local shared-Python `pip check` is contaminated by unrelated `python-telegram-bot`; the
  isolated current-head backend job is clean.

## 50. Remaining Risks / Technical Debt

Accepted, non-blocking limitations remain: single active application instance, no
distributed locks/workers/exactly-once guarantee, runtime-only fault injection and Mock
connector correlation, no production RBAC/reviewer assignment, no retention/purge/backup/
restore/encryption-at-rest certification, and no live ACRA or real GoldTier/PingFed proof.
These do not excuse PH12-QG-001 or PH12-QG-002.

## 51. Merge / Next-Phase Readiness

Merge is **not authorized**. Phase 13 planning is **not authorized** by this gate. Remediate
PH12-QG-001 and PH12-QG-002, add the bounded adverse restart tests in PH12-QG-003, rerun the
complete matrix including genuine Mongo at the new PR head, and request a report-only
Phase 12 re-quality gate. Live ACRA and real GoldTier readiness remain separately blocked
by sponsor/environment dependencies.

FAIL — PHASE 12 REMEDIATION REQUIRED
