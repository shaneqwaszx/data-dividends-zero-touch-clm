# Blocker resolution - independent final Quality Gate, review 1

## Executive result and findings first

**PASS WITH MINOR FIXES. P0=0, P1=0, P2=1.** The three primary outcomes and the
required local behavior/safety evidence are verified. One bounded presentation
correction remains under the owner's compact-workspace requirement. This is not
exact PASS and is not eligible for publication review as accepted content.

**BR-QG-01 [P2, required] - repeated generic intervention warnings still dominate the grouped workspace.**
`apps/frontend/src/pages/HumanInterventionPanel.tsx:51` renders one full card per
intervention, and `:105` repeats each generic explanation. The new `:36-55` logic
only deduplicates evidence-action buttons. On the actual four-field review workload,
four cards each say `Document or reconciliation review required` and `Document
evidence is not currently usable for deterministic reconciliation.` The frozen real
browser screenshot `BLOCKER_REVIEW_BROWSER_EVIDENCE/candidate-after-action-focus.png`
shows these identical large cards above the decision workspace. A fresh independent
actual-owner API probe also returns four DOCUMENT interventions, with one title and
one reason repeated four times, and zero target mutations. This is reproducible
presentation drift, not a security, contract, persistence or business-rule defect.

The owner section 10 requires compact reasons, a clear decision list, less scrolling
and avoidance of repeated warnings. The current presentation leaves that bounded
criterion incomplete even though action navigation reaches a real control. Required
correction: consolidate identical summary warnings in the existing intervention/view
owner while preserving the distinct backend exception IDs, per-field/document
reasons, technical details, current allowed actions, unavailable-action reasons and
history. Do not alter backend policy, merge different authorities or discard factual
evidence. Verify one compact visible reason/count with every individual detail/action
retained; exercise a four-field browser case, focus/navigation, isolation and affected
frontend regression. Re-freeze and obtain fresh independent review. Classification:
**Implementation Drift; scope: requirements**. No architecture defect is established.

No other required defect was found in the inspected scope. Residual limitations and
unexecuted external/publication lanes are recorded separately below.

## Scope, authority and frozen identity

This is the explicitly assigned 2026-10-10 overnight blocker-resolution and intelligent
IDP optimization package, not a new numbered phase. The fresh reviewer made no
implementation, test, configuration, ordinary documentation or evidence correction.
The sole durable write is this assigned gate report. Ignored review-owned temporary
caches/build output were used where needed; browser receipt writers were not rerun.

- Worktree: `C:/Users/shane/.codex-clean2/worktrees/blocker-resolution-idp-ux/data-dividends-zero-touch-clm`.
- Branch: `feat/blocker-resolution-idp-ux-optimization`; review scope: working-tree.
- BASE_SHA, HEAD, origin/main, merge base and independently queried remote main:
  `e799d74063678bb0eccbea445d5ab3c8628dd2c0`; committed ahead/behind 0/0.
- Candidate: intentionally uncommitted `WORKTREE`, with staged content empty.
- Complete reviewed set: 136 paths in `BLOCKER_REVIEW_CANDIDATE_MANIFEST.json`, including
  all changed/new product, test, tooling, documentation, fixture and evidence files.
  Independently compared against tracked diff and nonignored task-owned new paths.
  Only the manifest itself, this report and later delivery derivatives are outside its
  self-hash set; there is no product/source/test exclusion.
- Exact reviewed content SHA256:
  `db2c9d916c0cb2f8210965e31f0bc3cfe0121a6e06046ddd49d5d6b5412f3709`.
  Method: exact-byte per-file hashes/lengths; SHA256 of path-sorted entries encoded as
  UTF-8 JSON with sorted keys and comma/colon separators.
- Tracked binary diff SHA256:
  `cb497c95ad4e1e634c0787a64f70beb59c7d2476924dd7fe8da4011b096b59d9`.
- Every exact byte/hash, aggregate identity and diff hash matched independently at
  review start and immediately before report write. Executed source/CI hashes in
  `BLOCKER_REVIEW_VERIFICATION.json` independently match this frozen candidate.

Requirements/product baseline: the full attached owner request, AGENTS.md, current
contracts/decisions including D-070, explicit non-goals and unresolved questions.
Architecture baseline: ARCHITECTURE.md/PROJECT_STATE.md, current service/port/repository
owners and ADR-011/D-071. The context selector ran with separate arguments for
FRONTEND_UI, FRONTEND_STATE_CACHE, BACKEND_DOMAIN, BACKEND_API, AUTH_RBAC_SECURITY,
PERSISTENCE, EXTERNAL_PROVIDER, ARCHITECTURE_REFACTOR and CI_TOOLING. Tier 1, relevant
source/tests/contracts, sponsor questions and nearest accepted company-pack/classification
gates were inspected. Applied fyp-quality-gate/report template, the canonical Aegis
code-reviewer reference, integration-security, cache/persistence/architecture/provider
and accepted POC regression workflows. Prior verdicts were not transferred to this tree.

## Acceptance checklist

| Requirement | Independent assessment and evidence |
|---|---|
| Actual Orion CRLF defect reproduced and fixed at existing owner | PASS. Exact owner PDF hash unchanged before/after; baseline parser source from e799d74/native worker returns one page, 11 CRLF separators and zero labels. Current worker returns Company - Private / Corporate, page 1, PAGE_1_LINE_10/11, NATIVE_PDF_TEXT, score 0.97. |
| LF/CRLF/CR, actual PDF/DOCX/TXT and local OCR; unsafe/partial/conflict handling | PASS. Fresh 21 parser/media and 36 OCR checks, plus current classification authority/test inspection. No wrapped/unsupported value inference or filename exception. |
| Supported GoldTier input inventory and trustworthy automatic binding | PASS. Current mapper/document/classification/CLM owners and the IDP inventory inspected. Closed automatic KYC values and explicit segment, compatibility, identity/currentness and evidence score remain required. DOCUMENT selections bind through existing owners; no dictionary-driven extra mapping. |
| Four company documents and unchanged canonical/ownership seeds | PASS. Current bytes regenerated through existing generator; independent native worker sees four identity values and two classification labels in all four, with no ownership observations. Four-company API/physical/browser evidence retains exact seed/Decimal graphs and zero Marketplace requests. |
| Immediate local choice/change/clear/save and safe draft lifetime | PASS. Pure local draft component, version/actor/case-scoped remount key and session-generation owner inspected. Fresh full frontend tests include local zero-request, changed-evidence, route/session, late-response, 401 and isolation behavior. Save is explicitly tab-only. |
| Genuine one-family bounded group confirmation | PASS. One POST; strict extra/duplicate/version/fingerprint/action validation. Fresh 16 API tests and real browser duplicate-click/confirmation behavior pass. One four-GET supporting refresh; no hidden per-field request. |
| Whole-group prevalidation, coherent checkpoint recovery and at-most-once continuation | PASS within stated single-process scope. Fresh API failure/concurrency probes and four zero-skip physical restart tests. All documents prepare before first write; one save per document; one source UoW; retained source/automation failure repairs by explicit Resume; no target mutation repairs review. |
| Final Review & Send stays separate; unrelated blockers remain | PASS. Fresh group tests retain low/missing evidence, target calls unchanged; source groups stop at TARGET_CONFIRMATION_REQUIRED. Independent real browser lifecycle performs separate final confirmation and preserves no-replay/history after reload. |
| Actual authorized control navigation, disclosure/layout/focus/scroll | PASS. Complete CaseDetail/StageDisclosure/pipeline wiring inspected; full 571 frontend tests, actual focus receipts and one fresh authenticated lifecycle. Enabled current controls, delayed GET/stale generation guards, nested details and reduced motion are covered. Unavailable correction remains explained. |
| Small compact blocker workspace without repeated generic warnings | REQUIRED MINOR FIX: BR-QG-01. Four identical full intervention summaries remain above choices. Counts, draft status and primary confirmation exist, but unnecessary repeated summary cards violate the bounded presentation criterion. |
| Complete catalogue and requested browser simulation families | PASS for supported bounded fixtures. Exact serialized current catalogue equals the saved 62-code/27-family inventory. Requested 30-family matrix and all 18 added receipts inspected. Navigation-only, processing, unavailable/rare aliases and unsupported sponsor actions are explicitly distinguished; no fabricated GET acceptance or provider success. |
| Comparable before/after evidence | PASS. Recomputed browser 30 groups/120 choices per revision, all request counts, medians and p95s from individual receipts. Browser/API/Mongo are separate workloads. Mongo counts have n=1 and are not a distribution. |
| Affected regressions, lint/types/build, hygiene and truthful classifications | PASS for executed local candidate lanes; supplied broad results are separately attributed below. Candidate remote CI/external UAT/publication are not executed or claimed. |

## Fresh independent execution

Python used the task-owned Python 3.12 runtime with -B/PYTHONDONTWRITEBYTECODE=1 and
explicit task/root/backend/test-helper paths. Tesseract was available on PATH and
CLM_REAL_OCR_REQUIRED=1. Node 22.23.3/npm 10.9.9 and pinned frontend packages were
observed. Heavy runtime lanes ran sequentially. Physical tests used only the owned
loopback Mongo 7 server, newly generated allowlisted disposable names and existing
cleanup helpers, including asserted database absence. No URI was printed or persisted.

| Executed check | Fresh result |
|---|---|
| pytest: test_batch_review_decisions, test_idp_classification_line_endings, test_s2_local_ocr; -o addopts= -p no:cacheprovider -q --tb=short | 73 passed / 0 skipped, 34.76s: group/API 16, parser/media 21, OCR 36. |
| pytest: test_batch_review_real_mongo with guarded private environment | 4 passed / 0 skipped, 12.99s; ordinary receipt restart, interrupted document section repair and both canonical/source checkpoint cases. |
| npm test -- --cache false | 48 files / 571 tests passed, 7.45s. |
| Configured backend Ruff scope: python -B -m ruff check --no-cache ., cwd apps/backend | PASS. |
| mypy --config-file apps/backend/pyproject.toml --cache-dir tmp/independent-blocker-review-mypy apps/backend/app | PASS, 127 source files. |
| Both configured TypeScript projects, with only tsBuildInfoFile redirected into ignored tmp | PASS. |
| Pinned Vite production build, only outDir redirected into ignored tmp | PASS, 136 modules. |
| unittest tests.test_run_e2e tests.test_check_tooling_config -q | 58 passed: scheduler 47 and inventory 11. Negative injected failure text is expected test output; suite exit 0. |
| run_e2e.py --backend-port 18990 --frontend-port 19490 --timeout-seconds 60 --grep 'current document review progresses authoritatively and keeps superseded history read-only' | 1 real authenticated guarded browser lifecycle passed, 7.7s; grouped one POST despite double click, current replacement, historical read-only controls, explicit final send, reload/no automatic Resume. No frozen receipt/screenshot writer used. |
| Read-only exact owner PDF baseline/current worker and current four owned PDFs | PASS: 0 -> 2 labels on unchanged owner bytes; all four current PDFs have four identity values/two classification labels/no ownership observations. |
| Actual-owner four-low-confidence intervention probe | Reproduces BR-QG-01: four identical titles/reasons and zero target mutations. |
| check_project_state, check_architecture, check_tooling_config, check_policy_authority, check_external_provider_readiness, check_secrets | All PASS. |
| git diff --check plus explicit scan_file/UTF-8/trailing-whitespace review over all frozen paths and manifest | PASS; zero supported secret-pattern or whitespace findings. Binary content also inspected through fixture/source/evidence review; pattern scan is not universal secret assurance. |
| Current catalogue serialization, 18 simulation receipts, execution hashes, full path-set and browser receipt arithmetic | PASS: 62 codes/27 families, 18 PASS receipts, all zero pre-confirm calls; current executed source/CI hashes match. |
| git ls-remote origin refs/heads/main | e799d74063678bb0eccbea445d5ab3c8628dd2c0, unchanged. |

First reviewer harness/setup errors were retained and corrected without candidate edits:
the initial Ruff command used an incorrect relative Python path; an initial catalogue
comparison incorrectly compared dataclass/tuple objects directly with JSON. The actual
dataclass serialization was inspected and exact JSON equality then passed. These are
review-command defects, not product failures. Incidental read commands naming nonexistent
paths were replaced by bounded current-file discovery. No acceptance assertion, timeout
or reviewed file was changed. Inherited Starlette/httpx deprecation, React SSR
useLayoutEffect/act test warnings and the existing build chunk-size warning remain;
none is reported as a suppressed test failure.

## Broader execution evidence, separately attributed

The coordinator's final logs/receipts were inspected; these are not presented as new
reviewer full-backend/root/full-browser executions. Their recorded execution hashes
match the reviewed product and tooling bytes.

- Full backend: 2753 collected = 2617 passed + 136 conditional physical-only skips;
  four inherited warnings, 956.41s. Skips are not passes. The physical lane separately
  executed all 21 suites / 136 tests with 0 skipped, failed or errored.
- Full frontend: 48 files / 571 tests, typecheck/build. Fresh reviewer execution above
  independently confirms that lane.
- Full root: 373 tests / 0 skips, including real Windows demo start/stop/reset lifecycle.
  The printed injected E2E failure belongs to the negative scheduler test; unittest is OK.
- Unfiltered product browser: 81 isolated selectors / 104 tests with unchanged 60-second
  lifecycle deadline. Current CI shard executions are 41 and 40 disjoint selectors,
  union 81 / 104 tests, both PASS. All original 50 product/test/tooling byte hashes are
  retained in the execution receipt; current scheduler/workflow files are separately hashed.
- Configured Ruff/mypy/dependency/contract/security/governance and hygiene evidence PASS.
  The reviewer independently reran the changed focus and checkers above rather than
  treating authored tests or prior PASS as sufficient.

The implementation record preserves the first broad backend local HTTP timeout,
missing task-runtime/helper/psutil setup failures, outdated 73-selector budget
assertion, test-helper response deadlock and initial missing native-worker import path.
The final complete reruns passed. No timeout increase, test exclusion, weaker currentness
or fabricated success repaired those failures. Candidate GitHub CI has not run.
The baseline PR80 seven-job run37954652603 success is coordinator-observed baseline
history, not candidate CI evidence or a newly queried reviewer GitHub observation.

## Contract, architecture, security and adversarial assessment

Source DTO -> validated document/canonical evidence -> existing target mapping remains
intact. Local normalization changes separators only; original field values, page/line,
method and scores remain separate. D-070's Company - Private, Partnership - Unregulated
and Government automatic vocabulary/compatibility/currentness rules remain. Segment is
explicit; Government does not establish control or legal UBO. No new ANZSIC/SSIC,
controller/risk/approval/child-ID/relationship mapping or frontier-model API appears.
Quarantined sponsor examples and all broader sponsor questions remain unresolved.

Existence/ownership check: the existing DocumentProcessingService owns preparation and
retention, ReconciliationService its single canonical/source UoW, ZeroTouchOrchestrator
review/continuation, the case repository lock/CAS, and the target ledger dispatch and
no replay. The focused domain request module and frontend draft component are bounded
models/presentation; they do not create new business, persistence, auth or workflow
owners. ADR-011 truthfully describes section checkpoints and explicit Resume rather
than cross-owner atomicity. Source UoW success followed by automation failure is
independently exercised in memory and physical restart; a legal-name change requires
read-only Search before later readiness. Partial document retention does not advance.

New route is exactly inventoried as case-scoped. Current session/team/creator/CSRF and
capability gates precede source validation; in-lock reauthorization precedes all writes.
Whole-group duplicate/extra/action/version/fingerprint checks fail closed. Source and
field decisions retain distinct semantics; no universal source precedence. Changed
notes/values cannot replace retained receipts even when event type/time is identical.
Concurrent confirmation produces one accepted mutation plus one conflict without
extra receipts. Frozen target confirmation/snapshot/result/attempts reject review.
Safe messages contain no document bodies, raw external payloads or private exceptions.

AuthProvider's session generation remount and existing QueryClient cancellation/clear
remain authoritative. Drafts stay in tab memory and reset across actor/case/evidence
changes; no browser persistence or new query-cache authority was introduced. Late old
route/session evidence cannot publish into current scope; refresh error locks mutations.
Browser authorization is explanatory only. Existing update-only/create-only semantics,
strict identity/revision CAS, schema10/historical1..9 decode and deletion anti-resurrection
owners are unchanged. Physical restart supplements that inspection.

CI adds disjoint scheduling through the existing runner. The required e2e aggregate
uses always() and accepts only a successful e2e-shards result; cancellation/failure/skip
cannot satisfy it. Both shards remain fail-fast=false with unchanged 60s execution,
120s overhead, 60s discovery and 234-minute job deadline. No selector is removed.
Fresh 58 scheduler/inventory tests and actual two-shard logs substantiate local behavior;
remote workflow execution remains unverified until authorized publication.

Strengths: whole-group prevalidation before writes, exact receipt conflict protection,
truthful resumable failures, genuinely local drafts, actual-control focus guards and
separate final target confirmation. No required security, contract, architecture or
false-success finding remains beyond the stated presentation issue.

## Residual limits, retirement and readiness

These are accepted scope limits, not BR-QG-01 substitutes: drafts do not survive route
leave/refresh; case locks are in-process; no cross-owner transaction or multi-process
exactly-once guarantee; Government classification is not legal/control UBO; the old
standalone field-review API is retained for actual compatibility and explicit checkpoint
repair. Its retirement needs a separately assigned consumer audit. Existing large
CaseDetail/orchestrator owners remain a structural follow-up, not a new competing owner.

Browser evidence covers supported current families, not every transient/corrupt catalogue
alias. Unsupported correction, related-party child lifecycle, hierarchy, regulatory/
GoldTier approval, sponsor policies, Production/PingFed and Live interoperability remain
outside the verified claim. No real external ACRA/GoldTier/Sandbox write UAT ran here.
No protected database/private dotenv/original checkout/owner PDF was modified or inspected
beyond the explicitly authorized read-only owner PDF. No new external credential or call
was required. Temporary task resources do not prove provider approval.

**Required fixes: BR-QG-01 only.** Advisory readiness is for bounded remediation and
fresh independent re-review. Exact PASS and unchanged reviewed content are required
before STOP FOR OWNER PUBLICATION REVIEW. This gate does not establish merge,
production, external-integration or next-phase readiness. The intentionally uncommitted
publication gate pre_pr_check was correctly not run. No staging, commit, push, PR, merge,
new phase or real external write occurred or is authorized by this verdict.

## Change-class disclosures

| Surface | Reviewed disclosure |
|---|---|
| API/type | Changed: strict grouped review POST and derived document source fingerprint. |
| Durable schema/migration | Unchanged: schema10 and strict read-only historical1..9 support. |
| Persistence | Grouped document section saves/source UoW/checkpoint ordering changed through existing owners/CAS; no new repository or transaction claim. |
| Connector | Local IDP parser line-ending normalization changed; external HTTP/auth/TLS contracts unchanged. |
| Configuration/dependencies | Production settings/locks/dependencies unchanged; CI scheduling changed; ignored local test-runtime provisioning is separately disclosed. |
| Business rules | Review application changed; existing policy/UBO/source-authority rules unchanged. |
| Mapping/vocabulary | Unchanged existing mapping and explicit approved vocabulary. |
| Auth/security | New route applies existing creator/team/CSRF/in-lock boundaries; no role/capability grant. |
| Architecture | Existing owners and dependency direction retained; ADR-011 records the checkpoint decision. |
| Provider status | Local/Mock/offline protocol evidence remains; no Live or new real Sandbox interoperability claim. |
| Runtime/UI | Local drafts, grouped confirm, actual-control navigation, reliable classification extraction changed. |
| CI/tooling | Runner/physical suite inventory and two exact-coverage browser shards changed; deadlines/tests retained. |

## Evidence/report hashes and closeout

All four deliverable reports, verification receipts, screenshots, fixtures and source
bytes are covered by the complete136-path manifest. This reviewer report's own byte
hash is supplied in the coordinator handoff, rather than a self-referential embedded hash.

| Evidence | Exact SHA256 |
|---|---|
| BLOCKER_REVIEW_CANDIDATE_MANIFEST.json | `abdea5f409034bc78c6db55d7f08ce24ee5a507aefc4effd1bb2cb661e07da01` |
| BLOCKER_RESOLUTION_OPTIMIZATION_IMPLEMENTATION.md | `98d9ebe89510cd38a0d2f91966c6f0c9b7aa9a50dfa490d454189b71a0f2d8c5` |
| BLOCKER_RESOLUTION_SIMULATION_MATRIX.md | `cf6f47f9d79817ac01d76e3db1464d1086043f101a910e428c1dae5acab35d73` |
| BLOCKER_RESOLUTION_PERFORMANCE_BEFORE_AFTER.md | `1de7e22711802acc688958ce2e2fc466d86d4eda44c9d8803051d3e8f7c58590` |
| IDP_CLASSIFICATION_EXTRACTION_VERIFICATION.md | `2d757faeb03f131559069e09d12a2ac6859a05222c0a4abbeca697315e86e931` |
| BLOCKER_REVIEW_VERIFICATION.json | `1540647263a81ff8bcbd7c48b45e03f506b80c5c19c4dc87c007efbea60d9077` |
| BLOCKER_REVIEW_STATIC_VERIFICATION.json | `5be1b13c1d7adb86f16caa29a98afb9aedb92a6a0fe69717306e2a71c54da8b2` |
