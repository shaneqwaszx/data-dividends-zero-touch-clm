# AM Wave 1 independent Quality Gate R3

## Executive result

**PASS.** The complete frozen native staged candidate satisfies the included AM-05,
AM-09, AM-10 and AM-14 acceptance, with AM-15 regression preserved. Cycle 2 removes
the verified contradictory registry freshness claim in both actual consumers. No
required current fix remains. AM-18 is **NOT_REPRODUCED / OPEN**, with no repair or
established root cause; B/C acceptance is independent of that unresolved report.

Independent reviewer: `/root/am_wave1_cycle2_gate`, configured GPT-6.1 Sol / High
reviewer, separate from implementation and both earlier reviewers. This run did not
implement/remediate the candidate or spawn another agent. Owner pasted replacement
brief v2 controls scope; downloaded supporting prompts do not grant extra authority.
The second and final corrective cycle is consumed: **2/2**, with no third cycle.

Review began after the coordinator freeze at2026-10-13T19:19:51Z. Fresh verification
ran19:22-19:25UTC; final native identity readback19:30:59UTC. The original bounded
session started17:32:54UTC /01:32:54SGT;360-minute ceiling23:32:54UTC. This report
certifies reviewed local content, not clean committed pre-PR, latest published head,
remote CI/review clearance, owner exception, merge, another phase or Live integration.

## Reviewed identity and complete scope

- Worktree: `C:/Users/shane/Desktop/FYP/am-w1-1014-0132`.
- Branch: `feat/am-wave1-20261014-0132`.
- Published/current HEAD before cycle-2 commit: `07a2f1af48aebb59ca36e353313f481e4c7a7f13`.
- Initial base / locally inspected origin/main: `a497793be2615306bc7cfbd3104fd4352dead96d`.
- Actual full native staged tree, excluding this separately bound R3 report:
  `fd796ad64a72d37121d6c7e1ded2f54b583adfab`.
- Complete release inventory:23 paths;5 staged cycle-2 paths,18 already committed.
- Raw path aggregate SHA256:
  `ada0ca87957d96bbb38a71b942181b83aee37c0878b3bdce459ec562313b792f`.
- Native staged Git blob aggregate SHA256:
  `d191f75a542812e7770872eca87b4b12f5e80c25f8ad50c0ccdc74f5021740bb`.

Complete manifest: `tmp/am-wave1/frozen-staged-r3.json`; independent readbacks:
`tmp/am-wave1/reviewer-r3/identity-start.json` and `identity.json`. Individual raw
hashes and actual native blobs are listed below. Raw aggregation uses sorted UTF-8
`path + NUL + raw_sha256 + newline`; blob aggregation substitutes the actual index
object ID. Every23 file raw hash/length and native `git rev-parse :path` identity
matched. Native `cat-file blob` content matches the working bytes after CRLF/LF
normalization; each stored blob's header-and-content SHA1 was independently checked.
The full tree was independently reconstructed from every index mode/path/object using
Git tree serialization and directory sorting, without writing Git/index/objects.
Both before/after native identities matched the coordinator's actual tree. No
hash-object conversion prediction or HEAD-only identity substitutes for the candidate.

Scope classification: whole release BACKEND_DOMAIN + FRONTEND_UI + DOCS_ONLY;
cycle-2 delta FRONTEND_UI + DOCS_ONLY. Complete base-to-candidate diff and new paths
were inspected, including product owners, tests, browser assertions, preserved old
reports, plan/checkpoints and bounded runbook. Exactly five cycle-2 changes:shared.ts
moves existing provenance timestamp validation/description to registryReuseDescription;
RegistryProvenancePanel and CaseStatePanels call that presentation helper; five
combined-consumer regressions and a valid acquisition fixture; remediation report.
The published-head failing-first log `tmp/am-wave1/registry-summary-red.log` records
5 FAIL/38 PASS,0.836s. Its causal assertion directly shows fresh summary text beside
unavailable provenance dates. It is baseline diagnostic evidence, not a fresh R3 PASS.

Authority read-set included root/nested AGENTS, repository skills README, actual scoped
dev_context union, quality-gate skill/template, reviewer/security roles, current
workflow/architecture/provider state/branch/open sponsor-question context, task plan,
implementation checkpoint, initial and R2 gates, cycle-2 remediation and current
owners/tests. Triggered cache freshness, IDP review, ownership/source, intake,
reconciliation and readiness contracts plus D-061/062/067/070-072 and ADR-011 control
the assessed invariants. Dated historical baseline descriptions do not replace current
source or the inspected base. No original AM PDF/page-12 screenshot inspection is claimed.

## Acceptance checklist

| Requirement | Result and independent evidence |
|---|---|
| Frozen whole candidate, hygiene and independence | PASS. All23 raw/native blobs, aggregates and full native index tree match twice. No implementation/Git writer ran during review. New Markdown explicitly checked; secret scanner passes. |
| AM-05 valid SGT, UTC audit, invalid values | PASS. Fresh67 summary/provenance tests, full682 suite,28 production-helper probes, real HTTP audit. UTC rollover/fractions/leap-date/null/missing/malformed/non-UTC timestamps handled safely; original ISO remains inspectable. |
| Cycle-2 both actual consumers | PASS. Missing acquisition, impossible acquisition date, blank binding, invalid expiry and invalid operation time suppress fresh text twice in combined markup. CACHE_HIT, reuse/no-request, valid-cache behavior and owning-registry exception precedence remain. Existing shared helper makes no present-currentness/expiry calculation or backend action. |
| AM-14 new Singapore calendar date | PASS. Fresh26 owning tests,7 provider probes, full frontend and real Los Angeles-zone browser atUTC16:00. Defaults todaySGT; historical receipt/current/document source dates and explicit per-source drafts persist; future Singapore days and future UTC review instants remain refused. |
| AM-15 note/graph regression | PASS. Actual empty-note submission retains null; supplied-short-note rejection, graph prefill, stable identities, bindings and parent-total/source checks pass. No all-AM16 closure claim. |
| AM-09 responsive actual decision cards | PASS. Real1440/900/360 screenshots visually inspected:2/1/1 columns; long values wrap and no body overflow. Fieldset/legend/order/errors retained; fresh keyboard/sticky-rail/root/mobile routing tests pass. |
| AM-10 local eligible bulk drafts | PASS. Only pending document fields eligible under existing per-field choices; missing suggestion skipped. Existing CORRECTED choice/correction/note survive rapid clicks. Filled/skipped/remaining counts shown; source-family bulk controls absent. Zero writes/version change before explicit single Confirm; exact eligible batch observed; independent residual blockers remain. |
| Case/actor/version/replacement isolation | PASS. Full current-byte frontend repeats real CaseDetail boundaries; actual same-team noncreator403 and cross-team404, disabled/absent controls and no leaked draft. Source/date selections remain in existing case-bound ephemeral owners. |
| AM-18 boundary and B/C separation | NOT_REPRODUCED / OPEN. Fresh new and genuine existing-customer prior-finalized-proof journeys show balanced60/40->55/45 correction, fresh analysis/version, retained current classification, reachable Final Review and reload. Both primary cases NOT_SUBMITTED, no attempted target writes, no confirmation, zero target posts/external calls. No AM18 repair/root-cause claim. |
| PR82/83/84 and freeze/call stopping | PASS. Fresh both Garden same-case choices, count-bound intake, replacement/confirmation/root, mixed-route, attention, delayed current-document and S2 source/freeze journeys. Full unchanged backend adverse/currentness/auth/ledger suite attributed explicitly below. No target owner/source-policy change. |

## Fresh verification receipts

All successful commands below exit0. Independent ignored outputs:
`tmp/am-wave1/reviewer-r3/`, principally checks.json, browser-checks.json,
browser-s2-corrected.json, backend-attribution.json, browser-acceptance.json,
identity-start.json/identity.json and individual logs. No install/dependency update.
Python3.12.10 from existing
`C:/Users/shane/Desktop/FYP/data-dividends-zero-touch-clm/.venv/Scripts/python.exe`;
PYTHONPATH points to this task/apps/backend and actual import path was asserted.
Observed pytest8.4.2/FastAPI0.141.1/uvicorn0.52.1/Ruff0.16.2/mypy1.20.2/pymongo4.15.1
match the initial full-suite environment; Node/npm use the same installed locked runtime.

| Command / cwd | Fresh result |
|---|---|
| frontend:`npm test -- src/pages/CaseStatePanels.test.tsx src/pages/RegistryProvenancePanel.test.tsx --no-cache` |67 PASS/2 files,0 fail/skip,1.92s; outer3.344s. Includes43 summary+24 provenance and owning-registry failure precedence. |
| frontend:`npm test -- --no-cache` |682 PASS/53 files,0 fail/skip,10.72s; outer12.140s. |
| frontend:`npm run typecheck` |PASS; outer11.125s. |
| frontend:`npm run build` |PASS,140 modules,1.44s;617.94kB JS/gzip170.57kB; outer12.625s. Existing >500kB warning retained. |
| backend:`python -m pytest tests/test_manual_ownership_evidence.py -p no:cacheprovider` |26 PASS,0 skip,1 existing deprecation warning,0.33s; outer1.657s. |
| backend:`python -m ruff check . --no-cache` |Configured backend CI lint PASS; outer0.234s. |
| backend:`python -m mypy app --cache-dir ../../tmp/am-wave1/reviewer-r3/mypy` |Strict PASS,127 files; outer14.266s. |
| root:`python -m unittest discover -s tests/contract -p test_*.py` |44 PASS,2.370s; outer5.109s. |
| root:unittest discovery `test_phase_07_delivery_assets.py` |4 PASS,0.013s; outer0.125s. |
| root:unittest discovery `test_check_secrets.py` |8 PASS,0.013s; outer0.203s. |
| root:`python scripts/check_secrets.py` |PASS; outer6.063s. Repeated after report write. |
| root:check_project_state/check_architecture/check_policy_authority/check_external_provider_readiness/check_tooling_config |5 PASS; outer0.281/0.656/0.125/0.110/0.109s. |
| root:`node tmp/am-wave1/reviewer/date-probe.mjs` |28 PASS against actual current production shared.ts; outer0.500s. Probe inspected before reuse. |
| root:`python tmp/am-wave1/reviewer/domain-date-probe.py` |7 PASS against actual current ManualOwnershipEvidenceProvider; outer1.000s. UTC review instants/source dates preserved. |
| `python -m pip check`;frontend:`npm ls --all` |Both PASS; outer0.812/1.016s. Locked manifests unchanged. |
| native `git diff --cached --check`, full diff check, all23 explicit UTF8/whitespace/EOF/conflict checks and report hygiene |PASS, repeated final readback. |

Fresh browser execution used unchanged canonical
`python scripts/run_e2e.py --backend-port 19065 --frontend-port 14473 --timeout-seconds 60`
with guarded synthetic offline transports and
default assertions/retries. Eight meaningful invocations executed **17 PASS/0 FAIL/0
SKIP**. Exact command arrays and wall durations are in browser receipts.

| Grep / fixture | Fresh result; outer seconds | Log |
|---|---|---|
| `AM18 new customer\|AM14 Singapore midnight\|AM05 AM09 AM10` |3 PASS,16.5s;22.063 |browser-am.log |
| `AM18 existing-customer`;`--registry-demo synthetic-target-reuse` |1 PASS,10.3s;15.265 |browser-reuse.log |
| `Blocker simulation draft isolation\|PR83 initial multi-file\|PR84 mixed identity` |3 PASS,11.5s;16.688 |browser-regressions.log |
| `Ownership hotfix valid root identity\|Ownership hotfix replacement\|Ownership hotfix confirmation` |3 PASS,15.4s;20.687 |browser-root-replacement.log |
| `Garden PARTIAL wrong UEN`;`--sandbox-demo garden-existing-customer` |2 PASS,9.0s;13.688 |browser-garden.log |
| `UX refinement attention identity\|UX refinement specific document decisions` |2 PASS,8.5s;13.672 |browser-attention.log |
| `Blocker simulation early stage click waits` |1 PASS,4.9s;10.281 |browser-late-read.log |
| `S2 creator edits\|S2 document proposals`;`--garden-protocol` |2 PASS,10.3s;14.907 |browser-s2-corrected.log |

The table's literal pipes denote grep alternatives; exact argument arrays in JSON are
canonical for exact invocation details. Fresh AM screenshots/checkpoints
are under `tmp/browser-evidence/9aa37c24-f753-49ff-815e-8e61f47bab98/retained/`; genuine
reuse under `tmp/browser-evidence/cff61d8b-18a8-4635-bdfe-e6d5e497677a/retained/`.
Both after.json receipts independently asserted primaryCaseNOT_SUBMITTED,
targetConfirmedfalse,targetAttempts[],targetPosts[],externalCalls0. Responsive1440/
900/360 screenshots visually inspected; browser additionally asserts2/1/1 grid and no
overflow. Other runner outputs remain UUID-owned ignored task artifacts. Both owned
ports had no listeners at closeout; no unrelated process was stopped.

Reviewer setup-only failure: the first S2 grep `S2 ownership` discovered0 tests and
returned exit1/5.781s. Original browser-s2.log and browser-checks orchestration failure
are preserved. Reading actual titles identified correct `S2 creator edits|S2 document
proposals` and the required isolated offline Garden fixture; corrected run passes2.
No product test/source/assertion/timeout was changed or failure relabelled as a passing
executed test. Eight passing meaningful runs plus one zero-test setup invocation were
performed; this is not a third corrective cycle.

## Attributed evidence and failed/unexecuted lanes

**ATTRIBUTED, not freshly executed in R3:** initial independent gate's full backend
`python -m pytest tests -p no:cacheprovider` from apps/backend: **2692 PASS,157 SKIP,
4 warnings,1518.70s**,2849 total. It began18:17:35UTC after original raw freeze18:15:51.
Original backend-full.log and first gate were inspected. Independent R3 attribution
reconstructed every **302 tracked backend path**: the only two backend paths changed
from base match original frozen raw hashes exactly; every other tracked backend path
matches base/initial content after newline normalization. No backend untracked path or
unstaged delta exists. Backend pyproject, pinned dependency manifests, frontend locked
manifests, browser config, runner/server and relevant source/config inputs are unchanged.
Installed interpreter and package versions match, and pip/npm integrity passes. Receipt
backend-attribution.json contains every path/hash/native blob. The UI-only cycle-2 delta
cannot change those backend/test/config/runtime inputs. Owner brief section9 permits
this exact-input attribution. Fresh focused domain/frontend/contracts/browser probes
challenge the important accepted behavior; no required backend lane is waived or called
fresh. Original baseline RED2/RED10 are diagnostic evidence, not AM18 fix proof.

**ATTRIBUTED inherited failure:** broad root
`python -m ruff check apps/backend scripts tests --no-cache --output-format json`
previously exits1 with15 diagnostics in7 unchanged scripts. R3 independently checked
exact path/code/message/line/column equality between retained initial owner-main baseline
and R2 receipt, and all affected script bytes still equal base. This is not a root-wide
PASS or newly executed R3 lint; exact backend CI lint is freshly PASS. No script/config
rules/diagnostics were suppressed or repaired.

The157 backend skips remain151 guarded physical-Mongo and6 PATH-based OCR discovery.
They are not passing physical/OCR evidence. Initial receipts distinguish an installed
explicit Tesseract executable from absent PATH discovery. Physical Mongo/restart checks
and complete unfiltered E2E shards were NOT_EXECUTED in R3: no persistence/CAS/restart/
security boundary change and no AM18 repair triggers them. Fresh scoped real HTTP/browser
coverage is recorded above, not called full unfiltered E2E. Existing React act warnings,
Starlette/httpx deprecation, deliberately malformed Pydantic-fixture warnings and build
chunk warning remain disclosed; none was suppressed.

Remote status is coordinator-provided prior publication evidence, not a fresh R3 GitHub
observation: published PR85 HEAD07a2f1a; push38452390447 and pull_request38452403782,
attempt1,9 jobs each, all steps=[] and payment/spending-limit start refusal. These mean
**REMOTE CI NOT_EXECUTED**, not executed test FAIL or PASS. One verified old-head botP2
at discussion_r4262912151 is repaired locally; thread has not yet been resolved on
verified new published bytes. Future latest-head CI/review, clean committed pre_pr_check
and latest-main fetch remain coordinator obligations. R3 performs no rerun/billing/
settings/requirements/owner-exception action and claims no remote clearance.

## Contract, architecture and security findings

No required current finding. The single existing shared presentation owner now owns
one retained-reuse description rule. It checks already-required UTC wire timestamp
validity and keeps backend CACHE_HIT/no-request facts; it neither evaluates current
wall-clock freshness nor changes expiry/source policy, actions, statuses or authority.
Registry exceptions/registry technical failures still precede cache-summary success;
later independent target failures do not falsify retained registry reuse. Both actual
consumers use the same result, avoiding divergence. A valid cache fixture has real
recorded acquisition time rather than proving freshness from missing data.

The whole-release backend date guard intentionally interprets the existing no-future
calendar rule as Singapore under the explicit owner brief; review instants stay UTC.
Manual source dates/graph identities/versions/bindings remain under existing owners.
Bulk fills only existing local document drafts; current per-field ACCEPTED eligibility
is unchanged except robust null/undefined exclusion. Missing/low/ambiguous evidence
never gains canonical/source authority. Source reconciliation remains bounded legal-name
only; no address/UEN/country document-wins grant. Backend whole-group currentness,
creator/team/CSRF, reauthorization/CAS and residual blockers remain authoritative.
Existing count-bound intake, replacement lineage, D-062>=25% Decimal engine, explicit
Send, frozen intent, ledger ordering, uncertain stop and no-replay are unchanged.
No second owner/dependency/framework/storage/auth service or ADR-triggering boundary.

No new secret/hash/token/header/credential, real customer document/body/provider payload,
private exception, protected path or confidential sponsor artifact was introduced.
Only synthetic offline fixtures and safe bounded projections were used; strings remain
React-escaped. No dotenv, real ACRA/Marketplace/GoldTier/provider request, protected DB,
Copilot/Camunda feature work, other jurisdiction, hierarchy/RP/enrichment or later phase.
Current Mock/Local/Partial/Dormant evidence labels and sponsor questions remain distinct.
The native scanner's supported pattern PASS is evidence, not a guarantee about every
possible secret; complete diff/new-path inspection supplements it.

| Surface | Change from base / cycle2 |
|---|---|
| API/shared types |Unchanged; added type imports only. |
| Schema/repository/CAS/restart |Unchanged. |
| Connector/configuration/dependencies/CI |Unchanged. |
| Business rule |Accepted whole-release future declaration calendar basisUTC->Singapore; cycle2 adds no rule/currentness change. |
| Mapping/auth/security |Unchanged. |
| Architecture/provider status |Unchanged; no new owner or Live/Sandbox interoperability claim. |
| Runtime/UI |SGT audit/date provenance/default/responsive cards/bulk drafts; cycle2 aligns summary+provenance invalid-time display. |
| Documentation/tests |Bounded plan/checkpoint/runbook/regressions plus immutable prior reports and cycle2/R3 reports. |

## Required fixes, readiness and Git closeout

Required fixes: **none**. Exact **PASS** binds only the23-path native candidate above.
AM18 remains OPEN/NOT_REPRODUCED, AM03/all unassigned AM implementation deferred; sponsor
production/source/legal-control/RFA/provider dependencies stay open. No next phase or
real ACRA/GoldTier integration readiness is granted.

The coordinator may continue the already-authorized same-branch/SAME PR85 publication
sequence after separately binding/normal-staging this R3 report, proving resulting native
tree and unchanged23 accepted entries, fetching/assessing latest main, normal commit,
clean committed canonical pre_pr_check/checklist, normal push and bounded latest-head
push+PR CI/review observation. Old-head thread resolution requires published-byte proof.
No third corrective cycle, merge/auto-merge/owner approval, repeated billing-blocked
rerun, protections/billing/settings change or owner CI exception is authorized here.
A later changed accepted input/semantic integration requires fresh independent review;
this report does not bless future content or pending/failed remote lanes.

Reviewer wrote only this assigned report and ignored verification/build/cache artifacts.
No application/test/config/ordinary-doc/AGENTS/skill/index/Git configuration mutation,
commit,push,PR action,merge,fetch or next phase. At closeout the23 accepted raw/native
entries and full staged tree are unchanged. The original five staged changes remain;
this report is the sole new untracked durable reviewer path. External ignored
`tmp/am-wave1/reviewer-r3/report-binding.json` records this report's raw_sha256 and
exact_raw_git_blob_sha1 without a recursive self-hash. Coordinator must separately
validate actual native report blob after normal staging; raw report SHA1 is not a
predicted normalized index blob.

## Complete native frozen inventory

| Path | Raw SHA256 | Actual native staged Git blob SHA1 |
|---|---|---|
| `.ai-pipeline/001_planner/AM_WAVE1_PLAN.md` | `076ff6f168c7e9ba5667ea8cdc07d58f9b7e157794c875315dc6a668747322e3` | `96a0007a00289361797e8b7f9c0ed1df4603c37f` |
| `.ai-pipeline/reports/AM_WAVE1_IMPLEMENTATION.md` | `ee831ceac3ef2c9dcac260916aaf341899ac390bfcc1fee2024b9a8127ef3570` | `1131eece45196cd613af5fe1d54004e64d0a8823` |
| `.ai-pipeline/reports/AM_WAVE1_INDEPENDENT_QUALITY_GATE.md` | `9cfa52e4d2699932628a5685c0a0f726ec28eb6e82e586f97b59c1652183a216` | `9658ae82bb3bc30c953acba50c4af96d8ceee02b` |
| `.ai-pipeline/reports/AM_WAVE1_INDEPENDENT_QUALITY_GATE_R2.md` | `8c598f87c605f383452d5415ae327cd15e9da7b0da981d5a156074842226b3b1` | `914f317ec827c83f9b4f43b9c2b1f60526615a0a` |
| `.ai-pipeline/reports/AM_WAVE1_REMEDIATION_CYCLE_2.md` | `63d4f62a95e5d9c2d4cd1e7fc4950641e1f4ec535f536f761020d95ef38df6ac` | `c9af945119a0dc7b0bec90af2b711a3ac0cb6557` |
| `apps/backend/app/services/manual_ownership_evidence.py` | `91568c59f919be5a300636c06349180a80be22af460a5b44502b90ab7ab0c10e` | `1c01377a30111decd0875b6e99c1258e36e06cdc` |
| `apps/backend/tests/test_manual_ownership_evidence.py` | `790e15fbd3eb52c80474c3c2dba719f8571e53cd4b1e95c28804786c4ea589ac` | `da7f03ffcf97853d83242286f06095e0a5fb7b35` |
| `apps/frontend/e2e/am-wave1.e2e.ts` | `dd1c2599aeeea27f6bb2df642abe232beb6bc2b95790e3fb29e39b8bb26ad478` | `7317bb5f75b6c4f095fb431d719f72fa5f838539` |
| `apps/frontend/e2e/blocker-simulation.e2e.ts` | `004386f6c594650478fcc65868a42c2f426db1c1434854245a73abab4546513a` | `ddff7a91467d6abee02c23077d32faefa2b5c70c` |
| `apps/frontend/e2e/s2-ownership.e2e.ts` | `6b0168b64ba934dda0755fc74c15beb420fda0b061fd603ef8017c1edac118e0` | `78420fb5f6e0680fd214d2ced10cce8389ba4fff` |
| `apps/frontend/src/EvidenceWorkbenchIsolation.test.tsx` | `1ee54ad1126aaf1dce941768d11f08cd84d48fbbe02c2f385d6dd1bd9f5e72c2` | `55b871989aa2e7cb5b7cfb6f41e6d879684e5b45` |
| `apps/frontend/src/design-system.css` | `92b29038327b6e917a1cb289ce3c40485ab238ab7289b54a852a9d39da119e53` | `21491bd546715fe41cdbe5e1df8edccc8cae5023` |
| `apps/frontend/src/pages/BlockerDecisionReview.test.tsx` | `bf1eaa92537942caa1ab91244964ff45e8e3e541018b5affe6927b9f08c5c0ef` | `763c5d52322b075cf973bd8f8c0dd56c3b609d89` |
| `apps/frontend/src/pages/BlockerDecisionReview.tsx` | `da0cd260fd4e1a6b8f49ea65f8eeffc6eabfefeb60c1b971130fdedf925f424d` | `964cca76c6d6e502f631d9cc19cb6539fdaaac78` |
| `apps/frontend/src/pages/CaseStatePanels.test.tsx` | `dff2eb9f817ce7dc5e40c11b44fa6b08ce3c0be0b5146a0fdb73c49880fe0603` | `5f46f2c711c971b3ac0e581f13d3bee32be2d9b4` |
| `apps/frontend/src/pages/CaseStatePanels.tsx` | `6dfeeea0e97aded5f608e923e31545f33578fca139e6780f28aa6ee7cb41251c` | `4cd87828bb91ae3ac0e5a7a6f2ae301a513976a3` |
| `apps/frontend/src/pages/ManualOwnershipEvidenceForm.test.tsx` | `a55f2e4388213dbb0ff2a0f1d1314f5e422cfeb1d3a4df378f1c7645208f771d` | `f93f108687456b9eb097f7a6258cf653d71d0177` |
| `apps/frontend/src/pages/ManualOwnershipEvidenceForm.tsx` | `80cbd3dddf11fdd761bd99505e14b488fd33e7072f75c63dfcbbd95562dfd422` | `582403aab5ed62db283c077e5f2de08da7d8efd9` |
| `apps/frontend/src/pages/RegistryProvenancePanel.test.tsx` | `063a01cf2d11dcf1a8ddbc4357c07d13c0ada6ea2b091c9ce6c1535576d559d3` | `1968d2d9e0ece6c31f826c12e05396f9293946f0` |
| `apps/frontend/src/pages/RegistryProvenancePanel.tsx` | `c31b5460035414ebe1ca7c1ae878a2933fa74143645cacd3bca4e73ecf82d566` | `9b32cca89ac706947ad29c1735c0a4e03ec4fc6f` |
| `apps/frontend/src/pages/S2OwnershipReview.test.tsx` | `e7591917a6fc5bebc3c1ad47cd60ca187cf3d5ae1bc9103d14db35d2d8d35bd2` | `57b11123e86686726b1f153fa48e35e48324ca74` |
| `apps/frontend/src/shared.ts` | `dd6913ca2f3ce219a235513b80f451d98487836012d1dcfc3928c7eb46aed691` | `f71f31c5cbf6152434d976861e8413e01c37137c` |
| `docs/integration/AM_WAVE1_REVIEW_DATES.md` | `b163a2e753528af21c2a78607aef513bfc9aeb0fd1991d910dfc60372aa46a5e` | `6ebec159d63d66195eef53403c75813db5565ae8` |
