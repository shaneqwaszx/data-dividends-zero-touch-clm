# Phase 24B Part A fresh independent mini quality gate

## Executive Result

**FAIL.** The original contradiction and final-action defects are repaired in the executed bounds. Same-UEN reacquisition repairs ordinary and uninterrupted legacy cases, but a remaining **P2** leaves an obsolete legacy registry ownership blocker active after an interrupted composed write, even after a fresh authenticated retry. The explicit owner rule requires STOP for any remaining P0-P2. No Phase 24B continuation, remediation, publication or next phase is authorized by this report.

Reviewed content ID: `705139993fc21db5bde7f6fadb56454f9574250dfa64431b82d58d4b6cd31682`. Exact eight-path set and SHA256 values: `PHASE_24B_MINI_MANIFEST.json`; manifest SHA256 `4de754feb2121f6c7fcd36d9df0beac27b6c5fa51c86870efb6f38a116fd054b`. Branch `feat/phase24-registry-identity-ownership-ubo`; BASE_SHA, HEAD and inspected origin/main `039101b69772c4c9ae4ca7b4a7ca3e4c19b03f4c`. Entry and final hashes and compact sorted-JSON identity matched. The remaining prior-manifest paths also match their recorded hashes. This is a fresh independent reviewer; no implementation or ordinary-document writes occurred.

The gate follows the assigned Phase 24B plan and fyp-quality-gate skill/template. Root/backend/frontend AGENTS, workflow/context selection, preceding three P2 findings, exact mini paths, relevant owner/current tests, ownership/zero-touch contracts and evidence authority were inspected. Verdict scope is Part A's three repairs, not acceptance of the full Phase 24 or Phase 24B candidate.

## Phase Acceptance Checklist

| Criterion | Result | Independent evidence |
|---|---|---|
| Graph60% versus authoritative compatible units1/denominator100 fails closed | PASS | Service and authenticated normal upload probes reach REVIEW_REQUIRED with CONTRADICTORY_OWNERSHIP_EVIDENCE; retained 60 graph/all scalars; every candidate INDETERMINATE/REVIEW_REQUIRED; only read-only search, no confirmation/dispatch. |
| Missing, multiple and incompatible denominators and unknown units are not hidden by graph | PASS | Four additional stdin variants retain graph/scalars, emit OWNERSHIP_DENOMINATOR_REQUIRED and indeterminate candidates. Compatible60/100 control remains ANALYZED. |
| Same-UEN reacquisition retires obsolete blocker and recomputes current ownership | FAIL in recovery boundary | Uninterrupted metadata0 and legacyNone variants cancel old blocker, rebuild generation1 ANALYZED with history and reach explicit TARGET_CONFIRMATION_REQUIRED. Interrupted legacy case remains blocked after resume and generation2 retry; F1. |
| Current independent ownership blocker preserved | PASS in exercised bounds | Independently run focused regression retains independent provider blocker with unknown registry binding, REVIEW_REQUIRED ownership and search-only calls. No blanket clearing observed. |
| Ready zero-issue state names final user action; completed action truthful | PASS at component level | Independent in-memory transpile/render of actual TSX prints Review and confirm submission for READINESS/TARGET_CONFIRMATION_REQUIRED; COMPLETED prints Submitted — no action required. and retains unresolved human-approval aria text. |
| Covered behavior unchanged | PASS in executed suites | Full backend 1627 passed; full frontend402 passed; contracts44 passed; static checks below. These suites do not cover F1. |

## Contract and Integration Findings

No new precedence was invented. Compatible scalar/graph disagreement is diagnosed before final candidate classification, and the graph is retained. Arithmetic stays in the existing Decimal owner. Missing evidence remains a review result, never legal UBO or approval. No connector, mapping, provider classification, external authentication or business-threshold change is introduced by the mini delta. Existing sponsor questions and production/legal/Ready-for-Approval dependencies remain unresolved.

F1 is a current implementation defect, not sponsor authority or missing infrastructure. Physical Mongo, real browser/process proof, external provider interoperability and final production readiness are outside this mini execution; later Part J must supply its own evidence.

## Tester and Adversarial Findings

All shell commands explicitly used the assigned worktree. Python executable was reused from the Desktop checkout solely as runtime; PYTHONPATH selected the worktree backend, plus its tests for stdin probes. Python used `-B`; pytest disabled its cache. No .env, retained database or external provider was accessed.

| Independently executed command/lane | Result |
|---|---|
| `python -B -m pytest apps/backend/tests/test_phase24b_p2_regressions.py apps/backend/tests/test_phase24_identity.py apps/backend/tests/test_phase24_ownership_evidence.py -o addopts= -q -p no:cacheprovider --tb=short` | 92 passed, one existing Starlette warning, 9.72s. |
| Same pytest options on `apps/backend/tests` | 1627 passed, 43 guarded physical skips, four warnings, 143.83s. Skips are not physical PASS. |
| `npm --prefix apps/frontend test -- --run src/pages/CaseStatePanels.test.tsx` | 24 passed, one file. |
| `npm --prefix apps/frontend test -- --run` | 402 passed, 34 files, 6.11s; existing act/server-layout-effect warnings. |
| `npm --prefix apps/frontend run typecheck` | PASS. |
| `python -B -m ruff check` on five mini backend source/test paths, `--no-cache` | PASS. |
| `python -B -m mypy apps/backend/app --config-file apps/backend/pyproject.toml --no-incremental --cache-dir <external task cache>` | PASS, 115 source files. |
| `python -B -m unittest discover -s tests/contract -p test_*.py` | 44 passed. |
| `python -B scripts/check_secrets.py` | Supported-pattern scan PASS; not universal proof of all secret formats. |
| `git diff --check`; explicit whitespace scan of new mini planner Markdown | PASS. Assigned report separately checked after write. |
| No-write Python stdin and Node stdin probes | Original scalar counterexample, five controls/adverse variants, authenticated normal-route contradiction, ordinary/legacy reacquisition, two interrupted-checkpoint variants, direct current-evidence control and actual TSX rendering executed. |

Initial sandbox frontend runs failed on Vite parent-directory access and ignored TypeScript build-info writes. Exact test/typecheck retry with platform escalation succeeded; no approval rejection was bypassed. An initial mypy invocation from root without the backend configuration and with NUL cache failed internally; configured retry with an external task cache passed. No dependency install occurred. Ignored existing test/typecheck cache artifacts are not reviewed source changes.

No browser, build-output, physical Mongo, lifecycle/startup, external smoke or publication pre-PR check was run for this mini gate. Earlier phase reports cannot supply a current mini PASS for those lanes.

## Code and Architecture Review

### F1 — P2: interrupted same-UEN rebind strands legacy ownership blocker across retry

Owners: `apps/backend/app/services/zero_touch_orchestration.py:1455`, `:1492-1503`, `:1523-1542`, `:1589`; currentness filter `apps/backend/app/services/ownership_analysis.py:966-971`; resume/advance stopping at `zero_touch_orchestration.py:672-679` and `:2042-2043`.

The legacy fallback requires `prior_ownership = self._ownership.get(...)` to return the exact old registry analysis. Registry verification advances the parent generation before blocker cancellation is saved. If a later CLM/reconciliation/automation checkpoint fails, the old automation blocker remains OPEN but the currentness-filtered ownership getter returns None. A subsequent same-UEN retry therefore cannot bind and cancel a legacy blocker whose optional registry_evidence_generation is None. The newly added numeric generation binding avoids that retry loss, but existing records legitimately omit it.

Independent authenticated synthetic reproduction:

1. Use the normal create/documents routes with RegistryAcquisitionOwnershipProvider and a local registry temporarily returning empty ownership. Generation0 reaches WAITING_FOR_REVIEW/OWNERSHIP_REQUIRED; analysis generation0 is REVIEW_REQUIRED. Preserve the exact blocker ID; model the supported legacy record with its optional registry_evidence_generation=None.
2. Restore valid registry evidence. Inject one typed ReconciliationInfrastructureError from the existing reconcile_current checkpoint during the normal ENTERED same-UEN registry-identity route. The route propagates ZeroTouchInfrastructureError/RECONCILIATION_UNAVAILABLE in TestClient. Restore the checkpoint immediately. No data/implementation file is written by injection.
3. Parent generation is now1, current ownership getter is None, and the exact old blocker remains OPEN. Explicit POST /resume returns200 and remains OWNERSHIP_REQUIRED with no current ownership.
4. A fresh same-UEN correction using current automation/CLM/case versions returns200 and advances parent generation2, but remains WAITING_FOR_REVIEW/OWNERSHIP with the same old OPEN blocker and current ownership None. Calls are exactly search,search,search; no target write/confirmation occurs.
5. As a separate control within the synthetic process, direct existing ownership load/analyze against current generation2 succeeds ANALYZED with two edges and two candidates. The current evidence can satisfy ownership; the composed path is stranded by obsolete evidence.

| Record variant | After checkpoint failure | Explicit resume | Fresh correction retry |
|---|---|---|---|
| New metadata0 | generation1; old OPEN blocker; ownershipNone | 200; same stale blocker | generation2; old CANCELLED; current ANALYZED; TARGET_CONFIRMATION_REQUIRED |
| Supported legacyNone | generation1; old OPEN blocker; ownershipNone | 200; same stale blocker | generation2; old OPEN; ownershipNone; still OWNERSHIP_REQUIRED |

A separate typed CLM checkpoint-request failure independently produced the same generation/filter/legacy-retry result. The authored legacy regression covers only an uninterrupted first correction and misses this boundary. Failure preservation during the first request is safe; inability to repair on a later authorized exact retry is the defect. Retiring stale registry dependencies must remain distinguishable from current independent blockers. No fix was attempted.

The mini repairs reuse existing ownership/orchestration/presentation owners, with no new service, dependency or stage. Internal domain/API issue vocabulary changes by adding CONTRADICTORY_OWNERSHIP_EVIDENCE. Optional exception registry_evidence_generation changes durable record content; schema version remains7 and no migration is added. Existing API response fields, connectors, configuration, mapping, threshold policy, RBAC/reauthorization, architecture ownership and provider status remain unchanged in the mini delta. Runtime review/blocker behavior and UI next-action text change.

## Security Review

No new credential, provider transport, sensitive route authority or target-ledger bypass was found in the mini delta. Registry correction still runs reauthorization under the owning case lock; focused identity and broader auth/call-stopping coverage pass. All extra probes used synthetic local evidence and safe state/generation summaries. No confidential artifact, private payload or raw document content was persisted into this report. F1 stops progression; it does not prove unauthorized dispatch or false successful submission.

## Required Fixes

F1 remains a required P2 fix before this mini gate can pass. A future separately authorized remediation must provide a durable way to identify and retire the stale legacy registry dependency after an interrupted rebind, retain independent blockers, and prove resume/retry recomputes current ownership without target replay. This report does not authorize that remediation.

## Readiness

**Part A mini acceptance: FAIL. Phase 24B continuation: STOP.** No full Phase24/24B acceptance, Part B/Part J start, PR readiness, ACRA Live readiness or real GoldTier integration readiness is established. The coordinator must hand back this failure and await explicit owner direction. No repair or next phase may follow automatically.

## Git Status

The assigned worktree and branch were preserved. HEAD/base/origin/main remain the recorded039101b. The existing candidate remains dirty; index is empty. Before report there were70 status paths; the sole reviewer-owned addition is this report, making71. Eight frozen mini path hashes match; non-mini paths from the64-entry prior manifest also match. Earlier reports/manifests were not edited. The report itself is excluded from the reviewed implementation identity.

Reviewer writes: only `.ai-pipeline/reports/PHASE_24B_MINI_QUALITY_GATE.md` in the worktree, plus configurable ignored/external tooling caches. No implementation/test/configuration/ordinary-document fix, Git mutation, commit, push, PR, merge, worktree creation or next phase occurred.
