# Three frontend UX corrections — independent Round 1 Quality Gate

## Executive result

**PASS.** All three assigned UX corrections are verified on frozen content `316d753357ec2ac2de46014662868c6cb14590e4b10c902bf11117c45bd6759d`. Both Round 0 product findings are corrected and independently reproduced as passing in Chromium. The complete final guarded pair passes independent reconciliation: **107 selectors, 136 actual Chromium records, 13 required disposable-fixture cleanup receipts**. No required correction remains for this bounded UX scope.

This accepts the reviewed implementation and automated verification for planner review. It is not owner manual-rehearsal acceptance, publication authorization, PR readiness, a next-phase instruction or Live-integration approval. The existing KYC shortcut finding remains OPEN; the historical and newly observed intermittent summary HTTP500 cause remains UNKNOWN/OPEN.

Reviewer: `/root/ux_independent_gate`, independent of implementation and remediation. Coordinator owns source/Git changes. Round 0 report is preserved byte-for-byte. One of the human-authorized maximum two bounded correction/re-gate rounds has been used.

## Reviewed identity and authority

Worktree: `C:/Users/shane/.codex-clean2/worktrees/am-ux-accordion-ownership-cleanup/data-dividends-zero-touch-clm`.
Branch: `codex/am-ux-accordion-ownership-cleanup`.
BASE_SHA / HEAD / inspected local origin/main: `151802e0cfe02d5164ff6819c3e3dd7c85b05f1d`.
HEAD tree: `0d7b98d6863bfe6361937625110d86b7c912af62`.
Reviewed content: HEAD plus exactly twenty unstaged tracked paths in `freeze.json`; index empty. This is intentionally uncommitted content, distinct from eventual staged/stored Git objects.

The reviewer read the exact OWNER_REQUEST.txt, root/frontend guidance, Quality Gate skill/report guidance, selected FRONTEND_UI and DOCS_ONLY context and Tier 1 authorities, current presentation owners/tests, disclosure integration documents, preceding accepted gates, full initial diff and bounded Round 1 source/test/doc remediation. Current owner requirements supersede historical permanent-Main behavior. No backend or sponsor-controlled rule is inferred.

Every raw SHA256 and explicit Git-filtered hash matched independently at Round 1 entry and before issuance. Compact sorted JSON of the complete path/hash map reproduced the aggregate above. All changed paths equal the manifest set; HEAD/origin-main remain unchanged. Evidence: `qg-r1/entry-freeze.json`, `qg-r1/final-freeze-check.json`. The prior report SHA256 remains `b6fb82edb79bb3d0618c799d82395b359243e579eeb867f253832b63f37e5325`.

## Acceptance checklist

| Owner requirement | Independent assessment and evidence |
|---|---|
| A — Search, Registry, Documents, Ownership, readiness, package, Final visual order; separate history | PASS. Exact real-case browser DOM order and current screenshot; the original Search/Registry blocks are moved without changing backend orchestration. History stays separate before Final. |
| A — Identity form, IDs, authority, rationale, source distinctions and focus anchors | PASS. Existing predicates/handlers/anchors retained; one identity form. Existing Search/Registry tests and independently run ordinary-RM browser workflow preserve actual correction controls and focus. |
| B1–3 — Seven independent accessible parent toggles and retained More/Technical | PASS. Existing StageDisclosure owns a native button with meaningful title, aria-expanded, valid controlled IDs and current status description. Native Enter/Space/Tab, visible outline and contrast pass. Supports remain independent inside the parent. |
| B4 — Actionable stage initially expanded | PASS. Current opt-in callers initially expand all business stages, including the actionable one. Completed-stage initial collapse was optional in the owner request. Legacy child composition remains compatible. |
| B5 — Operator can collapse active stage; visible required-action meaning | PASS. Main/support content hides while heading/status stays visible. Current intervention ownership and exceptions both project attention, including projection-only, disabled and no-action cases. Actual Chromium re-verification closes QG-02. |
| B6 — Harmless GET/active updates do not reopen manual collapse | PASS. Parent state initializes per scope; same-scope refresh does not overwrite it. Owning units and native foundation fixture verify refresh/draft/focus behavior. |
| B7 — Action/attention/pipeline navigation opens owner before real control focus | PASS. Existing revealStage and PR87 focus-intent guards retained; presentation toggle excluded from corrective-control search. Independent ordinary-RM workflow covers collapsed Registry/classification/document/ownership edits. Canonical recovery/Final checks pass. Explicit KYC and Client-segment-only diagnostics focus the correct actual select after reopening readiness. |
| B8 — Same-scope unsaved forms and candidate/path selections survive toggles | PASS. Hidden content remains mounted. Existing integrated draft tests pass. Chromium retains selected path2 through parent collapse/reopen; graph selection remains usable. |
| B9 — Actor/case/session/incompatible analysis retirement | PASS. Existing auth/query/component identities remain owners; scoped child remount and analysis reset retire incompatible content. Full isolation/session suites pass; Chromium analysis replacement closes/unmounts old retained inspection. |
| B10 — No hidden keyboard focus | PASS. Parent closure and restored collapsed print state return focus to visible toggle; native support closure returns focus to summary. Existing external/newer focus protections and six actual ownership race cases pass. |
| B11–12 — Complete Final request/appendix and exact print-state restoration | PASS. Foundation browser verifies all eight parent/More/Technical combinations, real print media and focus restoration. Final AM18 canonical assertions retain the complete field/value preview, single Send, notes/audit content, print exclusions and exact eight-state restoration. |
| B13 — Responsive widths, zoom and narrow ownership | PASS. Actual stage fixture covers1440/1280/900/360; complete canonical responsive/zoom/narrow ownership coverage passes. No overflow or clipped required-control assertion fails. |
| B14 — Disclosure/inspection performs no business mutation | PASS. Actual browser request counters remain empty during inspection/navigation; toggles call only existing local presentation setters. No implicit Send/replay/confirmation is introduced. |
| C — Direct60/40 and50/30/20 deduplication; graph/Selected holder switching | PASS. Owning tests cover both graphs and source/calculation updates. Actual direct case and final screenshot retain graph/Selected holder while removing the lower candidate summary, long raw path heading and redundant one-row table. |
| C — Complex/indirect paths, pagination, same-holder occurrences | PASS. Single explorer retains candidate/path/page state; optional technical inspection is lazy and paginated at20 rows. Both actual graph occurrences preserve open multipath content and allow Inspect path2. QG-01 closed. |
| C — Exact Decimal/provenance, warnings and lazy large-path DOM | PASS. Existing backend values/formatting and exact Technical projection unchanged. Full unit suite retains tiny scientific/Decimal, cycle/incomplete/partial, source-label and5000-path closed-Technical safeguards; selected path visual remains bounded. |
| Scope, docs, regressions and rehearsal preservation | PASS. Twenty tracked files are frontend presentation/tests plus existing integration prose. No protected source/fixture/dependency change. Complete final pair passes, current screenshots are bound to reviewed content, and normal ports/PIDs remain unchanged. |

## Round 0 findings and correction verification

- **QG-01 closed for this freeze.** Same candidate/another occurrence no longer clears the lazy-content flag while the native disclosure stays open. Actual Chromium shows two retained rows after each occurrence is selected, Inspect path2 remains pressed/usable, parent collapse/reopen retains it, and analysis replacement closes/unmounts incompatible inspection. `qg-r1/reselect-browser.json` records each state.
- **QG-02 closed for this freeze.** Existing CaseDetail presentation helper checks current intervention owning_stage as well as active exceptions. Actual eligible and disabled projection-only Registry cases retain Attention required while Main is hidden; a no-action READINESS projection also retains attention. No capability is granted. One identity form, unique IDs, zero errors and zero business writes are verified in `qg-r1/header-browser.json`.
- **QG-03 closed as a scoped selector correction and required evidence completion.** Phase24's existing unavailable-Final assertion now selects intended Main content; its substantive visibility/absence assertions remain. Parent focused native1/1 passes, and the complete final pair includes it. No deadline, retry, fixture or assertion was removed/weakened.

The independent KYC/Client segment diagnostic uses existing backend-shaped retained classification projections. With both unresolved it focuses KYC; with KYC selected and only segment missing it focuses Client segment. In both cases collapsed readiness reopens, the actual enabled SELECT is focused, supports stay closed, and writes/errors remain empty. Receipt: `qg-r1/classification-focus-browser.json`. This does **not** close the separate earlier owner-observed KYC focus-shortcut issue.

## Independent execution

All results below exercise this exact frozen candidate; final raw/filtered hashes remain unchanged.

- `npm test`: **820 tests /54 files passed**, native0. `qg-r1/full-unit.log`.
- `npm run typecheck`: PASS, native0. `qg-r1/typecheck.log`.
- `npm run build`: PASS, native0. `qg-r1/build.log`. Existing React act warnings and Vite large-chunk advisory remain recorded.
- Six read-only scripts: `check_project_state.py`, `check_architecture.py`, `check_tooling_config.py`, `check_policy_authority.py`, `check_external_provider_readiness.py`, `check_secrets.py`: all native0. `qg-r1/governance.json` and named logs.
- Fresh installed Playwright discovery: **107 encountered selectors /136 actual records**, configured Chromium and retries0. Ordered inventory matches current owned discovery. `qg-r1/discovery.json`, `qg-r1/inventory.json`.
- Official isolated browser foundation plus real case disclosure: **2/2 passed**, native0. `qg-r1/focused-browser.log`.
- Official six ownership focus-intent cases, keyboard/pointer/none at queued-return/nested-handoff timings, using isolated Garden protocol: **6/6 passed**, native0. `qg-r1/ownership-intent-browser.log`.
- Official ordinary-RM correction/review workflow: **1/1 passed**, native0. `qg-r1/corrective-navigation-browser-final.log`.
- Additional actual-component Chromium diagnostics reproduce repaired ownership/header states and both classification-focus branches; these are separate focused evidence, not extra canonical inventory records.

Official reviewer browser commands use installed Python, `scripts/run_e2e.py`, backend24475/frontend23473, original `--timeout-seconds 60`, zero configured retries, process-local Tesseract PATH and task-owned synthetic Mongo27326. The canonical pair is retained coordinator execution, independently audited rather than run concurrently by the reviewer. Parent current governance-unit88 and runner/Slice-B/Slice-C workflow48 tests pass on the same freeze; exact receipts are in remediation-r1-governance-results.json. Strict RED/GREEN evidence is retained: initial10 failed/132 passed before the original production changes; Round1 four new failing assertions/124 passed before correction, then175/4 focused GREEN. Independent full820 suite includes those assertions.

## Complete canonical campaign audit

Independent `qg-r1/canonical-audit.json` recomputes expected ordered partitions from fresh discovery, compares each native Running/passed record count with its selector's discovered multiplicity, checks each guarded native result, verifies original60-second contract, and derives cleanup requirements from current fixture tags and runner source. It verifies disjoint/exhaustive coverage, per-lifecycle cleanup, native exit0/hash/freeze provenance and sequential timestamps in campaign-results.json.

| Final shard | Selectors | Actual passing Chromium records | Required cleanup receipts | Maximum lifecycle including cleanup | Log SHA256 |
|---|---:|---:|---:|---:|---|
|1/2|54/54|77/77|7/7|52.579s|`9cfad251a6e91e982e1bf0f1f9a17d8ec4f45f7127a45d2bcf9d45045acfa447`|
|2/2|53/53|59/59|6/6|55.125s|`33b858b3738611ea6ed1f91fa182a597809289e877015cecceb85dd03c4e8c48`|

Disjoint union:107/107 selectors and136/136 records. All13 required classification/seed/sponsor disposable cleanup receipts occur in exactly the expected lifecycle blocks. No failed, skipped, flaky, interrupted or undispatched final record remains; retries0 and60-second lifecycle deadline are unchanged. Runner source emits guarded PASS only after owned process cleanup succeeds. The reviewer did not connect to or clean a physical database.

## Preserved failures, residuals and limits

Prior unsuccessful runs remain failures and are not counted as final passing coverage:

- Round0 canonical selector23 duplicate-text failure is retained separately; the scoped Phase24 correction addresses it.
- The first Round1 canonical attempt fails at45/54 on summary GET500, text/plain, zero bytes, UNTYPED_RESPONSE during missing-field replacement confirmation, after44 passing selectors/63 records. Exact independent receipt/log: `qg-r1/first-campaign-failure.json` and `.log`; raw SHA256 `793e2612154d6e927179683cb5d6d9fafd6fc9ebbfcbbcd4ef2bd10ea6060468`. Its cause is **UNKNOWN/OPEN**. No speculative backend correction was made. An unchanged-source focused reproduction passes1/1, then the complete pair was restarted from the beginning and passes above. These later passes establish current execution coverage, not causal resolution or production reliability. No automatic test retry was added.
- Extra Windows default-port smoke had21 setup failures while protected rehearsal8000 was occupied. Startup/process ownership is unchanged; this extra unavailable lane is not treated as PASS and did not justify touching rehearsal. Applicable workflow48 passes separately.
- An anchored reviewer grep found no tests; it provides zero evidence. The corrected existing-title grep passes1/1. An initial combined component diagnostic failed a final aggregate assertion over immediate snapshots and did not retain the exact failing step; it is not acceptance evidence. Separate awaited per-state diagnostics pass and are retained. No source changed in response. Node receipt write was permission-denied; the normal authorized escalated shell saved the diagnostic. A delayed read-only shell completed normally without process termination.

The prior KYC shortcut remains **OPEN**. Historical/current intermittent summary/ownership HTTP500 causes remain **UNKNOWN/OPEN**. These explicit preserved investigation boundaries must accompany handoff; this scoped UI gate does not certify those issues fixed. No new sponsor decision or Live/prod/approval capability is claimed.

## Architecture, contract and security review

Existing owners remain authoritative: CaseDetail composes and performs guarded navigation; StageDisclosure owns local parent/support presentation; OwnershipPathExplorer owns candidate/path/page selection; OwnershipStructure retains its existing graph occurrence state. No second explorer, accordion framework, calculation engine, mutation form, cache/session owner or provider/authorization authority is introduced. Complex retained inspection stays optional/lazy; single direct inspection stays in the graph's Selected holder panel. Exact backend arithmetic, evidence values, classifications and provenance remain unchanged.

No new unsafe rendering, browser persistence, raw provider/credential projection, secret/confidential artifact, auth bypass, target-ledger bypass, replay or implicit business mutation was found in the full reviewed diff. Existing backend capability/role/identity and sensitive-action handlers remain. Mock/Local/provisional labels remain explicit. No full backend/physical-persistence certification is inferred from this frontend change or its fixture databases.

| Surface | Changed? |
|---|---|
|API/shared DTO/type contract|No; existing component-local presentation behavior only.|
|Durable schema/persistence semantics|No.|
|Connectors/provider transport/composition|No.|
|Configuration, dependencies, lockfiles, fixtures, runner or CI|No.|
|Business rules, Decimal arithmetic, thresholds, source precedence or mapping|No.|
|Backend auth/RBAC/security authority or frontend shared query/cache/session ownership|No.|
|Architecture owner/dependency direction|No.|
|Provider classifications or Live claims|No.|
|Frontend runtime rendering/order/disclosure/local focus wiring|Yes.|
|Existing integration documentation|Yes; current correction notes preserve historical provenance.|

`git diff --check` and explicit whitespace inspection of all twenty frozen paths plus task-owned Markdown pass. No newly tracked secret/confidential artifact exists. Source and staged-path inventories are exact.

## Visual evidence

The reviewer inspected `screenshots/after-r1-ownership.png` and `screenshots/after-r1-case-sections.png`, compared the direct ownership view with baseline, and independently verified all four before/after raw hashes in screenshot-binding-r1.json. Current images are bound to reviewed316d content and retained final-campaign invocations. The direct lower candidate/path duplicate is absent; graph, Selected holder, source, calculation and provisional labels remain. Search precedes Registry. These are **automated offline synthetic regression artifacts**, not normal-session manual rehearsal or human acceptance.

## Git/resource status and next authority

At issuance: twenty unstaged tracked changes equal freeze.json, index empty, HEAD/origin-main unchanged. Round0 report unchanged. The reviewer authored only this assigned report and allowed qg-r1 diagnostics/receipts; configured tests/builds also produce ignored runtime artifacts. No implementation/test/config/ordinary-doc fix, Git mutation, fetch, stage, commit, push, PR, merge, real provider action or next phase occurred during review. No .env or protected data was accessed.

Independent listener observation and root runtime-bindings.json agree: normal8000 PID39716 and5173 PID41456 remain; reviewer23473/24475 and known campaign browser ports are released. The exact task-owned Mongo container remains coordinator-owned pending post-gate verification/teardown; all individual required disposable database receipts are already verified. No normal browser/session/case interaction was performed.

**Next authorized action:** coordinator completes only task-owned runtime teardown and delta handoff, then stops for planner review. Separate owner authorization is required for publication and its latest-main/integration/clean committed pre-PR workflow. `pre_pr_check.py` is intentionally not run to certify this uncommitted handoff. Real ACRA/GoldTier readiness remains unchanged/unproved. No next product phase is authorized.

**Exact independent verdict: PASS for frozen316d content and the evidence above.**

## Complete reviewed path set

- apps/frontend/e2e/am-wave1.e2e.ts
- apps/frontend/e2e/authenticated-zero-touch.e2e.ts
- apps/frontend/e2e/phase24-identity.e2e.ts
- apps/frontend/e2e/responsive-layout.e2e.ts
- apps/frontend/e2e/s3-sandbox-submission.e2e.ts
- apps/frontend/e2e/slice-c-recovery.e2e.ts
- apps/frontend/src/EvidenceWorkbenchIsolation.test.tsx
- apps/frontend/src/pages/AM03SearchStage.test.tsx
- apps/frontend/src/pages/CaseDetail.tsx
- apps/frontend/src/pages/OwnershipPathExplorer.test.tsx
- apps/frontend/src/pages/OwnershipPathExplorer.tsx
- apps/frontend/src/pages/ReviewAndSend.tsx
- apps/frontend/src/pages/StageDisclosure.test.tsx
- apps/frontend/src/pages/StageDisclosure.tsx
- apps/frontend/src/styles.css
- docs/integration/AM_DOCUMENT_RECONCILIATION_DISCLOSURE.md
- docs/integration/AM_GOLDTIER_FINAL_REVIEW_DISCLOSURE.md
- docs/integration/AM_OWNERSHIP_READINESS_DISCLOSURE.md
- docs/integration/AM_SEARCH_REGISTRY_DISCLOSURE.md
- docs/integration/PROGRESSIVE_DISCLOSURE_FOUNDATION.md
