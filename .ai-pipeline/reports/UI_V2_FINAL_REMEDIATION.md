# UI V2 Final Remediation

## 1. Executive summary

This bounded pass addressed only findings F-01 through F-05 from
`UI_V2_FINAL_QUALITY_GATE.md`. The onboarding controller now retains the exact
created case before deciding whether document intake is valid, new-case reset
clears transient presentation state, Registry progress uses semantic non-colour
status markers, and every applicable Policy value carries one of the four
approved classifications. The secret scanner and its tests were restored
byte-for-byte to `origin/main`.

Frontend, focused phase, contract, lint, type, dependency, and GoldTier checks
pass. The full backend passed once, then a final repeat exposed one intermittent
pre-existing case-list ordering failure; the isolated test subsequently passed
five of five reruns. The mandatory standalone secret scan also does not pass in
this integration working tree: the restored latest-main scanner correctly
detects two sensitive assignments in the branch's older ACRA BizFile connector.
The same scanner passes from actual `origin/main` at
`74a5fd2f8bc8a37c02a24dadaaa32a895ce2ee93`. The task explicitly prohibited
altering backend connectors, merging, or rebasing, so that pre-existing branch
divergence was not changed. Consequently this working tree is not yet ready for
the final re-quality gate.

## 2. Reviewed Quality Gate findings

| Finding | Severity | Result |
|---|---:|---|
| F-01 registry-stage stop strands new onboarding | High | Closed in the UI controller and regression tests |
| F-02 secret-scanner weakening | High | Scanner changes removed and exact latest-main blobs restored; current-tree security gate remains blocked by the older connector |
| F-03 stale Start-new-case processing state | Medium | Closed |
| F-04 misleading registry success checkmarks | Medium | Closed |
| F-05 incomplete Policy classifications | Medium | Closed |

No approved shell, navigation, page composition, backend API, domain, service,
connector, workflow, reconciliation, ownership, persistence, or GoldTier
behavior was redesigned or changed in this pass.

## 3. F-01 root cause

The onboarding controller treated document intake as part of case creation's
success boundary. It created a case and immediately opened document intake,
but stored and displayed the returned case only after intake succeeded. Latest
main can validly retain a case at Registry with jurisdiction conflict,
unresolved jurisdiction, an unimplemented provider route, failed acquisition,
or another Registry-stage attention state. Intake is unavailable there, so the
subsequent 409 was misclassified as a document failure and the UI remained on
New onboarding with an impossible targeted-retry message.

## 4. F-01 implementation

`createRetainedCaseBeforeDocumentIntake` now applies the required ordering:

1. create the case;
2. retain the authoritative summary and exact case ID immediately;
3. classify whether Registry state makes intake unavailable;
4. route a Registry stop directly to the existing retained-case screen; or
5. start document intake only for a valid intake-open case.

Registry stops are distinguished from document upload failures. They clear
intake-progress presentation and never generate `Targeted retry required`.
Valid document failures retain the exact case ID and preserve the existing
same-case targeted retry. Selected local files are not presented as uploaded.
The Cases list and detail route continue to load the persisted backend case.

## 5. F-01 latest-main runtime reproduction

The backend used for the reproduction was the actual latest-main worktree at
`74a5fd2f8bc8a37c02a24dadaaa32a895ce2ee93`, isolated on port 8001. The
integrated working-tree frontend was run on port 5175 with its API proxy pointed
to that backend.

The previous failure was reproduced with synthetic AU input and UEN
`202400001A`. Actual create response:

- `POST /api/clm/zero-touch/cases` -> HTTP 201;
- retained case ID `716567b3-d20c-4450-abf0-35daaa85d7de`;
- status `WAITING_FOR_REVIEW`;
- current stage `REGISTRY`;
- jurisdiction resolution `CONFLICT`;
- registry route not selected;
- one active Registry exception.

The retained case was then listed and opened in the integrated frontend. The
visible state was Registry attention/unavailable, with Jurisdiction marked by
an attention symbol and Registry route marked Not selected. The impossible
targeted document retry was absent. Observed follow-up traffic comprised safe
execution-profile reads, case-list reads, the exact case-detail read, and its
read-only document/ownership evidence reads. There was no
`POST /api/clm/zero-touch/cases/{caseId}/intake/documents` and no intake-complete
request. The case remained accessible from Cases under its exact ID.

Browser automation could not attach a local file through the available
controlled-browser surface, so the end-to-end evidence is deliberately split:
the actual latest-main HTTP response and retained-case UI were verified at
runtime, while the exact create-before-intake controller ordering and absence
of the intake callback are proven by the integration test described below. No
mock frontend response or operational fallback was introduced.

## 6. F-01 tests

Focused integration coverage proves:

- create returns an immediate Registry stop, retains the exact summary, invokes
  no document intake, routes to attention, and emits no targeted retry;
- a normal intake-open create retains first and then performs document intake;
- a true document-intake failure retains the same case and preserves targeted
  retry messaging;
- a retained Registry-stop case is rediscovered from Cases and reopened through
  the exact case-detail ID.

These tests are part of the passing 95-test frontend suite.

## 7. F-02 scanner restoration

The initial comparison against `origin/main` identified the UI branch's broad
conversion-call exemption. Both security-tooling files were restored from
latest main without adding an exemption, allowlist, parser exception,
suppression, bypass, or exclusion:

- `scripts/check_secrets.py` blob:
  `beee6edfc0c59b379ddd791b2fc780eae0711fa7`;
- `tests/test_check_secrets.py` blob:
  `41cf1edcf583ad5b048b1fc398b44e6c828a4881`.

The working-tree blob hashes exactly equal their respective `origin/main`
blobs. Final `git diff origin/main -- scripts/check_secrets.py
tests/test_check_secrets.py` is empty (Git reports only the existing Windows
line-ending advisory).

The five scanner unit tests pass. Running the restored scanner from the actual
latest-main worktree passes. Running the required command in the current
integration tree fails, correctly reporting only:

- `apps/backend/app/connectors/acra_bizfile_sandbox.py:157`;
- `apps/backend/app/connectors/acra_bizfile_sandbox.py:213`.

Those lines are in the dormant OAuth implementation present at integration
HEAD `b196d887964f0d93b93dfd2d39c271195eb19af9` and removed by latest main.
Copying or editing that connector, or merging/rebasing main, was expressly out
of scope and was not performed.

## 8. Scanner adversarial verification

Temporary probe files were created outside the repository and scanned with the
restored latest-main implementation. All five required adversarial cases were
detected with matched values suppressed:

| Probe | Expected rule | Result |
|---|---|---|
| literal client-secret assignment | sensitive assignment | Detected |
| literal access-token assignment | sensitive assignment | Detected |
| literal bearer token | bearer authorization | Detected |
| API-key-like assignment | sensitive assignment | Detected |
| conversion-wrapped literal secret | sensitive assignment | Detected |

The probe directory was validated as outside the repository, removed after the
run, and confirmed absent. No probe file was committed or left in the working
tree.

## 9. F-03 stale-state reset

Start a new case now invalidates the prior navigation generation and clears all
case-local presentation state: visible and retained summaries, selected
documents, opened case ID, UEN/jurisdiction form state, request error, polling
warning, intake progress, submitting/resolving flags, retained intake binding,
successful-upload tracking, and failed-document retry tracking. Global
execution-profile/environment state is intentionally preserved.

The regression test starts from completed/review-style transient state, runs
the reset, verifies all eleven presentation reset callbacks, verifies a blank
intake with no stale processing/progress/error presentation, and confirms the
backend Cases source is not cleared.

## 10. F-04 registry status semantics

Registry progress now has explicit semantic variants:

- `SUCCESS` -> checkmark;
- `PENDING` -> neutral dot;
- `ATTENTION` -> exclamation marker;
- `UNAVAILABLE` -> blocked cross;
- `NOT_SELECTED` -> neutral dash;
- `FAILED` -> failure cross.

Jurisdiction conflict and unresolved jurisdiction map to attention; a selected
route maps to success; an unimplemented route maps to unavailable; an absent
route maps to not selected; failed acquisition operations map to failed. Every
row includes a visible `Status: ...` value plus a matching accessible label, so
the distinction does not rely on colour. The approved progress rail geometry
and visual language were retained. Tests cover selected SG success, conflict,
not-selected, failed, and pending states.

## 11. F-05 Policy classifications

Every applicable Policy/runtime value now carries exactly one explicit badge:
`REAL`, `DERIVED`, `PENDING SPONSOR CONFIRMATION`, or `UNAVAILABLE`.

Runtime execution profile, persistence, backend thresholds, and runtime UBO
threshold are Real. Implemented-route and pipeline-stage presentation are
Derived. Q-012, Q-015, and sponsor-dependent UBO/reviewer-authority questions
remain Pending sponsor confirmation. Missing screening threshold, reviewer
count/roles, schedule, production risk rule, and unconfirmed staleness policy
are Unavailable. Tests prove all four classifications render and that Q-012 and
Q-015 are never labelled Real.

## 12. Files changed

Files changed by this bounded remediation:

- `apps/frontend/src/App.tsx`;
- `apps/frontend/src/UiV2Integration.test.tsx`;
- `apps/frontend/src/design-system.css`;
- `apps/frontend/src/pages/CaseStatePanels.tsx`;
- `apps/frontend/src/pages/PolicyRules.tsx`;
- `apps/frontend/src/viewModels.ts`;
- `scripts/check_secrets.py` (restored exactly to `origin/main`);
- `tests/test_check_secrets.py` (restored exactly to `origin/main`);
- `.ai-pipeline/reports/UI_V2_FINAL_REMEDIATION.md`.

Several UI V2 files were already untracked or modified as part of the supplied
working tree; this pass edited only the bounded locations above. Existing
reports were not rewritten. The unrelated untracked filename beginning
`e workspace and multi-document intake` was not opened, changed, or removed.

## 13. Frontend verification

| Check | Result |
|---|---|
| `npm ls --all` | Pass; dependency tree resolved, with platform/feature optional packages reported as optional |
| `npm run typecheck` | Pass |
| `npm test` | Pass: 95/95 across 2 files (58 App, 37 UI V2 integration) |
| `npm run build` | Pass: 42 modules transformed; production bundle emitted |

The test count increased beyond the required baseline of 84. An initial
sandboxed Vite/Vitest attempt could not spawn esbuild (`EPERM`); the authorized
rerun completed successfully and is the result above. No source change was made
for that environment restriction.

## 14. Backend/security verification

| Check | Result |
|---|---|
| Full backend, first run | Pass: 706 passed, 11 skipped |
| Full backend, final repeat | **Fail: 705 passed, 11 skipped, 1 case-list ordering failure** |
| Isolated failed case-list test | Pass: 5/5 immediate reruns |
| Phase 09 | Pass: 39 |
| Phase 10 | Pass: 52 |
| Phase 11 | Pass: 58 |
| Pre-Phase 12 | Pass: 31 |
| Phase 12 | Pass: 16, 11 skipped |
| Contracts | Pass: 44 |
| POC orchestration/provider focused suite | Pass |
| Ruff over backend/scripts/tests | Pass |
| Strict mypy over backend application | Pass: 73 source files |
| `pip check` | Pass |
| Secret-scanner unit tests | Pass: 5 |
| GoldTier validator unit tests | Pass: 5 |
| GoldTier classification | Pass: 19 valid / 19 invalid-quarantined / 48 not validated |
| Restored scanner at actual latest main | Pass |
| Restored scanner in current integration tree | **Fail: two findings in the older ACRA connector** |

The 11 Phase 12 skips are the accepted genuine-Mongo cases because
`PHASE12_MONGO_URI` is absent locally. A non-required broad repository unittest
discovery was also attempted; 58 tests passed and 13 Windows demo-lifecycle
tests failed during setup because protected existing process trees could not be
terminated from the sandbox. This did not alter the requested focused security
or application results and is not used as passing evidence.

The intermittent full-backend failure was
`test_repository_listing_is_empty_ordered_and_defensively_copied`: two cases
created back-to-back were listed in the opposite order on one run. The same
test passed in the earlier full suite and in five isolated reruns. The relevant
backend application/test files have no diff from `origin/main`; only the older
ACRA connector differs under `apps/backend/app`. No backend fix was attempted
under this UI-only scope, and the failed run is retained as gate evidence.

## 15. Git hygiene

- No files were staged.
- No commit, push, merge, rebase, reset, or clean was performed.
- Remediation remains unstaged.
- `git diff --check` was run at final audit; only existing line-ending/access
  advisories are recorded below if present.
- `git diff origin/main -- scripts/check_secrets.py tests/test_check_secrets.py`
  is empty.
- Pre-existing inaccessible pytest-cache directories were not opened, changed,
  or removed.
- Temporary runtime listeners on ports 8001 and 5175 and the controlled browser
  tab were stopped/closed after verification.

## 16. Remaining limitations

The current integration branch is based at `b196d887...`, not latest main. Its
older `acra_bizfile_sandbox.py` still contains the dormant OAuth class and the
two assignments detected by the accepted latest-main scanner. Latest main
removes that code, and its standalone scan is green. Resolving the current-tree
gate requires bringing the already accepted latest-main connector state into
the integration branch through a separately authorized branch synchronization
or equivalent backend-scoped action. Both were prohibited here.

A final full-backend repeat also found one non-deterministic newest-first case
listing failure after an earlier clean full run. Although five isolated reruns
passed and the relevant backend code matches latest main, a re-quality gate
should require a clean full backend run and disposition any recurrence; this
UI-only pass did not alter backend ordering behavior.

The latest-main browser reproduction used actual backend create/list/detail
traffic and the integrated retained-case UI, while controller-level integration
tests prove the precise no-intake call order because controlled-browser file
attachment was unavailable. A final independent gate may repeat the physical
file-selection click path after the branch is synchronized.

## 17. Readiness

Unresolved High findings: 1

Unresolved Medium findings: 0

Registry-stop onboarding compatibility failures: 0

Impossible retry paths: 0

Stale new-case progress states: 0

Misleading registry success icons: 0

Unclassified Policy values: 0

Security scanner UI-branch changes: 0

Security scanner weakening: 0

Scanner bypasses: 0

Secret-detection regressions: 0

Frontend operational mock fallbacks: 0

Fake successful actions: 0

Unsupported endpoint calls: 0

The unresolved High count reflects the mandatory current-tree security scan,
not a remaining UI implementation defect or scanner weakening. Because every
metric must be zero for Ready and a required command is red, the bounded pass
cannot truthfully issue final re-quality-gate readiness.

NOT READY FOR UI V2 FINAL RE-QUALITY GATE
