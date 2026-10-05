# Post-closeout existing-customer final independent quality gate

Date: 2026-10-05. Fresh independent recheck after authorized remediation R1.
Workflow: fyp-quality-gate, with contract, security, persistence, cache and regression
review components. Owner-requested route: GPT-6.1 Sol / High; no child agent was used.
Exact runtime model labels are not independently exposed by a verification tool.

## Executive result

**PASS — P0/P1/P2 = 0/0/0. No required fix remains.**

The original P2 invalid-request echo is closed by the existing safe validation-error
owner and four focused regressions. Independent replay of the original defect and
additional malformed inputs now yields the fixed safe code/message, unchanged evidence
and zero additional provider calls. The complete post-fix backend coverage and required
affected checks pass. This verdict releases only the owner's conditional authorization
for local commits of unchanged reviewed content. It does not claim a commit, clean
committed tree, PR readiness, publication, merge, next phase or Live interoperability.

## Exact reviewed identity and history

Branch: `fix/goldtier-existing-customer-resolution`.
Worktree: `C:/Users/shane/.codex-clean2/worktrees/goldtier-existing-customer-resolution/data-dividends-zero-touch-clm`.
BASE_SHA, source HEAD and observed local `origin/main`:
`1e0600335a0c7677b5cd5d5c9dd8401dfaf3b90f`.
The coordinator's latest fetch recorded this same baseline; the reviewer made no Git
mutation. HEAD identifies the baseline, not the uncommitted remediation.

Final reviewed content: 42 changed/new paths, LF-normalized SHA256 aggregate
`f0b7e1c317fc6831d9216e1128f0e53b22f526d7ef82f145e2ccd89bf6bb0959`.
Each current file digest, sorted compact-JSON aggregate and complete Git changed/new
pathset was independently checked. Digest construction is SHA256 of file bytes with
CRLF normalized to LF; then SHA256 of compact UTF-8 JSON of sorted
`{path, sha256_lf}` entries with sorted keys. The assigned report is excluded.
The identity was checked again before and after report write.

Historical round 1: **FAIL, P0/P1/P2=0/0/1**, on
`b93f56ba45c7d6f8a76ce0b51942d2e8f4f7781eaea07a14bca1b5e85fafc56f`.
Original report SHA256 before this final update:
`f80b3949ce2318ab607920b131c6ed91a254c741ca1fc018d885b7dc7f854722`.
That finding is preserved below rather than rewritten as a historical PASS.
The earlier 40-path candidate was replaced before an independent verdict after
coordinator checks found the ordinary-read lock and selector-count issues.

R1 is limited to `apps/backend/app/main.py` and
`apps/backend/tests/test_goldtier_xpi_sandbox.py`: the fixed error-handler branch
and four no-echo regression variants. Independent compact-JSON reconstruction reproduces the recorded round1 aggregate;
all other 40 file hashes match. Independently removing only the exact new handler
branch and parameterized test block from the current two files reproduces their
round1 byte digests. The other 40 paths therefore retain the preceding review/execution
identity. No domain, provider, ledger, UI, durable field, owner,
configuration or acceptance-criterion delta occurred during R1.

Authority/read-set: owner assignment and subsequent direct provider-family correction;
AGENTS; emitted change-class Tier1 references and workflow; active planner;
quality-gate/template and relevant contract/security/persistence/cache/regression skills;
current architecture/state, family contracts/discrepancies, ADR-007/D-068 and sponsor
questions; all 42 changed/new paths and owning authorization/document/reconciliation/
target/persistence paths; prior accepted gate and regression catalogue. Selective private
XPI collection/EDS Search contract inspection confirmed the family distinction without
reading .env, credential material, quarantined authentication or customer bodies.

## Acceptance and owner review

| Assigned criterion | Result | Evidence and boundary |
|---|---|---|
| Worktree/base/scope and existing owners | PASS | Exact branch/base, pathset and empty index; existing Onboarding/CLM/ZeroTouch/access/codec/ledger owners retained. |
| Document Accept/Reject/Correct while Search unresolved | PASS | Three backend variants and reconciliation regression preserve earliest Search, blocked readiness and zero target mutations; guarded browser correction succeeds. |
| Automatic provider identity from singleton UEN/country | PASS | Retained provider registration/country equality produces provider EXACT_MATCH without prior local case; Mock finalized-proof prerequisite remains. |
| Bounded incomplete singleton confirmation | PASS | Matching normalized legal name and current independent identity; backend-authored creator action records CONFIRMED_EXISTING, never provider EXACT_MATCH. |
| Creator/session/team authority and exact versions | PASS | Reauthorization inside shared case lock; noncreator403/inaccessible404; stale Search UUID, automation, CLM and case counts rejected; canonical fingerprint recomputed. |
| No arbitrary GoldTier ID or confirmation provider call | PASS | Strict request extra-forbid; ID derived only from retained candidate; rejected requests and valid confirmation dispatch nothing. |
| Multiple/conflicting/correlation-only candidates | PASS | No silent selection; known name/UEN/country contradictions and correlation-only evidence remain review-only. |
| Audit, persistence and interrupted projection | PASS | Actor/UTC/rationale/request/ID retained; interrupted local projection repairs without replay; physical restart preserves receipt/document decisions. |
| Existing-customer target branch | PASS | Current guarded browser: Search 1, Shell 0, Policy 0, Amend 0; final Review & Send adds Readback 1 using retained ID and truthful SUBMISSION_CONFIRMED. |
| Garden ownership | PASS within offline scope | Fake official-Mock/native-document regression retains PARTIAL partnership/empty official quantitative relationships and OWNERSHIP review; reviewed LOCAL evidence and single Decimal engine remain required. |
| New-customer/no-replay/call stopping | PASS | Complete backend, physical adverse/restart evidence and affected new-success/uncertain/failed browser lanes retain ordering and prohibition of mutation replay. |
| Frontend authority/cache/action behavior | PASS | Creator/backend-derived form, no target-ID input, independent focused18/full509 tests, existing scoped cache/generation/mutation owner; current valid browser flow succeeds. |
| Family/sponsor truth and durable docs | PASS | XPI four aliases retained; supplied EDS registration/external-key Search remains separate; current overlays preserve historical/quarantined evidence and broader open questions. |
| Invalid-request safe errors — QG-01 | PASS after R1 | Exact constant422 body, no input/framework details, unchanged checkpoint/automation and no added provider call across new regressions and independent reproduction. |

## QG-01 disposition — historical P2, CLOSED after R1

Round 1 reproduced HTTP422 from the new confirmation route as a FastAPI default detail
list containing `type/loc/msg/input/ctx` and the rejected rationale sentinel.
This was rejected-input/framework-detail projection to the authorized caller, not a
cross-user disclosure or target mutation bypass. It violated the existing fixed
safe-error/minimization contract and blocked local commits.

The current `safe_request_validation` handler in `main.py:833` now recognizes the
zero-touch confirmation path and returns only
`ZERO_TOUCH_EXISTING_CUSTOMER_INVALID` plus the fixed trusted message.
The request model is unchanged. Four parameterized regressions in
`test_goldtier_xpi_sandbox.py:545` cover C0 rationale, arbitrary extra target ID,
invalid version type and invalid request UUID; they assert the exact response,
no input echo, unchanged receipt/checkpoint and automation version, and Search-only
transport count.

Independent replay used the original C0 sentinel plus extra ID, invalid version,
invalid UUID, whitespace rationale and negative event count. All six returned the same
fixed safe 422 and no mutation/provider call. Valid creator confirmation, stale versions,
conflicts/multiple candidates, interrupted recovery, document independence and access
denials also passed on the final content. No other finding was identified.

## Executed evidence and exact attribution

Fresh independent R1 execution:

| Lane | Actual result |
|---|---|
| Owning backend happy/adverse/API/security/document/reconciliation/recovery focus; anyio enabled, plugin autoload disabled and pytest cache disabled | 30 passed, 347 deselected, 12.23s. |
| Original defect plus additional ephemeral malformed requests | Six safe 422/no-echo/unchanged-evidence/no-added-call cases passed. |
| Current guarded existing-customer browser, reserved loopback 8895/4295, generated auth and fake transports | 1 passed, 5.6s; owned process cleanup succeeded. |
| Configured contract unittest discovery | 44 passed, 1.772s. |
| Ruff backend plus three changed scripts and owning tooling test, no cache | PASS. |
| Configured strict mypy with Pydantic plugin and external cache | PASS, 124 source files. |
| Secrets/architecture/project-state/policy-authority/external-readiness/tooling/guide checkers | All seven PASS; generated guide matches 62 codes. |
| Tracked whitespace and explicit UTF-8 Markdown inspection including new files | PASS; empty index; exact reviewed pathset plus assigned report only. |
| Backend shard inventory | Independently verified exhaustive/disjoint union of 106 tracked test files, groups 27/27/26/26; no test file removed. |

Coordinator post-fix complete backend execution, independently inspected actual result
artifact and orchestrator:
**PASS: 2330 passed, 120 prerequisite skips, 0 failures/errors; 2450 total cases,
498.86s overall; all four subprocesses exit 0.**
Shard counts (passed/skipped): 685/65,725/6,509/31,411/18.
The inspected result artifact's path union equals all 106 owning tracked test files,
with each included once. The final source stayed frozen at the identity above.

The temporary orchestrator is outside the repository. It invokes the standard pytest
flags on four disjoint file groups, removes physical-Mongo/OCR prerequisite switches,
captures subprocess output, reports sanitized aggregate counts/failed node IDs and uses
hidden Windows children. Every owning test file and all 2450 collected cases are included.
This is complete backend execution in four processes, not a second independent full
backend run or a claim of sequential execution.

Pre-R1 evidence remains separately attributed to the unchanged surfaces, not relabelled
as new execution:

- Independent physical Mongo: 16 suites/114 collected and passed, 0 failure/error/skip;
  task-owned verified mongo:7/label/loopback 27925, generated allowlisted databases and
  cleanup/absence helper only. No clm_poc access or URI output.
- Coordinator installed local Tesseract synthetic acceptance: 6 passed, 30 deselected,
 10.55s, using temporary process PATH only. Together these separately cover the 120
 ordinary backend prerequisite skips (114 physical, 6 OCR).
- Independent full frontend:509 passed/42 suites,9.23s; focused confirmation/document:
 18 passed/2 suites. Configured typecheck and build passed; build output was redirected
 outside the repository (128 modules, existing >500kB bundle warning only).
- Four affected guarded browser modes each passed 1: existing, new success,
 uncertain-policy and failed-policy. The fresh independent existing flow above exercises
 the final handler. The entire60-selector/67-test browser inventory was not run.
- Root checks excluding unchanged Windows module:345 passed,111.20s. Earlier combined
 root execution remains **1 failed/295 passed**,683.81s due to the old selector count.
 All31 unchanged Windows cases precede that first later failure; separate collection
 confirms 31. Their completion is derived execution/order evidence, not a standalone
 31-passed result or combined full-root PASS. Final tooling focus separately passed 3.
- Earlier complete backend on round1 content: 2326 passed/120 prerequisite skips,
 1064.80s. It is distinct from the post-fix aggregate above.
- Independent round1 malformed-request/whitespace scratch setup failures were corrected
 before conclusions and never counted as passing tests. Test-client deprecation and
 existing bundle warnings remain explicit.
- No pre-PR gate, external provider smoke, publication or next phase was executed.

## Security, persistence, architecture and limits

Source DTO -> canonical evidence -> target mapping, backend authorization, strict
provider identity, case lock/CAS and the sole target ledger remain authoritative.
Confirmation records human identity evidence without provider activity. Final Review &
Send owns local submission approval; ledger-owned ordering, required readback and
uncertain no-replay remain. Ordinary reads remain lock-free; only an actual interrupted
retained-confirmation Search seam takes the recovery lock and re-reads within it.

Schema9 retains additive initial candidate identity tuples and optional receipt/new
disposition. Missing historical values remain unknown. No version/migration, read rewrite,
CAS/create/update/delete semantic, fallback or repository owner changed. Physical evidence
proves persistence/restart/no-replay in the tested single-process POC; older binaries
cannot interpret newly written confirmed-existing values.

External ACRA calls=0. External GoldTier calls=0. No owner .env, credentials, protected
original database, raw customer/provider payload or quarantined authentication material
was used. Secret scanner passes within its configured pattern coverage.

XPI remains `goldTierID/legalName/groupCompanyName/countryOfIncorporation`.
Supplied EDS registration/external-key Search is a distinct future assigned provider-family
delta; no alias was invented. Provider classifications remain Mock/LOCAL/SANDBOX_PARTIAL.
Production/PingFed/Live, full legal/control UBO, related-party child lifecycle,
original-file upload, broader target value reconciliation/mapping and downstream
GoldTier KYC/four-eye/RFA remain separate later dependencies. Historical Garden failed/
uncertain attempts are preserved and cannot be replayed by this remediation.

## Change classes, readiness and Git/write boundary

Changed by the bounded remediation: API/types, additive durable fields, identity/evidence
decision and runtime behavior, creator-authorized route/action projection, frontend
affordances, CI outer budget/test inventory and active documentation.
R1 changes only invalid-request projection and its four tests.
Unchanged: connector endpoint/query/DTO transport contract, target mapping, runtime
configuration/provider-family composition, schema version, owner/dependency map,
provider classifications and external/production authority.

**Local-commit readiness: YES for unchanged reviewed content under the owner's existing
conditional authorization.** R1 closes the sole independent finding; no second
remediation round is required. No push, PR, merge or next phase follows. The coordinator
must verify this reviewed identity, stage only the reviewed paths plus this report and
inspect the staged diff before authorized local commits.

At gate: 39 tracked modifications plus 3 task-owned new paths and this additional report;
empty index. This reviewer wrote only the assigned report and performed no implementation
fix, Git mutation, install, commit, push, merge or next phase. Source/verification/review
identities remain distinct. The final 42 reviewed paths are listed below; the report is
excluded independent bookkeeping.


~~~text
.ai-pipeline/001_planner/POST_CLOSEOUT_EXISTING_CUSTOMER_REMEDIATION.md
.github/workflows/ci.yml
apps/backend/app/api_models.py
apps/backend/app/domain/clm.py
apps/backend/app/domain/models.py
apps/backend/app/domain/target_submission.py
apps/backend/app/domain/zero_touch.py
apps/backend/app/main.py
apps/backend/app/services/authorization.py
apps/backend/app/services/blocker_decision_policy.py
apps/backend/app/services/clm_orchestration.py
apps/backend/app/services/onboarding.py
apps/backend/app/services/zero_touch_orchestration.py
apps/backend/tests/test_goldtier_xpi_sandbox.py
apps/backend/tests/test_phase13_auth_rbac.py
apps/backend/tests/test_slice_c_real_mongo.py
apps/backend/tests/test_zero_touch_orchestration.py
apps/frontend/e2e/s3-sandbox-submission.e2e.ts
apps/frontend/src/api.ts
apps/frontend/src/pages/CaseDetail.tsx
apps/frontend/src/pages/DocumentEvidencePanel.test.tsx
apps/frontend/src/pages/ExistingCustomerConfirmation.test.tsx
apps/frontend/src/pages/HumanInterventionPanel.tsx
apps/frontend/src/pages/ReviewAndSend.tsx
apps/frontend/src/types.ts
docs/ARCHITECTURE.md
docs/PROJECT_STATE.md
docs/contracts/GOLDTIER_CONTRACT_BASELINE.md
docs/contracts/GOLDTIER_CONTRACT_DISCREPANCIES.md
docs/contracts/PERSISTENCE_RECOVERY_PROFILE.md
docs/decisions/ADR-007_RECOVERABLE_ONBOARDING_AND_FINAL_CONFIRMATION.md
docs/decisions/DECISION_LOG.md
docs/demo/BLOCKER_RECTIFICATION_GUIDE.md
docs/demo/FINAL_POC_LIMITATIONS_AND_NEXT_STEPS.md
docs/integration/GOLDTIER_EXISTING_CUSTOMER_RESOLUTION.md
docs/integration/GOLDTIER_XPI_MAPPING_MATRIX.md
docs/integration/GOLDTIER_XPI_SANDBOX_RECONCILIATION.md
docs/sponsor-questions/OPEN_QUESTIONS.md
scripts/generate_blocker_rectification_guide.py
scripts/run_e2e.py
scripts/s3_sandbox_fixture.py
tests/test_run_e2e.py
~~~
