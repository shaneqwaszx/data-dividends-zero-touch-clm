# Frontend UX refinement - fresh independent correction gate R1

## Executive result

**PASS. Required findings: P0=0, P1=0, P2=0, P3=0.** UX-QG-01 is closed.
The corrected display-only formatter accepts the actual scientific Decimal API value,
and all thirteen owner criteria pass on the complete frozen candidate. No required fix
remains. The initial FAIL report is preserved unchanged. This verdict accepts the
bounded frontend implementation; latest-main assessment, clean committed pre-PR checks,
publication and remote CI remain separate coordinator work.

Independent review date: 2026-10-12, Asia/Singapore. The reviewer did not implement
either the feature or its one correction, and made no source, test, configuration,
ordinary-documentation or Git mutation. The sole durable write is this report.

## Reviewed identity and authority

- Worktree: `C:/Users/shane/Desktop/FYP/data-dividends-zero-touch-clm/.ux-task`.
- Branch: `feat/case-ownership-ux-quick-refinement`.
- BASE_SHA, HEAD and locally inspected `origin/main`:
  `832ff770d37c3f4710a9fd271a8fe00af3d2a407`. No fetch occurred in this review.
- Current source is an uncommitted candidate: fifteen tracked modifications, six
  task-owned new paths, no staged content. The tested and independently reviewed
  implementation is this working content, not the unchanged HEAD commit alone.
- Manifest: `tmp/ux-refinement/frozen-r1.json`, twenty-one paths, raw-byte aggregate
  SHA256 `beac09384c7f69f74da16a4061d60687c8bb7362c841e84da5f90b721ce0b26f`.
  Algorithm: SHA256 of UTF-8 compact sorted-key JSON of entries sorted by path,
  including path, classification and each raw-byte SHA256. Every hash and the exact
  tracked/untracked scope matched before review, after execution and at report closeout.
- Git-normalized path/blob aggregate SHA256:
  `8ac4e6f1aab8c042ae7c83576493a5b5129c296079615704657cc7901e230746`.
  This hashes compact sorted-key JSON of sorted `{path, blob}` entries, using read-only
  `git hash-object --path=<path> <path>` so Git's line-ending filters participate.
- Full candidate Git tree, excluding this R1 report:
  `5ae9237cdd3ae00694312449d8cd995669315cc0`. Reconstructed without writing objects
  or an index from recursive HEAD path/mode/blob entries, replaced/extended by the
  twenty-one normalized candidate blobs and standard Git tree hashing.
- This report is separately excluded from both frozen identities. Publication scope
  is the twenty-one frozen paths plus this report; adding the report changes the full
  published tree, and does not change the independently accepted implementation.

Authority inspected: complete owner's FAST-TRACK brief; root/frontend AGENTS and
backend AGENTS for the read-only domain probe; repository skill routing; quality-gate
skill/template; FRONTEND_UI dev-context and selected current workflow, architecture and
project/provider-state sections; task document; initial gate; exact owning source/tests;
and the accepted ownership root-collision recovery gate. Historical and implementer
results were not used as substitutes for fresh execution.

Complete frozen inventory:

| Classification | Paths |
|---|---|
| INTENDED | `apps/frontend/src/design-system.css`; `apps/frontend/src/ownershipDisplay.ts`; `apps/frontend/src/pages/BlockerDecisionReview.tsx`; `apps/frontend/src/pages/CaseAttentionSummary.tsx`; `apps/frontend/src/pages/CaseDetail.tsx`; `apps/frontend/src/pages/HumanInterventionPanel.tsx`; `apps/frontend/src/pages/ManualOwnershipEvidenceForm.tsx`; `apps/frontend/src/pages/OwnershipPathExplorer.tsx`; `apps/frontend/src/pages/OwnershipStructure.tsx`; `apps/frontend/src/pages/UboSummary.tsx` |
| SUPPORTING | `.ai-pipeline/reports/FRONTEND_UX_REFINEMENT_QUALITY_GATE.md`; `apps/frontend/e2e/ownership-document-streamline.e2e.ts`; `apps/frontend/e2e/s3-sandbox-submission.e2e.ts`; `apps/frontend/e2e/slice-c-recovery.e2e.ts`; `apps/frontend/e2e/ux-refinement.e2e.ts`; `apps/frontend/src/EvidenceWorkbenchIsolation.test.tsx`; `apps/frontend/src/ownershipDisplay.test.ts`; `apps/frontend/src/pages/OwnershipPathExplorer.test.tsx`; `apps/frontend/src/pages/OwnershipStructure.test.tsx`; `apps/frontend/src/pages/ReviewAndSend.test.tsx`; `docs/integration/FRONTEND_UX_REFINEMENT.md` |

## Correction, contract and adversarial review

**UX-QG-01 CLOSED.** The reviewer independently constructed five valid synthetic
parties and four existing-contract relationships: ROOT -> HOLDING `0.000001%`,
ROOT -> B `99.999999%`, HOLDING -> A `0.000001%`, HOLDING -> C `99.999999%`.
Both entity ownership totals are 100; the direct edges obey the existing six-decimal
contract. Actual domain models, source validation, graph validation, path engine,
aggregator, candidate classifier and `OwnershipAnalysisResponse.from_domain` executed.
Candidate A's indirect, aggregate and effective-path API values are `1.00E-14`;
direct interest is `0`, threshold result `NOT_MET`, classification
`BELOW_PROVISIONAL_THRESHOLD`. The retained calculation remains
`0.000001% x 0.000001% = 0.00000000000001%`.

The corrected formatter interprets mantissa digits and exponent with BigInt, without
floating-point ownership arithmetic. Its compiled production source passed twelve
independent label probes plus scientific calculation-token inspection: actual wire
value, zero mantissa with exponent, extremely small positive exponent, half-cent
boundary, two threshold-adjacent values, carry to 100%, and the owner's examples.
Actual `1.00E-14` renders `<0.01%`; actual zero renders `0%`. Component execution
checks the serialized wire shape, retained raw-record equality, calculation labels and
unchanged classifications. The formatter remains presentation-only; no new backend
calculation, contract, mapping, comparison or threshold rule is introduced.

No current contract/integration finding remains. Sponsor-controlled final rules and
Live interoperability remain outside this frontend task. Current Mock/Local/Partial
provider classifications are unchanged.

## Owner acceptance checklist

| # | Result | Direct evidence |
|---|---|---|
| 1 | PASS | Shared formatter covers hierarchy, selected holder, UBO/Final Review, retained path/calculation labels and relevant technical/history/proposal tables. Scientific wire probe, 24 formatter tests and rendering regressions pass. Editable raw declarations remain exact. |
| 2 | PASS | Raw-record equality and below-threshold value rounded to 25% regressions pass. Actual engine/API probe retains `1.00E-14`, NOT_MET and BELOW_PROVISIONAL_THRESHOLD. No backend diff. |
| 3 | PASS | Redundant candidate row is absent; native holder selection, repeated occurrences, multiple retained paths, root/unlinked selection, collapse and current-analysis refresh remain functional in component and browser execution. |
| 4 | PASS | Valid relationship ID `root` and four additional valid identifiers pass component checks; authenticated keyboard holder selection and mobile reload pass without duplicate keys or incorrect holder details. |
| 5 | PASS | Actual desktop scroll keeps the rail at y <= 13 with bounded height; 1024 tablet interaction passes. Fresh desktop screenshot visually inspected. |
| 6 | PASS | Actual browser retains all twelve stage controls, keyboard-focuses the last stage and scrolls the rail independently. Existing rail/disclosure owners retained. |
| 7 | PASS | Actual 768/360 stacked layouts use a static rail and have no horizontal body overflow. Mobile corrective/final controls and holder labels are usable in fresh screenshots. |
| 8 | PASS | Specific source/field decisions, document-bound replacement upload, ownership evidence, UEN input, existing-customer rationale, final action and safe Search diagnostic verified through routing inspection plus component/authenticated browser checks. Existing unavailable risk decisions expose their retained reason and truthful feedback. |
| 9 | PASS | Collapsed registry/document/final stages open before corrective focus. Decision-group navigation does not select a draft or submit it. |
| 10 | PASS | Authoritative refresh removes document attention and shows final action; another case replaces those items. Delayed document focus cancels across case/version changes. |
| 11 | PASS | Native Enter attention activation reaches UEN and final controls on desktop/mobile. Holder keyboard activation, last-stage reach, disabled-control handling and unavailable feedback pass. |
| 12 | PASS | TARGET_CONFIRMATION_REQUIRED is Action: Review and send, excluded from blocker count. No immediate blockers is explicit; backend WARNING projection is also excluded by inspected derivation. |
| 13 | PASS | Attention-only navigation issues no POST/PUT/PATCH/DELETE and leaves decisions/confirmation untouched. Final navigation retains null confirmation/result; existing-customer and failed-Search tests preserve skip-write/no-replay and operation-count assertions. |

Code review covers pending attention identity/version binding, actor/case/generation
checks, disconnected and disabled controls, disclosure timing, specific current document
binding, draft preservation and case refresh/replacement. The new review handle exposes
an existing decision group without creating a decision or mutation. Percentages are
formatted at render sites while raw values remain in backend evidence and input owners.
No acceptance assertion, test exclusion or timeout was weakened for the correction.

## Fresh execution evidence

All checks used this frozen working content. Current task-local Python 3.12.10,
Node 22.23.3, locked frontend dependencies, Vitest 3.2.4 and the configured authenticated
Playwright lifecycle were available. Browser ports 8875/4283 were reserved exclusively
for this gate. Only memory-only synthetic Mock/offline protocol fixtures ran. No dotenv,
Mongo, live provider or dependency installation was used.

| Check | Actual result |
|---|---|
| Focused `npm test -- --run src/ownershipDisplay.test.ts src/pages/OwnershipPathExplorer.test.tsx src/pages/OwnershipStructure.test.tsx src/pages/ReviewAndSend.test.tsx src/EvidenceWorkbenchIsolation.test.tsx` | 5 files / 98 passed |
| Full `npm test` | Initial restricted run: 633 passed / 1 localhost Vite `connect EACCES 127.0.0.1` infrastructure failure. Fresh permitted-local-HTTP rerun: 52 files / 634 passed, exit 0, 8.44s. |
| `npm run typecheck` | PASS, exit 0 |
| `npm run build` | PASS, exit 0; existing 613.10kB bundle-size warning retained |
| Core authenticated browser selector below | 5 passed, 18.5s |
| Existing-customer authenticated browser selector below | 1 passed, 4.6s |
| Failed-Search authenticated browser selector below | 1 passed, 7.4s |
| Real unchanged backend domain/engine/API probe | PASS; actual scientific wire value and classifications asserted |
| Independently compiled shared formatter | 12 label probes plus scientific calculation probe PASS |
| `scripts/check_secrets.py`, `check_architecture.py`, `check_project_state.py`, `check_tooling_config.py`, `check_policy_authority.py` using task Python | All PASS |
| `git diff --check`; explicit task-owned new Markdown whitespace; exact scope/hash checks | PASS |

Browser commands, all using `.venv/Scripts/python.exe scripts/run_e2e.py`
with `--backend-port 8875 --frontend-port 4283 --timeout-seconds 60`:

- `--grep 'UX refinement|Ownership hotfix valid root identity|Ownership hotfix replacement|Ownership hotfix confirmation'`.
- `--sandbox-demo existing-customer --grep 'post-closeout existing-customer confirmation'`.
- `--recovery-demo search-recheck --grep 'Slice C failed Search exposes bounded read-only recheck'`.

The initial restricted core browser attempt exited with
`READINESS_FAILURE: backend readiness timed out`; required scenarios did not execute
there. The subsequent permitted-local-HTTP run passed all five with unchanged commands,
selectors and timeouts. Existing React act/flushSync warnings remain visible; they were
not suppressed or counted as failures. Ignored full-suite logs:
`tmp/ux-refinement/r1-qg-frontend-tests.log` and
`tmp/ux-refinement/r1-qg-frontend-tests-http.log`.

Fresh core browser evidence:
`tmp/browser-evidence/e2afbbcb-0bdd-4e4e-aa9f-b6bcfaef9951/retained/`.
Visually inspected `desktop-sticky.png`, `mobile-corrective-focus.png`,
`mobile-final-action.png` and `valid-root-360.png`: visible focus, readable wrapped
labels, unobstructed corrective controls, usable stacked ownership details and no
horizontal page overflow. Recovery retained diagnostic evidence is under
`tmp/browser-evidence/c0f0f3f6-59aa-46e5-9532-7bb9f40a467b/retained/`.
Screenshots and browser evidence contain synthetic task data only.

Full backend/contracts/full E2E/physical Mongo were not executed and are not claimed
PASS. They are not required solely by FRONTEND_UI without demonstrated broader impact.
The small backend probe independently verified the previously demonstrated Decimal
presentation defect. Clean committed pre-PR, latest remote main and remote CI evidence
were not executed by this reviewer and remain publication obligations.

## Security, scope and readiness

No security or architecture finding remains. Existing backend capability/RBAC,
authenticated query/session owners, document orchestration and target ledger remain
authoritative. Attention is derived from loaded projections and rendered as React text;
local focus/navigation creates no business operation, browser persistence or sensitive
URL value. No confidential artefact or credential was introduced in the scoped diff.

Changes are frontend presentation, accessibility and local holder/focus navigation,
including local component props and the internal decision navigation handle. API/shared
browser types, durable schema, connectors, configuration/dependencies, business rules,
backend mappings, auth/security semantics, architecture owners, provider status,
backend runtime and target-ledger semantics are unchanged. No autonomous resume/send,
new mutation, replay or sponsor decision is introduced.

**Implementation acceptance: PASS for the exact frozen candidate.** Publication may
proceed only through the owner's separately authorized coordinator workflow, with
unchanged accepted content, latest-main assessment and canonical clean committed
pre-PR verification. This gate does not establish Live ACRA/GoldTier readiness or
authorize another phase. Human owner retains merge authority.

## Git closeout

Reviewer wrote only this assigned durable report and ignored verification outputs.
No remediation, commit, push, fetch, PR, merge or branch/worktree mutation occurred.
The twenty-one frozen raw-byte hashes and aggregate remain unchanged; staged content
remains empty. This report is the sole additional task-owned untracked path at closeout.
Next authorized action is unchanged-content verification and the coordinator's
publication procedure.
