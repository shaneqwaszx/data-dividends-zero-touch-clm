# Sponsor demo expansion - independent final Quality Gate, review 2

## Executive result and findings first

**FAIL. P0=0, P1=1, P2=0 required findings.** SDQ-02 is independently verified
closed after its one authorized cleanup remediation. SDQ-01 remains an unverified
required browser-regression criterion. Passing focused implementation and eight-demo
evidence does not close that gap. No owner publication, merge, production, real
Sandbox UAT or next-phase readiness follows. This verdict applies to the new frozen
269-file candidate; neither the historical blocker PASS nor review1 is its verdict.

### SDQ-01 [P1, OPEN] - required complete browser regression is not passing

File: [authenticated-zero-touch.e2e.ts:670](C:/Users/shane/.codex-clean2/worktrees/blocker-resolution-idp-ux/data-dividends-zero-touch-clm/apps/frontend/e2e/authenticated-zero-touch.e2e.ts:670).
Plan Task4 requires the complete retained Playwright inventory. The unchanged required
progress lifecycle still lacks passing complete-shard evidence: first shard45
lifecycles/65 tests passes; full second shard fails after its first passing lifecycle,
while the separately executed unaffected43 lifecycles/46 tests are explicitly partial.
Unique broad coverage remains88/89 lifecycles and111/112 tests, not full E2E PASS.
The12 newly passing physical fixture lifecycles overlap that inventory; they cannot
be added to its numerator or replace the missing progress lifecycle.

The current file still matches the exact accepted original SHA256
`552b5d8bcc78851608af892997254921fb2e8402bf3008973883c5840321074b`.
The previous isolated diagnostic pass and two unsuccessful fixture corrections,
then restoration, remain preserved evidence. Root cause is unproven. Classification:
**required acceptance / verification gap; scope: requirements**, not an established
product, infrastructure, design or architecture defect.

Section15's two unsuccessful correction rounds are exhausted. Human extra-round
approval remains pending. This review did not diagnose, alter, rerun or weaken the
progress selector or its60-second deadline. If authorized later, complete required
regression evidence and a fresh frozen-content review must close this criterion.
No required test or acceptance criterion was removed or waived.

### SDQ-02 [previous P1, CLOSED] - cleanup now follows the configured physical port

At [run_e2e.py:697](C:/Users/shane/.codex-clean2/worktrees/blocker-resolution-idp-ux/data-dividends-zero-touch-clm/scripts/run_e2e.py:697),
the existing parent cleanup owner now unconditionally receives synthetic_seed_port
whenever a disposable classification database exists. Backend fixture creation and
parent fallback use the same port for all8 sponsor,3 legacy classification and1
synthetic-seed modes. Default unconfigured CI27185 remains intact. Existing generated
namespace allowlisting, loopback-only driver connection, failure redaction, failure
exit and process-stop-before-cleanup ordering remain.

Fresh independent execution:48 affected lifecycle tests PASS, including the36
mode/outcome routing subcases for startup failure, assertion failure and success.
A separate safe mocked default-port probe verifies all12 modes dispatch27185 when
unconfigured, with zero network operations or real processes. Current owner/test
inspection confirms the correction is at the single owning call, not a second owner.

Fresh actual Aurora and Garden browser lifecycles PASS on owned27419, respectively
14.375s and21.500s, with the existing60-second deadline. Driver/server database sets
match before/after each:38 non-system generated databases,0 new retained,0 old removed.
The cleanup marker agrees with actual owned-server observations. Neither probe nor
browser connected to the prior incorrect27185 server. Supplied post-repair12-mode
logs/receipts also verify PASS, correct owned port and unchanged database sets.

Required closure is met. The earlier wrong-port behavior remains accurately recorded
in the immutable review1 and before-probe evidence; it is not presented as current.
The38 previously retained generated databases still exist on this task-owned server.
This is not a claim of server-wide cleanup or container/volume removal.

### Measurement advisory - clarified, no required finding

Current browser p95 explicitly uses nearest rank, ceil(0.95*n)-1, index28 of30.
API benchmark uses floor(0.95*(n-1)), index27. Median331.5ms and the0 draft requests,
1POST/4GET group counts are unchanged. The current report does not claim a comparable
old/current browser p95 reduction or combine browser/API/Mongo workloads. No new
performance execution rewrote frozen receipts.

## Scope, authority and exact frozen identity

Owner-authorized additive Final Review editing plus4 recoverable and4 automatic
sponsor-demo journeys; this is not a numbered phase. Review2 is delta-focused after
SDQ-02. The full owner request, AGENTS, workflow, current plan/intent/checkpoint,
quality-gate skill/template, canonical code-reviewer, current authority/contracts/
D-070/D-071/ADR-011/D-072 and triggered security/regression/persistence/provider/cache/
architecture workflows were read in this continuing independent assignment. CI_TOOLING
dev_context was freshly run for the narrow delta. Prior9-class context and independent
product/adverse execution details are preserved in
[review1](C:/Users/shane/.codex-clean2/worktrees/blocker-resolution-idp-ux/data-dividends-zero-touch-clm/.ai-pipeline/reports/SPONSOR_DEMO_ROUND1_FINDINGS.md).
Their applicability was checked against unchanged exact bytes, not transferred as PASS.
Current remediation, checkpoint, five deliverables, owner summary, source/preservation/
verification/hygiene/performance records and every changed path were inspected.

| Identity | Current exact value |
|---|---|
| Worktree | C:/Users/shane/.codex-clean2/worktrees/blocker-resolution-idp-ux/data-dividends-zero-touch-clm |
| Branch / review scope | feat/blocker-resolution-idp-ux-optimization / working-tree, intentionally uncommitted |
| BASE_SHA / HEAD / origin/main / freshly observed remote main | e799d74063678bb0eccbea445d5ab3c8628dd2c0 |
| Staged paths |0 |
| Frozen paths / source paths |269 /68 |
| Reviewed-content SHA256 |24f30d1411e2ad018b56d410c2eecde7c1012903aeb6848891c8272842844acf |
| Source identity SHA256 |5de89b19dda6964828d87ecf744d7b30df4ea3ee8c872a5a4dd2ffabb9df38df |
| Tracked binary diff SHA256 |6943b15ef09a4c6fa71ff782982b3afb6d9db736a5983b48f1712ee9276aec40 |
| Manifest file SHA256 |ec79741c0487e8b9bfe30597f5382486ecca2b4129c26c54422ce86400aa89e1 |
| Prior266 content identity |4fdb85cc0562f7e04c2b0b82736d3ad95f9cc710003e14eff842af350cd844a9 |
| Exact prior manifest copy SHA256 |4d28e36dbdb41c83550679dbc66bf15e31a57311a20d6de87aa52a19a1ec2a2a |
| Exact prior findings copy SHA256 |e7d3df6429d1b43b33431b983d79689190bb444129a648345782dc6c116bdf5a |

All269 raw bytes/lengths/hashes and deterministic sorted JSON entry identity match
at entry and closeout. Full tracked diff, declared path set and non-ignored untracked
paths are accounted for; no source/test exclusion. Only manifest self, this assigned
report and post-verdict delivery receipt are excluded. Relative to review1:36 changed
paths,3 added,0 removed. Only code deltas are scripts/run_e2e.py and tests/test_run_e2e.py;
24 refreshed primary receipts/screens and10 document/metadata paths account for the
remaining changes. Added paths are remediation plus exact prior manifest/findings.
All application/backend/frontend/PDF/CI product source bytes remain unchanged. All68
source hashes,82 preserved historical paths and read-only owner PDF hash match.

## Acceptance checklist

| Assigned criterion | Current disposition and direct evidence |
|---|---|
|4 existing Final Review edit authorities and readonly constants | PASS implementation/direct evidence; company UEN re-verification, explicit classification, current document replacement and creator-reviewed ownership remain unchanged. |
| Current versions/creator/team/CSRF/in-lock authority and target freeze | PASS focused owner/adverse evidence and all8 refreshed receipts; stale409, unauthorized403 and frozen409; no browser authorization owner. |
| Supersession, dependency re-evaluation, fresh explicit confirmation and remaining blockers | PASS unchanged owner source plus prior independent2 physical restart tests and current recovery receipt. |
| Scoped actual-control focus and updated Final Review return | PASS prior99 focused frontend/navigation/isolation tests bound to unchanged files, refreshed receipts and fresh actual Garden recovery. |
| Aurora019S65/35 and preserved old3/default8/Orion/negative018R seed graphs | PASS unchanged native/seed memory/physical evidence and exact82-path preservation check. |
|4 separate informative native annex PDFs through existing parser/Decimal engine | PASS unchanged exact assets/native evidence; prior four renders were legible; no parser exemption or legal-UBO inference. |
| Normal Track B Marketplace Mock/Mongo/auto composition | PASS current receipts: COMPLETE/CACHE_HIT/LOCAL seed, automatic document classification and ownership; fresh actual Aurora with zero intermediate human interventions. |
|4 genuine recoverable Track A cases | PASS all4 current receipts: Garden LOCAL declaration with PARTIAL Mock registry, Merlion UEN correction, Multiple source decisions, MultiLevel replacement; fresh actual Garden traverses genuine controls/blockers. |
|8 distinct explicit Send/ledger/readback/reopen journeys | PASS refreshed8 unique receipts: COMPLETED/SUBMISSION_CONFIRMED, Shell1/Policy1/Amend0/Readback1 and reopen0 mutations; supplied post-repair8 actual modes plus fresh independent2. |
| Original broader matrix/terminal negatives retained | Exact preservation PASS; full retained browser regression remains unverified, SDQ-01. |
| Fresh comparable30-group measurements and truthful classifications | PASS unchanged raw evidence/arithmetic from review1 plus explicit current quantile convention; separate lanes, no production SLA or real UAT claim. |
| Complete required affected verification | FAIL SDQ-01; unchanged product suites have passing bound evidence, but broad browser remains88/89 and111/112, not full PASS. |
| Generated disposable DB isolation and verified cleanup | PASS SDQ-02 closed: fresh48 tests/36 configured subcases/12 mocked default controls/2 actual journeys, supplied12 actual modes and real owned-server set comparisons. |
|5 reports, current contracts/state/decisions and operator boundaries | PASS current delta review; cleanup wording corrected, root/browser pre-repair attribution explicit, overall status truthfully BLOCKED. |
| Remediation cap and authorized stop/publication boundary | PASS observed: SDQ-01 paused after2 unsuccessful rounds; SDQ-02 one separately authorized round; no unauthorized progress retest/publication. |

## Testing, adversarial execution and evidence revision

| Fresh reviewer execution in review2 | Result |
|---|---|
| python -B -m unittest tests.test_run_e2e -q |48 PASS,3.385s; expected negative-test diagnostic is not a failing lane. Includes all36 configured mode/outcome subcases, failure redaction and owned-process behavior. |
| Safe mocked unconfigured-port probe |12 physical modes PASS27185 default; no network/process start. |
| Artifact-safe sponsor-aurora lifecycle on18900/19400, owned27419 |1 PASS,14.375s; generated DB cleanup leaves38/38 set unchanged. |
| Artifact-safe sponsor-garden lifecycle on18900/19400, owned27419 |1 PASS,21.500s; generated DB cleanup leaves38/38 set unchanged. |
| Ruff --no-cache scripts/run_e2e.py | PASS. |
| check_project_state/check_architecture/check_tooling_config/check_policy_authority/check_external_provider_readiness/check_secrets |6 PASS. |
| Explicit269-path secret-pattern scan;32 frozen Markdown whitespace; git diff --check | PASS,0 findings. Supported-pattern scanning is not universal secret assurance. Assigned report checked separately after writing. |
| Freeze/source/log/preservation/receipt checks |269 hashes,68 source entries,29 complete log hashes,82 preserved entries,12 actual-mode logs and8 refreshed safe receipts all verify. Two representative refreshed screenshots inspected. |
| Read-only latest-main/task listener checks | Remote main unchanged e799d740;0 listeners on review-owned18900/19400 after browser cleanup. |

Fresh browser writes stayed in ignored tmp/sponsor-demo-browser; two sanitized reviewer
logs stayed under tmp/independent-sponsor-review2-*. No frozen screenshot or receipt was
rewritten. No wrong-server connection, private environment read, protected database,
provider body or external write occurred. Driver inspection used names/counts/set
comparison only, not database contents. Exact owned container147cdcaa63271cc3a100f9e46bed03abbbc2521c2dc78158825a4f8232e92698,
Mongo7 on loopback27419, with two owned anonymous volumes/no host bind, remains for
coordinator cleanup. Reviewer did not remove container/volumes or old generated DBs.

Unchanged-source prior independent execution remains separately attributed:
13 owner/native tests,7 physical tests with0 skips,5 frontend files99 tests, configured
backend Ruff and strict mypy127 files, and source/security/adverse review. These were
executed in review1, not freshly claimed here. Supplied complete product evidence is
backend2630 PASS+143 physical-only skips, separate23 physical suites143 PASS0skip,
frontend49 files576 PASS/typecheck/build. Earlier full-root373 and broad-browser
88/89,111/112 precede this narrow harness correction. Current48 affected tests and12
actual modes prove the repair; they are not a final full-root/full-browser PASS.
The added root test changes discovery count; this report makes no new full-root count.
All29 supplied log bindings matched full raw bytes. Before36 dispatch probes contain
33 wrong ports; after36 contain0, with expected statuses and stopped-process records.

## Contract, architecture and security assessment

No new required contract/security/architecture defect was found in the reviewed delta.
Cleanup routing now converges at its existing owner. It preserves generated allowlists,
loopback-only driver access, safe exception projection and fail-closed exit behavior.
The test inspects genuine run() finalization under controlled adverse conditions;
actual server observations support successful cleanup beyond authored mock assertions.
Strengths are narrow owning-call repair, retained causal failure evidence, honest
pre/post source attribution, and separate authority for unrelated findings.

Unchanged expansion alignment remains as reviewed in the exact prior findings:
untrusted source/evidence/canonical/target separation; existing case/auth/CAS owners;
strict update-only mutation/no resurrection; in-lock creator/currentness/freeze guards;
ledger-owned ordering/no replay; user/session/case-scoped UI state and explicit final
Send. Schema10, target mapping/TLS, Decimal ownership and source precedence are
unchanged. No additional architecture owner or retirement is required by this repair.
D-072/current profiles describe bounded edits, not sponsor-confirmed new rules.

Mock/LOCAL/PARTIAL/configured Sandbox and actual offline transport remain distinct.
The current8 receipts explicitly say AUTOMATED_OFFLINE_SIMULATION and real Sandbox UAT
NOT_VERIFIED. Sponsor questions/quarantined examples, related-party/hierarchy constraints,
legal UBO and approval/policy authority remain unresolved. No hierarchy creation,
autonomous/final approval, ML UBO, policy waiver, real interoperability, full MIS or
full Workbench claim is accepted. In-process locks, resumable checkpoints and tab-only
drafts remain stated limits; no multi-process transaction guarantee is implied.

## Required action, readiness and change disclosures

Only SDQ-01 remains required. Preserve its original test/assertions/deadline and partial
counts; dependent work requires the pending human extra-round decision. No reviewer fix
was made. A closed resource-isolation defect cannot waive required regression acceptance.

**Readiness: FAIL / NOT READY FOR OWNER PUBLICATION REVIEW.** No next phase or live
ACRA/GoldTier readiness is established. Candidate GitHub CI has not run. Later publication
requires exact independent PASS, unchanged reviewed content, explicit owner authority and
separate clean committed publication checks. Dirty-tree pre_pr_check was not run.

| Surface | Expansion/current repair disclosure |
|---|---|
| API/type | Existing edit routes with derived document-replacement authorization/current-context headers; unchanged by SDQ-02. |
| Durable schema/persistence | Schema10/no migration; existing supersession/checkpoints/CAS; no new persistence or transaction owner. |
| Connector/provider/mapping | External contracts/TLS/target mapping/Decimal/source policy unchanged; no real provider write. |
| Configuration/dependencies | Opt-in sponsor seed/fixture modes; pinned dependencies unchanged; cleanup now uses the existing configured port/default27185. |
| Business/auth/security | Existing edit/freeze/currentness policy and creator reauthorization; no new role, grant, sponsor rule or precedence. |
| Architecture/provider status | Same owner map and D-072 bounded profiles; offline/LOCAL/Mock/PARTIAL labels; real Sandbox UAT NOT_VERIFIED. |
| Runtime/frontend | Additive Final Review controls/return/confirmation, separate assets/eight journeys; application bytes unchanged in remediation. |
| CI/tooling | Single parent cleanup routing repaired plus affected regression; required aggregate/deadlines/inventory retained, SDQ-01 still open. |

## Git status and review receipt

Branch/base/HEAD/current-main and0 staged paths remain as above. Tracked/untracked
candidate changes are intentionally uncommitted and accounted for by the frozen manifest.
Only this assigned report was durably written by reviewer; ignored verification logs/
browser outputs were task-scoped. No implementation/test/doc/evidence fix, staging,
commit, push, PR, merge, original-checkout mutation, private dotenv access, external
provider write or next phase occurred. The report itself is excluded from candidate
identity; its exact SHA256 is returned in closeout to avoid self-hash recursion.
Final raw269-file identity/diff/ref/path-set and report hygiene recheck passed.

| Supporting record | Exact SHA256 |
|---|---|
| SPONSOR_DEMO_REMEDIATION.md |33188f549998336f573a6cf31ed7c9567b8634fee298d6dc5399a2833e96f72f |
| SPONSOR_DEMO_SOURCE_IDENTITY.json |bc3e9694ac79772d6d31a81a2a9bcfadbf1f1ec2aa492e7391b76e600c3c9add |
| SPONSOR_DEMO_VERIFICATION.json |9e692fa3ea2b67b57cd40300606c54fb1a6c526b053aaf6c90cff2886be05c0b |
| SPONSOR_DEMO_PRESERVATION.json |01aefefb31ec00861b2a35d402009d1b022e7d0b25ddac51fb9f3405ea3efc98 |
| SPONSOR_DEMO_HYGIENE.json |4b9a1a095f5b2bc87940ff69b86717694467954675ba3fd3de7e05b7e76ea976 |
| SPONSOR_DEMO_PERFORMANCE.json |a5ec626862d9c14174c561b0e23717bb488314ed59da068142f9caf1b712fe4f |
| SPONSOR_DEMO_OWNER_SUMMARY.md |0a510f247af2be484daa47bb64623c12bc8044e9b1179d22da126e6df0bbeebb |

Review boundary released after final receipt verification. Coordinator alone owns exact
task-container/two-volume cleanup and excluded delivery evidence; this does not authorize
SDQ-01 continuation, publication or mutation of reviewed product content.
