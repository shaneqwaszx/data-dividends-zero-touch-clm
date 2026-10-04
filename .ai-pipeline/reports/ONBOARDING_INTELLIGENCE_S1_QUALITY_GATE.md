# Onboarding intelligence — Session 1 independent quality gate, remediation round 1

## Current executive result

**PASS — the sole initial P2 is resolved.** Every Session 1 criterion is verified for
the frozen 60-path candidate below. The corrected readiness contract distinguishes
retained extraction/provenance/human decisions from refreshable current canonical
comparisons. No remaining P0, P1, P2 or P3 finding was identified.

Review date: 2026-10-04. Reviewer: independent `s1_independent_gate` agent.
This is a fresh review of the bounded documentation remediation. The initial FAIL,
finding and original execution record are retained verbatim in the historical review
below; those describe the superseded candidate, not the current verdict.

## Current reviewed and tested identity

| Item | Observation |
|---|---|
| Worktree | C:/Users/shane/.codex-clean2/worktrees/onboarding-intelligence-goldtier-sandbox/data-dividends-zero-touch-clm |
| Branch | feat/onboarding-intelligence-goldtier-sandbox |
| BASE_SHA / HEAD / inspected local origin/main | 1d426e0ceddc32d80b0aaec293c62fb761f2fecf |
| Frozen manifest | .ai-pipeline/reports/ONBOARDING_INTELLIGENCE_S1_MANIFEST.json |
| Manifest raw SHA256 | a45c8f84978c55be2785ed9578c4dbd4f60863b83a7431c7e883a1cfb6d947c9 |
| Complete current 60-path candidate SHA256 | acc325730273d83d1bb39bbc066a89584b21dad7eebd2f8baee0afe73aed6bff |
| Current implementation receipt raw SHA256 | f86e8c7f6d73d44f56fbf7d63b0969c29c1e9edc95e20aa63ced7b405756f4fc |
| Corrected CLM_READINESS_POLICY.md raw SHA256 | f56ad5e49bd37a2943ec0afc15d9f1682ae515348e1ac91b01c7840efaafc1e3 |
| Original reviewed 59-path candidate | a39c00cd8e707c83e037dc5f54a7032573bb0a5214ccc53f7a8935c663d0266e |
| Initial report before this append/prepend | Raw SHA256 0a32c1d67b730da79e465e7999182e38f638ba59fb3a2a12d218cc02f36f0408 |

Aggregate algorithm: SHA256 of UTF-8
`json.dumps(manifest["files"], sort_keys=True, separators=(",", ":"))`.
Records are sorted by repository-relative path and hold raw-byte per-file SHA256.
The manifest itself and this assigned gate output are excluded. All 60 raw hashes,
the exact changed-path set and the aggregate matched at review entry and final freeze
verification. The inspected manifest's explicit algorithm matches independent
recomputation.

The original 58 candidate paths other than the implementation receipt are unchanged;
this includes every product source and test file. Their aggregate is
`2eb879768564e3615d4b55b2bc7d671f795a934e6170d2b449c5c1d6a1b31cdc`.
Removing the added readiness-contract path and substituting the original receipt hash
`1822f986fd9cf5d59d201b70d932292e5fb4f1fd721ff0d3949237d61db52090`
reproduces the exact initial `a39c00…` candidate. This binds the prior complete code
review and executed behavioral evidence to the current product bytes. Fresh round-1
execution covers the revised documentation, security/governance and hygiene; runtime
suites are retained initial evidence and were not rerun for this documentation delta.

## Current Session 1 acceptance checklist

| Requirement | Result | Direct evidence |
|---|---|---|
| S1.1 wrong-UEN recovery | PASS | Retained-intake guard accepts ACRA_ENTITY_NOT_FOUND; document_processing.py:93–135 refreshes current comparisons, preserving original extraction/provenance/review decisions; existing correction/reconciliation/orchestration resumes. New backend happy/adverse tests and actual onboarding-recovery browser journey preserve document ID and reach the next real blocker. The amended owning contract at CLM_READINESS_POLICY.md:21 now matches this behavior. |
| S1.2 empty login | PASS | LoginPage has empty state and removes Maya placeholder; S1FormsSession and actual blank-login browser checks. Backend synthetic identities remain. |
| S1.3 blank/reset onboarding | PASS | App initializes UEN empty and clears identity, country, files, priority/team/scenario and retained draft state. Component and browser reset/role-change checks. |
| S1.4 Company Legal Name | PASS | HomeOnboarding creation label changed; canonical backend field names retained; component/browser selectors exercise the visible label. |
| S1.5 team selection | PASS | Director's actual required selector is inside the details card; fixed-team value is separated and labelled. Backend scope remains authoritative. Component and three-width browser checks. |
| S1.6 creation dates | PASS | Both endpoints convert inclusive Singapore UTC+08:00 dates to half-open UTC bounds over automation.created_at. Actor/team scope precedes query predicates; portfolio predicates precede sorting/paging. API/domain/adverse tests, 72 physical memory/Mongo comparisons, query-key/cancellation tests and both browser endpoints. |
| S1.7 processing overlay | PASS | OnboardingWorkspace scopes inert/aria-busy/live status to workspace content, preserving navigation; current exceptions, review, failure, recovery and completion remove it. Component focus tests and actual inert/keyboard browser checks. |
| S1.8 document wording | PASS | DocumentEvidencePanel distinguishes loading, failed query, no upload, uploaded, processing, review, processed and verified matching evidence; source reviews/reconciliation remain separate. Component states and failed-query browser path. |
| S1.9 pipeline names | PASS | Backend projects exactly the requested 12 top-level names, ending Final review & send; retained operation identifiers/history remain. Advisory qualification visible; no second HUMAN_APPROVAL node. Projection, historical/optional-Amend tests and browser label inventory. |
| S1.10 stage inspection | PASS | Every stage is a button or native disclosure with factual details; completed/skipped/not-reached stages use View details, genuine review/blocked stages use supported labels/actions. Source facts/children retain outcome, status, provider/environment, timestamps, blockers and target operation/no-call evidence where known. Actual browser opens all 12 stage regions. |
| S1.11 session reset | PASS | AuthProvider clears incompatible queries/transport, waits for root navigation before interactive identity acceptance, and remounts session draft state. Restore keeps valid same-session deep links. Component stale-request/401/same-user tests and HR→Director, Director→HR and ordinary-page browser swaps. Normal role landing follows root. |
| S1.12 ACRA diagnostics | PASS | Admin view labels Connector capabilities and unsupported operations as no provider call. Case view separately presents retained registry identity completeness and genuine blockers. No unsupported capital/relationship endpoint or missing-data rule invented. Frontend tests/source review. |
| S1.13 GoldTier configuration diagnosis | PASS | Frozen sanitized implementation receipt reports only the five allowlisted presence booleans, explicit sandbox selection false, writes false and zero calls. Reviewer did not reread private configuration. Console explains effective configuration and suppresses unconfigured Search; configured diagnostic/read-only behavior remains covered. |

All thirteen criteria pass. Sessions 2/3 remain later scope, as in the original review.
No additional OCR, ownership-intelligence, Sandbox or external-provider capability is
claimed by this Session 1 verdict.

## Remediation findings and authority

**Initial P2 closed:** `docs/contracts/CLM_READINESS_POLICY.md:21` now states that
original extraction, provider provenance and human decisions remain retained evidence;
accepted identity correction refreshes current canonical comparison values/statuses
from retained observations, with no provider replay or document replacement.
The rule keeps its PROJECT-DEFINED / PROVISIONAL classification and references
D-066/ADR-007 rather than asserting sponsor confirmation.

This matches `refresh_current_comparisons` at
`apps/backend/app/services/document_processing.py:93–135`, particularly the retained
evidence/currentness guard and assignments at 123–124, and the owner-authorized
D-066/ADR-007 recovery. The owning contract's agreement prerequisite and unresolved
policy boundaries remain accurate. The repair introduces no source precedence,
comparison authority, replacement behavior or external-integration claim.

The receipt truthfully records the initial FAIL, bounded row correction, unchanged
product evidence and round-1 checks. The revised manifest adds exactly the contract
path and documents the already-used hash algorithm. No further correction is required.
Current findings: P0 0; P1 0; P2 0; P3 0.

## Fresh tester, security and hygiene evidence

| Fresh round-1 independent execution/review | Result |
|---|---|
| `python -B -m unittest tests.test_check_architecture tests.test_check_project_state tests.test_check_policy_authority tests.test_check_secrets -q` | 59 passed in 31.852s; zero skips |
| `check_secrets.py` | PASS |
| `check_project_state.py` | PASS |
| `check_architecture.py` | PASS |
| `check_policy_authority.py` | PASS |
| Raw hashes, exact path set, current and reconstructed original aggregates | PASS |
| Complete contract diff, revised receipt and manifest; current source/authority comparison | PASS |
| Tracked/staged whitespace and explicit all 60 task-owned text files | PASS |
| Final gate-output whitespace and secret scan | PASS |

The interpreter was the read-only normal-repository pinned .venv, with `-B` and
bytecode disabled, and the worktree cwd. Approved managed-worktree escalation allowed
governance temporary fixtures. No auto-review rejection occurred. No .env, private
artifact, external request, Mongo/database access or browser launch occurred in this
remediation review.

The initial fresh 147 backend tests, 455 Vitest tests/39 files, both TypeScript checks,
Ruff, strict mypy/118 files, 44 contract tests, 78 governance/runner tests, guarded
real-HTTP browser pack/9 tests and changed physical date test/72 comparisons remain
valid evidence for unchanged product/test bytes, with their original scope and
limitations recorded below. Broad implementation receipts remain attributed rather
than converted to reviewer execution.

## Code, architecture and change classification

Round 1 changes the owning contract, sanitized receipt and manifest only. API/types,
durable schema/persistence, connectors, configuration, business rules/target mappings,
auth/security, architecture, provider classifications and runtime behavior have no
additional change. The cumulative Session 1 classifications and architecture/security
assessment remain as recorded in the initial review, with its sole documentation
exception now corrected. No implementation fix was made by the reviewer.

## Required fixes and readiness

**Required fixes: none. Session 2: READY.** The initial Session 1 documentation blocker
is resolved and this exact frozen candidate has independent PASS. The owner's existing
instruction to continue after PASS controls the coordinator's next action; this gate
does not independently grant publication or broaden the next session.

**External-provider readiness: not established.** Live ACRA verification and real
GoldTier/PingFed/Sandbox interoperability were not executed. Credentials or sanitized
presence booleans do not prove external access, sponsor approval or write readiness.
Those dependencies and Session 2/3 criteria remain separate from this local Session 1
acceptance.

## Current Git status and reviewer boundary

Branch, HEAD, BASE_SHA and inspected local origin/main remain as above. There are
48 tracked modifications and 14 untracked task files including the manifest and this
report; the index is empty. The current cumulative diff and new files are covered by
the initial complete review plus this independently inspected bounded delta.

The reviewer wrote only this assigned gate report, preserving the initial record.
No implementation/test/configuration/other-document change, commit, push, PR, merge,
branch/worktree mutation or next-session execution occurred. All owned initial
execution processes were cleaned; the round-1 governance process completed normally.
The final candidate/raw-manifest hashes and complete path set remain unchanged.

---

# Historical initial review — initial candidate a39c00…, verdict FAIL

The following original report is retained verbatim as historical evidence. Its FAIL,
P2 and Session 2 NOT READY applied before the contract remediation above.

# Onboarding intelligence — Session 1 independent quality gate

## Executive result

**FAIL — one P2 durable-contract correction remains.** Session 1 behavioral acceptance
passed the independent checks below. The owning readiness contract still promises
immutable captured canonical comparison values, although the authorized recovery now
refreshes those values. Session 2 must wait for that bounded correction and a fresh
independent PASS. No runtime recovery, security, provider, or target-ledger defect was found.

Review date: 2026-10-04. Reviewer: fresh independent `s1_independent_gate` agent.
Review-only; no subagents or implementation fixes. The only durable reviewer write
is this assigned report.

## Reviewed and tested identity

| Item | Observation |
|---|---|
| Worktree | C:/Users/shane/.codex-clean2/worktrees/onboarding-intelligence-goldtier-sandbox/data-dividends-zero-touch-clm |
| Branch | feat/onboarding-intelligence-goldtier-sandbox |
| BASE_SHA / HEAD / inspected local origin/main | 1d426e0ceddc32d80b0aaec293c62fb761f2fecf |
| Frozen manifest | .ai-pipeline/reports/ONBOARDING_INTELLIGENCE_S1_MANIFEST.json |
| Manifest raw SHA256 | c2d47d0d35db97826929348fc2a823fb71b0d5e29d210a4aff04350e13a5fd33 |
| Complete 59-path candidate SHA256 | a39c00cd8e707c83e037dc5f54a7032573bb0a5214ccc53f7a8935c663d0266e |
| Aggregate algorithm | SHA256 of UTF-8 `json.dumps(manifest["files"], sort_keys=True, separators=(",", ":"))`; records ordered by repository-relative path and containing raw-byte SHA256 values |
| Unchanged contract implicated by the finding | docs/contracts/CLM_READINESS_POLICY.md; raw SHA256 ed64116ad4973108ef8ceee498c8a3c34548bff258c6cd4cc8bac75de54c4ef2 |

All 59 file hashes and the exact changed-path set matched before and after execution.
The manifest itself and this report are outside the aggregate. The entire cumulative
diff and every task-owned new file were inspected. Unchanged authority sources remain
bound to the inspected baseline, including the readiness contract above. Fresh checks
exercise this frozen candidate, not merely HEAD's baseline tree.

Authority: explicit owner program's Session 1, Session 1 gate, global product intent,
safety and documentation requirements; repository AGENTS; current planner; current
workflow and emitted Tier 1 context; fyp-quality-gate/template and applicable cache,
persistence/security guidance; relevant document, reconciliation, portfolio, readiness
and persistence contracts; D-062/D-066 and ADR-007; nearest accepted A–G gate, used
only as baseline provenance. Sessions 2/3 were not treated as Session 1 criteria.
The reviewer accessed no private dotenv, raw sponsor artefact or credential.

Current-session capability: normal-repository pinned Python runtime used read-only
with -B/no bytecode; worktree locked frontend dependencies; actual guarded Playwright
HTTP/process run; explicit task-owned local Mongo service for the changed physical
test. Managed-worktree escalation was needed for esbuild and temporary-fixture access.
No external provider request was made.

## Session 1 acceptance checklist

| Requirement | Result | Direct evidence |
|---|---|---|
| S1.1 wrong-UEN recovery | Behavior PASS; documentation FAIL | Retained-intake guard accepts ACRA_ENTITY_NOT_FOUND; document_processing.py:93–135 refreshes current comparisons, preserving original extraction/provenance/review decisions; existing correction/reconciliation/orchestration resumes. New backend happy/adverse tests and actual onboarding-recovery browser journey preserve document ID and reach the next real blocker. P2 below concerns the owning contract's description. |
| S1.2 empty login | PASS | LoginPage has empty state and removes Maya placeholder; S1FormsSession and actual blank-login browser checks. Backend synthetic identities remain. |
| S1.3 blank/reset onboarding | PASS | App initializes UEN empty and clears identity, country, files, priority/team/scenario and retained draft state. Component and browser reset/role-change checks. |
| S1.4 Company Legal Name | PASS | HomeOnboarding creation label changed; canonical backend field names retained; component/browser selectors exercise the visible label. |
| S1.5 team selection | PASS | Director's actual required selector is inside the details card; fixed-team value is separated and labelled. Backend scope remains authoritative. Component and three-width browser checks. |
| S1.6 creation dates | PASS | Both endpoints convert inclusive Singapore UTC+08:00 dates to half-open UTC bounds over automation.created_at. Actor/team scope precedes query predicates; portfolio predicates precede sorting/paging. API/domain/adverse tests, 72 physical memory/Mongo comparisons, query-key/cancellation tests and both browser endpoints. |
| S1.7 processing overlay | PASS | OnboardingWorkspace scopes inert/aria-busy/live status to workspace content, preserving navigation; current exceptions, review, failure, recovery and completion remove it. Component focus tests and actual inert/keyboard browser checks. |
| S1.8 document wording | PASS | DocumentEvidencePanel distinguishes loading, failed query, no upload, uploaded, processing, review, processed and verified matching evidence; source reviews/reconciliation remain separate. Component states and failed-query browser path. |
| S1.9 pipeline names | PASS | Backend projects exactly the requested 12 top-level names, ending Final review & send; retained operation identifiers/history remain. Advisory qualification visible; no second HUMAN_APPROVAL node. Projection, historical/optional-Amend tests and browser label inventory. |
| S1.10 stage inspection | PASS | Every stage is a button or native disclosure with factual details; completed/skipped/not-reached stages use View details, genuine review/blocked stages use supported labels/actions. Source facts/children retain outcome, status, provider/environment, timestamps, blockers and target operation/no-call evidence where known. Actual browser opens all 12 stage regions. |
| S1.11 session reset | PASS | AuthProvider clears incompatible queries/transport, waits for root navigation before interactive identity acceptance, and remounts session draft state. Restore keeps valid same-session deep links. Component stale-request/401/same-user tests and HR→Director, Director→HR and ordinary-page browser swaps. Normal role landing follows root. |
| S1.12 ACRA diagnostics | PASS | Admin view labels Connector capabilities and unsupported operations as no provider call. Case view separately presents retained registry identity completeness and genuine blockers. No unsupported capital/relationship endpoint or missing-data rule invented. Frontend tests/source review. |
| S1.13 GoldTier configuration diagnosis | PASS | Frozen sanitized implementation receipt reports only the five allowlisted presence booleans, explicit sandbox selection false, writes false and zero calls. Reviewer did not reread private configuration. Console explains effective configuration and suppresses unconfigured Search; configured diagnostic/read-only behavior remains covered. |

The root's baseline browser/API diagnosis identified never-durable upload as the cause,
rather than document deletion. That reproduction is implementation evidence, not a
reviewer reproduction of the now-repaired baseline. Current recovery was independently
executed. Low-confidence/source-conflict and entered/document/other identity recovery
retain genuine independent blockers and do not bypass confirmation or target no-replay.

## Required finding

**P2 — reconcile the owning readiness contract with refreshed comparison snapshots.**

- Location: `docs/contracts/CLM_READINESS_POLICY.md:21`, Document agreement row.
- Current wording promises that the canonical value captured during Phase 03 remains
  immutable historical evidence.
- Current authorized implementation at
  `apps/backend/app/services/document_processing.py:123–124` assigns current
  `canonical_value` and `comparison_status` after accepted identity correction.
  D-066 and ADR-007 describe this refresh, but the owning contract row still presents
  the obsolete preservation rule as current.
- Consequence: the durable contract incorrectly tells a future reader that the prior
  comparison snapshot is retained unchanged. This conflicts with the changed source
  and the task's requirement for current affected authoritative documentation.
- Correction: update only the owning contract statement, or explicitly amend it,
  distinguishing immutable original extraction/provenance and retained human decisions
  from refreshable current canonical/comparison values under D-066/ADR-007. Keep current
  agreement/readiness rules, no source-precedence invention, replacement semantics and
  no provider/extraction replay. Do not change the passing recovery implementation.
- Verification: inspect the repaired row against refresh_current_comparisons, rerun
  affected documentation/governance/whitespace checks, freeze the revised complete
  path/hash manifest and obtain a fresh independent review.

P0: 0. P1: 0. P2: 1. No other required correction found. This is a current
documentation blocker, not a sponsor-authority blocker or reproduced runtime defect.

## Independent execution and adversarial evidence

| Fresh independent check | Result |
|---|---|
| Backend focused S1 projection/date, Phase24 identity, Slice-C recovery and zero-touch suites | 131 collected/executed, all passed; one existing FastAPI/httpx deprecation warning |
| Changed Garden projection/history suite | 16 passed |
| Full Vitest, `node node_modules/vitest/vitest.mjs run --no-cache` | 455 passed / 39 files; existing React act/server-layout warnings |
| Both TypeScript configs, `--noEmit --incremental false` | Both exit 0 |
| Configured backend Ruff from apps/backend; changed runner Ruff from root; --no-cache | Both PASS |
| Strict mypy app, --no-incremental --cache-dir=nul | PASS, 118 source files |
| Contract unittest discovery | 44 passed |
| Architecture/state/policy/secret checker tests plus physical-runner tests | 78 passed (59 governance/security + 19 runner tests) |
| check_secrets / check_project_state / check_architecture / check_policy_authority | All PASS |
| Guarded local real-HTTP Playwright S1 + Phase24 identity pack | 9 passed in 23.3s; retries 0; owned processes cleaned; network violations 0 |
| Changed physical date-filter test | 1 passed / 72 memory-Mongo comparisons; generated allowlisted database cleaned by safety helper; zero skips |
| git diff --check / staged whitespace / explicit all task-owned text whitespace | PASS; new/untracked text checked explicitly |

Commands use the read-only normal .venv interpreter and worktree cwd/PYTHONPATH.
Browser launcher selected `S1 |Phase24.*identity|Phase24 entered UEN` on reserved
18765/14173, redirecting Playwright output to the OS temporary directory; unchanged
guarded launcher/composition/network policy remained active. Browser tests cover
320/720/1280, workspace/navigation containment, blank/reset forms, date endpoints,
all stage regions, failed document query and role swaps. No comprehensive accessibility
or production-host certification is claimed.

Adverse coverage includes reversed/malformed/unrepresentable dates, exact microsecond
boundaries and leap day, backend team-filter denial, filtering before pagination,
date-key isolation and late-response cancellation, low confidence/source conflict,
completed identity freeze, stale/cross-case decisions, safe target failure/recovery,
uncertain operation no-replay and historical confirmation truth.

Resolved reviewer invocation issues: anchored `^S1 ` selected no tests and was corrected
without source edits; root-cwd explicit backend Ruff configuration changed first-party
import discovery, so canonical cwd/configured commands were rerun and passed; restricted
esbuild access was resolved by approved escalation. An initial broad governance run
remained silent under restricted fixture permissions and was terminated using its exact
verified command/process tree. The approved unchanged rerun completed 78/78. These
attempts are not represented as passing executions. No automatic approval rejection
occurred.

## Attributed implementation evidence, not reviewer reruns

The frozen S1 implementation receipt records full backend 2041 PASS with 90 explicit
physical skips, separate physical 90 PASS / 14 suites / zero skips, full frontend
455/39, type/build, Ruff, strict mypy, 44 contracts, 59 governance and 19 runner tests.
The full backend imported the prior recovery status string; the receipt explicitly
attributes final wording to the later 52-test focused execution. Current projection
wording is additionally covered by this review's focused execution. The reviewer did
not repeat the full backend, complete physical inventory or production build; these
remain attributed implementation receipts. The prior main A–G gate does not certify
this candidate.

## Architecture, contract and security assessment

Existing document/reconciliation/orchestration, case query/portfolio, auth/query,
Decimal ownership and target-ledger owners remain. No direct route-to-Mongo access,
second engine/state owner, schema bump, write/CAS change, resurrection path, dormant
provider composition, target bypass/replay, TLS weakening or external mutation was added.
Source-neutral evidence boundaries and safe browser/error fields remain.

Raw bytes/text stay transient; retained extraction/provenance/review decisions survive.
Date filters are project-defined and optional. Session transition clears incompatible
data and drafts before publishing the new identity; backend capabilities/team scope
remain authoritative. Secret scanning includes non-ignored untracked files; its
pattern coverage is not proof against every possible secret. No private configuration
value or protected artefact was printed or newly tracked.

| Change dimension | Reviewed delta |
|---|---|
| API/type | Optional creation-date inputs and pipeline projection changed |
| Schema/persistence | Read predicates changed; durable schema/index/write/CAS unchanged |
| Connector/provider | No connector activation or provider-status change |
| Configuration | No private/default configuration change |
| Business rule/mapping | Project-defined date semantics and local final-approval presentation; target mappings unchanged |
| Auth/security | Session routes/drafts/query lifecycle changed; backend authority preserved |
| Architecture | Existing owners extended |
| Runtime/frontend/tooling/docs | Intake/recomparison and UX changed; physical suite registered; docs updated except P2 row |

## Readiness and Git status

**Session 2: NOT READY until the single P2 correction receives fresh independent PASS.**
OCR/intelligence/ownership enhancements are later authorized work, not missing Session 1
features. Review & Send is final local submission approval; provider-internal/regulatory
approval remains separate. Real ACRA/GoldTier readiness is not established by this gate.
No external smoke or Sandbox lifecycle was executed; sanitized configuration presence
does not prove external interoperability or write readiness.

Before this report: 47 tracked modifications, 13 untracked task files including the
manifest, empty index; branch/HEAD/origin-main unchanged. This report adds one untracked
report. Frozen implementation hashes/pathset remain unchanged. No commit, push, PR,
merge, branch/worktree mutation or next session was performed by the reviewer.
No clm_poc access occurred. Next authorized action: bounded contract-documentation
remediation, refreshed manifest, independent recheck; then Session 2 only after PASS.
