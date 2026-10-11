# Sponsor demo expansion - independent final Quality Gate, review 1

## Executive result and findings first

**FAIL. P0=0, P1=2, P2=0 required findings.** The new frozen candidate has passing
focused Final Review editing/native/physical/frontend evidence and supplied passing
eight-journey evidence. Whole-task acceptance remains blocked by the incomplete
required browser regression and a separately reproduced wrong-server cleanup defect.
The historical141-file blocker PASS does not accept this expanded266-file candidate.
No publication, merge, production, real Sandbox UAT or next-phase readiness follows.

### SDQ-01 [P1, required acceptance gap] - full browser regression is not passing

Evidence: `apps/frontend/e2e/authenticated-zero-touch.e2e.ts:670`,
`tmp/sponsor-demo-e2e-final-shard2.log`, verification blocker SDQ-01, plan Task4.
Fresh read-only discovery contains89 lifecycles; supplied first shard passes45,
but full second shard exits1 at lifecycle2/44, the existing onboarding progress test,
after the unchanged60-second deadline. A separately labelled unaffected43-lifecycle
run is partial evidence, not a full second-shard result. Unique coverage is88/89
lifecycles and111/112 tests, not full E2E PASS.

Current test bytes match exact historical accepted SHA256
`552b5d8bcc78851608af892997254921fb2e8402bf3008973883c5840321074b`.
Supplied logs preserve an isolated diagnostic pass and two unsuccessful altered
fixture attempts, then restoration. Those facts do not close the current complete
regression gap or establish its root cause. Do not call the issue an infrastructure
failure, product defect or waived flake without evidence. Current classification is
**unverified required acceptance / verification gap; scope: requirements**,
not an established design or architecture defect.

Section15's two unsuccessful corrections for this underlying finding are exhausted.
Dependent diagnosis/fix/retest is paused pending explicit human extra-round authority.
This reviewer did not diagnose an await, rerun the selector, change a fixture, weaken
assertions or increase a timeout. If additional authority arrives, the existing
selector must remain and current full-shard evidence plus fresh frozen review must
close the required criterion; the unaffected subset cannot substitute for it.

### SDQ-02 [P1, required] - parent fallback cleanup ignores the configured physical port

Files: `scripts/run_e2e.py:699`, `scripts/run_e2e.py:703`, default cleanup owner near
line489; `scripts/e2e_backend_server.py:254` and `:264` pass the selected port to
both legacy database and sponsor fixtures. With CLM_E2E_SYNTHETIC_MONGO_PORT=27419,
SponsorDemoBrowserFixture creates its disposable database on the owned27419 server.
In run()'s finally, only registry_demo=synthetic-seed receives synthetic_seed_port;
all sandbox-demo databases call _cleanup_classification_database(database) with its
default27185. This includes all8 new sponsor modes and3 legacy database modes.

Fresh safe reproduction: mock OwnedProcess, readiness wait, test wait and cleanup;
set only the configured port; run sponsor-aurora with no process/network/database
operation. The actual owning finally dispatches cleanup27185. Control mode
synthetic-seed dispatches27419. Both generated arguments remain allowlisted, so
naming validation cannot correct server selection. No wrong-server connection was
made by this reviewer; actual sponsor browser execution was withheld once discovered.
The coordinator independently supplied a36-case mocked matrix (12 physical modes x
startup failure/assertion failure/success), with33 wrong-port and3 seed controls
correct. That matrix is corroboration, not this reviewer's fresh execution.

Why required: fallback may connect to an unrelated27185 server, drop/check the
same generated name there and print CLASSIFICATION_DATABASE_CLEANUP=VERIFIED while
the owned27419 database remains. If27185 is absent it instead turns cleanup into
failure. A normal backend close may clean its own database, but cannot make parent
fallback correct on forced process exit/startup failure. The task-owned server's
remaining generated names are consistent with this risk; counts alone are not causal
proof and this review did not inspect their content. No protected DB access is alleged.

**Implementation Drift; scope: requirements/resource isolation**, at the existing
lifecycle cleanup owner; no new architecture owner is needed. Pass the selected
owned port whenever a physical database is allocated, preserve default unconfigured
CI behavior, verify sponsor/legacy/seed cleanup dispatch after process stopping for
success and adverse exits, then obtain actual owned-port eight-journey cleanup evidence.
Keep safe allowlist/cleanup verification. Correct the runbook's cleanup assertion and
current evidence accordingly. This finding has its own unused bounded remediation
budget; it does not authorize another round for SDQ-01. Reviewer made no fix.

### Advisory measurement note (not a required product finding)

Current browser medians and every0-choice-request /1POST /4GET count recompute exactly.
Reported browser p95374 uses nearest-rank index ceil(.95*n)-1 =28 for n30; the prior
accepted browser/API convention floor(.95*(n-1)) uses27 and yields current363.
Current API p95101.321 uses the latter convention. State the estimator explicitly
in future measurement reporting before comparing p95 values across revisions/lanes.
The current table makes no numerical cross-revision p95 improvement claim; valid
nearest-rank quantiles are not fabricated failures. No timing threshold is acceptance.

## Scope, authority and frozen identity

Owner-authorized additive Final Review editing plus4 recoverable blocker and4 automatic
happy-path journeys. This is distinct from the historical blocker implementation, not
a numbered phase. Read-set: AGENTS.md, DEVELOPMENT_WORKFLOW and current dev_context
routing, fyp-quality-gate/report-template, canonical requesting-code-review reviewer,
new plan/intent/checkpoint, all5 deliverable reports, owner summary, verification,
source identity, preservation, hygiene, fixture inventory and performance evidence.
Relevant current source/tests and changed architecture/state/contracts/D-072 were
reviewed alongside unchanged D-070/D-071/ADR-011 authority. Nine classes ran separately:
FRONTEND_UI, FRONTEND_STATE_CACHE, BACKEND_DOMAIN, BACKEND_API, AUTH_RBAC_SECURITY,
PERSISTENCE, CI_TOOLING, EXTERNAL_PROVIDER and ARCHITECTURE_REFACTOR context.
Security/regression/persistence/provider/cache/architecture workflows remain applicable.

Product authority is the owner addendum/plan plus synchronized source/tests/current
contracts, not a historical PASS. Architecture authority is the current owner/interface
map, source DTO -> canonical/evidence -> target mapping and existing ledger/repositories.
No sponsor question or quarantined example was silently resolved. Real Sandbox UAT
remains NOT_VERIFIED; all eight executions are AUTOMATED_OFFLINE_SIMULATION.

| Identity | Exact current reviewed value |
|---|---|
| Worktree | C:/Users/shane/.codex-clean2/worktrees/blocker-resolution-idp-ux/data-dividends-zero-touch-clm |
| Branch | feat/blocker-resolution-idp-ux-optimization |
| Scope / candidate | working-tree / intentionally uncommitted |
| BASE_SHA / HEAD / origin/main / freshly read latest remote main | e799d74063678bb0eccbea445d5ab3c8628dd2c0 |
| Staged paths |0 |
| Frozen manifest paths |266 |
| Reviewed-content SHA256 |4fdb85cc0562f7e04c2b0b82736d3ad95f9cc710003e14eff842af350cd844a9 |
| Source identity / source path count |b464e9b44cfaa96ad2fb38067a0beac5c7ae66d6bd09a1dd63d34a31dad69f56 /68 |
| Tracked binary diff SHA256 |aa001a23a2ae2c8a7134e982597544d1b9f849ba007d0470a62c79f29d69ddda |
| Manifest SHA256 |4d28e36dbdb41c83550679dbc66bf15e31a57311a20d6de87aa52a19a1ec2a2a |
| Historical141-path identity / gate |8e737f07426d1369f1dcb485db074114a47b01ca2282808f69f95d7880a1dbd7 / e53f6285a2d9fb70c800cfd9ac1237025a7597113380fd2234a3d7494b9e8f59; historical only |

All raw byte lengths/hashes, deterministic sorted compact JSON aggregate, complete
tracked/task-owned untracked path union, source68 identity and binary diff were
independently checked. Exclusions are only manifest self, this assigned independent
report and post-review delivery receipt; no source/test exclusion. All266 frozen paths
and manifest remained unchanged during review. Sole durable write is this report;
ignored reviewer type/PDF-render caches are not candidate artifacts. No Git mutation.

## Acceptance checklist

| Assigned criterion | Disposition / evidence |
|---|---|
| Reuse4 current Final Review edit authorities and readonly constants | Supported PASS for inspected implementation/direct evidence: company UEN re-verification, classification selects, current document replacement, creator-reviewed ownership; no arbitrary canonical name/address or constant overwrite. Full task blocked separately. |
| Current version/creator/team/CSRF/in-lock guards and target freeze | PASS focused owner/native/browser-receipt evidence:8 edit tests, stale context409, noncreator403, frozen409; version/fingerprint/currentness authority preserved. |
| Supersession, dependency re-evaluation, fresh confirmation and remaining blocker | PASS: current document lineage/RESUMING-DOCUMENT checkpoint, fresh CLM/readiness version, changed-source blocker and stale old confirmation rejection;2 independent physical restart tests. |
| Scoped actual-control focus and return to updated Final Review | Supported direct browser8 plus fresh99 frontend/navigation/isolation tests; CaseDetail uses actor/case/generation and authoritative supporting refresh. New browser replay withheld for SDQ-02; complete regression unresolved SDQ-01. |
| Aurora019S fictional65/35, old3 exact seed graphs, negative018R/default8/Orion preservation | PASS native/seed memory+physical tests and exact preservation; no target seeding or startup seeding. |
|4 separate informative native annex PDFs through unchanged parser/Decimal engine | PASS: all4 actual native identities/classification scores/graph results tested; no ownership proposals from informative annex; every single-page PDF rendered and legible, no clipping. |
| Normal Track B Marketplace Mock/Mongo/auto seed composition | PASS focused actual in-process/physical current owners: CACHE_HIT, LOCAL_SYNTHETIC_UAT_V1, COMPLETE,4 identity MATCH/HIGH,2 DOCUMENT selections, ANALYZED engine results,0 Marketplace calls/0 intermediate human decisions. |
|4 genuine recoverable Track A cases | Supplied direct8 evidence inspected: Garden PARTIAL plus LOCAL declaration; Merlion wrong UEN; Multiple independent source conflicts; MultiLevel missing-country replacement. No hard stop waived. Fresh sponsor browser replay blocked by SDQ-02. |
|8 distinct explicit final Send/ledger/readback/reopen journeys | Supplied receipts/source support all8 COMPLETED/SUBMISSION_CONFIRMED, separate Send, one Shell/Policy, no Amend for these plans, exact-ID readback,0 replay; cleanup condition FAIL SDQ-02. |
| Original broader blocker matrix and terminal negatives retained | Preserved82 historical evidence/assets and current partial regression/matrix evidence inspected; full regression FAIL SDQ-01. No prior PASS transfer. |
| Comparable fresh30-group measurements and truthful labels | PASS arithmetic with disclosed percentile conventions; lanes separate; Mongo reads197 vs prior147 is not claimed improvement; production SLA/real UAT absent. |
| Complete required affected checks | FAIL: backend/frontend/root/physical/static have bound PASS evidence, but full second browser shard not PASS;88/89 lifecycles111/112tests only. |
| Safe generated disposable DB ownership/verified cleanup | FAIL SDQ-02 parent fallback routes sandbox physical cleanup to wrong server; fresh independent physical-test fixtures clean their own generated DBs correctly. |
|5 reports, current contracts/state/decisions and operator boundaries | Present and mostly truthful; owner summary/checkpoint explicitly blocked. Runbook's configured-port cleanup claim requires SDQ-02 correction. Real Sandbox UAT NOT_VERIFIED. |
| Remediation budget/no unauthorized continuation/publication | PASS observed stop: SDQ-01 after2 unsuccessful rounds pending human extra-round approval; no fixes, timeout/test weakening, commit/push/PR/merge/other phase/external writes. |

## Independent execution and supplied evidence attribution

Fresh checks use task Python3.12 -B/PYTHONDONTWRITEBYTECODE=1, explicit worktree app/
contract paths, pinned Node/npm/Tesseract, no private dotenv. Physical URI was assembled
only in private environment, never printed or persisted. Existing safety fixtures use
fresh allowlisted disposable names on owned27419 and verified cleanup. No clm_poc.

| Fresh reviewer execution | Result |
|---|---|
| pytest test_final_review_editing + test_sponsor_demo_fixtures; -o addopts= -p no:cacheprovider |13 PASS,13.53s;8 edit/adverse owner +5 native/seed/offline-target tests. |
| pytest test_final_review_editing_real_mongo + test_sponsor_demo_real_mongo |7 PASS0skip,30.63s;2 restart/checkpoint +5 physical CLI/native/seed/reopen tests, own generated DB cleanup. |
| Focused ReviewAndSend/IdentityCorrectionForm/TargetClassificationPanel + Phase15CNavigation/EvidenceWorkbenchIsolation |5 files99 PASS,3.35s;19+6+10+41+23. Existing React act warnings only. |
| Configured backend Ruff check --no-cache . | PASS. |
| Configured strict mypy with ignored reviewer cache | PASS127 files. |
|6 current governance/security checkers |check_project_state/check_architecture/check_tooling_config/check_policy_authority/check_external_provider_readiness/check_secrets all PASS. |
| Explicit266-path secret-pattern/UTF8 Markdown whitespace + git diff --check | PASS0findings. Pattern scan is not universal secret assurance. |
| Mocked parent cleanup dispatch, no process/network | Reproduces SDQ-02: sponsor27419 -> cleanup27185; synthetic-seed27419 -> cleanup27419. |
| Read-only inventory, source/log/preservation/PDF/receipt/performance checks |89 selectors retained;68 source hashes/82 preserved files/10 embedded log receipts match;4 rendered PDFs and8 safe receipts verified. |

**Not executed by reviewer:** blocked progress diagnosis/retest, actual sponsor8 browser,
broad browser/performance/recovery suites that rewrite frozen evidence, full backend/
frontend/root suites, real provider writes and publication gate. Actual sponsor replay
was withheld to avoid wrong-server cleanup; no temporary runtime fix masked SDQ-02.
Focused actual physical/native owner execution above still substantiates unrelated
verified behaviors. Existing18900/19400 ports remained unused by reviewer browser work.

Bound implementer logs are separately attributed: backend2630PASS143physical-onlySKIP,
4warnings; separate physical23suites143PASS0skip; frontend49files576PASS/typecheck/build;
root373PASS. Full browser first shard45lifecycles/65tests PASS561.094s; separately
unaffected second43lifecycles/46tests PASS; full second shard FAIL. Repeated overlap in
failed shard is not added to unique counts. Current89 selector inventory retains670.
An isolated diagnostic log's1 pass does not override failed full-shard acceptance.
All10 referenced structured log hashes matched complete raw bytes; the report preserves
first causal failures and the uncertain root cause rather than presenting them as fixed.

Current browser30 median selection76ms/confirmation245/total331.5, nearest-rank p95374;
0 selecting requests,1POST/4GET each. Current API30 median81.719/p95101.321 with1
reconciliation/document save each. Mongo one descriptive workload197find/5update,
0 target and WAITING_FOR_REVIEW; not a latency distribution. No performance rerun
rewrote frozen receipts. An initial reviewer quantile check assumed the earlier floor
estimator; explicit convention inspection resolved that assumption without changing
receipts or claiming an error. Initial reviewer test comparison incorrectly used HEAD
instead of historical accepted package, and text scan omitted explicit UTF8; corrected
read-only verifiers pass against actual accepted hash/UTF8. Candidate never changed.

## Contract, code, architecture and security assessment

The additive final edit implementation uses existing owners. ZeroTouch case lock
reauthorizes creator before writes; derived document replacement/ownership capabilities
consume freeze/currentness rather than grant browser authority. Final READINESS document
replacement requires automation/CLM/case/document versions, retains document lineage,
cancels old confirmation, preserves registry/Search checkpoints and re-evaluates dependent
evidence/readiness before another explicit Send. Partial CLM refresh failure leaves an
explicit RESUMING/DOCUMENT checkpoint; tested restart Resume makes no target mutation.
Classification review uses existing closed vocabulary/current document assessment and
refreshes confirmation. CaseDetail return hints are actor/case/action-generation scoped,
wait for authoritative refreshed evidence and otherwise expose the remaining blocker.

No new persistence schema/migration, canonical repository, source precedence, mapper,
Decimal engine, production provider composition or ledger bypass appears. Existing
schema10/historical reads, strict identity/revision CAS, insert/update-only semantics,
delete anti-resurrection, target freeze/order/no replay and session/query isolation
remain. D-072/current profile amendments describe the bounded behavior and checkpoint
limits without pretending cross-owner transactions. Old APIs/fixtures retain actual
compatibility use; no retirement is assigned. Large existing owners remain structural
follow-up, not a reason to add another owner or broaden the assignment.

Track B fixture uses normal Marketplace Mock connector/cache/Mongo composition and
explicit complete LOCAL seeds through the existing manager. Injected no-network
Marketplace/strict offline XPI transports are test-only; target results arise from
ordinary Search/plan/ledger/Shell/Policy/readback, not a product completion flag.
Native informative annex describes seed graph and is not a client declaration; parser
has no new exemption and quantitative authority remains registry fixture/Decimal engine.
Legacy default8, Orion and negative018R remain. Garden PARTIAL source is supplemented
through current approved LOCAL evidence/review, not relabelled official COMPLETE ACRA.

Sensitive mutation route guards remain backend authoritative. Current stale/noncreator/
frozen assertions and no-target-before-final boundaries pass where executed. Safe logs/
receipts contain synthetic identities, allowed states/IDs/provenance and no private
credentials, raw sponsor payload/document or exception details. Actual original owner
PDF hash76e5c9922abbd2ba7b71c51bd8139ede37ba91c599168e2550f2c7e7e5d50d48 remains unchanged.
SDQ-02 is a real resource-isolation/cleanup defect at a test lifecycle boundary; it is
not excused by ordinary success assertions or future container removal.

## Required fixes, limits and readiness

Required findings: **SDQ-01 and SDQ-02**. No reviewer fix occurred. SDQ-02 may receive
its own authorized bounded remediation; freeze changed source/tests/evidence and
obtain fresh review. SDQ-01 remains dependent on human extra-round approval after2
unsuccessful corrections; no diagnosis/retest from this reviewer is implied or permitted
by the new cleanup finding. Passing SDQ-02 cannot turn the required full browser gap
into PASS. Keep exact failed selector/assertions/deadline and honest partial counts.

Accepted limits/non-goals remain distinct: in-process locks and resumable sections,
tab-only drafts, provisional/local ownership rather than legal UBO, sponsor questions/
quarantines, unsupported hierarchy/related-party child flows, approval/policy waivers,
full MIS/Workbench, real Live/Sandbox interoperability and production hardening.
Configured Sandbox and offline test transport are distinct; MANUAL REAL SANDBOX UAT
NOT_VERIFIED. Mock/Local/Partial/Dormant/Live classifications cannot substitute for
sponsor authority. No autonomous/final approval or real Ready-for-Approval claim.

**Readiness: FAIL / NOT READY FOR OWNER PUBLICATION REVIEW.** Historical blocker PASS
remains scoped to its original tree. Candidate GitHub CI has not run. Explicit owner
publication authorization, exact independent PASS and separate clean-committed checks
would be required later. Dirty-tree pre_pr_check was not run. No commit, staging, push,
PR, merge, original checkout/private dotenv/protected DB mutation, real provider write
or next phase was performed. Coordinator owns exact task container/anonymous-volume
cleanup after review; reviewer's physical test cleanup does not imply container-wide
cleanup or removal. No container/volume removal was performed by reviewer.

## Change-class disclosures

| Surface | Expansion disclosure |
|---|---|
| API/type | Derived document replacement authorization and current-context headers added; existing routes reused. |
| Durable schema | Unchanged schema10; no migration. |
| Persistence | Existing supersession/checkpoint/re-evaluation through current CAS owners; physical restart tested; no new transaction owner. |
| Connector/provider mapping | External contracts/TLS/target mapper/Decimal source policy unchanged. |
| Configuration/dependencies | Opt-in sponsor fixture/seed/browser modes; pinned dependencies unchanged; no startup target seed. |
| Business/source rules | Existing edit/currentness/freeze policy enforced; no new precedence/UBO/sponsor rule. |
| Auth/security | Creator replacement/classification reauthorization strengthened in existing boundary; no role/grant. |
| Architecture | Same owners/dependency direction; D-072 profiles/state reflect the additive behavior. |
| Provider status | Offline/LOCAL/Mock/Partial labels retained; real Sandbox UAT NOT_VERIFIED. |
| Runtime/frontend | Final Review current control edits, return/remaining blocker, fresh preview/confirmation;4 separate native assets and8 test journeys. |
| CI/tooling | Inventory89/112 and opt-in physical fixture dispatch; deadlines and required fail-closed shard aggregate retained; cleanup SDQ-02 defective. |

## Report hashes and final review receipt

The complete266-path manifest covers source/tests/docs/assets/evidence and historical
reports. This report is the only durable reviewer write. Its own hash is supplied in
handoff rather than embedded self-referentially. Final content/manifest/diff/ref/path-set/
staged0 and report whitespace/secret-pattern verification are required before handoff.

| Evidence | Exact SHA256 |
|---|---|
| SPONSOR_DEMO_CANDIDATE_MANIFEST.json | `4d28e36dbdb41c83550679dbc66bf15e31a57311a20d6de87aa52a19a1ec2a2a` |
| SPONSOR_DEMO_SOURCE_IDENTITY.json | `34a683ae6aaaaea8e8411404866b1749290da7f8c34a0914a92142fe565f2d74` |
| SPONSOR_DEMO_VERIFICATION.json | `4c987c0258f5488f99f2737c36247d3c3ce7009213ba4e7e8aa6db1ef35f89b0` |
| SPONSOR_DEMO_PRESERVATION.json | `01aefefb31ec00861b2a35d402009d1b022e7d0b25ddac51fb9f3405ea3efc98` |
| SPONSOR_DEMO_HYGIENE.json | `f2c4a3966980fa652e3a38be6dad78fda8dbb6ab10c7a09c8c77f42baeeaab8e` |
| SPONSOR_DEMO_PERFORMANCE.json | `fa4a0349de94e1fe451fb2c586625c1b68d9b9b38141af4738ab1dab4f82ef0a` |
| SPONSOR_DEMO_OWNER_SUMMARY.md | `80b72c0018913921895d5bd131db5604d53601fa360d33cbac821d4a894ea030` |
| FINAL_REVIEW_EDITING_ACCEPTANCE.md | `130b2dc67a6430c9ca028d275840534cd50379638a075f0eec414877876e793a` |
| FOUR_BLOCKER_DEMO_JOURNEYS.md | `642e2e27a5639c90e0793a3200a15f445ce29bcaf9341f17f19039f17212d970` |
| FOUR_HAPPY_PATH_DEMO_JOURNEYS.md | `9c2db373e2f6d764f0631ed4cdeb47be21da25adb13d09e7309b8673c1d24bc4` |
| DEMO_FIXTURE_AND_DOCUMENT_MANIFEST.md | `bdded14150c568e58bc90d46d1a04fa7bcbe313c7daf9d04d56cbd0ae4674c96` |
| SPONSOR_DEMO_OPERATOR_RUNBOOK.md | `efbac234a72bd37b7dac77163ba75894ef6e919af1c86ece4620f52852b01e36` |
