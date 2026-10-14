# AM-18 checkpoint independent Quality Gate — initial candidate

Independent reviewer: `/root/am18_independent_gate`, 15 October 2026, Asia/Singapore.
This reviewer had no implementation/remediation involvement and performed no Git mutation.

## Executive Result

**FAIL — AM18-QG-01 (P2) is a required correction. Publication is blocked.**
The retained incomplete-ownership branch now reaches a CLM prerequisite whose typed
CAS and infrastructure failures are not translated through the existing trusted API
error boundary. Both independently reproduce HTTP 500 without typed error metadata.
Evidence retention, readiness blocking, no target mutation and deliberate fresh recovery
remain safe in these probes; this finding is an error-contract failure, not unsafe Send
or proof of original-incident attribution.

The coordinator explicitly released the narrow causal probes and requested this failed
checkpoint before continuing expensive verification. Required broader and independent
runtime lanes remain pending below. No missing lane is called passing. This initial
candidate does not have independent acceptance; corrective budget is still A0/1 at
report issuance. A separately assigned implementation run may use the one authorized
narrow correction and must obtain a fresh independent re-gate on its new frozen bytes.

## Reviewed Identity and Authority

Worktree: `C:/Users/shane/.codex-clean2/worktrees/am18-checkpoint-20261015-0235/data-dividends-zero-touch-clm`.
Branch: `fix/am18-ownership-checkpoint-20261015`.
HEAD, BASE_SHA, merge base and inspected local origin/main:
`7a2804c32e17a19ab886253c6025a60c52b5167d`; baseline tree
`67a00479283c31b658482890b4ca2ae544630ffd`.
Reviewed content: HEAD plus the complete five-path uncommitted delta, including the
untracked test. Manifest: `tmp/extended-am-release/am18-frozen-candidate.json`.
Raw aggregate: `ef703260e3de084ee7b2c9c9dfbcf86ecbd91b5c2643cc9844bb70a8a864a3d7`.
Aggregate algorithm: SHA256 of UTF-8 compact sorted-key JSON of the path-sorted full
records array. Every raw hash and the aggregate were independently verified before
execution; all five raw hashes still matched after both causal probes. This report is
excluded from its own manifest. No index/stored/commit identity is predicted or certified.

| Complete reviewed path | Raw SHA256 |
|---|---|
| apps/backend/app/main.py | 10939017f35cfe090de7d29a614b4590c54b3a5f2a744144f2f961cfd7bd8f5b |
| apps/backend/app/services/zero_touch_orchestration.py | 193550af80e24bfffb1f7bd309be964b25a004d9aee78b1c9e6bde112eb945cc |
| apps/backend/tests/test_am18_ownership_checkpoint.py | 927975f8276603288b9a47181660b5bd83adb6c1563defe2fd08e1bd7a923b74 |
| apps/backend/tests/test_final_review_editing_real_mongo.py | b3b7ad1701a6e577524c9b90d8d06075ab1a449240a0f1228aa9830c518f8365 |
| apps/frontend/e2e/s2-ownership.e2e.ts | 78ef77c04fd6baad35e42a30b38b1785d59c918eaa5372b238f56b72c1f4fcd0 |

Authority read: exact owner assignment attachment; full root/backend/frontend AGENTS;
repository skill routing; fyp-quality-gate and template; persistence-schema-change,
integration-security-review/checklist and poc-regression-check/catalogue; selected
BACKEND_DOMAIN + BACKEND_API + PERSISTENCE + AUTH_RBAC_SECURITY dev-context Tier 1;
current architecture/state/workflow/branch protocol/pipeline; ownership, persistence
and automation contracts; D-062/D-067/D-072 and ADR-009; current owning services,
API/error projection and owning security tests; complete candidate diff/new file;
forensic final v3 appendix; nearest AM03 post-PR85 accepted gate for context only.
Historical PR85/86 tests supply no fresh acceptance. Original AM-18 attribution remains
UNCONFIRMED. Current-main behavior and current contracts outrank dated metadata.

## Acceptance Checklist

| Assigned criterion | Initial-candidate assessment |
|---|---|
| A: complete multi-level percentage edit, identity and Decimal result | Coordinator final 11-test focus PASS inspected; independent normal-path replay pending |
| B: retained incomplete graph/receipt, true issue, safe409, ownership stage/action, no Send | Normal regression authored and coordinator focus PASS; independent faults retain graph/readiness/no dispatch; typed failure contract FAIL |
| C: fresh complete recovery and new confirmation | FRESH independent causal probes recover200 with no readiness blocker and zero target mutation; full confirmation replay pending |
| D: independent document conflict remains | Source preserves unrelated exceptions and earliest open stage; coordinator focused test PASS; independent mixed-blocker probe pending |
| E: classification currentness/retention | Existing binder/CLM owner unchanged; focused and browser assertions inspected; independent runtime pending |
| F: stale duplicates/versions, no blind retry | Three stale-version regressions inspected; coordinator focus PASS; independent adverse suite pending |
| G: creator/team/locked reauthorization | Existing ownership and API reauthorization guards unchanged; owning tests inspected; independent security runtime pending |
| H: confirmed/submitted/frozen/uncertain target protection | Canonical invalidation rechecks retained target execution before replacement; complete runtime challenge pending |
| I: prior confirmation cannot replay/resurrect | Old confirmation retired/history preserved; fault probes have no confirmation/submission/target mutation; full browser pending |
| J: missing/replaced documents and source bindings | Existing provider checks preserved and focused regressions inspected; independent execution pending |
| K: one Decimal engine, >=25%, no invented child | No engine/rule change; synthetic child expressly declared; current-main other orchestrator AST identical |
| L: truthful attention/progress and ownership navigation | Existing backend exception owner reused; complete actual browser verification pending |
| M: physical restart/CAS retention and recovery | Guarded test inspected; final frozen physical execution and independent restart pending |
| N: zero Shell/Policy/Amend/Readback during edits | FRESH independent CAS and infrastructure probes retain Search-only call record; canonical confirmation/replay lanes pending |
| AM-16 date/default/retention/optional note | Bounded canonical S2 assertions inspected; final exact-content browser execution pending |
| Full required verification union | Pending; no release acceptance |

## Contract and Integration Findings

**AM18-QG-01 — P2: newly reached typed CLM failures escape the manual evidence API.**
Owner location: `apps/backend/app/services/zero_touch_orchestration.py:1507`, with
`apps/backend/app/main.py:2448` API invocation/error handling. After ownership and its
receipt are retained, direct `refresh_pre_submission_evidence` can raise ClmRequestError
or ClmInfrastructureError. This method translates ownership failures but not those CLM
failures. The route translates only ZeroTouchRequestError/ZeroTouchInfrastructureError.
The existing document-refresh helper at zero_touch_orchestration.py:942-955 shows the
established trusted translation pattern. The changed incomplete branch newly reaches
this prerequisite; the baseline returned its safe409 before it.

Independent actual CLM repository CAS injection produces ClmRequestError with existing
code CLM_ORCHESTRATION_CONFLICT, but the candidate emits generic HTTP500/no JSON detail.
The separate real ClmInfrastructureError type injected at the refresh port has the same
missing projection. Its fixture uses an existing safe code and synthetic trusted message;
it does not claim that a submission operation occurred. Required behavior is to preserve
the owning typed conflict/infrastructure outcome through existing safe409/503 adapters,
stop the failed prerequisite, retain already durable evidence and require explicit fresh
recovery. This is a current in-scope error-contract/CAS adverse-path failure.

No sponsor contract, target mapping, source precedence, provider or threshold authority
changed. Quarantined examples were not reused. GT-S03/S04/S05/S06/S11/S12 and broader
sponsor questions remain later dependencies; no real provider write or Live claim follows.

## Tester and Adversarial Evidence

FRESH independent execution, frozen candidate:

| Check | Exact outcome |
|---|---|
| Raw five-path SHA256 and compact records aggregate | PASS, ef703260...; raw hashes unchanged after probes |
| git diff --check and explicit all-five UTF-8 trailing-whitespace/EOF check | PASS; untracked test included, no terminal blank line |
| Exact main versus candidate orchestration AST excluding assigned method | PASS, every other executable owner statement identical |
| Canonical Ruff on clean exact Git-baseline OS-temp archive and candidate | Both exit1, exact15 diagnostic equivalence; see exception below |
| Changed/task Python Ruff | PASS, all four Python paths |
| Real CLM repository CAS rejection, baseline then candidate | Baseline409/safe code/0 CLM save attempts; candidate500/no typed metadata/1 save attempt |
| Typed CLM infrastructure rejection at refresh port, baseline then candidate | Baseline409/safe code/0 refresh attempts; candidate500/no typed metadata/1 refresh attempt |
| Deliberate fresh complete recovery after each fault | PASS, all four recoveries200, readiness blockers empty, Search-only target calls |

Commands used the existing read-only primary venv Python with `-B`, current worktree
apps/backend/tests plus apps/backend and root first on child PYTHONPATH, ordinary-test
conftest safety and runtime-only synthetic authentication. The printed owner.__file__
matched this new worktree. No .env, browser, Mongo, external HTTP or shared port was used
by these probes. TestClient transport disabled server-exception propagation only to
observe the actual production HTTP response; no application exception handling changed.

Baseline method was independently reconstructed from exact `git show 7a2804c:...`,
compiled in memory and temporarily bound only in the probe process. Baseline owner raw
SHA256: `f439f91a4b9c02f1089a9536ff9cb152a6cf71de456ac5a99c5e2c3b68f58c38`.
Baseline method AST SHA256: `ef171c74255d6452b4793a42be29134cddfa010acf69c651062e043f8fde515c`.
Candidate method AST SHA256: `19394dc7e52f5189507c0e5ef9a9a4cf4ff2df12035f6de1525f28ec72989027`.
For both fault kinds and both trees, graph/receipt remained REVIEW_REQUIRED; automation
retained its previous durable checkpoint; current CLM readiness blocked Send; target
calls remained exactly [search]; fresh correction recovered200. The candidate's generic
500 did not disclose the injected message, authorize dispatch or falsely succeed.

Coordinator evidence independently inspected, not reviewer-executed:
final focused 11 PASS/10.16s on frozen bytes (am18-final-focus-after-safe-error.log);
configured strict mypy127 PASS (am18-final-mypy.log); six final scanners and final Ruff
receipts. Baseline RED log fails READINESS != OWNERSHIP after retained409/graph/receipt/
CLM/no-dispatch assertions. Earlier owning317, browser1 and physical1 outcomes precede
the final API catch and remain earlier implementation evidence, not final broad proof.
Full backend log was still executing at98% at report preparation and has no accepted
terminal summary. Final full physical, frontend/build/type/governance test union,
full canonical disjoint pair, independent normal/adverse suite, independent actual S2
browser and independent physical restart are PENDING / NOT_EXECUTED at this checkpoint.
Authoring assertions and the dynamic discovery receipt do not prove execution.

One independent Ruff verifier setup attempt expected a nonexistent root pyproject.toml
and stopped before checks. Corrected only that temporary verifier; candidate/config
unchanged. Its owned temporary snapshots cleaned automatically. Known installed
Starlette TestClient deprecation warning remained visible; no dependency install,
warning suppression, timeout inflation, retry, selector or assertion weakening occurred.
Independent evidence is retained in this chat's tool receipts; the coordinator may index
those receipts without treating its register as independent acceptance.

## Narrow Owner-Accepted Ruff Exception

**FAILED — 15 VERIFIED UNCHANGED BASELINE DIAGNOSTICS; OWNER-ACCEPTED EXCEPTION.**
Explicit human amendment applies only to AM-18. Independent canonical command on both:
`python -B -m ruff check apps/backend scripts tests`, Ruff0.16.2, identical current config.
Backend pyproject raw SHA256:
`054e2bb3ba666f369d81bf09f1dfaea1c1edcc2adac9e2684c1ebd78b3016f27`.
Complete root output was emitted for both independently executed commands. JSON diagnostic
comparison additionally proves exact file/rule/row/column/message equivalence, not counts
alone. No config/exclusion/noqa edits, introduced/worsened diagnostic or exception for
B/future work. Changed/task Python passes. This exception does not excuse QG-01 or any
other unexecuted/failed runtime, security, persistence, browser or hosted-CI lane.

| File | Rule | Row:column | Exact message |
|---|---|---|---|
| scripts/benchmark_blocker_review.py | RUF100 | 14:18 | Unused `noqa` directive (non-enabled: `E402`) |
| scripts/benchmark_blocker_review.py | RUF100 | 15:54 | Unused `noqa` directive (non-enabled: `E402`) |
| scripts/benchmark_blocker_review.py | RUF100 | 16:62 | Unused `noqa` directive (non-enabled: `E402`) |
| scripts/generate_zero_touch_happy_path_documents.py | RUF100 | 12:55 | Unused `noqa` directive (non-enabled: `E402`) |
| scripts/performance_concurrency.py | RUF059 | 45:54 | Unpacked variable `bundle` is never used |
| scripts/performance_load.py | FURB157 | 302:29 | Verbose expression in `Decimal` constructor |
| scripts/performance_load.py | FURB157 | 303:29 | Verbose expression in `Decimal` constructor |
| scripts/performance_load.py | FURB157 | 306:83 | Verbose expression in `Decimal` constructor |
| scripts/performance_optimization.py | BLE001 | 132:16 | Do not catch blind exception: `Exception` |
| scripts/performance_optimization.py | RUF059 | 308:48 | Unpacked variable `bundle` is never used |
| scripts/performance_optimization.py | I001 | 417:9 | Import block is un-sorted or un-formatted |
| scripts/performance_optimization.py | FURB157 | 446:65 | Verbose expression in `Decimal` constructor |
| scripts/sponsor_demo_browser_fixture.py | I001 | 3:1 | Import block is un-sorted or un-formatted |
| scripts/sponsor_demo_browser_fixture.py | I001 | 101:21 | Import block is un-sorted or un-formatted |
| scripts/zero_touch_classification_browser_fixture.py | I001 | 3:1 | Import block is un-sorted or un-formatted |

## Code, Architecture and Security Review

The production delta uses existing orchestration, CLM, ownership, exception and repository
owners; the API addition delegates the existing safe503 adapter. No new owner/dependency,
schema, provider, mapping, business rule, permission or cache responsibility appears.
The normal retained409 reconciliation is causally appropriate and keeps one Decimal
engine. History, old confirmation retirement, current ownership evidence binding,
case/creator/version checks and target freeze guards remain. Independent unrelated
exceptions continue to select the earliest open stage. Complete runtime verification
of those static conclusions remains pending.

QG-01 violates stable safe error projection. No sensitive value, raw provider/document
body or private exception text appeared in the inspected delta or observed responses.
No .env/protected database/sponsor credential was accessed. Generic500 stays fail closed;
this limits severity but does not satisfy the assigned trusted error contract.
Inherited architecture/project-state metadata is dated and belongs to Workstream C's
read-only audit; it was not changed or promoted into current runtime evidence.

## Required Fixes

1. Correct AM18-QG-01 within the existing manual-orchestration owner: translate both
   typed CLM request/CAS and infrastructure failures to the existing zero-touch safe
   outcomes, preserving prerequisite call stopping, retained graph/receipt and no retry.
2. Add meaningful failure-first owning regressions for both typed failures and explicit
   fresh recovery/no-target mutation; do not weaken the established409 contract.
3. Freeze revised full content and rerun all affected mandatory evidence, then fresh
   independent re-gate. Pending browser/physical/broad lanes cannot be deferred into PASS.

These are remediation guidance only. This reviewer implemented nothing. No unrelated
repair, third release or second corrective cycle is authorized.

## Readiness and Git Status

AM-18 publication: BLOCKED by FAIL and pending mandatory evidence. Original incident
attribution: UNCONFIRMED. Real ACRA/GoldTier readiness: NOT_VALIDATED by this review;
no new interoperability/Live claim. Workstream B: MUST NOT START until A safely publishes
under its exact independent PASS and owner-authorized release procedure. This report
certifies no B design/implementation or future phase. Pre-PR/commit/stored identity,
remote CI and human merge remain separate gates; hosted zero-step jobs are NOT_EXECUTED.

At report preparation four tracked candidate files were modified, the complete owning
test was untracked, no candidate path was staged, and HEAD/main remained7a2804c. The
reviewer's only durable modification is this assigned report. No implementation fix,
source/test/config/ordinary-document change, commit, push, PR, merge, container/process
cleanup or next phase was performed. Owned Mongo container remains coordinator-owned.

Actual change classification: API shape/type UNCHANGED, API infrastructure status/error
projection CHANGED (existing safe503 adapter); schema/connector/config/business rule/
mapping/permission/architecture ownership/provider status UNCHANGED; safe-error security
surface CHANGED; persisted automation checkpoint reconciliation CHANGED; frontend
production source UNCHANGED, resulting backend-authored attention/progress behavior
CHANGED; supporting tests CHANGED. The finding concerns the typed CLM failure path.

## Initial-Candidate Evidence Addendum — Before Remediation

The coordinator subsequently completed the original frozen candidate's full backend
command: **2709 passed, 152 skipped, 4 warnings in1000.83s**, terminal log
`tmp/extended-am-release/am18-full-backend.log`. This is fresh coordinator execution on
aggregateef703260..., independently inspected at this checkpoint. The152skips are not
passing physical evidence; the guarded physical lane remains NOT_EXECUTED. This updates
the earlier in-progress observation without changing the failed verdict or its cause.

After explicit narrow runtime release, the reviewer independently executed the complete
owning AM-18 test file (11passing cases, exit0), plus separate authenticated API probes:
repeated incomplete retention with new current exception/history; stale duplicate leaves
graph unchanged; fresh complete recovery; combined incomplete ownership and independent
document conflict selects DOCUMENT and preserves both blockers; valid correction retires
only ownership while document conflict remains; hostile boolean/nonfinite percentages
return safe422 without writes; same-team noncreator403 and cross-team404 without writes;
completed/confirmed submission rejects a fresh ownership edit409 and performs no target
replay. All these probes PASS; no additional required finding was identified.

One larger verifier attempt stopped at a setup expectation that the Mock helper began
with a classification blocker. Safe observations establish that this helper already
starts with usable classifications and final confirmation. This was a fixture assumption,
not a product failure. The successful preceding probes were rerun separately to produce
complete PASS receipts. Independent unresolved-classification, uncertain-target, actual
browser and physical restart lanes remain pending for the revised freeze. No broad
suite/inventory/tolerance/timeout/assertion was changed, and no browser/Mongo was used.

**Initial-candidate verdict remains FAIL, AM18-QG-01; no source fix was implemented by
the reviewer.** Source/test hashes still match the five-path initial freeze. The failed
report section and this addendum are preserved for the separately assigned one-cycle
remediation and append-only independent re-gate record.

# R1 Re-Gate — Current Effective Result

Independent reviewer: `/root/am18_independent_gate`; fresh R1 review, 15 October 2026,
Asia/Singapore, completed after final resource-absence verification at 07:51 SGT.

## R1 Executive Result

**PASS. Current required findings: P0=0, P1=0, P2=0, P3=0.**
The sole corrective cycle resolves AM18-QG-01, and every assigned AM-18 acceptance
criterion and mandatory local verification lane is now verified on the revised frozen
content. No required implementation fix or unverified required local criterion remains.
This is the effective verdict for R1 only. The initial FAIL above remains immutable
history for its different five-path aggregate and is not relabelled passing.

The result is conditional local publication readiness under the owner's existing
release procedure. It does not certify staged/stored/committed identities, a clean
committed pre-PR gate, remote CI, original-incident attribution, Workstream B or a merge.
A1/1 is consumed; B0/1 remains separate. No second corrective cycle was used or granted.

## R1 Frozen Content and Review Independence

Worktree and branch remain as recorded above. HEAD/BASE_SHA/merge base and inspected
origin/main remain `7a2804c32e17a19ab886253c6025a60c52b5167d`, tree
`67a00479283c31b658482890b4ca2ae544630ffd`. The coordinator freshly fetched unchanged
main before final acceptance; this reviewer made no fetch or other Git mutation.

R1 manifest: `tmp/extended-am-release/am18-r1-frozen-candidate.json`.
R1 raw aggregate: `00601992e2dd7fc84ef387d5ce2a02415e78c685e423f2259b83fefc3932d754`.
Same deterministic records-array algorithm as the initial review. Current source is
HEAD plus the complete uncommitted five-path delta, not HEAD alone. All raw hashes and
the aggregate were independently checked before execution; all five raw hashes remained
unchanged through browser/physical execution and final resource verification.

| Complete R1 path | Raw-byte SHA256 |
|---|---|
| apps/backend/app/main.py | 10939017f35cfe090de7d29a614b4590c54b3a5f2a744144f2f961cfd7bd8f5b |
| apps/backend/app/services/zero_touch_orchestration.py | 9ac067410cb31b9f3cfa24dcfd888ec52218bf953eaa0bad7f96ff2dff516b25 |
| apps/backend/tests/test_am18_ownership_checkpoint.py | 2a21ca6fd3219d3a7547d1c4208074172b358a5e986a3a55d4823842115017db |
| apps/backend/tests/test_final_review_editing_real_mongo.py | b3b7ad1701a6e577524c9b90d8d06075ab1a449240a0f1228aa9830c518f8365 |
| apps/frontend/e2e/s2-ownership.e2e.ts | 78ef77c04fd6baad35e42a30b38b1785d59c918eaa5372b238f56b72c1f4fcd0 |

Only the orchestration method and the appended two-case regression changed from the
failed freeze. The original 11-test file prefix is byte-identical to its initial raw
manifest record. Every other executable statement in the orchestration module is
AST-identical to exact main. R1 owner-method AST SHA256:
`6a13585f7318819a35cc9f28995b41c5806cdd41d3272e29dd426518341c9e7a`.
The complete initial report plus addendum remains the byte prefix with SHA256
`fb4bb2e9ba21c345586d534ccc03b221006b2a57df200969d55a0f1f4ef0a47f`;
the ignored immutable copy AM18_INITIAL_QG_FAIL.md retains that same historical identity.
This R1 section is appended; the reviewer implemented/remediated no source or test.

## R1 Acceptance Checklist

| Owner requirement | Verified outcome and direct evidence |
|---|---|
| A: valid complete multi-level percentage edit | PASS: independent13focus, direct fresh correction and actual S2 browser; identity retained and the sole Decimal engine unchanged |
| B: retained incomplete legal owner, safe409, current blocker | PASS: independent exact-main/R1 comparison plus browser and physical test retain REVIEW_REQUIRED/INCOMPLETE_LEGAL_ENTITY/receipt, select OWNERSHIP, advertise OWNERSHIP_DETAILS and keep Send absent |
| C: fresh correction recovers Final Review | PASS: independent API, browser and restart correction return200/ANALYZED, clear ownership hold and create a new explicit final-confirmation dependency |
| D: independent document conflict remains | PASS: normal owning regression plus full backend and canonical blocker journeys; independent mixed-blocker probe established DOCUMENT remains earliest and valid ownership correction does not retire it; existing exception selection unchanged in R1 |
| E: classification currentness/retention | PASS: focused recovery assertions and real S2 browser compare retained selected classification across incomplete and complete edits; full canonical classification/conflict journeys pass |
| F: stale duplicate/version and no blind retry | PASS: independent13focus covers all3expected versions, duplicate and rejected checkpoint recovery; physical stale request rejects409 without changing graph; typed failures attempted once with no automation save/retry |
| G: creator/team/locked authority | PASS: unchanged locked creator reauthorization/source-owner trace; current full backend creator/security/access cases; independent denial probe established same-team403/cross-team404 without writes before R1's error-only correction |
| H: freeze/confirmed/submitted/uncertain states | PASS: current full backend and canonical retained-target/recovery lanes; actual S2 completes explicit Send then hides/disables editing; physical test has no target intent; canonical invalidation rechecks any retained execution before graph replacement |
| I: no old confirmation replay/resurrection | PASS: API/browser/physical all retain old exception history, clear dispatch confirmation, and require a different fresh final confirmation; repeated GET/restart/stale requests produce no target call |
| J: document and ownership bindings | PASS: independent13focus rejects missing/stale support before writes; existing provider equality/lineage guards preserved; full backend and physical persistence/security currentness evidence pass |
| K: multi-level Decimal and >=25% rule | PASS: complete synthetic graph retains exact60/40path results; current full ownership suite and canonical calculation journey pass; no threshold/engine/source rule change or inferred child |
| L: truthful backend attention/progress/actions | PASS: actual authenticated S2 browser proves1active blocker, no false no-blockers or Review-and-send action, correct ownership next action/focus at1440/1280/900/360 and reload consistency |
| M: physical persistence/restart/CAS | PASS: complete guarded24-suite/152-test lane plus independent retained409/restart/stale-writer/fresh-correction/second-restart test, with generated database absence proved |
| N: no target operations during ownership edits | PASS: independent normal/fault/API and physical probes retain Search-only calls and no target mutation; browser operation statuses remain NOT_ATTEMPTED until a separate explicit Send |
| AM-16 bounded regression | PASS: actual S2 browser checks Singapore current-day default, explicit historical2026-10-04retention after reload and blank optional note/null receipt on a complete explicit graph; PR85 is not reimplemented |
| Safe typed partial failures | PASS: QG-01 CAS409/infrastructure503, safe identifiers, exactly one failed prerequisite, zero automation writes/retries, retained graph/receipt/readiness block and deliberate fresh200recovery |
| Complete local required verification union | PASS: fresh exact-R1 broad logs and independent runtime below; root Ruff remains the explicit narrow owner-accepted failed baseline exception |

## R1 Independent Testing and Causal Review

Fresh reviewer execution on R1, not transferred from the failed tree:

| Independent command/probe | Result |
|---|---|
| `python -B -m pytest apps/backend/tests/test_am18_ownership_checkpoint.py -o addopts= -q --tb=short -p no:cacheprovider` | PASS13/11.71s, visible TestClient deprecation warning |
| Exact-main versus R1 normal retained409 method reconstruction | Main remains READINESS/old confirmation/no version advance; R1 selects OWNERSHIP/current OWNERSHIP_INCOMPLETE/advanced version/history; both retain true graph/receipt/readiness and recover200with zero mutations |
| Real CLM repository CAS rejection | R1safe409/CLM_ORCHESTRATION_CONFLICT,1failed prerequisite,0automation saves; retained review evidence, no target write, fresh200recovery |
| Real typed CLM infrastructure rejection at service port | R1safe503with case/automation IDs,1failed prerequisite,0automation saves; retained review evidence, no target write, fresh200recovery |
| Canonical real authenticated S2 browser, below | PASS1/10.1s, unchanged60s lifecycle guard, zero network-policy violations |
| Guarded physical AM18 restart test, below | PASS1/8.14s, zero skips; generated fixture database absence explicitly checked |
| Fresh clean exact-Git baseline and R1 canonical root Ruff | Same15file/rule/location/message diagnostics, normalized complete output identical; changed Python PASS |
| Raw source hashes/aggregate, full diff/new-file review and all-five whitespace/EOF | PASS before/after; `git diff --check` and explicit untracked-test check pass |
| Final command-log identity and canonical executed inventory | All22completed command logs' raw hashes verified; actual52+52ordered lifecycles match discovery,67+61passed records |
| Exact owned-container/ports/lifecycle absence | PASS after coordinator cleanup; all215receipt ports independently bind-free |

The real browser command used the existing primary venv read-only from this worktree:
`python -u -B scripts/run_e2e.py --backend-port 19102 --frontend-port 19502 --garden-protocol --grep "S2 creator edits calculable multi-level ownership before send and inspects exact collapsed calculations" --timeout-seconds 60`.
It executes the actual normal login/session/CSRF/local HTTP/browser path against strict
offline Garden protocol evidence, native document processing and current frontend source.
No assertion, selector/title/tag, network guard, timeout, retry or fixture policy changed.
It verifies complete edits, retained incomplete409, correct attention/progress/ownership
focus, reload, date/note retention, deliberate fresh recovery, fresh explicit Send and
post-submission frozen controls. No business mutation comes from view navigation/reload.

Independent physical execution selected
`apps/backend/tests/test_final_review_editing_real_mongo.py::test_physical_am18_retained_409_checkpoint_survives_restart_and_stale_writer`
with `-o addopts= -q --tb=short -p no:cacheprovider`. Child-only runtime connection targeted
the verified exact owned loopback27188container. The existing generated-database helper
was instrumented in the probe process only: exactly1new allowlisted fixture database,
ordinary owning fixture teardown, then explicit absence verified with the real driver.
The accepted graph/receipt/issue/current exception/automation version/CLM blocker survive
restart; stale resubmission does not write; fresh correction restores readiness and a new
confirmation; second restart retains it. Replacement target connectors record zero calls.
The visible anyio already-imported assertion-rewrite warning is a probe setup warning,
not a skip or disabled assertion. No URI/credential was printed or persisted.

Child PYTHONPATH was explicitly this worktree's apps/backend/tests, apps/backend and root;
owner.__file__ was asserted against the new worktree. Exact-main method reconstruction
used Git source in memory without modifying candidate bytes, with every other executable
owner statement independently shown identical. This proves the synthetic defect/correction;
it does not identify the cause of the owner's original AM-18 occurrence.

## R1 Completed Broad Evidence

Fresh coordinator-executed evidence on aggregate00601992..., independently read and
hash-validated by this reviewer. These are attributed current executions, not claimed
reviewer execution or borrowed PR85/86 history. Reproducible argv/cwd/safe environment
and raw log hashes are in `tmp/extended-am-release/am18-r1-broad-command-receipt.json`.

| Lane / actual log | Terminal result |
|---|---|
| am18-r1-full-backend.log | PASS2711,152guarded skips,4warnings,996.47s |
| am18-r1-full-physical.log | PASS24current suites/152collected/152passed,0failed/errors/skips |
| am18-r1-frontend-focus.log | PASS59/4files |
| am18-r1-frontend-full.log | PASS706/54files |
| am18-r1-typecheck.log / am18-r1-build.log | PASS;140modules, inherited619.42kBchunk warning |
| am18-r1-mypy.log | PASS127files, configured strict backend command |
| am18-r1-configured-backend-ruff.log / changed/task Python | PASS |
| am18-r1-contract-tests.log | PASS44 |
| am18-r1-delivery-assets.log | PASS4 |
| am18-r1-windows-lifecycle.log | PASS31/288.851s, owned19301/19701cleanup verified |
| am18-r1-governance-tests.log | PASS196/108.846s |
| Six am18-r1-check_*.log scanners/checkers | PASS architecture, project state, secrets, tooling, policy authority, external-provider readiness |
| am18-r1-canonical-shard1.log | PASS52lifecycles/67records,597.765s |
| am18-r1-canonical-shard2.log | PASS52lifecycles/61records,635.328s |

The152ordinary backend skips are supplied by the separate guarded physical152PASS lane;
no skipped physical check is represented as an ordinary-test pass. Real local OCR was
required by the backend command's CLM_REAL_OCR_REQUIRED=1 and child Tesseract PATH. The
additional source-owner/OCR assertion in the receipt is explicitly post-run; it is not
misrepresented as original in-run logging. Existing interpreter/source-binding flags,
ordinary-test dotenv isolation and physical safety owners were inspected. The actual
Windows lifecycle suite and canonical launcher use their normal owned-process cleanup.

Fresh discovery has128specs/128test records; the unchanged canonical selector owner
deduplicates configured same-line cases into104lifecycles. The actual ordered executed
selector set for each shard equals its52-element partition; disjoint union equals104;
all52per-shard success summaries and terminal SUITE PASS are present. Their passed
record sums are67and61, equal to128discovered records, with zero skips/failures. Retries0
and lifecycle60s remain unchanged. Both modified S2 test titles/tags/options equal exact
main; all other E2E production/inventory paths are unchanged.
Raw canonical log hashes:
shard1 `e16e90f1ff37358c06e7848fde3daab017f5c5978c749b37fca50e0523bb57ce`;
shard2 `05677aa21f0eac65d96e738752e64f152a0557fd3c2d767647c87165dad0b1ce`.
Coverage receipt: am18-r1-canonical-coverage.json, independently reconstructed from logs.

Failure evidence stays failed: initial product checkpoint RED; QG-01initial FAIL; the
R1two-case RED2failed/11deselected before correction; final-test exact-main replay
1failed/12deselected at READINESS != OWNERSHIP. Setup/authoring failures documented above
remain separate. All final broad evidence here uses revised frozen bytes. No deadline,
warning, inventory, assertion or test acceptance was weakened.

## R1 Ruff Exception, Architecture, Contract and Security Findings

The exact fifteen diagnostics and full owner amendment above remain authoritative and
unchanged. Independently re-executed canonical command on a fresh clean exact-main
OS-temp archive and R1: both exit1, exact same fifteen diagnostic tuples, zero introduced
or worsened. Backend config/tool unchanged; all changed Python passes. Complete canonical
output was emitted and root's complete failed output is retained in am18-r1-root-ruff.log.
Classification remains **FAILED — 15 VERIFIED UNCHANGED BASELINE DIAGNOSTICS;
OWNER-ACCEPTED EXCEPTION**, solely for AM-18. No blanket lint/CI exception or B transfer.
Temporary baseline snapshots were cleaned. This narrow debt is nonblocking only because
all other assigned current requirements now pass.

AM18-QG-01 is CLOSED for this R1 identity: existing ClmRequestError/ClmInfrastructureError
translate within the existing manual-ownership owner to existing zero-touch safe adapters.
No document_revision flag or event meaning was reused incorrectly. The failed prerequisite
is attempted once and stops before automation retention; durable graph/receipt may remain
under the established sequential checkpoint contract. Recovery is explicit and fresh,
not rollback, a cross-section transaction or blind retry. No remaining current finding.

The source DTO/canonical evidence/target mapping flow, single Decimal engine, existing
CLM/exception/access/repository/ledger owners, earliest independent open stage, creator/
team/version checks, target freeze, no replay, strict schema10/read compatibility and
insert/update/CAS/no-resurrection rules remain. No new owner/dependency/ADR, provider,
mapper, schema, business policy, threshold, source winner or permission grant is introduced.
No external target/provider write occurred in review. Browser/physical labels remain
Mock/Local or strict offline Sandbox-shaped fixtures, never Live/interoperability proof.
No .env/protected database/sponsor secret/private artefact was accessed; changed fixtures
and report contain synthetic/safe evidence. Full root-wide configured scanners and manual
changed-path inspection supply bounded hygiene evidence, not an unlimited secret audit.

Known visible warnings remain: installed Starlette TestClient deprecation, deliberately
malformed-provider serializer warnings, existing React test act warnings, probe import
rewrite warning, inherited frontend chunk size and Docker CLI deprecation. None was
suppressed or treated as a failed check. No runtime dependency/configuration changed.
The current dated architecture/project-state metadata debt remains Workstream C's
read-only audit; no tracked context rewrite or sponsor-question closure occurred.

## R1 Physical and Process Cleanup

The coordinator checked generated-database absence before stopping/removing only exact
CID `2368907fadedc5f89663247bf7137559d192edb709e0b92efbed08b285fffa9a`, whose label and
loopback27188binding this reviewer independently verified before physical use. Its safe
receipt is am18-r1-final-resource-cleanup.json; removal output is am18-r1-container-cleanup.log.
After removal, the reviewer independently queried container inventory for that exact ID
and observed absence, bound every one of215owned ports successfully, and verified
.runtime/demo-processes.json absent. The215include208canonical ports, the Windows pair,
initial focused pair, independent browser pair and Mongo port. Own physical fixture
absence was separately proved before container removal. No unrelated process/container/
database/worktree was targeted. Retained worktree and ignored safe evidence are intended;
keeping the pre-existing cached image does not retain a running task service.

## R1 Required Fixes, Readiness and Git Status

Required fixes: **NONE for the reviewed R1 implementation.**
AM-18 synthetic checkpoint defect: REMEDIATED — INDEPENDENT PASS on this raw identity.
Original AM-18 occurrence: attribution remains UNCONFIRMED; the exact original response/
issue is still unknown. No claim that all possible original causes are fixed.
Real ACRA/GoldTier/Sandbox-write/Live readiness is not established by this offline gate;
GT-S03/S04/S05/S06/S11/S12 and broader sponsor dependencies remain open. No new phase or
B implementation is certified or started by this reviewer. The coordinator may consider
B only after A safely publishes and the owner's independent baseline/non-overlap/resource
conditions are rechecked; B needs its own implementation, evidence and fresh gate.

Publication's next authorized action is latest-main/unchanged-content verification,
scoped staging and an exact staged/stored identity supplement including this report,
then the separately authorized commit/clean committed pre_pr_check.py/checklist/normal
push/one AM-18 PR/current-head review and honest push plus PR CI observation. A source
change requires fresh independent acceptance. Hosted zero-step/billing-refused jobs stay
NOT_EXECUTED; no hosted CI PASS, PR approval or merge is certified. Humans merge.

Final review worktree state remains four tracked modified candidate files, the complete
new owning test and this assigned report untracked; nothing staged and HEAD/main7a2804c.
The reviewer changed only this report, appending R1 while preserving the initial failed
prefix. No implementation/remediation, Git mutation, dependency install, unrelated
cleanup, commit, push, PR, merge or next phase occurred in this reviewer run.

Final change disclosure: request/response API types/shapes UNCHANGED; safe typed API
status/error projection CHANGED; schema/connector/configuration/business-rule/Decimal/
threshold/mapping/permission/architecture ownership/provider classification UNCHANGED;
security error-projection surface CHANGED without an authorization grant; persistence
checkpoint reconciliation and resulting backend-authored UI attention/progress CHANGED;
frontend production source UNCHANGED; supporting tests and independent report CHANGED.
This is bounded single-instance sequential recovery, not distributed atomicity,
exactly-once delivery, legal UBO, autonomous approval or original-incident closure.

## R1 Publication Identity Supplement — Actual Staged Content

**PASS maintained.** This is an identity supplement, not a source correction, new
implementation or transfer of acceptance to changed executable content.
The reviewer independently inspected the actual index after the coordinator staged
exactly the five accepted implementation/test paths plus this assigned report.
The existing pre-supplement tree object
`9f594885d0d6f01aa352ec9ce478517203a9b121` was read and compared against every index
mode/blob/path using read-only ls-files/ls-tree/cat-file/show operations; they match.
Native staged whitespace passes and there are no unexpected staged paths.

All five actual stored blobs equal the frozen accepted raw bytes with CRLF normalized
to LF, and their stored SHA256 values equal the manifest's LF identities. All four
Python ASTs are identical between raw and stored content. Actual stored Git blobs:

| Path | Stored Git blob |
|---|---|
| apps/backend/app/main.py | 28a51f6e2a6b966afa0632c23af990dd01dbabbd |
| apps/backend/app/services/zero_touch_orchestration.py | 5814f20d6e4b14cd1dcfcdb87bee0091a7eb9275 |
| apps/backend/tests/test_am18_ownership_checkpoint.py | 6022a4c9d4e8bd017f28e7913f088310c1378d39 |
| apps/backend/tests/test_final_review_editing_real_mongo.py | 0106876ecf23128d917dc1bad1b0495c21f3cd1a |
| apps/frontend/e2e/s2-ownership.e2e.ts | e115936bbcd8dbde793f92d9d1f5745fac653cfd |

Installed TypeScript5.9.3 independently transpiled both raw and actual stored E2E source
with targetES2022, moduleESNext and fileName s2-ownership.e2e.ts. Emitted JavaScript is
identical, UTF-8 SHA256
`4e326d127efc330335083d76ba37b4dc0c8189c47526e24ce8df455f3536561b`.
This supplements exact LF equality; it does not substitute for runtime verification.

The sixth staged path was this report at pre-supplement raw SHA256
`97fbc9f17b830bd98782cd9d7a47beffa023ea67397821e748de126a87559421`, stored blob
`fef65cffe880b2bcd59ebc13a73f8766e8a7654f`; its actual stored bytes equal raw LF-normalized
content and the initial failed-report prefix remains intact. This appended supplement
changes only report content, so the coordinator must restage that report alone and
verify its final stored LF identity. The pre-supplement tree above is not claimed as
the future final committed tree. No executable-content retest or corrective cycle is
needed for proved newline-only storage normalization. Clean committed pre-PR checks,
latest-main/remote identity and CI observation remain the publication owner's steps.

One proposed inspection batch included git write-tree; automatic approval review
rejected it before execution because creating a Git object exceeds this reviewer's
read-only authority. The safer existing-tree/index comparison above completed all
identity requirements without that command, index mutation or an approval bypass.
The reviewer appended only this report; all five accepted raw source/test hashes and
the effective independent R1 PASS remain unchanged.
