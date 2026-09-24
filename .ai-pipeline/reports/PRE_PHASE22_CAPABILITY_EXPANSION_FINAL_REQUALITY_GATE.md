# Pre-Phase 22 Integrated Capability Expansion — Final Re-Quality Gate

Date: 2026-09-24
Reviewer role: fresh independent final quality gate
Decision scope: the complete user-authorized Pre-Phase 22 Integrated Capability
Expansion, not only the separable locally implementable subset

## 1. Executive Result

**FAIL**

The exact frozen candidate closes every implementation defect from the first quality
gate and first re-quality gate. Independent adverse probes and the current automated
suites pass for the implemented entity-resolution, advisory UBO/risk, schema-v5,
persistence, authorization/cache, workflow/ledger, audit/CSV, evaluation, and
governance slices.

The combined request is nevertheless incomplete in two separately governed lanes:

1. the named GoldTier XPI PDF, Postman collection, approved non-secret sandbox
   configuration, and executable provider access are absent, so the requested XPI
   reconciliation, transform/preview, search, and optional guarded-write acceptance
   cannot be established; and
2. Q-016 still supplies no sponsor authority for assignment, note, due/SLA, routing,
   escalation, or notification mutations, so the requested Exception Workbench
   mutation acceptance is absent.

Omitting those capabilities was the correct fail-closed implementation choice. It does
not satisfy the original combined acceptance or permit a `PASS`. Publication is not
authorized. Phase 22 remains on hold.

## 2. Evidence Identity

| Identity item | Independently established value |
|---|---|
| Repository | `C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm` |
| Branch | `feature/pre-phase22-capability-expansion` |
| `HEAD` / current source revision | `3ca232b58c3842f413c4552dbd3b85aabea4591c` |
| `origin/main` | `3ca232b58c3842f413c4552dbd3b85aabea4591c` |
| merge base | `3ca232b58c3842f413c4552dbd3b85aabea4591c` |
| `HEAD` tree / accepted base tree | `848dcde901a33908bc5a3a6446021da2489d6be1` |
| Reviewed and tested content identity | working-tree candidate fingerprint `efc3369595389387513f492ed800fd1250e03d808a74e15d722ec0176f857417` |
| Fingerprint definition | SHA-256 over the ordinal, case-sensitive sorted union of tracked-modified, staged, and untracked candidate paths; each line is `path<TAB>git hash-object`; lines are LF-joined with no terminal LF |
| Candidate state before this report | 83 paths: 47 tracked modifications, 36 untracked files, 0 staged |
| Report exclusion | only this final re-quality-gate report is excluded from the candidate fingerprint |

The fingerprint was independently recomputed before substantive review, matched the
coordinator's corrected re-freeze, and was recomputed immediately before this report.
The earlier `90811e...` value was an acknowledged PowerShell collection/join calculation
error, not candidate drift. Current source revision, behavior-tested content, and exact
reviewed content are therefore recorded separately: the Git revision remains the base
commit while the behavior and review apply to the fingerprinted uncommitted candidate.

## 3. Findings First

### FINAL-RQG-001 — Blocker — Required GoldTier XPI contract and sandbox acceptance is absent

**Status:** dependent blocker; not an implemented-code defect.

The request expressly treats the supplied XPI PDF and Postman collection as authority
for XPI DTOs, enum spellings, paths, headers, authentication shape, mapping, search, and
guarded write behavior. The exact attachment directory contains only `Pasted text.txt`.
No named PDF or Postman collection is available in the reviewed input, and no approved
non-secret XPI host/user configuration or executable sandbox access was available in
this reviewer session.

The candidate truthfully records `NOT EXECUTED`, retains Mock GoldTier, and adds no XPI
DTO, mapper, connector, search client, preview, or write path. No provider/network call
was made. These are correct controls, but goals A and B and the provider portions of the
verification/demo matrix are not delivered or verified. A missing authoritative
contract cannot be replaced with the old combined bundle, examples, guesses, or the
current legacy mock mapper.

**Required closure:** attach the exact XPI PDF and Postman collection; provide approved
non-secret host/user configuration and an authorized test window; reconcile them under
the GoldTier precedence rules; then implement and independently verify the requested
preview/search and any explicitly enabled write behavior without activating a Live
claim.

### FINAL-RQG-002 — Blocker — Q-016 leaves requested assignment/note/SLA behavior unauthorized and absent

**Status:** dependent sponsor-authority blocker; not an implemented-code defect.

`docs/sponsor-questions/OPEN_QUESTIONS.md` keeps Q-016 open. It does not define eligible
roles, target-user/team constraints, assignment/reassignment ownership, note privacy,
CAS and audit semantics, due-time/SLA calculation, or routing/escalation/notification
effects. The candidate therefore correctly omits claim/assign/unassign, notes, due time,
SLA policy, and their backend/API/UI mutations. It also does not claim that current
project-defined priority behavior resolves Q-016.

The read-only workbench integration is useful: typed entity/risk exception categories
flow through the existing Attention Queue, case detail exposes bounded advisory
evidence, and current status/priority/team/exception filtering remains authoritative.
It is not the complete Exception Workbench requested in goal F and the acceptance
matrix. Safe omission cannot be converted into combined acceptance.

**Required closure:** obtain an explicit sponsor decision for Q-016, record the
capability/RBAC/team-scope, assignment, note, due/SLA, CAS, audit, and downstream-effect
contracts, and run a separately planned implementation and independent gate.

### Implemented-slice result

No additional current defect was found in the implemented separable slices. In
particular, the prior gate findings are closed as follows.

| Prior finding | Final disposition | Independent evidence |
|---|---|---|
| `P22-QG-001` / `P22-RQG-001`: false entity matches, finally distinct usable identifiers when either country is missing | **CLOSED** | Both one-sided missing-country/different-ID directions return `NO_MATCH`, no selected candidate, and identifier agreement `0`; the v3 evaluation includes both cases. |
| `P22-QG-002` / `P22-RQG-002`: fail-open schema-v5 semantic and case/policy binding | **CLOSED** | Aggregate validation binds catalogue, case/entity outcome, immutable weights/model, UBO threshold/model, risk thresholds/readiness/model, and service reuse/replacement. Five raw corruption probes are rejected at durable boundaries. |
| `P22-QG-003`: CSV control-prefix injection | **CLOSED** | Independent exhaustive probe neutralized all 3,860,460 Unicode whitespace/category-C plus `=+-@` combinations; direct marker and safe-text controls also passed. |
| `P22-QG-004`: missing canonical ADR | **CLOSED** | `docs/decisions/ADR-003_ONBOARDING_INTELLIGENCE.md` is `Accepted`; D-047 links it; the planning ADR is explicitly superseded. |
| `P22-RQG-003`: stale canonical policy/activity contracts | **CLOSED** | The canonical profiles and authority checker now bind the 21-rule/13-intelligence catalogue, schema v1-v5, required v5 projection, and bounded authorized CSV route. |

## 4. Full Acceptance Matrix

| Requested requirement | Result | Direct evidence / boundary |
|---|---|---|
| A. Validate authoritative GoldTier XPI contract and sandbox access | **FAIL — BLOCKED** | Named PDF/Postman and approved runtime configuration are absent; DNS/TLS/auth/HTTP/search were not executed. `GOLDTIER_XPI_SANDBOX_DIAGNOSIS.md` truthfully says `NOT EXECUTED`. |
| B. Implement XPI source-to-request transform, preview, connector/search, and guarded optional writes | **FAIL — BLOCKED** | No authoritative DTO/path/enum/header contract exists in the supplied evidence; the candidate correctly adds no XPI implementation and leaves GoldTier Mock only. |
| C. Deterministic/ML-assisted entity resolution with explainability and false-positive controls | **PASS** | Unicode-normalized descriptive features, strict usable-ID conflict handling, bounded candidate contributions, reason codes, manual-review states, two missing-country adverse directions, and 17/17 v3 scenarios pass. |
| D. ML-assisted UBO remains advisory over the one Decimal ownership engine | **PASS** | The advisory owner consumes the authoritative ownership result, preserves cycle/incomplete/threshold semantics, exposes non-legal labels, and passes 3/3 evaluation scenarios. No second ownership engine exists. |
| E. Mock advisory risk remains non-compliance and non-blocking by default | **PASS** | Closed limitation vocabulary, explicit Mock/non-production labels, policy-bound thresholds, default `affects_readiness=false`, and 5/5 evaluation scenarios pass. Any readiness effect is case-bound and opt-in. |
| F. Exception Workbench read-only triage | **PASS for implemented subset** | Existing Attention Queue receives typed entity/risk exceptions and opens the case; case detail shows bounded intelligence; existing status/priority/team/exception filters remain authoritative. |
| F. Exception Workbench claim/assign/unassign, note, due/SLA, routing/escalation/notification behavior | **FAIL — BLOCKED** | Q-016 authority and required mutation contracts are absent; the candidate intentionally does not implement them. |
| G. Audit activity and bounded CSV export | **PASS** | Safe `INTELLIGENCE_EVALUATED` event, backend case/team authorization, current filters, UTC, fixed columns, 100-row maximum, `no-store`/`nosniff`/download headers, and Unicode-wide formula neutralization pass. |
| H. Two integrated SME scenarios and truthful demonstration | **PASS for local/mock scope** | Straight-through and exception/review scenarios use Mock ACRA/local deterministic services/Mock GoldTier; labels and demo docs do not claim Live provider interoperability. |
| Schema v5 plus legacy v1-v4 reads | **PASS** | v5 requires the complete intelligence projection and semantic/case-policy binding; legacy reads remain covered without inventing v5 data. |
| Persistence, CAS, restart, deletion/no-resurrection, BSON safety | **PASS in logical suites; independently physical-unverified** | Memory/Mongo encoders and decoders fail closed, reuse/replacement is validated, CAS and deletion tests pass. Implementer evidence reports disposable Mongo 8 suites/29 tests including corrupted restart rejection; this reviewer could not rerun because the Docker daemon was unavailable. |
| Projection cache/service reuse and replacement | **PASS** | Identical fingerprint reuses version 1; an authoritative ownership-version change replaces it with version 2; corrupt retained projections are rejected by both `get` and `evaluate`. |
| Backend authorization, inaccessible-case behavior, and team scope | **PASS** | Intelligence/API and CSV routes reuse backend case access; inaccessible and absent cases retain safe 404 behavior; no frontend authorization owner is introduced. |
| Frontend authenticated cache boundaries | **PASS** | Query keys are user/session and case scoped; supporting mutation invalidation, deletion cancellation/removal, logout/identity/401 clearing remain covered. |
| Workflow, terminal-state, provider-call stopping, and target-ledger invariants | **PASS** | Entity conflict/review and opted-in high risk stop before target work; ownership/readiness gates and ledger ordering/no-replay recovery remain the only target execution authority. |
| Evaluation v3 coverage and metrics | **PASS for synthetic scope** | `synthetic-adverse-v3`: entity 17/17, TP 5/FP 0/TN 12/FN 0, precision/recall/F1 1.0, FPR/FNR 0; UBO 3/3; risk 5/5. Reported limitations correctly prohibit production-performance claims. |
| Canonical 21-rule/13-intelligence policy and activity contracts | **PASS** | Authority registry/checker and docs agree on catalogue membership, schema v1-v5, v5 projection, and CSV semantics. |
| Architecture decision and anti-duplication constraints | **PASS** | Accepted ADR-003/D-047 establish one advisory owner; no second scoring/persistence/authorization/ledger owner or compatibility fallback is added. |
| Security/privacy and provider truth | **PASS for implemented scope** | Bounded projections omit raw provider payloads, identity values, names, addresses, document bodies, credentials, private notes, and target responses. GoldTier remains Mock; no Live claim or secret/config change exists. |
| Documentation/governance synchronization | **PASS** | Architecture, project state, contracts, decision/open-question records, model cards, research limitations, demo, and provider reconciliation consistently distinguish implemented local/mock behavior from blocked provider/sponsor lanes. |
| Combined user request and publication protocol | **FAIL** | Goals A/B and the Q-016-dependent portion of F are incomplete; exact `PASS` is therefore unavailable and publication is prohibited. |

## 5. Contract and Integration Findings

The current source/tests, accepted ADR-003/D-047, canonical contracts, project state,
and configuration agree on the implemented boundary:

- ACRA remains Mock by default; generic sandbox-shaped ACRA is Partial and BizFile is
  Dormant.
- IDP is Local deterministic extraction with Mock demo/fault behavior; it is not vendor
  OCR.
- ownership remains the single local deterministic Decimal graph engine.
- GoldTier remains Mock only; PingFed/live target integration is not active.
- Mongo remains an explicit optional mode; memory remains the default; there is no
  silent fallback.
- advisory intelligence is case-bound, versioned, explainable, non-legal and
  non-compliance; readiness effects remain deterministic and explicitly opted in.

The named XPI materials have no authoritative substitute in the repository. The
project's older GoldTier baseline and discrepancy records remain provisional supporting
evidence, not authority to infer XPI request shapes. Q-004, Q-016, Q-017, and the
GoldTier contract questions remain open; configurable local defaults close none of
them. No contradictory example was promoted into a DTO, enum, fixture, or assertion.

## 6. Tester and Adversarial Findings

### Independent commands and results

| Command / probe | Result |
|---|---|
| `python -B -m pytest -p no:cacheprovider tests/test_onboarding_intelligence.py tests/test_intelligence_evaluation.py tests/test_activity_export.py tests/test_phase12_persistence.py tests/test_zero_touch_orchestration.py -q` from `apps/backend` | **PASS — 120 tests**. |
| direct entity/persistence/service adversarial probe | **PASS** — two missing-country unequal-ID directions; four reuse/replacement/corrupt-retained checks; five raw schema-v5 corruption classes. |
| `python -B scripts/evaluate_onboarding_intelligence.py` | **PASS** — v3 entity 17/17, UBO 3/3, risk 5/5 with the metrics in the acceptance matrix. |
| exhaustive Unicode CSV formula probe | **PASS** — 3,860,460 whitespace/category-C-prefix combinations plus direct markers; safe strings unchanged. |
| `python -B -m pytest -p no:cacheprovider -q` from `apps/backend` | **PASS — 1,236 passed, 29 expected physical/infrastructure skips; 1,265 collected**. Three expected Pydantic serializer warnings came from deliberately malformed provider fixtures. |
| `python -B -m ruff check --no-cache app tests` from `apps/backend` | **PASS**. |
| `python -B -m mypy --no-incremental app` from `apps/backend` | **PASS — 101 source files**. |
| `npm.cmd test -- --cache=false` from `apps/frontend` | **PASS — 21 files, 276 tests**. Existing SSR `useLayoutEffect` and React `act` warnings do not indicate a candidate failure. |
| app and node `tsc --noEmit` checks | **PASS**. |
| Vite production build to a task-owned temporary output directory | **PASS — 113 modules**; temporary output removed. |
| `python -B -m unittest discover -s tests/contract -p 'test_*.py'` | **PASS — 44 tests**. |
| scoped governance unittest modules | **PASS — 185 tests**. The text `E2E SUITE FAILED: isolated selection 1/2 failed.` is expected output from an adverse unit fixture; unittest exited 0 with `OK`. |
| direct `check_architecture`, `check_project_state`, `check_tooling_config`, `check_policy_authority`, `check_external_provider_readiness`, and `check_secrets` scripts | **PASS**. |
| `python -B -m ruff check --no-cache scripts tests` | **PASS**. |
| `git diff --check` | **PASS**; only Windows LF-to-CRLF advisory warnings. |
| strict UTF-8/NUL/conflict-marker/final-LF/trailing-whitespace scan across all 36 task-owned untracked files | **PASS with expected Markdown hard breaks** — no invalid UTF-8, NUL, conflict marker, or missing final LF; 11 trailing-space occurrences are deliberate two-space Markdown line breaks in four reports/docs. |

### Unavailable or inherited evidence

- Docker client `29.8.0` was present, but the Docker Desktop Linux daemon endpoint was
  unavailable. A new disposable physical Mongo database/container therefore could not
  be created and no physical suite was run by this reviewer. The implementation report
  supplies supporting evidence of a final guarded disposable-container pass (8 suites,
  29 tests, including raw/BSON and restart corruption rejection); it is not represented
  as an independent rerun.
- The final reviewer did not rerun the shared-port Windows lifecycle or Playwright
  suites. The implementation evidence reports 23 lifecycle tests and 14/14 Playwright
  tests passing after the final remediation. Fresh frontend unit/type/build evidence
  passed here, but the inherited browser/lifecycle evidence is identified as such.
- XPI DNS, TLS 1.3, authentication, HTTP, search, and optional writes were not attempted
  because the authoritative artefacts/configuration were absent. This is not converted
  into an integration pass.
- `pre_pr_check.py`, publication CI, commit, push, and PR creation were not run: this
  candidate has a final `FAIL`, and publication is authorized only after exact `PASS`.

The first sandbox attempt at the governance unit batch was invalid because Windows temp
directories inherited restrictive sandbox ACLs. Only the exact task-created temp
directories were removed. The same read-only batch was rerun outside the sandbox and
passed 185/185; the invalid infrastructure attempt is not counted as candidate evidence.

## 7. Code and Architecture Review

The implemented design is cohesive and preserves the repository's owners:

- strict provider/case evidence flows into one immutable onboarding-intelligence
  projection;
- entity evidence derives its outcome and selected candidate from bounded facts rather
  than trusting persisted labels;
- UBO advice consumes the authoritative Decimal ownership output instead of recomputing
  ownership;
- mock risk has a closed limitation vocabulary and no default blocking authority;
- schema-v5 aggregate validation executes at model, encode, decode, retained-read,
  fingerprint-reuse, and replacement boundaries;
- case deletion removes the projection with the owning aggregate and does not allow
  stale resurrection;
- existing readiness, workflow, and target-ledger owners retain call ordering, stopping,
  and no-replay authority;
- frontend additions consume backend-authorized projections and do not become a second
  authorization or policy owner.

The canonical contract now contains exactly 21 policy rules and 13 intelligence rules.
The activity profile covers schemas v1-v5 and the bounded authorized CSV behavior.
Accepted ADR-003 and D-047 establish the durable architecture decision; the earlier
planning ADR is explicitly superseded. No current maintainability or architecture
defect was found in the implemented slice.

## 8. Security Review

No new implemented-scope security defect was found.

Verified controls include backend-authoritative case/team access; indistinguishable
404s; user/session/case-scoped cache keys; cancellation/removal on deletion and
session/identity/401 transitions; immutable/case-bound policy metadata; fail-closed
schema-v5 persistence; bounded activity projection; fixed-size CSV; Unicode-wide
spreadsheet formula neutralization; no-store/no-sniff/download headers; sanitized
activity/model evidence; and no new provider secret, credential, raw KYC payload,
document body, private note, or target response in normal projection/logging surfaces.

The absence of XPI access and Q-016 authority is correctly contained. Activating a
provider or inventing assignment/SLA rules would create security and authorization risk;
the candidate does neither.

## 9. Required Fixes and Blockers

### Current implemented-code fixes

None identified in the exact frozen candidate. All findings from the prior two gates
are independently closed.

### Dependent blockers required for combined acceptance

1. Supply and reconcile the exact GoldTier XPI PDF/Postman contract and approved
   non-secret sandbox configuration; then implement and independently verify the
   requested XPI transform/preview/search and only explicitly authorized guarded writes.
2. Resolve Q-016 with sponsor-approved capability/RBAC, team/target-user, assignment,
   note, due/SLA, CAS, audit, routing, escalation, and notification semantics; then plan,
   implement, and independently gate that mutation slice.
3. Re-run physical Mongo and relevant browser/lifecycle/provider evidence on the final
   post-blocker candidate. Do not substitute historical or mock evidence for an
   unavailable external smoke test.

These blockers must not be worked around with guessed DTOs, fallback mapping, a second
policy/authorization owner, frontend-only controls, or undocumented project defaults.

## 10. Readiness and Publication Decision

- Implemented local/mock intelligence slice: **technically verified, but not separately
  publishable under the original combined request**.
- Live ACRA: **not verified and not claimed**.
- Real GoldTier/XPI integration: **not ready and not verified**.
- Assignment/note/SLA mutations: **not authorized and not implemented**.
- Combined Pre-Phase 22 acceptance: **FAIL**.
- Publication: **NOT AUTHORIZED**. Do not commit, push, create a PR, or invoke the
  publisher on this gate result.
- Phase 22: **DO NOT START**. A separate human-authorized planner is still required even
  after a future exact `PASS` and human merge.

## 11. Git Status and Reviewer Mutation Statement

Before creating this report, the candidate contained 47 tracked modifications, 36
untracked files, and 0 staged paths. The current review adds exactly one untracked file:
`.ai-pipeline/reports/PRE_PHASE22_CAPABILITY_EXPANSION_FINAL_REQUALITY_GATE.md`.

This reviewer made no implementation, contract, plan, historical-report, configuration,
test, Git-index, branch, commit, remote, PR, provider, database, or Phase 22 mutation.
No file was staged, committed, pushed, merged, or published. The only durable change is
this assigned report.

## Appendix A — Reviewed Candidate Manifest (report excluded)

```text
.ai-pipeline/reports/GOLDTIER_XPI_SANDBOX_DIAGNOSIS.md
.ai-pipeline/reports/ONBOARDING_INTELLIGENCE_SYNTHETIC_EVALUATION.md
.ai-pipeline/reports/PRE_PHASE22_CAPABILITY_EXPANSION_IMPLEMENTATION.md
.ai-pipeline/reports/PRE_PHASE22_CAPABILITY_EXPANSION_QUALITY_GATE.md
.ai-pipeline/reports/PRE_PHASE22_CAPABILITY_EXPANSION_REQUALITY_GATE.md
apps/backend/app/api_intelligence.py
apps/backend/app/composition.py
apps/backend/app/demo/zero_touch_control.py
apps/backend/app/domain/case_management.py
apps/backend/app/domain/onboarding_intelligence.py
apps/backend/app/domain/policy.py
apps/backend/app/domain/zero_touch.py
apps/backend/app/main.py
apps/backend/app/persistence/composition.py
apps/backend/app/persistence/models.py
apps/backend/app/persistence/mongo_case_store.py
apps/backend/app/persistence/repositories.py
apps/backend/app/services/activity_export.py
apps/backend/app/services/authorization.py
apps/backend/app/services/case_deletion.py
apps/backend/app/services/intelligence_evaluation.py
apps/backend/app/services/onboarding_intelligence.py
apps/backend/app/services/onboarding_intelligence_repository.py
apps/backend/app/services/policy_management.py
apps/backend/app/services/zero_touch_orchestration.py
apps/backend/tests/test_activity_export.py
apps/backend/tests/test_intelligence_evaluation.py
apps/backend/tests/test_onboarding_intelligence.py
apps/backend/tests/test_phase12_persistence.py
apps/backend/tests/test_phase12_real_mongo.py
apps/backend/tests/test_phase13_auth_rbac.py
apps/backend/tests/test_phase13_priority.py
apps/backend/tests/test_phase13_real_mongo.py
apps/backend/tests/test_phase14_5_policy.py
apps/backend/tests/test_phase14_5_real_mongo.py
apps/backend/tests/test_phase14_case_management_performance.py
apps/backend/tests/test_phase17_case_activity.py
apps/backend/tests/test_zero_touch_orchestration.py
apps/frontend/src/App.tsx
apps/frontend/src/AttentionQueue.test.tsx
apps/frontend/src/EvidenceWorkbenchIsolation.test.tsx
apps/frontend/src/Phase15CNavigation.test.tsx
apps/frontend/src/Phase17CaseActivity.test.tsx
apps/frontend/src/PrePhase22Intelligence.test.tsx
apps/frontend/src/api.ts
apps/frontend/src/caseQueries.ts
apps/frontend/src/pages/AuditTrail.tsx
apps/frontend/src/pages/CaseDetail.tsx
apps/frontend/src/pages/IntelligencePanel.tsx
apps/frontend/src/types.ts
docs/ARCHITECTURE.md
docs/PROJECT_STATE.md
docs/aegis/INDEX.md
docs/aegis/adr/ADR-0001-onboarding-intelligence-advisory-boundary.md
docs/aegis/plans/2026-09-23-pre-phase22-capability-expansion.md
docs/aegis/work/2026-09-23-pre-phase22-capability-expansion/10-intent.md
docs/aegis/work/2026-09-23-pre-phase22-capability-expansion/20-checkpoint.md
docs/aegis/work/2026-09-23-pre-phase22-capability-expansion/90-evidence.md
docs/aegis/work/2026-09-23-pre-phase22-capability-expansion/99-reflection.md
docs/aegis/work/2026-09-23-pre-phase22-capability-expansion/baseline-read-set-hint.json
docs/aegis/work/2026-09-23-pre-phase22-capability-expansion/baseline-usage-draft.json
docs/aegis/work/2026-09-23-pre-phase22-capability-expansion/drift-check-draft.json
docs/aegis/work/2026-09-23-pre-phase22-capability-expansion/impact-statement-draft.json
docs/aegis/work/2026-09-23-pre-phase22-capability-expansion/task-intent-draft.json
docs/aegis/work/2026-09-23-pre-phase22-capability-expansion/todo-checkpoint-draft.json
docs/contracts/CASE_ACTIVITY_QUERY_PROFILE.md
docs/contracts/OWNERSHIP_UBO_PROFILE.md
docs/contracts/PERSISTENCE_RECOVERY_PROFILE.md
docs/contracts/POLICY_AUTHORITY_MATRIX.md
docs/contracts/POLICY_TEAM_IDENTITY_ADMIN_PROFILE.md
docs/decisions/ADR-003_ONBOARDING_INTELLIGENCE.md
docs/decisions/DECISION_LOG.md
docs/demo/PRE_PHASE22_INTELLIGENCE_DEMO.md
docs/integration/GOLDTIER_XPI_SANDBOX_RECONCILIATION.md
docs/models/ENTITY_RESOLUTION_MODEL_CARD.md
docs/models/MOCK_ADVISORY_RISK_MODEL_CARD.md
docs/models/UBO_ADVISORY_MODEL_CARD.md
docs/research/INDUSTRY_STANDARD_USAGE.md
docs/sponsor-questions/OPEN_QUESTIONS.md
scripts/check_policy_authority.py
scripts/dev_context.py
scripts/evaluate_onboarding_intelligence.py
tests/test_check_policy_authority.py
```
