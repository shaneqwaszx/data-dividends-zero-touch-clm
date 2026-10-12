# PR84 attention remediation independent quality gate

## Executive result

**PASS. Required findings: P0=0, P1=0, P2=0, P3=0.** The projection-only attention
defect identified by review comments 4245900339 and 4246017855 is addressed. The complete
frozen PR candidate satisfies the original four UX features and all twelve remediation
criteria. No required fix remains. This accepts local implementation only; integration,
clean committed pre-PR verification, publication and remote review remain coordinator work.

Review date: 2026-10-12, Asia/Singapore. The reviewer did not implement this feature or
remediation. The sole durable reviewer write is this report; source, tests, configuration,
ordinary documentation and Git remained read-only. Ignored verification output is separate.

## Identity and reviewed scope

- Worktree: `C:/Users/shane/Desktop/FYP/data-dividends-zero-touch-clm/.ux-task`.
- Branch: `feat/case-ownership-ux-quick-refinement`.
- HEAD: `15a4b2cb7d770b4f54efbebdee611cb9c7a3b56e`.
- BASE_SHA, merge base and locally inspected `origin/main`:
  `832ff770d37c3f4710a9fd271a8fe00af3d2a407`. No fetch or remote mutation occurred.
- Reviewed and tested content is the working candidate, not HEAD alone: five tracked
  modifications and three new remediation files, superimposed on the published feature.
- Full PR candidate: twenty-five paths. Manifest:
  `tmp/ux-refinement/pr84-attention-frozen.json`; raw aggregate SHA256:
  `d87f26a01972c1262580a6f55018f88607d89da80f66fc9c851102b69a675fd6`.
- Algorithm: SHA256 of UTF-8 compact sorted-key JSON of entries sorted by path, each
  containing `path`, `classification` and raw-byte `sha256`. Every file hash and exact
  full diff/untracked scope matched before execution and at closeout. This report is
  excluded from the freeze; it is additional supporting publication content.

Complete inventory:

| Class | Paths |
|---|---|
| INTENDED | `apps/frontend/src/design-system.css`; `apps/frontend/src/ownershipDisplay.ts`; `apps/frontend/src/pages/BlockerDecisionReview.tsx`; `apps/frontend/src/pages/CaseAttentionSummary.tsx`; `apps/frontend/src/pages/CaseDetail.tsx`; `apps/frontend/src/pages/HumanInterventionPanel.tsx`; `apps/frontend/src/pages/ManualOwnershipEvidenceForm.tsx`; `apps/frontend/src/pages/OwnershipPathExplorer.tsx`; `apps/frontend/src/pages/OwnershipStructure.tsx`; `apps/frontend/src/pages/UboSummary.tsx` |
| SUPPORTING | `.ai-pipeline/reports/FRONTEND_UX_REFINEMENT_QUALITY_GATE.md`; `.ai-pipeline/reports/FRONTEND_UX_REFINEMENT_QUALITY_GATE_R1.md`; `apps/frontend/e2e/ownership-document-streamline.e2e.ts`; `apps/frontend/e2e/s3-sandbox-submission.e2e.ts`; `apps/frontend/e2e/slice-c-recovery.e2e.ts`; `apps/frontend/e2e/ux-refinement.e2e.ts`; `apps/frontend/src/EvidenceWorkbenchIsolation.test.tsx`; `apps/frontend/src/ownershipDisplay.test.ts`; `apps/frontend/src/pages/CaseAttentionSummary.test.tsx`; `apps/frontend/src/pages/OwnershipPathExplorer.test.tsx`; `apps/frontend/src/pages/OwnershipStructure.test.tsx`; `apps/frontend/src/pages/ReviewAndSend.test.tsx`; `apps/frontend/src/test-fixtures/attention-projections.json`; `docs/integration/FRONTEND_UX_REFINEMENT.md`; `docs/integration/PR84_REVIEW_REMEDIATION.md` |

Authority read: both complete owner briefs, root/frontend/backend AGENTS, repository
workflow and skill routing, quality-gate skill/template, FRONTEND_UI dev-context and
selected current architecture/provider/state sections, original task/remediation documents,
previous R1 gate, full PR diff and new files, current projection/domain/lifecycle owners,
and current affected tests. The previous gate supplies context, never fresh PASS evidence.

## Original acceptance checklist

| # | Result | Direct fresh evidence |
|---|---|---|
| 1: maximum two decimal percentage display | PASS | Shared display formatter and all hierarchy/selected-holder/UBO/Final Review/path/technical consumers inspected; 24 formatter tests and full suite pass. |
| 2: raw precision and classification | PASS | Actual validated engine/API yields `1.00E-14`, NOT_MET, BELOW_PROVISIONAL_THRESHOLD; production formatter renders `<0.01%`. Raw-record equality and rounded-to-threshold exclusion regressions pass. No backend diff. |
| 3: holder/path selection after candidate-row removal | PASS | Hierarchy native selection, repeated occurrences, retained path inspection, root/unlinked selection and analysis refresh tests pass; actual authenticated holder browser passes. |
| 4: valid relationship ID `root` | PASS | Five identifier variants pass component tests; real keyboard/mobile/reload root-ID browser passes. |
| 5: sticky desktop rail | PASS | Actual main-page scroll retains rail y <=13 and height <=696 at 1280x720; screenshot inspected. |
| 6: all twelve stages | PASS | Browser counts twelve controls, focuses final stage and independently scrolls rail. |
| 7: mobile usability | PASS | Actual 1024/768/360 layouts, static narrow rail, no body horizontal overflow; fresh screenshots inspected. |
| 8: correct actionable destination | PASS | UEN, specific document/source decision, replacement file input, ownership evidence, existing-customer rationale, final action and safe Search diagnostic verified by component and authenticated browser execution. |
| 9: disclosure before focus | PASS | Collapsed registry/document/final stages open before real corrective focus. |
| 10: current authoritative issues | PASS | Refresh removes resolved records; case switch replaces attention; delayed focus and late old-case GET regressions pass. |
| 11: keyboard controls | PASS | Native Enter reaches UEN and final controls at desktop/mobile; holder and last-stage keyboard reach verified. |
| 12: final review is action | PASS | TARGET_CONFIRMATION_REQUIRED excluded from genuine blockers; strict zero-blocker/final-action browser assertion remains. |
| 13: no navigation mutation or replay | PASS | Navigation request listeners remain empty; retained case equality and absent target confirmation/result assertions pass. Safe Search diagnostic retains operations `[SEARCH]`; existing-customer no-write regression passes. |

## Remediation acceptance checklist

| # | Result | Evidence |
|---|---|---|
| 1: unmatched identity projection visible | PASS | Strict-schema actual producer probe, panel test and labelled projection-only browser. |
| 2: genuine blocker count | PASS | Zero exceptions/one identity projection; one document exception/two distinct projections; actual invalid-UEN API one exception/two projections and two UI blockers. |
| 3: Correct identity reaches authorized input | PASS | Actual UEN focus and existing Search recheck control at desktop/mobile; no request on click. |
| 4: independent document blocker preserved | PASS | Actual Mock-IDP lifecycle producer probe, union test and mixed projection browser. |
| 5: linked records counted once | PASS | Exception ID equals linked projection ID; matching-ID regression passes. |
| 6: WARNING excluded | PASS | Unmatched and linked WARNING regressions pass; attention retained without blocker inflation. |
| 7: target confirmation action | PASS | Unmatched and linked final-action regressions plus authenticated final-review browser. |
| 8: technical truth without duplicate cancelled exception | PASS | Backend lifecycle requires no open exceptions in technical failure; linked cancelled-record test and actual Search diagnostic browser pass. No code-based suppression added. |
| 9: refresh/switch currentness | PASS | Projection refresh/removal, late old-case GET, rapid case/version delayed-focus and actual reload/switch checks pass. |
| 10: click causes no correction | PASS | Component fetch spy, browser method listeners, unchanged actual retained case/version and target state. |
| 11: unavailable controls truthful | PASS | Disabled identity input and unavailable risk decision retain reason/status and safe section focus; no invented action. |
| 12: keyboard/mobile preserved | PASS | Both new edges use native Enter and 1280/360 widths; original 1024/768/360 and twelve-stage checks pass. |

## Contract, code, architecture and security review

No required finding. The panel unions OPEN exceptions with unmatched current interventions,
links only `exception_id` to `intervention_id`, and preserves equal-code independent IDs.
Final confirmation and WARNING exclusions retain backend semantics. Unmatched records use
the first projected evidence action or retained intervention card. Navigation stays with
CaseDetail's existing disclosure/focus owners; case/action generation and evidence version
guard deferred work. The identity form selects the existing initial-identity recheck when
the backend projection declares its blocker. Disabled/currentness/backend capability gates
remain intact; navigation never calls the form's mutation handler.

The reviewer independently executed unchanged `project_human_interventions` using ordinary
test composition with dotenv disabled and memory/Mock providers. `OnboardingCase` accepts
missing optional initial identity; the automation record passed strict model and
`validate_automation_record` validation. PENDING_INPUTS yielded zero exceptions and one
identity intervention. A real Mock-IDP LOW_CONFIDENCE document and normal `zero.start`
yielded WAITING_FOR_REVIEW, one document exception and two distinct projections. Linked
document IDs matched; the permanent JSON passed `BrowserHumanIntervention` strict schemas
and matched producer codes/classes/actions. Target mutation count was zero. Modern
legal-name creation may instead produce a matching identity exception; these retained
inputs deliberately exercise the supported unmatched branch.

The actual unmodified invalid-UEN browser API independently reports one registry exception
and two distinct interventions, including unmatched missing identity. Two additional
browser cases authenticate through the real backend but layer only one case GET with the
generated synthetic fixture. These are UI projection-edge evidence, not unmodified backend
response claims. The document-resolution case now supplies complete initial identity;
its strict zero-blocker/final-action assertion is preserved. No assertion, timeout or
normal test-discovery exclusion was weakened.

The original Decimal feature was freshly challenged through the actual ownership service
and `OwnershipAnalysisResponse`: two valid six-decimal `0.000001%` edges, with valid
100%-total siblings, serialize A's effective value as `1.00E-14` and retain
`0.000001% x 0.000001% = 0.00000000000001%`, NOT_MET and BELOW_PROVISIONAL_THRESHOLD.
Eight independent probes of compiled production formatter source plus that calculation
pass. BigInt formatting is presentation-only; backend classifications remain authoritative.

No API/shared browser type, persisted schema, connector, configuration/dependency, business
rule, mapping, auth/security semantic, architecture owner, provider classification or
backend runtime changed. Internal component props/navigation handle and frontend rendering,
focus and form-selection behavior change. No frontend authorization, persistent browser
evidence, direct provider access, extra ownership engine or target-ledger bypass appears.
Tracked/task-owned secret scan passes; the JSON contains fictional test evidence only,
with no credential, document body or confidential sponsor artefact.

## Fresh execution evidence

All successful results below exercised the recorded frozen candidate. No installations,
dotenv access, physical Mongo or real-provider/Sandbox writes occurred.

| Check | Result |
|---|---|
| `npm test -- --run src/pages/CaseAttentionSummary.test.tsx src/EvidenceWorkbenchIsolation.test.tsx` | 49 PASS / 2 files: 10 panel and 39 integration tests, 5.79s. |
| `npm test` with permitted local HTTP | 649 PASS / 53 files, 7.19s; zero skips. |
| `npm run typecheck`; `npm run build`; `npm ls --all` | PASS. Build 140 modules; JS 613.72 kB / gzip 169.41 kB; existing >500 kB warning retained. |
| Core runner with the exact command below | 7 PASS, 25.1s; actual authenticated guarded local Mock browser. |
| Same runner/ports/timeout, `--sandbox-demo existing-customer --grep 'post-closeout existing-customer confirmation'` | 1 PASS, 4.4s; simulated local transport, no real Sandbox write. |
| Same runner/ports/timeout, `--recovery-demo search-recheck --grep 'Slice C failed Search exposes bounded read-only recheck'` | 1 PASS, 7.1s; diagnostic focus and no-replay operation assertions. |
| `check_project_state.py`, `check_architecture.py`, `check_policy_authority.py`, `check_external_provider_readiness.py`, `check_tooling_config.py` | Five PASS. |
| `check_secrets.py`; `git diff --check origin/main`; explicit all candidate Markdown trailing-whitespace check | PASS. |
| Independent backend projection/schema/lifecycle and actual Decimal/API probes | PASS as detailed above; no target mutation. |
| Before/after file hashes and exact full PR scope | MATCH: twenty-five paths and recorded aggregate. |

```powershell
.venv/Scripts/python.exe scripts/run_e2e.py --backend-port 8875 --frontend-port 4283 --grep 'UX refinement|PR84 projection-only|Ownership hotfix valid root identity|Ownership hotfix replacement|Ownership hotfix confirmation' --timeout-seconds 60
```

First full frontend execution under the restricted sandbox had 648 PASS and one
`connect EACCES` in the existing ViteHistoryFallback loopback contract. Unchanged full-suite
execution with permitted local HTTP passed all 649; the first run is not reported as PASS.
The reviewer-only producer probe initially omitted an excluded internal binding during
model serialization, then corrected its input; sandbox temporary-file denial subsequently
required permitted execution for existing PDF validation. The final unchanged production
probe passed. Three guessed check filenames did not exist; actual canonical five checks
and scanner above were located and executed. These are verification setup corrections,
not candidate defects or skipped checks. Existing React `act` warnings remain disclosed.

Ignored drill-down logs: `tmp/ux-refinement/attention-qg-full.log`,
`attention-qg-full-http.log`, `attention-qg-npm-ls.log`,
`attention-qg-browser-core.log`, `attention-qg-browser-customer.log`,
`attention-qg-browser-recovery.log`. Implementer failing-first logs were inspected only as
historical reproduction evidence: panel six failures/three passes, focus four failures;
they do not supply this independent gate's PASS.

Fresh browser retained screenshots are under
`tmp/browser-evidence/ec76243b-a697-4504-a1a1-38fd8c91ba6f/retained/`.
The reviewer visually inspected desktop sticky, desktop unmatched identity, mobile mixed
projection corrective focus and mobile valid-root holder screenshots. Actual browser
assertions additionally cover tablet/mobile overflow, independent rail scroll and final focus.

## Required fixes, limitations and readiness

Required fixes: **none**. No current sponsor-authority blocker was introduced. Existing
production SSO/policy, Live ACRA/GoldTier, sponsor approval and real interoperability remain
later dependencies; Mock/Local/Partial classifications remain unchanged.

Full backend/contracts/full unfiltered E2E/physical Mongo are not required for this
FRONTEND_UI scope and were not executed. Production hosting fallback and exhaustive
accessibility audit are not certified; bounded authenticated keyboard/responsive behavior
is verified. Remote CI is **NOT EXECUTED** in this gate; the owner's billing limitation
is not remote PASS. The gate does not certify current remote review clearance.

Ready for the separately authorized coordinator integration/publication procedure on
unchanged reviewed content, including latest-main assessment, clean committed canonical
pre-PR gate and normal PR84 push/review. This is not a merge, release exception or
next-phase authorization. Owner alone performs final merge.

## Git closeout

At report closeout HEAD/base/locally inspected main remained as recorded. No staged
content; five tracked remediation modifications and three new remediation files remained,
plus this new report. Complete original published feature scope was reviewed against
origin/main. Hash/scope checks exclude only this assigned report. No implementation fix,
commit, push, fetch, branch mutation, remote action, merge or next phase occurred.
