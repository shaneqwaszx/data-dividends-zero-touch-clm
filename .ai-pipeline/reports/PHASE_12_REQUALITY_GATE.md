# Phase 12 — Independent Re-Quality Gate

Date: 2026-08-31  
Review mode: independent, report-only re-quality gate  
Scope: Phase 12 — Durable CLM Case Persistence & Restart Recovery

## 1. Executive summary

**PASS.** The current Phase 12 head closes both prior High findings, the prior
Medium evidence gap, and CI-F1. Corrupt Mongo identity fails closed on every durable
read path; interrupted current documents return to bounded same-case input recovery;
uncertain attempted target work remains `RECOVERY_PENDING` across repeated resumes;
and retained-outcome finalisation remains replay-free and functional. Current-head
genuine-Mongo CI, local regressions, frontend checks, static/security checks, and the
Windows lifecycle suite pass. No unresolved Critical or High finding remains.

## 2. Current branch / SHA / PR

- Branch: `phase/12-durable-persistence-restart-recovery`.
- Current branch and PR head: `e483f6e33f60240ddbfea672560c9fce7f1b31dd`.
- PR: #19, **Phase 12: durable persistence and restart recovery**, base `main`.
- PR state during review: Draft; merge state `CLEAN`.
- Current PR merge SHA exercised by pull-request CI:
  `e066d1c9c75e8eb1632f9d6e76b4c7d094f01290`, explicitly recorded by checkout as
  merging head `e483f6e` into base `cf382eb`.
- Superseded evidence at `d2551e8`, `923547d`, and `614e1da` was not used to close
  this gate.
- Before this report, there were no staged or tracked working-tree edits. The
  pre-existing unrelated untracked filename beginning `e workspace and multi-document
  intake` and inaccessible pytest-cache directories were not modified.

## 3. Previous gate findings

- **PH12-QG-001 — High:** Mongo `_id` and embedded `case_id` could disagree.
- **PH12-QG-002 — High:** interrupted documents could be marked re-upload-required
  while automation remained unusable.
- **PH12-QG-003 — Medium:** genuine-Mongo adverse restart/CAS/atomicity evidence was
  incomplete.
- **CI-F1 — High safety consequence:** uncertain target work restarted pending but a
  stale terminal CLM projection could make explicit resume return false `COMPLETED`.

All four are independently closed below.

## 4. Current CI evidence

GitHub PR metadata and job logs were inspected, not only check icons.

| Evidence | Run / job | Checkout | Exact result |
| --- | --- | --- | --- |
| Push `phase12-mongo` | `33363697770` / `99399935147` | exact head `e483f6e33f60240ddbfea672560c9fce7f1b31dd` | Mongo 7 healthy; `python -m pytest tests/test_phase12_real_mongo.py`; **11 passed, 0 skipped, 0 failed** in 6.29s |
| PR `phase12-mongo` | `33363701395` / `99399944478` | merge SHA `e066d1c...`, containing head `e483f6e...` | Mongo 7 healthy; same test module; **11 passed, 0 skipped, 0 failed** in 6.43s |
| Push Windows lifecycle | `33363697770` / `99399935237` | exact head `e483f6e...` | **13 passed** in 125.828s |
| Current-head backend | push and PR checks | exact head / current merge SHA | **706 passed, 11 skipped**, with the skips limited to real-Mongo tests in the non-Mongo backend job |

All ten current rollup checks were successful: backend, frontend, security,
demo-lifecycle-windows, and phase12-mongo for both push and pull-request triggers.

## 5. PH12-QG-001 re-test

**ID:** PH12-QG-001  
**Severity:** High  
**Status:** CLOSED  
**Evidence:** `MongoCaseStore._decode` first requires a string `_id`, parses it as a
UUID, requires the already-canonical lowercase string form, reconstructs the strict
snapshot, and then requires `_id == str(snapshot.case_id)`. Missing, integer,
malformed, uppercase/noncanonical, and valid-but-mismatched keys were executed by the
focused adapter suite. A separate runtime probe injected `_id=A/case_id=B` and observed
`PersistenceDataInvalidError` from `initialize`, `get`, `list`,
`find_by_submission`, and `find_by_document`. The current genuine-Mongo suite also
physically inserts `_id=A/case_id=B`, proves `get(B)` returns no case, and proves direct,
list, document-secondary, and composition-start reads fail closed. All store lookup
methods pass returned documents through the same decoder. No normalization, repair,
rewrite, deletion, or cross-case projection occurs.  
**Consequence if unfixed:** corrupt storage metadata could project one case as another.  
**Required remediation:** None; the previous required remediation is verified.

## 6. PH12-QG-002 re-test

**ID:** PH12-QG-002  
**Severity:** High  
**Status:** CLOSED  
**Evidence:** Executed adapter tests cover both `UPLOADED` and `PROCESSING`, plus a
mixed case containing one completed document and two interrupted current documents.
After recovery, each interrupted document is `FAILED /
DOCUMENT_REUPLOAD_REQUIRED`; automation is `PENDING_INPUTS` at `DOCUMENT`; completed
Registry state and completed document evidence/events are retained. Unrelated ordinary
intake returns `409 / ZERO_TOUCH_DOCUMENT_REUPLOAD_REQUIRED`. Retry requires the exact
same-case, current, failed document ID. Retrying A supersedes only A and leaves B
outstanding; ordinary intake remains blocked until B is individually retried. The
genuine-Mongo composition test proves restart adds Registry/IDP/Ownership/GoldTier
`+0`; retrying the affected document adds IDP `+1` and all other provider families
`+0`. The case ID and supersession lineage remain unchanged.  
**Consequence if unfixed:** a case could be durably stranded or bypass mandatory
re-upload and progress from incomplete evidence.  
**Required remediation:** None; the previous required remediation is verified.

## 7. PH12-QG-003 re-test

**ID:** PH12-QG-003  
**Severity:** Medium  
**Status:** CLOSED  
**Evidence:** The current 899-line real-Mongo module contains 11 executed tests, not a
single happy-path smoke. It covers completed/pending/review restart, corrupt identity,
interrupted-document recovery, safe technical failure, uncertain target recovery,
replacement/stale decision, two-store stale CAS, cross-repository lost update, and
Phase 11 atomic success/stale-CAS/pre-commit failure. Both current-head Mongo 7 jobs
executed all 11 with zero skip/failure.  
**Consequence if unfixed:** adapter doubles alone could miss real Mongo query, CAS, and
whole-envelope failure behavior.  
**Required remediation:** None; genuine-Mongo evidence now meets the gate.

## 8. CI-F1 uncertain-target re-test

**ID:** CI-F1  
**Severity:** High safety consequence  
**Status:** CLOSED  
**Evidence:** The adversarial state uses an `IN_PROGRESS` target ledger with Search
attempted, no target outcome, and no receipt, while retaining an older terminal-looking
CLM projection. On restart, GET returns `RECOVERY_PENDING`. Three successive
`POST /resume` calls each return `RECOVERY_PENDING`; adapter assertions prove unchanged
automation version, unchanged event count, unchanged ledger, and Search/Shell/Policy/
Amend `+0`. The genuine-Mongo test repeats resume three times and proves all provider
counters remain unchanged. `ClmOrchestrationService.submit` consults the target ledger
before every terminal-looking CLM early return, and zero-touch treats the typed
uncertainty result as an unchanged recovery record.  
**Consequence if unfixed:** unknown external side effects could be falsely reported as
successful completion.  
**Required remediation:** None; current-head runtime behavior and real-Mongo CI close
the defect.

## 9. Finalisation-only recovery

**PASS.** `TARGET_OUTCOME_RECORDED` remains distinct from uncertain `IN_PROGRESS`.
The retained-outcome/finalisation tests in `test_clm_orchestration.py` and
`test_zero_touch_orchestration.py` passed within the 240-test orchestration/provider
matrix. Explicit recovery finalizes retained success, match-found, policy-failure, and
partial-amend outcomes without another Search, Shell, Policy, or Amend call. The CI-F1
guard is narrowly conditioned on attempted work with neither outcome nor receipt; it
does not freeze legitimate finalisation-only recovery.

## 10. Completed restart

**PASS.** The genuine-Mongo three-case test creates a real completed case with three
documents, discards the first application composition, and opens a second composition.
Case status, document set, history-bearing structured envelope, reconciliation,
ownership, readiness, and target ledger remain available. List, GET, document read, and
resume retain `COMPLETED` and add Registry/IDP/Ownership/GoldTier `+0`.

## 11. Technical failure restart

**PASS.** A durable `TECHNICAL_FAILURE` retains its fixed safe public code/message after
a new composition. No provider counter changes, no success/review substitution, and no
automatic progression were observed.

## 12. Replacement/stale-decision restart

**PASS.** Real Mongo evidence performs A+B, replaces B with B2, restarts, and observes A
and B2 current and B superseded. Current reconciliation provenance contains A/B2, not B;
the old discrepancy/version/fingerprint request receives `409`; Registry is not replayed
and A is not reprocessed. Persisted source/document IDs prevent accidental regeneration
from reviving the stale decision.

## 13. Mongo identity

**PASS.** The authoritative invariant is exactly:

`mongo_document["_id"] == str(snapshot.case_id)`

The `_id` must already be canonical lowercase UUID text. Every envelope also validates
the onboarding, document, ownership, reconciliation, CLM, automation, and target-ledger
case bindings. Secondary queries never bypass decoding. Invalid identity is classified
as invalid persistence data and is not exposed through API/browser projections.

## 14. Mongo CAS

**PASS.** `replace` filters on canonical `_id` plus `revision=N` and persists revision
`N+1`. With two independent real stores at N, writer A succeeds and writer B receives
`PersistenceConflictError`; durable state contains only A's update.

## 15. Cross-repository lost-update test

**PASS.** Independent document and automation repositories read the same envelope.
The document repository commits its section; the stale automation whole-envelope write
is rejected; the document change remains durable and the stale automation mutation is
absent. No unrelated section is lost.

## 16. Phase 11 Mongo atomicity

**PASS.** The Mongo reconciliation unit of work validates current reconciliation
version and onboarding/entity fingerprints, prepares both candidates, and applies one
envelope CAS. Real-Mongo success proves legal name and decision resolve together.
Separate stale-CAS and injected pre-commit failures prove neither half persists; the
stale-CAS test also proves an unrelated concurrently committed demo section survives.

## 17. Provider replay/call-count evidence

- Completed three-document case before restart: Registry four operations `4`, IDP `3`,
  Ownership `1`, GoldTier Search/Shell/Policy/Amend `1/1/1/1`.
- Completed restart/list/GET/resume: every provider delta `+0`.
- Uncertain target restart plus three resumes: GoldTier `0/0/0/0`; no ledger, event, or
  automation-version growth.
- Technical-failure restart: every provider delta `+0`.
- Interrupted-document restart: every provider delta `+0`; one exact retry is IDP `+1`
  only until normal progression is explicitly permitted.
- Replacement restart: Registry `+0`, unchanged A IDP `+0`; only B2 was processed.
- Read-only history/review/case access remains provider-free.

## 18. Persistence architecture

**PASS.** `CLM_PERSISTENCE_MODE=memory|mongo` is explicit. Memory mode never contacts
Mongo. Mongo mode requires `MONGO_URI`, pings and initializes Mongo, and fails closed
without memory fallback. One `schema_version=1` envelope per case retains bounded
structured onboarding/Registry evidence, documents and supersession, reconciliation and
decisions, Decimal ownership, CLM/readiness, automation, safe demo binding, timeline,
and target intent/outcome/receipt state. Unknown schema, unknown fields, malformed data,
and invalid nested identity fail closed. CAS is single-document and the documented
single-instance POC limit remains explicit.

Raw PDF/DOCX/TXT bytes, full extracted bodies, raw external payloads, credentials,
connection strings, provider objects, stack traces, and browser state are not fields of
the durable envelope. The round-trip test confirms bounded structured persistence and
absence of raw bytes.

## 19. Security review

**PASS; no Critical or High finding.** The remediation closes cross-case projection and
weak recovery bypasses without adding an external call path. Corrupt state is neither
repaired nor exposed. Uncertain target work cannot replay or falsely complete. Targeted
retry remains case/document bound. Errors use fixed safe codes/messages. Secret unit
tests passed 5/5; the repository secret scan was clean. No raw document body, unrestricted
text, sensitive target/Registry payload, credential, token, certificate, Mongo URI,
private exception, or KYC/PII log path was introduced. Production encryption, RBAC,
retention, HA, distributed locks/outbox, and exactly-once delivery remain explicitly
unimplemented later boundaries, not Phase 12 claims.

## 20. Regression results

| Check | Independent result |
| --- | --- |
| Phase 09 jurisdiction gateway | **39 passed** |
| Phase 10 registry acquisition | **52 passed** |
| Phase 11 reconciliation + remediation | **58 passed** |
| Pre-Phase 12 workspace/multi-document | **31 passed** |
| Phase 12 adapter/remediation | **16 passed** |
| CLM + zero-touch + provider conformance | **240 passed** |
| Full backend | **706 passed, 11 skipped** locally/normal backend job; 717 collected; skips are the Mongo-gated module |
| Genuine Mongo 7 job | **11 passed, 0 skipped, 0 failed** at current head |
| Contract tests | **44 passed** |
| Ruff | passed over `apps/backend`, `scripts`, and `tests` |
| strict mypy | passed, **72 source files** |
| dependency consistency | `pip check`: no broken requirements |
| GoldTier validator tests | **5 passed** |
| GoldTier example validation | expected **19 valid / 19 invalid-quarantined / 48 not validated** |

The initial local full-backend invocation used an incorrect `PYTHONPATH` from the
backend working directory and failed collection for repository `scripts`; it was an
invocation error, not a product failure. The corrected repo-root `PYTHONPATH` run passed.
Known Starlette/httpx deprecation and three deliberate Pydantic adversarial serializer
warnings remain non-blocking and unchanged.

## 21. Frontend results

- TypeScript typecheck: passed.
- Vitest: **58 passed** in one test file.
- Production build: passed; 29 modules transformed; output directed to a temporary
  directory outside the repository.
- Dependency tree: resolved; npm reported only expected optional platform packages.

The first sandboxed Vitest/build attempt was blocked by Windows `spawn EPERM`; the
approved normal-host reruns passed. This is separated from repository quality.

## 22. Windows lifecycle evidence

**PASS.** Current-head CI ran **13 tests in 125.828s, OK**. The independent local normal-
host rerun also ran **13 tests in 164.079s, OK**. After local completion, a separate
read-only residue check found:

- `.runtime/demo-processes.json`: absent;
- listeners on ports 8000 and 5173: `0`;
- project-owned Python/Node processes: `0`.

## 23. Documentation review

**PASS.** README, project context, Phase 12 architecture, persistence/recovery profile,
security boundary, and regression catalogue describe canonical Mongo identity,
fail-closed corruption, interrupted-document targeted re-upload, ordinary-intake guard,
multiple outstanding interrupted documents, completed-evidence reuse, uncertain target
recovery, no blind replay, retained-outcome finalisation, CAS scope, and the single-
instance/non-exactly-once boundary. The original `PHASE_12_QUALITY_GATE.md` still records
the historical FAIL at `d2551e8`; only whitespace in its header changed during
remediation, so prior failure evidence was not rewritten.

## 24. Scope/non-goals

**PASS.** The diff adds no live ACRA or ACRA+ binding, ASIC/foreign registry provider,
real GoldTier/PingFed, GridFS/raw document persistence, production RBAC, distributed
lock/workflow/HA system, exactly-once claim, sponsor-unsanctioned TTL/retention policy,
new UBO rule, source-precedence rule, or production Ready-for-Approval claim. Mongo mode
is consistently labelled a durable single-instance POC.

## 25. Q-012/Q-015 status

- **Q-012 remains OPEN:** authoritative ACRA Business Profile API contract/access.
- **Q-015 remains OPEN:** jurisdiction source precedence, disagreement, reviewer/audit
  authority, retention, and production restart policy.

Phase 12 supplies technical POC persistence only and does not answer either sponsor
question.

## 26. Findings by severity

### Critical

None.

### High

None remaining. PH12-QG-001, PH12-QG-002, and CI-F1 are closed with the evidence above.

### Medium

None remaining for Phase 12. PH12-QG-003 is closed by current-head genuine-Mongo
execution.

### Low / informational

- **ID:** PH12-RQG-I01  
  **Severity:** Informational  
  **Evidence:** local real-Mongo tests skip because `PHASE12_MONGO_URI` is not configured;
  two current-head Mongo 7 CI jobs executed the same 11-test module successfully.  
  **Consequence:** no local Mongo-backed reproduction on this workstation; not a gap in
  current-head required evidence.  
  **Required remediation:** None for merge; retain the current CI job as a required gate.
- **ID:** PH12-RQG-I02  
  **Severity:** Informational  
  **Evidence:** PR #19 remains Draft even though its merge state and checks are clean.  
  **Consequence:** normal repository review controls still prevent immediate merge.  
  **Required remediation:** user/reviewer may mark ready and merge through the normal PR
  process; this quality-gate task did not change PR state.

## 27. Merge readiness

Phase 12 is ready for merge from the independent quality-gate perspective. The gate
does not itself merge, mark the draft ready, push, or waive ordinary reviewer/branch
controls. Phase 13 planning may begin after the user completes the normal PR decision;
this review did not start Phase 13. Live ACRA and real GoldTier/PingFed remain separately
not ready under open sponsor and integration dependencies.

## 28. Final verdict

PASS — READY FOR MERGE / PHASE 13 PLANNING
