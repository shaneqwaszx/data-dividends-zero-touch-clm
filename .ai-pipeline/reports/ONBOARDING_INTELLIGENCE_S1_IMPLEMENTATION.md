# Session 1 implementation evidence

Owner-authorized program received 2026-10-04. Candidate uncommitted on
`feat/onboarding-intelligence-goldtier-sandbox`; BASE_SHA/HEAD/origin/main at task start
`1d426e0ceddc32d80b0aaec293c62fb761f2fecf` (PR68). No publication authorized.
Current content is not independently accepted until the separate gate records PASS.

## Reproduced defect and repair

The real guarded browser journey selected a synthetic PDF, created wrong UEN 99999999Z,
then inspected its case documents: the baseline returned zero records. The browser's
retained-intake helper stopped before upload on ACRA_ENTITY_NOT_FOUND. The API separately
rejected retained intake with 409. Identity correction did not delete a durable document;
in this journey the document had never been uploaded. Earlier test-selector/racing mistakes
were corrected before using this observation as defect evidence.

Retained intake now accepts recoverable registry-not-found cases while preserving hard
jurisdiction/provider safety stops. Identity correction refreshes existing document-owner
comparisons using retained observations, then existing reconciliation/orchestration
auto-resumes. Document IDs, original fields, provenance and review decisions remain retained.
Replacement semantics remain separate. Low-quality and source-conflict adverse cases
retain genuine document blockers rather than clearing them with identity correction.

## Sanitized configuration diagnosis

Only the five owner-allowlisted fields were parsed for presence, with effective environment
override considered. No values were printed or persisted; no private file was modified.

| Variable | Present |
|---|---|
| GOLDTIER_CONNECTOR_MODE | Yes |
| GOLDTIER_SANDBOX_BASE_URL | Yes |
| GOLDTIER_SANDBOX_ENVIRONMENT | Yes |
| GOLDTIER_SANDBOX_USER_ID | Yes |
| GOLDTIER_SANDBOX_ALLOW_WRITES | Yes |

Explicit Sandbox selection: false. Writes enabled: false. Network calls: zero.
The reported GOLDTIER_SANDBOX_NOT_CONFIGURED is an effective composition/configuration
guard, not evidence of a provider outage. The console now explains configuration readiness
and prevents an unconfigured Search dispatch. Configured Search remains diagnostic/read-only.
No private setting is changed automatically. Any future isolated Sandbox acceptance must
satisfy the Session 3 prerequisites and use only authorized backend configuration.

## Verification receipts

Focused backend recovery/date/portfolio: 48 tests passed; real wrong-UEN browser journey:
1 passed after upload-durability synchronization. Auth/forms focus: 80 passed; date UI
and portfolio focus: 12 passed; diagnostics/configured console focus: 15 passed.
Broader frontend at this intermediate tree: 454 passed / 39 files. Strict mypy:
118 source files passed. Physical Mongo: 90 passed / 14 explicit suites, zero skips,
including 72 new memory/Mongo date-query comparisons. Disposable task-owned container
only; original clm_poc never accessed. Secret scanner and policy authority checker passed.

Final Session 1 checks: backend 2041 passed / 90 physical skips (physical suite separately
90 passed / zero skips); full frontend 455 passed / 39 files; typecheck/build passed;
strict mypy 118 source files; backend Ruff and changed runner Ruff passed. Contracts:
44 passed. Governance/security checker tests: 59 passed. Physical runner: 19 passed.
Final focused backend projection/recovery/optional-Amend: 52 passed after final wording.
The full backend imported an earlier recovery status string; this focused execution
verifies its later truthful wording. No workflow/target behavior changed in that string delta.
Earlier failed runs and incorrect selector/import/cache assumptions were corrected and
rerun; no failed or unexecuted result is presented as PASS.

Browser pack: five new S1 journeys plus four Phase24 identity-recovery journeys; eight
passed together, then the one old final-label assertion was corrected and rerun separately.
Keyboard diagnostic-focus journey also passed. Native browser widths 320/720/1280,
inert workspace/live status, all 12 stages, failed document query, neutral role switches,
draft resets and both server date endpoints were exercised. No network policy violation.
Owned browser processes were cleaned by the launcher. Vite retains its existing >500kB
bundle warning; FastAPI/httpx and deliberate malformed-Pydantic fixtures emit known warnings.

The frozen path/content manifest identifies the review candidate independently from HEAD.
No further implementation write is allowed during independent review. These receipts
are implementation evidence, not an independent gate verdict.

## Change classification

API/type: optional creation-date queries and safe pipeline projection changed.
Schema/persistence: repository read predicates changed; durable schema/index/write/CAS
semantics unchanged. Connector/provider: unchanged. Configuration: no private/default
change. Business rules/mapping: no target business mapping changed; project-defined date
semantics and owner-final local approval language documented. Auth/security: session route,
query and draft reset changed; backend scope unchanged. Architecture: existing owners
retained. Runtime/frontend state: intake/recomparison, scoped queries, state language and
workspace presentation changed. Tooling: new physical suite registered. Docs updated.

## Session 1 remediation round 1

The initial independent gate reviewed the frozen 59-path candidate
`a39c00cd8e707c83e037dc5f54a7032573bb0a5214ccc53f7a8935c663d0266e`.
All independently executed behavioral checks passed; its sole P2 finding was stale
owning-contract wording at `CLM_READINESS_POLICY.md:21`. This round changes only that
row to distinguish retained original extraction/provenance/human decisions from the
current comparison snapshot refreshed under D-066/ADR-007. Product source and tests
remain byte-identical to the initial independently reviewed candidate.

Fresh documentation/governance checks passed: 59 checker tests; project-state,
architecture, policy-authority and secret scanners; tracked diff and explicit untracked
text whitespace. The complete contract delta was inspected against the passing source.
The revised complete manifest records its reproducible aggregate algorithm. Fresh
independent PASS remains required before Session 2; the initial FAIL is not rewritten
as a passing execution. Remediation rounds used: 1 of 2.

## Sequential handoff

Obtain the frozen independent S1 mini-gate. S2 OCR and
ownership intelligence remain unimplemented. S3 external acceptance remains unexecuted.
No external Sandbox call, commit, push, PR or merge has occurred.
