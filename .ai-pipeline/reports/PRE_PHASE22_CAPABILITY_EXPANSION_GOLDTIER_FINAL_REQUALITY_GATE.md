# Pre-Phase 22 capability expansion — GoldTier XPI final re-quality gate

## 1. Executive Result

**FAIL**

The third narrow remediation closes the previously reported hard-coded Mock wording in
retained CLM, zero-touch, audit, CSV, API, and frontend projections when provider mode is
stable. Mock remains truthfully Mock, and a stable Sandbox plan is rendered as GoldTier
Sandbox or provider-neutral target wording.

One High provider-truthfulness blocker remains. The persisted
`ClmOrchestrationRecord.submission_plan` is captured from the provider configured when
the CLM record is created, while the later `GoldTierSubmissionInput.provider_mode` is
captured independently from the provider configured when submission is built. No domain,
service, durable-snapshot, or schema-v5 decode invariant binds those values. A restart or
configuration change can therefore execute Sandbox while the backend plan and frontend
claim Mock, or execute Mock while the plan claims Sandbox. Fresh adversarial probes
reproduced both directions and a schema-v5 codec round trip preserved the contradiction.
See GT-FINAL-RQG-01.

The exact reviewed identity is:

- branch: `feature/pre-phase22-capability-expansion`
- base / `HEAD` / locally recorded `origin/main`:
  `3ca232b58c3842f413c4552dbd3b85aabea4591c`
- candidate paths: 141
- candidate fingerprint:
  `5be7ac8979ba08afe7e8ff4004437a1f34e60f6c540d28a64b0358bf9366e772`
- source revision: the uncommitted 141-path candidate at the commit and fingerprint
  above
- test revision: the same exact candidate fingerprint
- review revision: the same exact candidate fingerprint; this report is the sole
  reviewer write and is excluded from the candidate fingerprint
- staged paths: zero

The ordinal, case-sensitive verifier matched the supplied count and fingerprint before
substantive review, immediately before this report, and after this report. A separately
reconstructed helper initially used a different ordering/hash invocation and produced a
non-authoritative digest; the unchanged 141 path/object records and the specified
ordinal verifier resolved that as a verifier-method discrepancy, not content drift.
The unexpected untracked root artefact was excluded by its assigned prefix and was not
opened, hashed, moved, deleted, or otherwise touched.

Q-016 remains deliberately deferred and is not a reason for this verdict. Phase 22
remains untouched and on hold. The prior FAIL reports are preserved. Publication may
proceed only on exact independent `PASS`, so this candidate is not publication-ready.

## 2. Phase Acceptance Checklist

| Review axis | Result | Independent evidence |
|---|---:|---|
| A. Complete accumulated candidate is sound | **FAIL** | GT-FINAL-RQG-01 permits retained provider plan/classification to contradict the actual target execution provider. |
| B. All prior gate findings are closed without regression | **FAIL** | Hard-coded retained Mock narratives are corrected, but the underlying Sandbox-must-never-display-as-Mock requirement still fails under provider configuration drift. Earlier entity, schema-v5 semantic, CSV, ADR, policy-binding, mutation-uncertainty, and percentage findings remain closed in reviewed source/tests. |
| C. Mock remains truthfully Mock | PASS | Stable Mock plan and execution render Mock-derived labels; the independent reverse-drift probe also confirms actual Mock execution is represented by `provider_mode=MOCK`, although its stale Sandbox plan proves the missing binding. |
| D. Sandbox never retains, projects, or displays Mock provider claims | **FAIL** | A persisted Mock plan followed by actual Sandbox execution completed four fake-transport HTTP operations while the retained plan remained `MOCK / MOCK`; frontend labels derive from that stale plan. |
| E. Authoritative provider mode/classification agree with execution identity | **FAIL** | CLM plan creation reads current provider mode independently from later submission-input construction. No cross-owner invariant rejects a mismatch. |
| F. Human messages and structured provider state agree | **FAIL** | Human narratives are now provider-neutral, but structured plan/classification can still contradict `GoldTierSubmissionInput.provider_mode` and the executed connector. |
| G. Memory and schema-v5 codec behavior fail closed | **FAIL** | In-memory orchestration accepted both drift directions. `MongoCaseStore` encode/decode preserved `plan=MOCK/MOCK` with `execution=SANDBOX` and a completed legacy status instead of rejecting it. Fresh physical Mongo is `MISSING_INFRASTRUCTURE`. |
| H. Frontend derives provider truth from backend plan/environment | **FAIL** | The frontend correctly consumes backend plan/environment, but the backend plan is not bound to actual execution. This makes the otherwise correct frontend derivation a vehicle for the stale Mock claim. |
| I. Audit and CSV truthfulness | PASS WITH DEPENDENCY | Stable-mode retained messages and CSV projections are provider-neutral and focused tests are green. They inherit the backend record's unbound structured provider context; no distinct audit/CSV defect was found. |
| J. Target ordering, stopping, ledger durability, and no-replay | PASS | Fresh focused target/orchestration/API/persistence selection passed 70 tests; XPI suite passed 59 tests. No separate ordering, stopping, or replay regression was reproduced. |
| K. No external provider/customer/database mutation | PASS | Reviewer probes used in-process fake transports only. No external provider, customer, related-party, or database mutation occurred. |
| L. Q-016 stays explicitly deferred | PASS | Assignment, note, due-time, and SLA mutation authority remains open/deferred; no owner or rule was invented. |
| M. Phase 22 stays untouched/on hold | PASS | No Phase 22 implementation or activation was found or performed. |
| N. Current verification supports publication | **FAIL** | Broad same-fingerprint implementer evidence and fresh focused reviewer checks are green, but existing tests omit provider-mode drift/restart binding and therefore do not falsify GT-FINAL-RQG-01. |

## 3. Contract and Integration Findings

### GT-FINAL-RQG-01 — HIGH — Retained provider plan is not bound to the provider actually executed

**Authority:** current source and tests, architecture/provider activation contracts,
the immutable execution-context requirement in the assignment, and the explicit rule
that Sandbox must never be presented as Mock.

The provider identity is captured twice from mutable service composition:

- `apps/backend/app/services/clm_orchestration.py:448-470` reads
  `OnboardingService.target_provider_mode` and builds the retained
  `GoldTierSubmissionPlan`.
- `apps/backend/app/services/clm_orchestration.py:472-482` persists that plan in the CLM
  record.
- `apps/backend/app/services/clm_orchestration.py:562-589` later asks the onboarding
  service to build the target submission input.
- `apps/backend/app/services/onboarding.py:523-558` independently reads
  `self._goldtier_mapper.environment` into `GoldTierSubmissionInput.provider_mode`.

The relevant models do not close the gap:

- `apps/backend/app/domain/clm.py:153-169` defines plan environment and classification
  as independent strings without a pair or execution-binding validator.
- `apps/backend/app/persistence/models.py:291-326` validates case and submission
  identities but does not compare the CLM plan with target-execution provider mode.
- The schema-v5 codec consequently accepts and reconstructs a contradictory durable
  snapshot.

Fresh independent adverse probes reproduced the observable impact:

1. Create a CLM record under Sandbox, then replace the execution mapper/connector with
   Mock before document completion and submission. The retained plan stayed
   `SANDBOX / SANDBOX_PARTIAL`; execution input was `MOCK`; terminal state was
   `COMPLETED / MOCK_GOLDTIER_SUBMITTED`.
2. Create a CLM record under Mock, then replace the execution mapper/connector with the
   real Sandbox dialect using a local fake transport before document completion and
   submission. The retained plan stayed `MOCK / MOCK`; execution input was `SANDBOX`;
   four Sandbox-dialect HTTP operations were observed; terminal state was
   `COMPLETED / MOCK_GOLDTIER_SUBMITTED`.
3. Encode/decode the second state through `MongoCaseStore`. The decoded snapshot still
   held `plan=MOCK/MOCK`, `execution_mode=SANDBOX`, and the completed legacy status.

The frontend follows the backend plan as intended:

- `apps/frontend/src/shared.ts:37-51` derives journey/outcome labels from environment.
- `apps/frontend/src/App.tsx:764-876` uses the plan environment for the main journey.
- `apps/frontend/src/pages/CaseDetail.tsx:560` uses the CLM plan for final outcome.

That is insufficient unless the backend plan is immutable and bound to execution. In
probe 2, actual Sandbox execution would therefore be displayed as Mock. In probe 1, a
Mock execution would be displayed as Sandbox. The same contradiction survives memory
and schema-v5 reconstruction, so a restart/configuration drift is not safely rejected.

This violates the provider-truthfulness and immutable execution-context requirements.
It is operationally security-relevant because an operator can mistake a networked
Sandbox action for a Mock-only action. Current all-TBD target policy limits customer
dispatch, but that separate precondition does not make false durable evidence
acceptable.

### Prior finding disposition

- The previous retained-message finding is closed for stable provider composition:
  orchestration, API, audit/CSV, and user-facing narratives no longer hard-code Mock.
- The earlier target-policy validation/snapshot-binding, mutation uncertainty/no-replay,
  and related-party percentage findings remain closed in current source and focused
  checks.
- The first capability-expansion gate's entity-resolution, schema-v5 intelligence,
  CSV-hardening, and canonical ADR findings remain closed.
- Prior FAIL reports remain unchanged and continue to provide failure history.

### Contract authority and deferred dependencies

- GoldTier XPI remains `PARTIAL / SANDBOX_PARTIAL`, never Live. Mock remains the
  default. No Mock fallback from Sandbox was found.
- All eight target-policy defaults remain `TBD_SPONSOR`; examples are not treated as
  policy authority.
- Related-party external execution remains blocked on child-ID lifecycle and
  relationship authority.
- Q-016 remains open/deferred and Phase 22 remains on hold. Neither is permission to
  expand this remediation.

## 4. Tester and Adversarial Findings

### Fresh independent evidence on the frozen candidate

| Check | Result |
|---|---|
| Frozen candidate verifier | PASS: 141 paths; fingerprint `5be7ac89...36e772`; branch/HEAD/origin-main matched; index empty. Repeated before and after the report. |
| `tests/test_goldtier_xpi_sandbox.py` | PASS: 59 tests in 1.43s. |
| Focused CLM/zero-touch/persistence/API target, GoldTier, submission, replay, and schema-v5 selection | PASS: 70 tests; 87 deselected in 5.31s. |
| Focused frontend App/request-preview/case-activity/state-explanation set | PASS: 4 files / 76 tests. Initial sandboxed execution could not spawn the local esbuild helper (`EPERM`); the authorized local-child-process rerun passed. |
| Contract suite | PASS: 44 tests. |
| Direct architecture, project-state, policy-authority, and external-provider-readiness checks | PASS. |
| Ruff over backend app/tests | PASS. |
| `git diff --check` | PASS; informational Windows LF-to-CRLF warnings only. |
| Docker daemon / fresh physical Mongo | **MISSING_INFRASTRUCTURE**: Docker client exists, but the Docker Desktop Linux daemon pipe is unavailable. |
| Independent provider-drift probes | **FAIL reproduced** in both directions; details in GT-FINAL-RQG-01. No external call was made. |
| Schema-v5 codec adverse probe | **FAIL reproduced**: contradictory plan/execution provider modes round-tripped without rejection. |

The physical Mongo limitation does not independently block this narrow cycle because it
changed no persistence schema or repository behavior. The deterministic model/codec
probe already proves the current blocker without a database. Earlier physical evidence
is historical supporting evidence only and is not relabelled as current.

### Inherited same-fingerprint evidence, not independently rerun

The implementation owner records the following against the exact frozen candidate:

- focused backend 151 passed and focused frontend 112 passed;
- full backend 1,297 passed / 29 infrastructure-skipped;
- frontend 22 files / 282 tests;
- contract 44, Windows lifecycle 23, and isolated Playwright 14/14;
- Ruff, strict Mypy, TypeScript, production build, dependency, governance, security,
  and provider-evidence checks green.

Those results are revision-matched supporting evidence. They do not cover configuration
drift between CLM plan creation and target execution, so their green status does not
override the reproduced defect.

## 5. Code and Architecture Review

The accumulated candidate otherwise preserves the intended boundaries: strict XPI DTO,
mapper, connector, safe response validation, one canonical entity owner, one Decimal UBO
engine, one target ledger, explicit Mock/Sandbox composition, backend authorization,
one persistence owner, and authenticated user/session/team-scoped frontend state. No
direct ACRA-to-GoldTier mapping, second target ledger, route-level Mongo logic, silent
provider fallback, production activation, or Phase 22 implementation was found.

GT-FINAL-RQG-01 is a missing cross-owner invariant at an existing boundary. It does not
justify a new provider-status owner or persistence schema. The immutable submission
context must either capture one provider identity used by both plan and execution, or
validate the retained plan/classification against the target input and fail closed at
construction, execution, and durable decode/recovery boundaries.

## 6. Security Review

The reviewed Sandbox connector continues to use TLS 1.3, certificate verification,
disabled redirects, bounded timeout/body/candidate counts, backend-only transport
identity, fixed safe errors, explicit write opt-in, and no fallback to Mock. The target
ledger's mutation-uncertain no-replay behavior remains intact in reviewed source/tests.

No credential, `.env`, bearer token, password, private key, raw provider response,
confidential KYC payload, or private sponsor value was read or written. Reviewer probes
used deterministic local objects and fake transports. No provider, customer,
related-party, Mongo, or other external mutation occurred.

The remaining finding is security-relevant as evidence integrity and operator safety:
durable/UI provider claims can misrepresent whether a networked Sandbox boundary was
used. It does not expose a secret or bypass RBAC, but it prevents a truthful audit and
publication decision.

## 7. Required Fixes

1. Establish one immutable provider identity for a case submission and bind
   `submission_plan.environment/provider_classification` to
   `GoldTierSubmissionInput.provider_mode` and the selected connector before any ledger
   or network action. Reject any mismatch fail closed.
2. Enforce the same binding in durable schema-v5 reconstruction/recovery without
   silently rewriting historical data or inventing schema-v6 unless genuinely required.
3. Add focused adverse tests for Mock→Sandbox and Sandbox→Mock configuration/restart
   drift across memory, schema-v5 codec, API/audit projection, and frontend rendering.
   Prove actual Sandbox can never display Mock and actual Mock cannot display Sandbox.
4. Rerun affected focused and required broad/static/contract/governance/lifecycle/
   browser checks, freeze a new fingerprint, and obtain a fresh independent exact gate.

This is the third remediation cycle. Stop and return the design/ownership question to
the planner/human owner rather than performing a fourth speculative repair in this
review. Do not fold Q-016, related-party dispatch, sponsor policy values, Live provider
claims, or Phase 22 into any correction.

## 8. Readiness and Residual Risks

- **Publication readiness:** NOT READY. Exact `PASS` was not achieved.
- **Pre-Phase 22 candidate readiness:** NOT READY pending GT-FINAL-RQG-01 ownership
  decision, remediation, a new freeze, and fresh independent exact review.
- **GoldTier status:** Mock by default; XPI `PARTIAL / SANDBOX_PARTIAL`; never Live.
- **Persistence evidence:** current logical memory/codec defect reproduced; fresh
  physical Mongo is `MISSING_INFRASTRUCTURE` and is not borrowed from history.
- **Q-016:** open and deliberately deferred; not the gate blocker.
- **Related party:** dispatch remains blocked pending child-ID lifecycle and relationship
  authority.
- **Phase 22:** remains untouched and on hold regardless of this verdict.
- **Authorized next action:** planner/human review of the provider-identity ownership
  defect. No staging, commit, push, PR, publication CI, merge, or next phase is
  authorized by this report.

## 9. Git Status

- branch: `feature/pre-phase22-capability-expansion`
- base / `HEAD` / locally recorded `origin/main`:
  `3ca232b58c3842f413c4552dbd3b85aabea4591c`
- staged paths: 0
- frozen candidate: 141 paths
- exact reviewed fingerprint:
  `5be7ac8979ba08afe7e8ff4004437a1f34e60f6c540d28a64b0358bf9366e772`
- final post-report verifier: 141 paths, same fingerprint
- permitted reviewer write: this report only
- implementation/source/test/configuration/ordinary-doc/other-report changes by
  reviewer: none
- Git index/refs changed by reviewer: none
- external provider/database state changed by reviewer: none
- commit/fetch/push/PR/merge/Phase-22 action: none

The unexpected root artefact was preserved and excluded exactly as instructed. It was
not opened, hashed, moved, deleted, or otherwise inspected.
