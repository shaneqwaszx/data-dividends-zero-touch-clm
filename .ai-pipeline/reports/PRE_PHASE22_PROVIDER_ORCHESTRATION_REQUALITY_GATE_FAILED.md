# PRE-PHASE 22 — Provider Orchestration & Sandbox Testing

## Final Independent Re-Quality Gate

**Date:** 2026-09-24
**Role:** Fresh independent review-only quality gate
**Branch:** `feature/pre-phase22-provider-orchestration`
**Baseline / candidate source revision:** `5f71b4d4d4dcf11ccf4d742446a0fec67aac7da3`
**Candidate form:** intentionally uncommitted and unstaged working-tree delta
**Verdict:** **FAIL**

## 1. Executive result

The candidate is not ready for publication or Phase 22 entry.

The three findings from the preserved first gate are closed:

1. generic restart selection now schedules GoldTier Search after a completed Registry stage;
2. the safe local Mock configuration is reported as `MOCK`, not `SANDBOX_PARTIAL`;
3. the HR console Search action uses the existing entity-resolution owner and returns its outcome.

However, this re-gate found one new blocking acceptance defect. For a Certificate of Incorporation, the document profile correctly says that registered address is optional, but the downstream reconciliation owner still emits `MISSING_IN_SOURCE` for the absent document address. Zero-touch orchestration converts that reconciliation result into `DOCUMENT_REQUIRED_FIELD_MISSING`, leaves the case `WAITING_FOR_REVIEW`, and stops after Search. The required behavior is that the registry-owned address remains usable without fabricating document evidence and without an automatic document blocker when the selected document profile does not require that field.

This is a current-source behavior defect, a missing end-to-end adverse regression, and a contradiction of the implementation/status claims. It blocks a clean quality-gate PASS even though the original three findings and the other reviewed boundaries are satisfactory.

## 2. Candidate identity and review boundary

The candidate was independently frozen before review and re-verified immediately before this report was written.

| Identity check | Required | Observed before report | Result |
|---|---:|---:|---|
| Branch | `feature/pre-phase22-provider-orchestration` | same | PASS |
| `HEAD` | `5f71b4d4d4dcf11ccf4d742446a0fec67aac7da3` | same | PASS |
| `origin/main` | `5f71b4d4d4dcf11ccf4d742446a0fec67aac7da3` | same | PASS |
| Tracked modifications | 72 | 72 | PASS |
| Nonignored untracked candidate files | 14 | 14 | PASS |
| Total candidate paths | 86 | 86 | PASS |
| Staged paths | 0 | 0 | PASS |
| Candidate manifest SHA-256 | `acf1c20bfa5d76fa58688056c39b09711de54731547a038b05f3567e0740e881` | same | PASS |

The manifest was computed from the 86 candidate paths, excluding only this canonical report, by sorting paths with ordinal case-sensitive ordering, forming `path<TAB>git-hash-object` rows, and joining the rows with LF without a terminal LF.

This was a review-only run. It did not implement or remediate code, stage or commit files, push, create a PR, call an external provider, start Docker, inspect `.env`, use credentials, or alter runtime configuration. The only file written was this report.

## 3. Blocking finding

### PP22-RQG-001 — High — COI optional registered address still creates a document failure and review stop

**Affected owners:**

- `apps/backend/app/services/document_processing.py`
- `apps/backend/app/services/reconciliation.py`
- `apps/backend/app/services/zero_touch_orchestration.py`
- `apps/backend/tests/test_document_processing.py`
- `apps/backend/tests/test_zero_touch_orchestration.py`
- `.ai-pipeline/reports/PRE_PHASE22_PROVIDER_ORCHESTRATION_IMPLEMENTATION.md`
- `docs/demo/PRE_PHASE22_CAPABILITY_STATUS_MATRIX.md`

**Observed behavior:**

The `CERTIFICATE_OF_INCORPORATION_POC` semantic profile intentionally excludes `registered_address` from `required_document_fields`. Its unit-level semantic assessment can therefore be eligible when the certificate supplies legal name, registration identifier, and country of incorporation but no address.

The complete path does not preserve that policy. Reconciliation still compares the canonical registry address against a missing document address and records:

```text
registered_address -> MISSING_IN_SOURCE
```

Zero-touch orchestration treats that result as a reconciliation blocker and produces:

```text
status: WAITING_FOR_REVIEW
exception: DOCUMENT_REQUIRED_FIELD_MISSING
target calls: search only
```

A fresh direct adverse journey using the repository's existing deterministic test helpers reproduced exactly that state. The reconciliation output was:

```text
legal_name                 MATCH
registration_identifier   MATCH
registered_address         MISSING_IN_SOURCE
country_of_incorporation   MATCH
```

**Why this blocks acceptance:**

- The selected COI profile expressly makes registered address optional.
- The brief requires absent certificate address to remain registry-only evidence rather than becoming fabricated document evidence or an automatic document failure.
- Search is correctly allowed to occur early, but the false document blocker prevents the intended downstream policy/amend path for an otherwise sufficient COI.
- The implementation report and capability matrix describe the optional/registry-only behavior as implemented, so the current documentation overstates the exercised behavior.
- Existing coverage proves the profile-level rule, but does not exercise the complete reconciliation and zero-touch journey for a COI with no address. The gap allowed the policy owners to disagree.

**Required closure evidence for a new independent gate:**

1. Preserve a single authoritative rule across semantic assessment, reconciliation, and orchestration: absent registered address must not block a COI profile that does not require it.
2. Continue to compare registered address when the document actually provides it; a material mismatch must remain reviewable.
3. Preserve any legacy/default document profile whose contract still requires registered address.
4. Add an end-to-end zero-touch regression proving that a valid COI without document address does not emit `DOCUMENT_REQUIRED_FIELD_MISSING` and can continue beyond Search when all other inputs are sufficient.
5. Add or retain adverse coverage for a supplied-but-mismatching address and for profiles where address remains required.
6. Correct the implementation/status evidence so it describes only behavior actually proved at the integrated owner boundary.

No remediation was performed in this review-only gate.

## 4. Disposition of the first gate findings

The prior failed report was inspected as historical evidence, then each finding was independently rechecked against current source and focused tests.

| Prior finding | Independent disposition | Evidence |
|---|---|---|
| PP22-QG-001 — Search omitted from generic restart helpers | CLOSED | `_next_stage` and `_stage_after` now place `GOLDTIER_SEARCH` between Registry and Document. A registry-only durable restart test verifies Registry → Search → Document, and the persistence suite round-trips a Registry-complete/Search-current checkpoint. |
| PP22-QG-002 — Mock exposed `SANDBOX_PARTIAL` | CLOSED | Provider status now returns `SANDBOX_PARTIAL` only when the sandbox is configured; the safe default local provider is `MOCK`. Write enablement additionally requires configured sandbox plus explicit opt-in. |
| PP22-QG-003 — HR Search hard-coded `NOT_ASSESSED` | CLOSED | The HR console delegates Search to the onboarding service, which invokes the existing `OnboardingIntelligenceService` resolution owner and returns its actual outcome. Focused tests exercise a review-required result. |

These closures do not offset PP22-RQG-001.

## 5. Acceptance and governance review

| Required category | Assessment | Independent conclusion |
|---|---|---|
| GoldTier workflow and ordering | PASS | Canonical Registry precedes Search. Exact existing customer selection bypasses Shell. No-match can create Shell only after source/document/ownership/readiness requirements are satisfied. Policy precedes Amend. |
| Existing customer never receives Shell | PASS | The selected exact-match path rejects a Shell checkpoint/call and proceeds to Policy/Amend for the existing customer identifier. Tests cover exact-match ordering and no Shell call. |
| No-match and ambiguous resolution | PASS | No-match is distinct from exact match and can use Shell after readiness. Ambiguous/review-required resolution stops before target mutation and retains bounded safe candidate evidence. |
| Early Search and restart placement | PASS | Search now has an explicit orchestration stage and occurs directly after Registry on new and registry-only resumed flows. |
| Incremental durable target ledger | PASS | Shell, Policy, and Amend have separate attempted/completed evidence. Completed operations are not replayed, and attempted-but-unconfirmed writes stop for review rather than being retried as though they were safe reads. |
| Restart/no-replay/uncertain-write behavior | PASS | Focused orchestration and persistence tests cover restart boundaries, completed-step skip behavior, and uncertain write handling. The Search checkpoint is persisted separately from target mutations. |
| Sandbox write gates | PASS | Standalone console writes are denied. Case-ledger writes require sandbox configuration, explicit write opt-in, synthetic-only data, and safe-host controls; unresolved authority fields keep writes blocked. |
| Synthetic-data limit / unsafe mutation | PASS | The candidate does not authorize arbitrary real-customer mutation. The console and orchestration surfaces remain bounded by synthetic and ledger controls. |
| Related-party `childId` blocker | PASS | Related-party mutation remains blocked because the required child identifier/authority is unresolved. No speculative relationship or hierarchy creation was added. |
| Official ACRA Marketplace Mock mode and auth truth | PASS | The official mock mode is explicit and separate from generic sandbox-shaped support. Runtime composition fails closed where auth details are unresolved. The candidate does not claim proven Live ACRA or invent OAuth. |
| ACRA/GoldTier provider truth | PASS | Default ACRA and GoldTier behavior remains Mock; generic ACRA sandbox support remains Partial; official Marketplace Mock activation remains unresolved; GoldTier live/PingFed activation remains blocked. |
| COI profile and account-type authority | **FAIL** | Profile-level optional-address logic exists, but integrated reconciliation/orchestration still blocks a missing COI address. Account-type/source authority is not enough to overcome the inconsistent field-policy owners. See PP22-RQG-001. |
| HR-only provider console RBAC | PASS | Provider console capability is HR-owned and does not grant `CASE_ACCESS`. Direct non-HR access is denied. Backend capability is authoritative. |
| Browser credential exposure | PASS | Browser-visible status is a safe projection. No credential, bearer token, secret, or raw auth material was found in the reviewed response/types/UI path. |
| Backend-authored progress | PASS | Detailed progress comes from the backend summary; UI rendering does not independently reconstruct orchestration truth. Completed/not-attempted presentation is bounded and covered. |
| Frontend cache and identity scope | PASS | Session/user-scoped query keys are retained; prefetch does not grant or imply `CASE_ACCESS`; logout/identity controls remain aligned with the existing cache owner. |
| Entity resolution | PASS | The existing resolution service remains the single owner for console and zero-touch Search; bounded candidates and exact/no-match/review-required outcomes remain distinct. |
| Decimal UBO / mock-risk regressions | PASS | No second ownership engine or floating-point ownership rule was introduced. The implementation evidence reports the existing UBO and mock-risk regression suites passing; inspected orchestration retains those owners. |
| Memory persistence and codecs | PASS at deterministic boundary | Current schema/codecs include Search and target-ledger state, reject invalid combinations, and focused persistence tests pass, including Registry-complete/Search-current restart. |
| Physical Mongo restart compatibility | NOT FRESHLY PROVED | Docker Linux daemon was unavailable. No Mongo URI was accessed and no physical test was attempted. Historical physical evidence was not relabelled as current. This gate makes no fresh physical-Mongo claim. |
| Security, audit, and log safety | PASS within reviewed scope | Capability checks, safe projections, synthetic restrictions, no-replay handling, audit events, and sanitized provider evidence remain present. No secret-bearing output or raw provider/customer payload was observed in the reviewed paths. |
| Docs/contracts/decisions/source authority | **FAIL** | Provider status labels and open authority boundaries are generally conservative, but the COI optional-address implementation/status claims exceed integrated behavior. |
| Q-016 | PASS | Remains deferred; it is not silently implemented or described as sponsor-confirmed. |
| Phase 22 hold | PASS | The candidate continues to hold Phase 22 and does not present this pre-phase work as Phase 22 completion. |
| Full test evidence and hygiene | **FAIL overall** | Broad reported evidence is substantial and focused fresh checks pass, but the integrated COI adverse case is absent and demonstrably fails. Some Markdown files use intentional trailing double spaces for hard line breaks; no code whitespace error was found by `git diff --check`. |

## 6. Fresh independent verification

### 6.1 Freshly executed checks

All Python checks were run with bytecode generation disabled. Pytest cache creation was disabled. No provider, Docker, browser, or database lifecycle was started.

| Check | Fresh result |
|---|---|
| Candidate identity freeze | PASS — 72 tracked + 14 untracked = 86, zero staged, expected SHA-256 |
| Focused provider/orchestration/persistence/document suite | **285 passed** across `test_provider_sandbox_api.py`, `test_zero_touch_orchestration.py`, `test_clm_orchestration.py`, `test_phase12_persistence.py`, `test_document_processing.py`, `test_acra_modes.py`, and `test_goldtier_xpi_sandbox.py` |
| Focused RBAC/business-fixture/CLM-contract suite | **85 passed** across `test_phase13_auth_rbac.py`, `test_garden_business_fixture.py`, and `test_phase_05_clm_contract.py` |
| Direct COI missing-address journey | **FAILED acceptance** — reproduced `WAITING_FOR_REVIEW`, `DOCUMENT_REQUIRED_FIELD_MISSING`, and Search-only target calls |
| `scripts/check_project_state.py` | PASS |
| `scripts/check_architecture.py` | PASS |
| `scripts/check_policy_authority.py` | PASS |
| `scripts/check_external_provider_readiness.py` | PASS |
| `scripts/check_secrets.py` | PASS |
| `git diff --check` | PASS, with Git line-ending conversion warnings only |
| Fourteen untracked candidate files: final LF/trailing-whitespace inspection | Final LF present. Trailing spaces were limited to Markdown header metadata lines using two-space hard breaks in the implementation report, preserved failed report, and capability status matrix. |

The test totals above were independently collected from the selected test files; they are not copied from the implementation report.

### 6.2 Implementer evidence inspected but not rerun in full

The implementation report and Aegis evidence record were treated as supporting evidence, not authority. Their relevance was checked against current source/test ownership and the frozen identity. They report:

- backend: 1,323 passed and 35 physical-only skips;
- frontend: 23 files / 285 tests;
- TypeScript build: 116 modules;
- Ruff, strict Mypy over 106 source files, and dependency check passing;
- contract: 44 passed;
- delivery: 4 passed;
- governance/security: 159 passed;
- project-state/checker: 18 passed;
- intelligence: 17 passed;
- UBO: 3 passed;
- mock risk: 5 passed;
- GoldTier validator: 19 valid, 19 quarantined, 48 not validated;
- Playwright: 14 passed after remediation;
- Windows lifecycle: 23 passed after remediation, with an earlier transient loopback/header failure preserved rather than erased;
- physical Mongo unavailable because the Docker Linux daemon was absent.

Those broad results increase confidence in unaffected boundaries but do not close PP22-RQG-001. The missing integrated COI case demonstrates why aggregate green evidence cannot substitute for the required adverse acceptance path.

## 7. Source, contract, and decision conclusions

- The candidate preserves the architecture direction `strict source DTO -> canonical model/evidence -> target mapping` and does not introduce direct ACRA-to-GoldTier mapping.
- The target ledger remains the owner of mutation order, attempted/completed state, restart behavior, and no-replay safety.
- Provider status remains conservative: Mock is not Sandbox, Partial is not Live, and configuration/credentials are not interoperability proof.
- ACRA Marketplace Mock auth remains an open activation question; no speculative OAuth or successful-live claim appears.
- GoldTier live/PingFed, multi-level hierarchy creation, autonomous approval, production OCR, external ownership, Camunda, and production SSO remain outside the implemented truth.
- Q-016 remains deferred, and the related-party child-identifier gap remains a mutation blocker.
- Phase 22 remains on hold.
- The COI registered-address rule currently has two effective owners: semantic profile assessment says optional, while reconciliation/orchestration makes absence blocking. That divergence must be collapsed before publication.

## 8. Limitations and prohibited inferences

No physical Mongo evidence was freshly produced because the required Docker Linux daemon was unavailable. The deterministic persistence/schema/codec tests passed, but this report does not claim current physical Mongo restart proof.

No external ACRA or GoldTier endpoint was called. No credentials or `.env` values were inspected. Passing mock, sandbox-shaped, contract, or lifecycle tests must not be described as Live provider interoperability or sponsor approval.

The candidate remains uncommitted and unstaged. This report evaluates only the exact frozen 86-path content identity recorded above, plus this report itself as a review artifact.

## 9. Required next action

Publication is forbidden. Remediate PP22-RQG-001 in a separate authorized implementation run, add the integrated positive and adverse tests described above, refresh any overstated implementation/status evidence, re-run affected backend/contract/frontend/governance checks, and submit the resulting exact candidate identity to a fresh independent gate.

Until that gate returns exact PASS, do not publish, commit as accepted evidence, open the Phase 22 implementation gate, or claim Pre-Phase 22 completion.

FAIL
