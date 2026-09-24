# Pre-Phase 22 capability-expansion provider-identity re-quality gate

Date: 2026-09-24
Reviewer role: fresh independent quality gate; no implementation or publication authority exercised

## 1. Executive Result

**FAIL**

The provider-identity remediation is coherent in source and passed the focused domain,
orchestration, persistence-model, contract, regression, lint, type, and governance checks
executed by this review. The retained `GoldTierSubmissionPlan` is the single immutable
provider-identity owner, execution derives its input from that plan, mapper and connector
compatibility fail closed before ledger or network access, and schema-v5 decoding rejects
the reviewed identity contradictions.

Exact `PASS` is nevertheless blocked by two required verification gaps on the reviewed
candidate:

1. the provider-identity schema-v5 behavior was not exercised through physical Mongo
   persistence/restart, because the Docker daemon is unavailable and the registered
   physical suite contains no provider-identity case; and
2. the applicable Case Activity browser scenario timed out on the current candidate and
   then passed unchanged on retry, proving current nondeterminism rather than a stable
   browser result.

These are verification blockers, not evidence of a reproduced defect in the
provider-identity logic. Missing or unstable required verification cannot be converted
to `PASS WITH MINOR FIXES`. Publication and the next phase are not ready.

## 2. Phase Acceptance Checklist

| Acceptance requirement | Result | Direct evidence |
| --- | --- | --- |
| One immutable GoldTier provider identity is owned by the retained submission plan/context | PASS | `GoldTierSubmissionPlan` owns `environment` and `provider_classification`; its pairing validator admits only Mock/Mock and Sandbox/Sandbox Partial. The plan is constructed at record creation and retained thereafter. |
| Submission input derives from the frozen plan rather than later mutable configuration | PASS | `CLMOrchestrationService._build_snapshot` passes `submission_plan.environment` explicitly to `build_submission_input`; submission execution consumes the resulting frozen input. |
| Mapper and connector compatibility are checked before ledger or network access | PASS | `execute_submission_input` validates input-versus-mapper and input-versus-connector environments before acquiring the case lock, reading or creating a target ledger entry, or invoking the connector. Focused tests assert `NOT_STARTED` and zero target calls in both drift directions. |
| Drift fails closed with a typed, sanitized error | PASS | The domain service raises `TargetProviderContextMismatchError` (`GT_PROVIDER_CONTEXT_MISMATCH`) with a non-sensitive public message; CLM orchestration maps it to `CLM_TARGET_PROVIDER_CONTEXT_MISMATCH`. |
| Schema-v5 rejects plan/input/ledger provider-identity mismatch without schema v6 | PASS at model/decode level; physical evidence blocked | Schema version remains 5. Current-model validation rejects plan/input mismatch and a matching submission-ledger entry whose environment differs from the plan. `MongoCaseStore._decode` maps validation failures to `PersistenceDataInvalidError`. Physical Mongo round-trip/startup evidence is missing. |
| Old schemas and plan-only/no-submission records remain supported | PASS at owned model/unit level | Existing v1-v4 compatibility tests remain green; provider-identity tests accept a plan-only record and stable Mock and Sandbox records. |
| Tests cover both runtime drift directions, stable Mock/Sandbox, and schema-v5 valid/invalid records | PASS for unit/in-memory scope | Fresh focused suites passed 170 tests, including Sandbox plan to Mock connector drift, Mock plan to Sandbox mapper drift, stable Mock/Sandbox, contradictory plan/input, contradictory matching ledger, and plan-only records. Physical Mongo scope remains missing. |
| No provider claim expansion, Q-016 resolution, Phase 22 activation, alternate owner/router/fallback/dual write, business-rule invention, or secret exposure | PASS | Diff/source/contract review found no such expansion. GoldTier remains Mock-only, Sandbox remains partial, Q-016 remains unresolved, and no Live claim or second identity/persistence owner was added. |
| Required affected verification is complete and stable | FAIL | Physical Mongo evidence is unavailable and lacks a registered provider-identity case; the current focused browser check failed once and passed only on an unchanged retry. |

## 3. Contract and Integration Findings

### Current findings

- No contract defect was found in the bounded remediation. ADR-004 and D-049 agree that
  the retained submission plan is the sole execution-time provider identity. Current
  source and tests implement that ownership without an alternate router or fallback.
- The remediation does not change GoldTier payload mappings, sponsor-defined business
  fields, endpoint claims, or provider status. GoldTier remains Mock-only; the generic
  Sandbox-shaped path remains partial and is not interoperability or Live evidence.
- The mismatch failure is typed and is surfaced as a sanitized CLM failure rather than a
  provider response, credential detail, payload body, or mutable configuration value.
- Existing contradictory examples remain quarantined by the current contract hierarchy;
  this change does not promote an example to an authoritative fixture or resolve Q-016.

### Authority and deferred dependencies

- Current acceptance is governed by the project constitution, architecture, persistence
  profile, external-provider activation contract, ADR-004, D-049, and current owning
  source/tests.
- Q-016, real GoldTier credentials/interoperability, PingFed details, and Phase 22
  capability activation remain later sponsor/phase dependencies. None is needed to
  evaluate the bounded provider-identity remediation, and none was claimed here.

## 4. Tester and Adversarial Findings

### Fresh independent evidence on the immutable candidate

| Check | Result |
| --- | --- |
| `python -m pytest -p no:cacheprovider apps/backend/tests/test_clm_orchestration.py apps/backend/tests/test_phase12_persistence.py apps/backend/tests/test_goldtier_xpi_sandbox.py -q` | PASS — 170 tests |
| `python -m pytest -p no:cacheprovider apps/backend/tests/test_zero_touch_orchestration.py apps/backend/tests/test_phase06_provider_conformance.py apps/backend/tests/test_onboarding_resilience.py apps/backend/tests/test_phase13_priority.py -q` | PASS — 260 tests; three expected malformed-fixture serializer warnings |
| `python -m unittest discover -s tests/contract -p "test_*.py"` | PASS — 44 tests |
| `python -m ruff check apps/backend/app apps/backend/tests tests scripts` | PASS |
| `python -m mypy app --no-incremental` from `apps/backend` | PASS — 105 source files |
| `python scripts/check_project_state.py` | PASS |
| `python scripts/check_architecture.py` | PASS |
| `python scripts/check_policy_authority.py` | PASS |
| `python scripts/check_external_provider_readiness.py` | PASS |
| `python scripts/check_secrets.py` | PASS |
| Full frontend Vitest run, escalated only for local child-process permission | Initial run: 21 files passed, 1 file failed; 281 tests passed, 1 test timed out in `ViteHistoryFallback.test.ts`. Unchanged rerun: PASS — 22 files, 282 tests. The final full result is green, with the transient failure preserved here. |
| Guarded focused browser E2E: `Case activity uses one paged read`, diagnostics enabled, 240-second harness timeout | First current run: FAIL — Playwright timed out after 120 seconds waiting for the initial `/api/clm/zero-touch/activity` response after the Audit selection. Unchanged rerun: PASS — 1/1 in 3.6 seconds. This is not stable green evidence. |
| Physical Mongo | MISSING_INFRASTRUCTURE — Docker client is installed, but the Docker Desktop Linux daemon pipe is unavailable. The registered physical suites were inspected and contain no provider-identity scenario. |
| `git diff --check` plus explicit hygiene scan of all candidate-owned untracked text paths | PASS — no whitespace error; zero untracked-text hygiene findings. Line-ending conversion warnings did not identify a whitespace defect. |

The first strict-Mypy attempt used `--cache-dir=NUL` and triggered a Mypy internal error
on Windows. That invocation defect was eliminated rather than waived: the clean
`--no-incremental` run passed all 105 source files.

The frontend and browser commands initially required only a local sandbox-permission
escalation because their JavaScript runners spawn child processes. No external provider,
database, repository, or publication mutation was performed.

### Implementer evidence retained as supporting, not independently substituted

The implementation report associates the same immutable candidate fingerprint with:
backend 1308 passed/29 skipped; Ruff pass; strict Mypy 105 files pass; frontend typecheck
pass; Vitest 22 files/282 tests pass; frontend build pass; contract 44; delivery 4;
governance/security 163; Windows lifecycle 23/23; project/architecture/tooling/policy/
provider/secrets checks pass; examples 19 valid/19 quarantined/48 not validated; and
synthetic intelligence 17/17, 3/3, and 5/5. This review did not treat those reported
results as a replacement for its own focused/adversarial executions.

### Failure-path and false-success review

- Both mutable-drift directions stop before ledger creation and connector calls.
- A persisted matching submission-ledger entry cannot disagree with the plan in schema
  v5; unrelated historical entries do not become a second current-submission owner.
- Plan-only/no-submission records remain valid.
- Invalid persistence data becomes a typed persistence-invalid failure rather than being
  silently repaired or reinterpreted.
- An unchanged retry passing after a 120-second browser timeout is explicitly not treated
  as proof that the failed path is reliable.

## 5. Code and Architecture Review

No implementation defect was found in the bounded provider-identity design.

- The owner/dependency direction remains plan -> submission input -> mapper/connector
  compatibility -> ledger/network, matching the architecture constitution.
- Configuration is consulted when the plan is created, not again to redefine identity at
  execution time.
- Compatibility checks are placed before persistence-ledger and external-call side
  effects, so drift cannot create a false started/submitted state.
- Persistence validation strengthens schema-v5 semantics without introducing schema v6,
  a parallel durable model, a migration, a second repository, fallback, or dual write.
- Existing old-schema conversion remains centralized in the persistence owner.
- No direct ACRA-to-GoldTier mapping, target-ledger bypass, provider router, or dormant
  provider composition was introduced.

Accepted later-phase dependencies such as actual Sandbox/Live interoperability are not
technical debt created by this remediation and are not accepted as current evidence.

## 6. Security Review

No security finding was reproduced in the reviewed remediation.

- The mismatch is detected before any network call and before ledger mutation.
- The public error is fixed and sanitized; it contains no provider payload, endpoint,
  credential, header, certificate, raw KYC data, or internal exception detail.
- The change does not add authentication material, logging of confidential data, weaker
  TLS behavior, provider fallbacks, or runtime Live activation.
- No `.env`, `private/`, sponsor credentials, secrets, or raw confidential provider
  artefacts were accessed during this review.

Real GoldTier authentication, PingFed, certificate handling, and Live transport remain
deferred external-provider activation work and are not implied by this gate.

## 7. Required Fixes

### PI-RQG-01 — High — required physical persistence evidence is absent

Add and register physical Mongo coverage for the provider-identity invariant, including:

1. stable Mock and Sandbox schema-v5 round-trip/restart behavior;
2. rejection on read/startup of contradictory schema-v5 plan/input and matching-ledger
   identity; and
3. preservation of plan-only/no-submission records.

Run it through the guarded physical-Mongo harness using a newly generated allowlisted
disposable database and prove cleanup when Docker infrastructure is available. Do not
use or expose a real/project Mongo URI.

### PI-RQG-02 — High gate blocker — browser reliability is unverified

Diagnose and stabilize the Case Activity request/readiness sequence that timed out waiting
for the initial activity response. Re-run the isolated scenario and the complete guarded
browser suite repeatedly on unchanged candidate content and retain deterministic current
green evidence. Merely increasing the timeout without identifying the readiness/request
failure would not close this blocker.

After both blockers are closed, re-run the affected verification matrix, freeze a new
candidate fingerprint, and obtain a fresh independent quality gate.

## 8. Readiness

- **Provider-identity remediation publication:** NOT READY because required persistence
  evidence is unavailable and browser evidence is unstable.
- **Pre-Phase 22 bounded logic:** source behavior appears complete, but the gate remains
  failed until the evidence blockers above are closed.
- **Phase 22:** NOT AUTHORIZED and not started. This report does not resolve Q-016 or
  activate any later capability.
- **Live ACRA verification:** not part of this remediation and not established. ACRA
  remains Mock by default; generic Sandbox-shaped support remains partial.
- **Real GoldTier integration:** not ready and not claimed. GoldTier remains Mock-only;
  no PingFed/credential/interoperability proof exists.

## 9. Git Status and Candidate Identity

- Branch: `feature/pre-phase22-capability-expansion`
- `HEAD`: `3ca232b58c3842f413c4552dbd3b85aabea4591c`
- `origin/main`: `3ca232b58c3842f413c4552dbd3b85aabea4591c`
- Staged paths: 0
- Candidate manifest paths, excluding the unrelated protected root prefix and this report:
  146
- First manifest entry:
  `.ai-pipeline/reports/GOLDTIER_XPI_SANDBOX_DIAGNOSIS.md<TAB>90435639a8598b270a90c7ca10c49c983318b9ca`
- Last manifest entry:
  `tests/test_check_project_state.py<TAB>b6d9488bbf4bf5266c42a75cbf6872a955de257c`
- Candidate SHA-256 fingerprint:
  `38603321bcd0bd114bb2a7f029b879567af36be77c413295357cd83f3767876a`

The immutable manifest matched before substantive review and again immediately before
this report was written. A post-write recomputation, excluding exactly this report, also
matched the same branch, revisions, staged count, path count, boundary entries, and
fingerprint.

The working tree contains the pre-existing 146-path implementation candidate plus this
new untracked quality-gate report. This report is the reviewer's sole authored change.
The earlier FAIL reports were preserved. No implementation fix, stage, commit, push, PR,
merge, publication action, branch switch, or next-phase work occurred.
