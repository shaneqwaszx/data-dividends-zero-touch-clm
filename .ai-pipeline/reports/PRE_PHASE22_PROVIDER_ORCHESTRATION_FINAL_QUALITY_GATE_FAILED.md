# PRE-PHASE 22 — Provider Orchestration & Sandbox Testing Quality Gate

## Review identity

- Review role: fresh independent, review-only final quality gate.
- Review date: 2026-09-24 (Asia/Singapore).
- Candidate branch: `feature/pre-phase22-provider-orchestration`.
- Assigned `BASE_SHA`: `5f71b4d4d4dcf11ccf4d742446a0fec67aac7da3`.
- Observed current `HEAD`: `5f71b4d4d4dcf11ccf4d742446a0fec67aac7da3`.
- Observed local `origin/main`: `5f71b4d4d4dcf11ccf4d742446a0fec67aac7da3`.
- Staged paths: none.
- The current source revision is the base commit plus the reviewed working-tree candidate. The behavior independently tested in this gate is the exact candidate fingerprint below. No independent acceptance commit exists because the candidate is uncommitted.
- This report is the only gate-authored file and is deliberately excluded from the reviewed candidate.

## Exact candidate inventory

The inventory was recomputed from the set union of tracked `git diff --name-only` paths and untracked `git ls-files --others --exclude-standard` paths, excluding only this report. Paths were sorted with ordinal ordering. Each row was `path<TAB>git hash-object`, rows were joined with LF and no trailing LF, and the UTF-8 bytes were SHA-256 hashed.

- Path count: `94`
- Fingerprint: `130dd4bb51f98500aa3901b2582caa9ba661c8c46d429b44812471fed72a4f25`
- Assigned fingerprint match: yes.

The fingerprint was rechecked after independent test execution and before this report was written. Test-created temporary directories were removed; no temporary path remained in the inventory.

## Scope reviewed

The gate reviewed the full brief, constitution and selected/full development context, current source and tests, contracts, decisions, configuration and composition, implementation report, both earlier failed gate reports, and the Aegis work record. The review covered:

- early identity-bound GoldTier Search and exact/no-match/ambiguous/failure routing;
- exact-match party reuse and Shell skip, no-match Shell creation, and incremental Policy/Amend processing;
- durable operation ordering, CAS, attempted-before-call semantics, uncertain-write no-replay behavior, restart behavior, and recovery;
- related-party preparation without invented `childId` and the explicit related-party write blocker;
- safe Sandbox diagnostics, write blocking, HR-only `PROVIDER_SANDBOX_TEST`, and absence of a `CASE_ACCESS` dependency;
- backend-authored workflow progress and authenticated-user-scoped frontend query keys;
- ACRA local Mock, API Marketplace Mock, generic Sandbox, dormant BizFile, and Live classifications and fail-closed composition;
- COI POC optional-address reconciliation, supplied-value mismatch blocking, and legacy required-profile behavior;
- provisional `accountEntityType`, the seven remaining `TBD_SPONSOR` values, provider classifications, logging/secrets, and external-evidence governance;
- persistence/schema compatibility and memory/Mongo ownership boundaries;
- architecture/source-of-truth boundaries, Q-016 deferral, and the hold on Phase 22.

No `.env`, private/confidential artefact, external provider mutation, provider write, or database mutation was accessed or performed.

## Executive result

The prior four gate findings are closed, and the focused orchestration, provider, RBAC, frontend, contract, governance, secret, and documentation checks are otherwise green. The candidate nevertheless has one new High-severity persistence compatibility defect: existing schema-v5 automation records that were valid at the assigned base can be rejected by the current schema-v5 Mongo decoder after `GOLDTIER_SEARCH` was inserted into the automation stage prefix.

This breaks the required durable restart/read-compatibility boundary and invalidates the candidate's explicit claims that existing schema-v5 records remain readable. A final acceptance result cannot be issued until the old-v5 automation state is handled truthfully and tested.

## Findings

### PP22-FQG-001 — High — Baseline-valid schema-v5 automation records are unreadable after the Search-stage insertion

Evidence:

1. At the assigned base, the canonical automation prefix was `REGISTRY -> DOCUMENT -> OWNERSHIP -> READINESS -> MOCK_GOLDTIER`. A valid base schema-v5 `PENDING_INPUTS` record used `current_stage=DOCUMENT` and `completed_stages=(REGISTRY,)`.
2. The candidate inserts `GOLDTIER_SEARCH` into `AUTOMATION_STAGE_ORDER` at `apps/backend/app/domain/zero_touch.py:12` and now requires a pending-input record to contain `(REGISTRY, GOLDTIER_SEARCH)` at `apps/backend/app/domain/zero_touch.py:281`.
3. The durable envelope remains `schema_version: Literal[5] = 5` at `apps/backend/app/persistence/models.py:270`.
4. Current-version decode calls `DurableCaseSnapshot.model_validate(value)` directly at `apps/backend/app/persistence/mongo_case_store.py:506`; there is no compatibility branch that recognizes the baseline schema-v5 automation shape.
5. An independent in-memory codec probe built a current valid schema-v5 snapshot, changed only its automation checkpoint to the exact base-valid pending-input shape, and invoked `MongoCaseStore._decode`. The observed result was `BASELINE_VALID_SCHEMA_V5_DECODE=REJECTED_AS_INVALID`.
6. The new persistence test at `apps/backend/tests/test_phase12_persistence.py:473` proves only a round trip for a newly authored registry/Search checkpoint. The compatibility test at `apps/backend/tests/test_phase12_persistence.py:737` removes new GoldTier preparation fields but does not include a baseline automation record, so it cannot detect this regression.
7. Interrupted-document recovery unconditionally assigns `(REGISTRY, GOLDTIER_SEARCH)` at `apps/backend/app/persistence/mongo_case_store.py:802`. If a compatibility reader is added, that path must not silently claim that historical Search completed when no Search checkpoint exists.

Impact:

- A Mongo-backed case created before this candidate and retained in a normal pre-Search automation state can fail closed as invalid on read/startup after deployment.
- Durable restart and case recovery can be unavailable for otherwise valid stored cases.
- Merely appending `GOLDTIER_SEARCH` during decode/recovery would manufacture provider evidence and violate the source-of-truth and evidence-lineage rules.
- The defect contradicts `docs/PROJECT_STATE.md:238`, `docs/decisions/ADR-005_INCREMENTAL_GOLDTIER_ORCHESTRATION.md:53`, and `.ai-pipeline/reports/PRE_PHASE22_PROVIDER_ORCHESTRATION_IMPLEMENTATION.md:130`.

Required remediation:

1. Define one explicit versioned or structurally unambiguous compatibility path for automation records written by the assigned base. Do not preserve the schema number while changing accepted semantics without a reader for the old shape.
2. Preserve evidence truth during conversion: a historical record without a Search checkpoint must not be labelled Search-complete. In-progress and uncertain target operations must remain non-replayable; historical terminal outcomes may be handled only under the documented terminal compatibility rule.
3. Reconcile `_recover_interrupted` with the compatibility strategy so recovery cannot fabricate Search completion.
4. Add raw base-revision schema-v5 fixtures covering at least pending inputs, document/review progression, interrupted recovery, uncertain target activity, and historical terminal state. Assert decode, restart ordering, CAS behavior, and no replay.
5. Re-run the persistence, restart, contract, governance, and full regression matrices. Run disposable physical Mongo coverage when the infrastructure is available; do not represent model-only codec tests as physical persistence proof.
6. Correct the ADR, project-state, and implementation-report compatibility claims only after the behavior is proved.

## Closure of prior findings

| Prior finding | Status | Current evidence |
|---|---|---|
| `PP22-QG-001` — generic restart helpers skipped Search | CLOSED | The generic sequence includes `GOLDTIER_SEARCH` in `apps/backend/app/services/zero_touch_orchestration.py:2124`, the next-stage map routes Registry to Search at line 2137, and `apps/backend/tests/test_zero_touch_orchestration.py:338` exercises a registry-complete restart before Document. |
| `PP22-QG-002` — Mock status was labelled `SANDBOX_PARTIAL` | CLOSED | `apps/backend/app/api_provider_sandbox.py:155` emits `MOCK` when the sandbox connector is not configured, while configured Sandbox remains `SANDBOX_PARTIAL`; the focused provider API suite passed. |
| `PP22-QG-003` — HR Search hard-coded `NOT_ASSESSED` | CLOSED | `apps/backend/app/api_provider_sandbox.py:197` delegates Search through the existing onboarding owner and returns the retained resolver outcome at line 231; `apps/backend/tests/test_provider_sandbox_api.py:115` observes `REVIEW_REQUIRED`. |
| `PP22-RQG-001` — optional missing COI address still blocked the integrated journey | CLOSED | `apps/backend/app/services/reconciliation.py:370` derives field requiredness from the document profile, and `apps/backend/tests/test_phase11_reconciliation.py:144` bounds `REGISTRY_ONLY` to the optional registered-address case while retaining mismatch/legacy blocking. |

Closure of these findings does not waive the novel persistence defect.

## Independent evidence observed on the exact candidate

Successful gate-observed evidence:

- Candidate identity: 94 paths and the assigned SHA-256 fingerprint, before and after testing.
- Focused backend orchestration/provider/persistence/document/ACRA/GoldTier tests: `289 passed`.
- Focused backend RBAC and business-fixture tests: `76 passed`.
- Focused frontend Sandbox/navigation/workflow tests: 3 files, `103 passed`.
- Contract suite with its required test helper path: `44 passed`.
- Governance unit tests for project state, provider readiness, and evidence validation: `56 passed`.
- Direct governance commands: project state, architecture, policy authority, and external-provider readiness all succeeded.
- Secret checker: succeeded with no supported secret pattern found.
- `git diff --check`: no whitespace error; Git emitted only existing line-ending conversion warnings.
- Direct old-v5 automation decoder probe: reproducibly rejected the base-valid record as invalid.
- Docker capability probe: the Docker Desktop Linux engine pipe was absent, so physical Mongo tests were unavailable.

Some first invocations were excluded from evidence because the sandbox blocked the frontend build subprocess or temporary-directory access, or because the contract helper path was initially omitted. The corrected invocations above completed successfully. These environment/operator errors are not candidate failures and do not mitigate `PP22-FQG-001`.

## Relied-on implementation evidence

The implementation report records broader candidate evidence that this gate did not independently rerun in full: backend `1327 passed / 35 skipped`, frontend 23 files / 286 tests, Ruff, Mypy, TypeScript and build, contracts 44, delivery 4, governance/security 159, intelligence 17/3/5, GoldTier validation 19 valid / 19 invalid quarantined / 48 not validated, Playwright 14, and Windows lifecycle 23. This is relied-on implementer evidence only. The independently reproduced schema-v5 defect is outside the reported successful coverage and takes precedence over those passing counts.

## Acceptance and adverse-case assessment

- Early GoldTier Search, identity binding, exact/no-match/ambiguous/failure routing, exact-match Shell skip, and incremental Shell/Policy/Amend behavior: materially satisfied in current source and focused tests.
- Attempted-before-call ledger semantics, CAS ownership, stopping, and uncertain-write no replay for newly authored state: materially satisfied in current source and focused tests.
- Restart/persistence compatibility for records authored by the assigned base: not satisfied because of `PP22-FQG-001`.
- Sandbox safety, read-only diagnostics, disabled write UI, backend write rejection, related-party `childId` blocker, HR-only capability, and direct non-HR denial: materially satisfied.
- Backend-authored progress and user-scoped Sandbox/cache identity: materially satisfied.
- ACRA mode/classification truth and fail-closed unknown Marketplace authentication: materially satisfied. API Marketplace Mock remains blocked/no-auth-success unproved; generic Sandbox remains partial; BizFile remains dormant; no Live ACRA claim is made.
- COI optional-address behavior, supplied mismatch blocking, and legacy required-profile behavior: materially satisfied.
- `accountEntityType` remains provisional and the other seven target values remain `TBD_SPONSOR`: materially satisfied; this is not sponsor approval.
- Security/logging/secrets and architecture/source-of-truth boundaries: no additional material defect found in the reviewed candidate.
- Q-016 remains deferred and Phase 22 remains held: materially satisfied.

## Residual limitations and blockers

- Physical Mongo behavior was not independently proved because the Docker Linux daemon is unavailable. No database was created, accessed, mutated, or dropped.
- No external ACRA Marketplace authentication success, GoldTier write, related-party write, PingFed integration, production provider interoperability, or Live execution was performed or proved.
- The related-party write path remains blocked pending child-ID lifecycle and relationship authority.
- Seven GoldTier policy values remain sponsor-TBD; only `accountEntityType` has provisional project authority.
- Q-016 remains open, and this work does not authorize autonomous/final approval or Phase 22 implementation.
- The candidate must not be committed, pushed, published, or advanced as accepted on the basis of this gate.

## Final verdict

FAIL
