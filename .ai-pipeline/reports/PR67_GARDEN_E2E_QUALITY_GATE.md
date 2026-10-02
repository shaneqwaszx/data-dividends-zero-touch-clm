# PR #67 Garden E2E independent quality gate — 2026-10-02

## Result and reviewed identity

**PASS.** The bounded E2E remediation satisfies the assigned diagnosis, readiness,
regression and verification criteria. No P0/P1/P2 finding or required correction
remains in this delta. This verdict does not cover the entire previously published
Phase 24 implementation, certify remote CI after publication, or authorize a merge.

Reviewer: fresh independent subagent, requested GPT-6.1 Sol / High route. The reviewer
read the explicit task attachment, full AGENTS.md, fyp-quality-gate/template, selected
CI_TOOLING/FRONTEND_UI context, current owners, Phase 24/24C planner and accepted gate,
and the requested PR #52 document synchronization sections. Implementation was
read-only; the sole reviewer-authored file is this report.

Worktree: `C:/Users/shane/.codex-clean2/worktrees/pr67-garden-e2e-sync/data-dividends-zero-touch-clm`.
Branch: `codex/pr67-garden-e2e-sync`. Source HEAD / remediation base:
`0d3b88af9ac65f7ae1af8df6d175b07f77842613`. Inspected `origin/main` / integration merge
base: `039101b69772c4c9ae4ca7b4a7ca3e4c19b03f4c`. No reviewer fetch or freshness claim.

Complete frozen reviewed path set:

- `apps/frontend/e2e/garden-happy-path.e2e.ts` — byte SHA256
  `2bf540448fc457d34d9821390aa760cfb855d99686e5e6d44761db626696a525`.
- `.ai-pipeline/reports/PR67_GARDEN_E2E_REMEDIATION.md` — final evidence-report SHA256
  `2c1d7a6c24c8fdbe67b61adb33918ace0d0ed5b98d23dc8972550da549683d4d`.

Executable Git diff SHA256:
`b66c00c90d66b84bd85bd98392a4c08593b7c3435bb69e9f670c543e54752072`.
The executable hashes matched before and after independent execution; the final
supporting report hash matched its coordinator freeze before this verdict. All
reviewed executable behavior is HEAD plus that one-file uncommitted diff. The report
and ignored task-local diagnostic logs are supporting evidence, not executable changes.

## Acceptance and evidence

| Assigned criterion | Result and evidence |
|---|---|
| Original repeated CI failure understood | PASS. Independent read-only `gh run view 36975135420 --attempt 1/2 --log-failed` confirms both failures at original Garden line 116: accessible document heading absent for 15,000 ms. Source and controlled real-browser evidence support the mechanism below. No CI rerun occurred. |
| Bounded fresh reproduction and neighboring control | PASS. Coordinator retained ten fresh baseline lifecycle logs: heading 10/10 passed; whole selector 9/10 passed, with one later disabled review-control failure. All ten show mounted heading and expansion followed by automatic closure. Clean Garden control passed separately. Counts are not represented as ten reproductions of the heading failure. |
| Failing-first evidence before fix | PASS. Coordinator's exact pre-fix command/session 88317 exit 1 and transcribed actual output show held documents GET, expanded Documents, release, mounted heading beneath collapsed content, backend WAITING_FOR_REVIEW / DOCUMENT, then the original 15,000 ms heading assertion failure. The transcript is explicitly distinguished from a persisted log. Independent retained-regression execution verifies the same controlled transition. |
| Correct readiness owner | PASS. Garden fixture helper waits for one current document card and, for the conflicting fixture, visible Use document UEN before opening Documents. This verifies committed query-derived presentation, rather than response headers alone. |
| No timeout inflation, arbitrary sleep/retry or assertion weakening | PASS. Complete diff inspected. No new timeout, waitForTimeout, reload, test retry, swallowed failure or skip. Original visible-heading assertion and all acquisition/field-review assertions remain. Existing generic helper retry contract is unchanged. |
| Meaningful retained regression | PASS. New held-GET browser test proves expanded -> collapsed with heading DOM count 1 after conflict arrival, reopens through the helper, asserts visible heading and backend DOCUMENT. Existing delayed-review regression retains four accepted-field events, identity, event growth and REVIEWED state assertions. Both passed independently. |
| Exact failing selector after fix | PASS. Final frozen-content coordinator matrix: 10/10 consecutive isolated PASS, ports 9300–9309 / 5300–5309; all ten log footers inspected. Independent original selector also PASS on 9442 / 5442. |
| All Garden and Phase 24/24C focused E2E | PASS. Coordinator evidence: Garden 5 selectors / 5 instances; Phase 24 identity 3 / 4; Phase 24C policy 2 / 7, with isolated lifecycles. |
| Full configured E2E twice | PASS. Independently inspected both retained logs: 32 completed selectors / 39 executed instances each; 351.062 s and 348.203 s. Both report suite PASS and coordinator confirmed process exit 0/cleanup. |
| Affected frontend tests | PASS. Independent StageDisclosure, DocumentEvidencePanel and IdentityCorrectionForm: 3 files / 20 tests; Phase15CNavigation: 1 file / 40 tests. Coordinator full frontend log: 35 files / 388 tests PASS; existing act/layout-effect warnings. |
| Typecheck and build | PASS. Coordinator final frozen-content execution evidence; existing large-chunk build warning remains. No manifest or lockfile change. |
| Hygiene and governance | PASS. Independent executable/report hashes, complete diff, tracked whitespace, explicit new-report whitespace, architecture, project-state and secret scan checked. |

Independent browser commands used the configured lifecycle harness, pinned Chromium,
real local HTTP and strict offline Garden protocol. Each command used
`.venv/Scripts/python.exe scripts/run_e2e.py --garden-protocol --timeout-seconds 60`
with the exact title supplied to `--grep` and a fresh port pair:

| Title | Ports | Result |
|---|---|---|
| Garden document arrival settles identity focus before explicit Documents inspection | 9440 / 5440 | 1/1 PASS, exit 0, harness PASS |
| Garden delayed current document rendering cannot skip required field review | 9441 / 5441 | 1/1 PASS, exit 0, harness PASS |
| Garden discrepancy human intervention clears reviewed conflicts and continues onboarding | 9442 / 5442 | 1/1 PASS, exit 0, harness PASS |

The reviewer waited for explicit browser resource release and ran these sequentially.
Initial sandbox Vitest and GitHub CLI attempts were blocked by loader/config access;
narrow approved executions succeeded. Blocked attempts are not counted as passes.

## Diagnosis, code and architecture assessment

Deepest confirmed boundary: **J — query-derived active-stage transition closes the
disclosure after the test observed expansion.** CaseDetail initially uses its cached
backend summary while `documents=[]`. DocumentEvidencePanel already mounts its heading.
When the current document query commits the conflicting UEN, CaseDetail derives
`identityConflict=true`: Registry identity becomes active and Documents becomes inactive.
StageDisclosure's existing `useEffect` follows `active`, closes Documents and hides its
still-mounted children. `openStage` returning expanded=true cannot promise stable
visibility across that subsequent query-driven transition.

The fixture-specific wait is at the appropriate owner. The current card proves document
data was committed. Use document UEN is inside Registry's controlled stage body; its
visibility proves the derived stage presentation has settled before explicitly opening
Documents. The clean fixture still requires its current evidence. Empty/error document
results cannot falsely satisfy the one-card predicate. Generic openStage and product
StageDisclosure remain unchanged; the independent component test verifies the existing
active-stage closure and explicit reveal semantics.

Historical comparison: **DIFFERENT CLASS** from the requested PR #52 stale-presentation
failure. Here current documents commit successfully and drive a legitimate stage change;
PR #52 involved delayed publication/stale overwrite after backend review advanced.
No stale-query product repair or backend-state change is justified by this evidence.

The exact GitHub attempts contain no internal query/DOM milestones. The diagnosis is
supported by current source, ten observed local transitions, controlled failing-first
symptom and independent retained regression; it does not claim direct observation of
CI's internal query state. The separate pre-fix disabled review-control failure is
preserved as baseline evidence; it did not recur in the required final matrices or
independent original-selector run and is not assigned as this heading mechanism.

No new service, state owner, cache policy, dependency direction, business authority,
provider composition or target execution path was introduced. Product API/type, schema,
connector, configuration, business-rule, mapping, auth/security, architecture, provider
classification and runtime behavior are unchanged. E2E readiness orchestration and
regression coverage changed.

## Security, limitations and required fixes

No new credentials, confidential artefacts, raw provider/document payload, KYC/PII,
authorization logic, browser storage or external request was found in the frozen delta.
Tests retain the existing guarded network policy and synthetic fixtures. All new evidence
remains Mock/Local; this gate supplies no Live ACRA/GoldTier claim. Backend product,
physical Mongo, external-provider and Windows demo-lifecycle lanes are unaffected and
were not rerun.

Optional broader tooling-unit aggregate is **FAIL: 95/96**, not passing evidence. The
unchanged historical-patch fixture copies CRLF checkout bytes into a core.autocrlf=false
temporary repository. Independent source inspection and byte-only comparison confirm
all three checkout files normalized to LF equal their unchanged HEAD blobs. This
pre-existing Windows fixture issue is outside the E2E-only delta and the task's required
frontend/browser acceptance; it does not block this bounded verdict. Official clean
committed pre-PR remains required and must pass independently before publication.

Required fixes for this bounded delta: **none**. No P0/P1/P2 finding. Later sponsor
and Live-integration dependencies remain as recorded in current project authority.

## Readiness and Git status

This bounded remediation is independently accepted for the user's conditional
publication workflow on unchanged reviewed content. This is not whole-phase reapproval
or next-phase readiness. Publication still requires the official clean committed
pre-PR result, exact original remote PR head check, latest-main assessment and the one
scoped fast-forward commit/push authorized in the explicit task. Remote CI and human
merge remain separate. No merge or Phase 25 is authorized by this gate.

At review entry and final pre-report check, the index was empty; the only tracked change
was the Garden E2E file and the only nonignored untracked file was the supporting
remediation report. Writing this assigned gate adds the third task-owned publication
path. The reviewer made no implementation, test, configuration, ordinary documentation
or Git mutation, commit, push, CI rerun, integration, provider operation or merge.