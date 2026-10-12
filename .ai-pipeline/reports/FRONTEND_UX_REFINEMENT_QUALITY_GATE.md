# Frontend UX refinement — independent Quality Gate

## Verdict and frozen identity

**FAIL. Required findings: P0=0, P1=0, P2=1.** Valid scientific-notation backend
Decimal strings are rejected by the display formatter. The mandatory tiny-positive
percentage behavior is therefore not satisfied. No publication is permitted for
this frozen candidate; the owner's one bounded correction and fresh gate remain the
next authorized action.

Reviewed independently on 2026-10-12 in
`C:/Users/shane/Desktop/FYP/data-dividends-zero-touch-clm/.ux-task`, branch
`feat/case-ownership-ux-quick-refinement`. BASE_SHA, HEAD and locally inspected
`origin/main` are `832ff770d37c3f4710a9fd271a8fe00af3d2a407`. No fetch occurred in
this review. Reviewed implementation is uncommitted: 15 modified tracked paths and
five task-owned untracked paths, no staged content. All 20 raw-byte hashes and the
aggregate matched before review and at closeout:
`29d571a1ad2ce76a124d58e0e83c34d76d2292f87473942e44ce73878ee84a1c`.
Algorithm: SHA256 of UTF-8 compact sorted-key JSON of the sorted manifest entries,
including their classifications; each entry hashes raw file bytes. Manifest:
`tmp/ux-refinement/frozen.json`. This report is excluded from that identity.

Complete reviewed paths:

- `apps/frontend/e2e/ownership-document-streamline.e2e.ts`
- `apps/frontend/e2e/s3-sandbox-submission.e2e.ts`
- `apps/frontend/e2e/slice-c-recovery.e2e.ts`
- `apps/frontend/e2e/ux-refinement.e2e.ts` (new)
- `apps/frontend/src/EvidenceWorkbenchIsolation.test.tsx`
- `apps/frontend/src/design-system.css`
- `apps/frontend/src/ownershipDisplay.test.ts` (new)
- `apps/frontend/src/ownershipDisplay.ts` (new)
- `apps/frontend/src/pages/BlockerDecisionReview.tsx`
- `apps/frontend/src/pages/CaseAttentionSummary.tsx` (new)
- `apps/frontend/src/pages/CaseDetail.tsx`
- `apps/frontend/src/pages/HumanInterventionPanel.tsx`
- `apps/frontend/src/pages/ManualOwnershipEvidenceForm.tsx`
- `apps/frontend/src/pages/OwnershipPathExplorer.test.tsx`
- `apps/frontend/src/pages/OwnershipPathExplorer.tsx`
- `apps/frontend/src/pages/OwnershipStructure.test.tsx`
- `apps/frontend/src/pages/OwnershipStructure.tsx`
- `apps/frontend/src/pages/ReviewAndSend.test.tsx`
- `apps/frontend/src/pages/UboSummary.tsx`
- `docs/integration/FRONTEND_UX_REFINEMENT.md` (new)

Authority: owner's complete FAST-TRACK brief, root/frontend AGENTS, quality-gate skill
and report template, FRONTEND_UI dev-context Tier 1 workflow/architecture/project-state
sections, task handoff, owning code/tests, and relevant accepted root-collision recovery
gate. Previous gates and implementer results were not substituted for fresh evidence.

## Required finding

**UX-QG-01 [P2, REQUIRED] — accept actual backend scientific Decimal strings.**
`apps/frontend/src/ownershipDisplay.ts:4` accepts only unsigned fixed-point decimal
syntax. `CalculatedPercent` in the unchanged backend is an unrestricted nonnegative
Decimal, and `OwnershipAnalysisResponse` serializes Decimal through Pydantic JSON.
Consequently legitimate calculated values can contain an exponent.

Independent read-only reproduction used the actual domain, graph validator, path
calculator, aggregator, candidate classifier and `OwnershipAnalysisResponse.from_domain`:
five synthetic parties; ROOT→HOLDING `0.000001%`, ROOT→B `99.999999%`,
HOLDING→A `0.000001%`, HOLDING→C `99.999999%`. Both owned-entity totals equal 100;
every edge meets the existing six-decimal input contract. Candidate A's actual API JSON
contains indirect, aggregate and effective-path values **`1.00E-14`** and retains
`NOT_MET` / `BELOW_PROVISIONAL_THRESHOLD`. Its calculation string is
`0.000001% x 0.000001% = 0.00000000000001%`.

The frozen formatter returns **`Not available`** for `1.00E-14` (and `1E-18`),
while its fixed-point calculation token renders `<0.01%`. Hierarchy, selected-holder,
candidate technical and path labels therefore misreport valid retained evidence as
unavailable. Current fixed-point-only tiny fixtures do not exercise the API wire shape.
This violates required change A and acceptance criterion 1. Backend precision and
classification remain correct; no backend correction is requested.

Required bounded correction: parse valid finite nonnegative scientific decimal strings
with arbitrary precision in the shared display-only owner; preserve tiny-positive
labels, exact threshold semantics and original strings. Add regressions using actual
serialized calculated values, including zero/exponent forms and boundary rounding,
then freeze and obtain a fresh independent gate. Do not convert to floating point or
change backend math, API serialization or classification to accommodate presentation.

## Owner acceptance evidence

| # | Result | Evidence |
|---|---|---|
| 1 | FAIL | Fixed-point labels round consistently across hierarchy, selected holder, UBO/Final Review, paths, calculations and technical/history tables; actual scientific API tiny values fail UX-QG-01. |
| 2 | PASS | Formatter is display-only; original-record equality and rounded-25% NOT_MET regression pass. Actual domain/API probe retains exact `1.00E-14` and backend classification. No backend diff. |
| 3 | PASS | Candidate row removed; native hierarchy buttons retain root, unlinked, repeated-holder, candidate/path selection and current-analysis refresh behavior. Focused component and authenticated ownership runs pass. |
| 4 | PASS | Valid relationship ID `root` and additional valid-ID component cases pass; authenticated keyboard selection/reload at 1280/360 passes without duplicate keys or wrong selected holder. |
| 5 | PASS | Actual 1280 browser scroll leaves sticky rail at y≤13 with bounded height; desktop screenshot visually inspected. 1024 interaction also passes. |
| 6 | PASS | Browser retains twelve stage controls, reaches/focuses last stage through independent rail scrolling; unchanged rail/disclosure owners inspected. |
| 7 | PASS | Actual 768/360 stacked layouts retain static rail, no body overflow, keyboard corrective/final focus; mobile screenshots visually inspected. |
| 8 | PASS | Specific source and field decisions, bound replacement upload, ownership evidence, UEN input, existing-customer rationale, final send and safe Search diagnostic verified through component/runtime checks and routing review. Unavailable risk decisions expose retained reason plus truthful feedback; no invented decision. Projected evidence actions reuse existing owners. |
| 9 | PASS | Collapsed document/registry/final stages open before corrective focus; specific decision group opens without drafting a choice. Actual browser and component checks pass. |
| 10 | PASS | Authoritative refresh replaces document attention with final action; switching to another case replaces attention. Delayed document load across case/version changes cancels focus. |
| 11 | PASS | Native Enter activation reaches UEN and final controls in desktop/mobile browser. Holder keyboard selection and last pipeline-stage keyboard reach pass; disabled-control and retained-unavailable feedback checks pass. |
| 12 | PASS | TARGET_CONFIRMATION_REQUIRED is labelled Action: Review and send, excluded from genuine blocker count; no immediate blockers remains explicit. Backend WARNING classification is excluded by inspected projection logic. |
| 13 | PASS | Attention navigation records no POST/PUT/PATCH/DELETE; review/confirm draft remains untouched. Final navigation retains null confirmation/result. Existing-customer and failed-Search scenarios preserve skip-write/no-replay assertions and retained operation counts. |

Focus/currentness review covers actor/case/generation checks, pending attention version
binding, disconnected/disabled controls, disclosure reveal timing, synchronous clearing
of old draft controls, and refresh/case replacement. No required issue was found there.

## Fresh execution and visual evidence

Commands ran against the frozen working content using current task-local Python,
installed Node/npm/Vitest/Playwright, configured authenticated memory-only Mock/offline
protocol fixtures, and exclusively reserved ports 8875/4283. No dependency installation,
dotenv access, Mongo access or live-provider call occurred in this gate.

- Focused `npm test -- --run src/ownershipDisplay.test.ts src/pages/OwnershipPathExplorer.test.tsx src/pages/OwnershipStructure.test.tsx src/pages/ReviewAndSend.test.tsx src/EvidenceWorkbenchIsolation.test.tsx`: **5 files / 86 passed**.
- Full `npm test`: initial sandbox run **621 passed / 1 failed** due local Vite HTTP `connect EACCES 127.0.0.1`; fresh permitted-local-HTTP rerun **52 files / 622 passed**, exit 0. Logs: `tmp/ux-refinement/qg-frontend-tests.log` and `qg-frontend-tests-http.log`.
- `npm run typecheck`: PASS. `npm run build`: PASS; existing >500kB bundle-size warning remains disclosed.
- `.venv/Scripts/python.exe scripts/run_e2e.py --backend-port 8875 --frontend-port 4283 --grep 'UX refinement|Ownership hotfix valid root identity|Ownership hotfix replacement|Ownership hotfix confirmation' --timeout-seconds 60`: **5 passed**, 19.0s.
- Same configured harness with `--sandbox-demo existing-customer --grep 'post-closeout existing-customer confirmation' --timeout-seconds 60`: **1 passed**, 4.4s.
- Same configured harness with `--recovery-demo search-recheck --grep 'Slice C failed Search exposes bounded read-only recheck' --timeout-seconds 60`: **1 passed**, 7.1s.
- Independent compiled-formatter probes: eight fixed-point arbitrary-precision/tiny/half-cent/threshold assertions PASS; scientific-input challenge FAIL as described above. Actual unchanged backend-domain/API serialization probe executed successfully and established the wire value.
- `python scripts/check_secrets.py`, `check_architecture.py`, `check_project_state.py`, `check_tooling_config.py`, `check_policy_authority.py`: all PASS. `git diff --check` and explicit new Markdown whitespace scan: PASS. Full tracked plus task-owned untracked scope matches the frozen manifest exactly.

Existing React act/flushSync warnings are visible in component/full-suite output; they
were not hidden or treated as failures. No assertions/exclusions/timeouts were changed.
Full backend/contracts/full E2E/physical Mongo were not executed and are not claimed
PASS; FRONTEND_UI does not require them absent demonstrated broader impact. The minimal
domain/API probe investigated the demonstrated formatter defect only. Clean committed
pre-PR verification and current-remote assessment belong to later publication.

Independent core browser evidence is under
`tmp/browser-evidence/4ecff892-7bc8-45a6-879e-d88f1c6f6011/retained/`.
Visually inspected `desktop-sticky.png`, `mobile-corrective-focus.png`,
`mobile-final-action.png`, and `valid-root-360.png`: real settled focus, readable wrapped
labels, unobstructed corrective controls, no horizontal page overflow. Customer/recovery
runs are `b8fb1403-ba48-4582-ae5c-99f430db9915` and
`5b5229f3-2e78-4713-9384-2981a238503c`. Screenshots contain synthetic data only.

## Scope, security and next action

Frontend presentation, accessibility and local selection/focus behavior change;
internal review navigation handle/component props change locally. API/shared browser
types, durable schema, connector, configuration/dependencies, business rules, backend
mapping, auth/security semantics, architecture ownership, provider classifications,
backend runtime and target ledger do not change. Existing auth/cache/capability owners
remain authoritative; attention is derived from loaded case projections, rendered as
React text, and initiates no business operation. No credentials, protected artefacts,
raw provider data, browser persistence or sensitive URL values were introduced.

No contract/security/architecture finding beyond the presentation defect was found.
Existing risk/sponsor decisions remain unavailable; Mock/Local/Partial evidence does
not establish Live ACRA/GoldTier readiness. No next phase was started.

Reviewer changed only this assigned durable report plus ignored verification outputs.
No source/test/configuration/ordinary-documentation fix or Git/remote mutation occurred.
The 20-path frozen content remains unchanged. Next authorized action is the owner's
one scoped correction followed by a fresh independent freeze/gate. Commit, push and PR
publication require exact PASS on the corrected content and subsequent canonical
latest-main/committed pre-PR procedure. Human owner retains merge authority.
