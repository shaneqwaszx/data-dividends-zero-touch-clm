# Review/Rework UI Follow-up — Independent Quality Gate

Date: 2026-09-20<br>
Role: fresh independent read-only quality-gate reviewer<br>
Verdict: **FAIL**

## 1. Executive result

The frozen review/rework UI follow-up is **not publication-ready**. The main field-review
slice is substantially implemented and the deterministic frontend, type, build, contract,
governance, and secret checks are green. However, exact `PASS` is blocked by current
acceptance defects and missing required browser evidence:

1. the recovered-intake predicate can expose `Continue recovered intake` while a different
   current document is still failed, contrary to UI-RR-07 and the planner's explicit
   “no current record is failed” rule;
2. an evidence mutation does not disable the case's Priority or Delete controls, so a user
   can start a second case mutation while the first outcome is uncertain, contrary to the
   planner's pending-mutation invariant and UI-RR-12;
3. the required real-browser final-review and failed-replacement retry/continue lanes are
   not proved; the implementation report explicitly says the public harness cannot create
   a failed replacement, and the authored Playwright test covers only one partial review,
   ordinary replacement, history, and reload; and
4. the replacement/retry file controls are not keyboard-accessible because the actual file
   inputs use the HTML `hidden` attribute and the styled wrapping labels are not focusable.

The guarded Playwright run was also not stable in this gate: the first fresh run failed the
history-after-reload assertion (2/3 passed), while one complete fresh rerun passed 3/3. The
passing rerun is recorded, but it does not erase the required-lane gaps or establish a
stable exact PASS.

No implementation, test, configuration, contract, planner, or ordinary documentation was
modified by this reviewer. This report is the sole authorized write.

## 2. Frozen reviewed-content identity

- Worktree: `C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm-review-rework-ui`
- Branch: `followup/review-rework-ui`
- `BASE_SHA`: `cab05d7dc98d4c50c8fc096835fe49802d5896e2`
- Current `HEAD`: `cab05d7dc98d4c50c8fc096835fe49802d5896e2`
- Local `origin/main`: `cab05d7dc98d4c50c8fc096835fe49802d5896e2`
- Merge base: `cab05d7dc98d4c50c8fc096835fe49802d5896e2`
- Ahead/behind: `0/0`
- Staged paths: none
- Reviewed implementation state: uncommitted working tree
- Deterministic aggregate SHA-256 over the sorted `SHA256  path` manifest below:
  `4a92dfa5e29c726f4d410299c52953322972c35d2b856bc8785ecebbd1385037`

The aggregate was computed before execution and repeated after all checks. It was unchanged.

| SHA-256 | Reviewed path |
|---|---|
| `c303eb67da894ee16bfa5f798f7023c7d327783a725d4c1223851d60d364e247` | `.ai-pipeline/001_planner/REVIEW_REWORK_UI_FOLLOWUP.md` |
| `101828e18d25eeb11fc80b9cc934b7db4dfef9666aaf394261b50951ee26e01d` | `.ai-pipeline/001_planner/REVIEW_REWORK_UI_EXECUTION_ADDENDUM.md` |
| `650dcf3cc3dd37fce520c15bad01cb8d5b47b4b9ed36d8d3ccab494046010f3b` | `.ai-pipeline/reports/REVIEW_REWORK_UI_IMPLEMENTATION.md` |
| `569febb8c4e842f469219aaef22f6b1dc193fe0327fe7a799ad41747f781caa8` | `apps/frontend/e2e/authenticated-zero-touch.e2e.ts` |
| `7aea3894a55b4053588c85574495c131fe78cf2667978f29f0c36ed85bb31f5c` | `apps/frontend/src/Phase15CNavigation.test.tsx` |
| `74c9687e321b5c84c1a4e09faa8ab577866bbce43666537574119d4470000c58` | `apps/frontend/src/UiV2Integration.test.tsx` |
| `2aa6fc1d80c509546b20d81e2eec4efa4c6b85db42775b12b8d68cd40650afc1` | `apps/frontend/src/pages/CaseDetail.tsx` |
| `480ea494ff2e5c60d0e356f46daf128fdc8ca18019c186ce24add97521a82cec` | `apps/frontend/src/pages/DocumentEvidencePanel.tsx` |
| `74bb2afa978e5981e91355e60412242f5af25b4026cc1651d3fe03567f1f7875` | `apps/frontend/src/pages/DocumentEvidencePanel.test.tsx` |
| `9e8e72c8d146dfb0aefa945bcf965800e107451dfe4d0384b42665f04caa83bf` | `apps/frontend/src/styles.css` |

The reviewed path set includes every tracked change and every task-owned new file supplied
for this follow-up. Current backend/API/auth/cache owner files and relevant contracts/tests
were read as unchanged authority, not included in the changed-content aggregate.

## 3. Capability and resource preflight

- Available and used: local PowerShell, Git read-only inspection, Python 3.12 task-local
  virtual environment, installed Node/npm dependencies, Vitest, TypeScript, Vite 7.1.11,
  repository contract/governance scripts, and the guarded Playwright 1.56.1 runner with
  Chromium and repository-owned loopback lifecycle.
- The sandbox initially denied the esbuild child process with `spawn EPERM`; the identical
  focused test command was rerun with the approved process-spawn permission and passed.
- No external plugin, credential, provider, remote API, Mongo URI, database, or protected
  artefact was accessed. Physical Mongo is not applicable to this frontend-only change.
- The guarded runner owned its backend/frontend ports and cleaned them after both browser
  runs. No port or service was manually reserved.
- `pre_pr_check.py` was not run or claimed because the planner explicitly assigns it to a
  later clean committed PR-readiness state, while this tree is intentionally uncommitted.

## 4. UI-RR acceptance results

| ID | Result | Independent assessment |
|---|---|---|
| UI-RR-01 | **PASS** | Current pending fields expose the existing accept/reject/correct actions; Accept is absent without a suggestion; focused tests and browser traffic prove the exact accepted payload. |
| UI-RR-02 | **PASS** | Partial counts and independent-blocker wording are present; one real-browser decision remained waiting, issued one review POST, and issued no `/resume`. |
| UI-RR-03 | **FAIL — required evidence incomplete** | Source correctly refreshes summary/documents/ownership and does not call `/resume`, but the real-browser test stops after one partial decision. It does not complete the supported field sequence or observe backend-authored final-review progression as required. |
| UI-RR-04 | **PASS (deterministic)** | Missing and below-threshold corrected evidence is labelled retained-but-replacement-required from the case-bound threshold. |
| UI-RR-05 | **PARTIAL / BLOCKED BY UNSTABLE BROWSER EVIDENCE** | Static/component evidence makes history read-only and bidirectionally labelled. The first fresh browser run failed to reconstruct `Evidence history (1)` after reload; the rerun passed. |
| UI-RR-06 | **FAIL — required evidence incomplete** | Source exposes targeted retry only for current `DOCUMENT_REUPLOAD_REQUIRED`, but neither the focused interaction suite nor the real browser executes retry and proves authoritative post-retry refetch/call counts. |
| UI-RR-07 | **FAIL — reproducible source defect** | `canContinueRecoveredIntake` proves one recovered lineage but does not reject another current failed document. It can therefore advertise/call resume before all current failed evidence is recovered. No real-browser failed-replacement/continue lane exists. |
| UI-RR-08 | **PASS** | Fresh deterministic evidence proves one refresh after 409 with one mutation call, refreshed state, stale copy, and no replay/resume. |
| UI-RR-09 | **PASS** | Auth transport retains global 401 session clearing; stale actor completion is contained; safe 404 uses the generic unavailable-case presentation. Backend RBAC remains authoritative. |
| UI-RR-10 | **PASS (deterministic)** | 503 and ambiguous transport outcomes issue one mutation, perform one bounded three-read refresh, do not replay, and preserve last-confirmed state when refresh fails. |
| UI-RR-11 | **PASS for the shared settlement path** | Generation, case ID, and actor ID contain stale review success/failure; the panel is keyed by actor and case, so inline state does not migrate through those identities. |
| UI-RR-12 | **FAIL** | The synchronous evidence-mutation ref blocks duplicate evidence dispatch, but `PriorityControl` and the Delete control are not disabled or bound to that ref while evidence is busy. The planner required every displayed-case mutation to be disabled. |
| UI-RR-13 | **PARTIAL** | Controls are derived from backend queries with no persistent client store; deterministic remount behavior is sound. The fresh browser history-after-reload assertion failed once and passed once. |
| UI-RR-14 | **PASS within the authorized Case Detail slice** | Assign reviewer and Return for rework are absent from Case Detail. Their component files were correctly retained because repository search found active `HomeOnboarding` consumers outside this write boundary; no unsafe retirement occurred. No final approval control was added. |
| UI-RR-15 | **PASS** | Native URL ownership, guarded network behavior, Mock/Local/not-approval labels, and safe existing navigation remain intact in source and the passing browser rerun. |

## 5. Findings

### F-01 — Current failed evidence does not suppress recovered-intake continuation

**Severity:** high current acceptance blocker<br>
**Affected criterion:** UI-RR-07

`canContinueRecoveredIntake` returns true when it finds any valid recovered lineage. Its
candidate check rejects that candidate when failed, but there is no preceding or following
check that every other current document is non-failed. A multi-document case containing a
valid recovered pair plus an unrelated current `FAILED` record therefore receives the
“Recovered intake is ready” banner and an enabled `/resume` control. The backend remains
authoritative and should fail closed, so this is not evidence of target replay; it is a
false browser eligibility/success cue and an unnecessary business mutation expressly
prohibited by the planner.

Required remediation: make continuation require zero failed current records and add the
missing negative multi-document regression before independently rechecking.

### F-02 — Evidence-busy state does not serialize all displayed-case mutations

**Severity:** medium current acceptance blocker<br>
**Affected criteria:** UI-RR-10, UI-RR-12

The evidence panel disables its own controls through `isBusy`, and the common settlement
ref rejects duplicate evidence actions. However, `PriorityControl` receives no disabled or
shared-pending state, and the Case Detail Delete button is not disabled. Its dialog/confirm
path also bypasses `mutationPending`. A user can therefore begin a priority update or
permanent deletion while a review/replacement/retry/resume result is uncertain. Backend
locking and reauthorization remain safety owners, but the frontend violates the explicit
one-pending-mutation interaction contract and creates avoidable competing settlements.

Required remediation: bind all Case Detail mutation entry points to the one case-action
pending owner (including the controls' disabled state and dispatch guard) and add
cross-control duplicate/concurrency tests.

### F-03 — Required browser lanes are absent, and the authored lane is unstable

**Severity:** current evidence blocker<br>
**Affected criteria:** UI-RR-03, UI-RR-05, UI-RR-06, UI-RR-07, UI-RR-13

The Playwright journey exercises one partial review, ordinary replacement, read-only
history, reload/deep link, and Mock truth. It does not finish the review sequence, create a
failed accepted replacement, retry that exact current failed record, prove continuation
eligibility from authoritative lineage, or invoke continuation once. The implementation
report accurately discloses that the public guarded runtime cannot deterministically
create the failed-replacement state. Under the quality-gate rules this is missing
infrastructure for those dependent browser claims, not evidence that the claims passed.

In addition, the first independent browser run failed at the post-reload history assertion
after 15 seconds (2/3 tests passed). A complete fresh rerun passed 3/3. The divergence is
recorded as unstable current evidence rather than silently replacing the failed run with
the passing run.

Required remediation: provide a repository-authorized deterministic setup path for the
failed-replacement browser state (without adding product fault behavior), complete the
UI-RR-03 final-review browser lane, and remove the reload/history instability.

### F-04 — Replacement and retry upload controls are not keyboard-operable

**Severity:** medium accessibility blocker<br>
**Affected criteria:** UI-RR-05, UI-RR-06 and the planner's accessibility requirements

Both `Retry affected document` and `Replace current document` are styled `<label>` elements
wrapping `<input hidden type="file">`. The HTML `hidden` attribute removes the input from
the accessibility tree and keyboard tab order, while the label itself has no native button
semantics or focusability. Pointer activation works, but keyboard-only users cannot reach
these required recovery controls.

Required remediation: use a keyboard-operable native control pattern with an accessible
name and focus state, then add keyboard-focused component and real-browser coverage.

## 6. Contract, architecture, security, and scope assessment

- No backend route, public request/response model, shared type, cache key, authentication
  rule, persistence schema, provider, configuration, target ledger, business rule, mapping,
  or architecture owner changed.
- Exact saved-decision repair is conservative and contract-aligned: only current, fully
  final `REVIEWED` evidence at `WAITING_FOR_REVIEW / DOCUMENT` exposes it; payloads come
  from retained typed status/value/note; final values remain read-only; no browser
  `/resume` is issued for review repair.
- Success and uncertain review outcomes perform the required bounded authoritative read;
  409/503/network paths do not replay the mutation; refresh failure preserves last-confirmed
  data and exposes only a read-only refresh action.
- Case/actor/generation binding, the panel's actor/case React key, safe 404, and global 401
  handling preserve session and case isolation for the reviewed evidence path.
- Original suggestions/provenance remain immutable in the browser presentation. Superseded
  evidence is historical and receives no mutation controls.
- ACRA remains Mock by default, generic sandbox-shaped ACRA remains Partial, BizFile remains
  Dormant, IDP remains Local/Mock, ownership remains the local deterministic Decimal engine,
  and GoldTier remains Mock only. `COMPLETED / MOCK_GOLDTIER_SUBMITTED` is not approval or
  Ready-for-Approval. No Live provider, production SSO, Camunda, legal UBO, compliance, or
  production reviewer claim was added.
- Q-014/Q-015/Q-016 remain sponsor dependencies for production reviewer identity,
  separation of duties, source authority, and production access policy. They do not excuse
  the current bounded UI defects and evidence gaps.
- The two unsupported dialog components were not retired because active out-of-scope
  consumers remain. This is safe component-retirement behavior, not dead-code leakage from
  Case Detail.

## 7. Independent execution evidence

| Check | Fresh result on the frozen content |
|---|---|
| Focused Vitest: panel + UI V2 + Phase 15C navigation | **PASS — 3 files, 81/81 tests**. Initial sandbox attempt did not collect due `spawn EPERM`; identical approved rerun passed. |
| Full frontend Vitest | **PASS — 10 files, 199/199 tests**; existing React Router SSR `useLayoutEffect` warnings only. |
| Frontend typecheck | **PASS** |
| Frontend production build | **PASS** — Vite 7.1.11, 109 modules; JS 354.22 kB / 103.03 kB gzip; CSS 60.96 kB / 12.99 kB gzip |
| Guarded Playwright run 1 | **FAIL — 2/3 passed**; history-after-reload assertion timed out |
| Guarded Playwright run 2 | **PASS — 3/3 passed in 7.9 s**; runner's trailing “2 tests” prose is stale, while direct Playwright output is authoritative |
| Canonical contract suite | **PASS — 44/44 tests** |
| `check_architecture.py` | **PASS** |
| `check_project_state.py` | **PASS** |
| `check_tooling_config.py` | **PASS** |
| `check_secrets.py` | **PASS** |
| `dev_context.py` | **PASS**; branch/SHAs/status remained as recorded |
| `git diff --check` | **PASS**; only LF-to-CRLF working-copy notices |
| Explicit final-newline check for every task-owned new file | **PASS** |
| Explicit trailing-whitespace check for task-owned new files | No unintended trailing whitespace; the two-space Markdown line breaks in the addendum/report headers are intentional |
| Full backend pytest / Ruff / mypy / physical Mongo | **Not required / not run** for this frontend-only frozen delta; owning backend and persistence sources are unchanged |
| `pre_pr_check.py` | **Not run by design**; clean committed PR-readiness prerequisite is absent |

The green deterministic suites do not test the counterexample in F-01, global competing
mutations in F-02, the missing browser lanes in F-03, or keyboard operation in F-04.

## 8. Verdict and readiness

**INDEPENDENT QUALITY-GATE VERDICT: FAIL**

- Current bounded follow-up acceptance: **not accepted**.
- Governance/publication readiness: **not ready**. Repository publication requires an
  exact independent `PASS`; this report does not provide one.
- Remediation scope: F-01 through F-04 only, plus their focused and affected regressions.
- Required next action: a separately assigned remediation run, followed by a fresh
  independent re-quality gate over a new frozen content identity.
- This verdict authorizes no stage, commit, push, PR, merge, deployment, provider work,
  production claim, or next phase.

## 9. Reviewer safety and final Git state

Before this report, the working tree contained five modified tracked implementation/test
paths and five task-owned untracked planner/report/source/test paths, with no staged path.
The source aggregate remained unchanged through the gate. After this report, the only
additional path is:

- `.ai-pipeline/reports/REVIEW_REWORK_UI_QUALITY_GATE.md`

No Git mutation, branch switch, dependency installation, implementation remediation,
database operation, external message, publication action, or protected artefact access
occurred.

---

# Fresh Re-Quality Gate After F-01–F-04 Remediation

Date: 2026-09-20<br>
Role: fresh independent read-only re-quality-gate reviewer<br>
Verdict: **FAIL**

## 10. Re-QG executive result

The original independent `FAIL` above is preserved as historical evidence. The bounded
remediation closes F-01, F-02, and F-04 in current source and fresh deterministic tests:

- recovered-intake continuation now fails closed when any current document is failed;
- the `CaseDetail` identity-token mutation owner now serializes evidence, priority,
  deletion (including an already-open confirmation), exception, reconciliation, and
  recovery actions; and
- replacement and targeted-retry uploads now use labelled, keyboard-focusable native
  file inputs with visible focus treatment.

The remediation also expands the authored Playwright journey to complete all four field
reviews, require backend-authored `REVIEWED`, assert no browser `/resume`, operate the
replacement input, inspect read-only history, and reload the deep-linked case.

Exact `PASS` is nevertheless blocked because that required browser lane did not complete
in either fresh independent guarded run on the frozen content:

1. run 1 passed the login and clean-Mock tests, then timed out after case creation while
   polling for the review case's first document (`2/3 passed`); and
2. run 2 passed login, then the clean-Mock workflow timed out waiting for completion;
   the review/reload test did not run (`1 passed`, `1 failed`, `1 did not run`).

These two different timeouts confirm unstable current browser evidence. A prior
implementer-authored passing rerun cannot supply independent proof for final review,
replacement, or reload stability on this re-QG. This is a required-evidence failure, not
a newly reproduced deterministic product defect.

The failed-replacement browser scenario is separately classified as infeasible in the
current guarded public runtime: `scripts/e2e_backend_server.py` explicitly sets
`DEMO_CONTROLS_ENABLED=false` and the deterministic local replacement provider exposes
no public fault selector. The re-QG does **not** require a fabricated production hook,
hidden setup endpoint, or browser interception. Its positive/negative lineage,
targeted-retry, authoritative-refetch, and continuation behavior is accepted from the
fresh deterministic tests. This bounded infrastructure limitation is not the reason for
the `FAIL`; the independently failing supported public browser journeys are.

## 11. Frozen re-reviewed content identity

- Worktree: `C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm-review-rework-ui`
- Branch: `followup/review-rework-ui`
- `BASE_SHA`, `HEAD`, local `origin/main`, and merge base:
  `cab05d7dc98d4c50c8fc096835fe49802d5896e2`
- Ahead/behind: `0/0`
- Staged paths: none
- Reviewed implementation state: uncommitted working tree
- Original quality-gate report SHA-256 before this authorized append:
  `806fd88a4165a5010689c2e8f628fee53511166fb49a7bba7687d3dc416227f4`
- Deterministic aggregate SHA-256 over the sorted `SHA256  path` manifest below:
  `85d4a6584fd36ac0da1e2f8bd2aec3287e08e40f779d5b8bc12ec3e4c01116a1`

The aggregate was computed before fresh execution and repeated after every implementation
and test check. It was unchanged. This re-QG report is the sole excluded write.

| SHA-256 | Re-reviewed path |
|---|---|
| `101828e18d25eeb11fc80b9cc934b7db4dfef9666aaf394261b50951ee26e01d` | `.ai-pipeline/001_planner/REVIEW_REWORK_UI_EXECUTION_ADDENDUM.md` |
| `c303eb67da894ee16bfa5f798f7023c7d327783a725d4c1223851d60d364e247` | `.ai-pipeline/001_planner/REVIEW_REWORK_UI_FOLLOWUP.md` |
| `264326c231840ee2cb32a556a69498450f327519480e18dc899e3b2c34df89b8` | `.ai-pipeline/reports/REVIEW_REWORK_UI_IMPLEMENTATION.md` |
| `284ffb132fa836dd1e8a62d98aca27839860acca4e9df030b119a2452b248c0` | `apps/frontend/e2e/authenticated-zero-touch.e2e.ts` |
| `0faefa580f454cbda7664dde98aca27839860acca4e9df030b119a2452b248c0` | `apps/frontend/src/Phase15CNavigation.test.tsx` |
| `74c9687e321b5c84c1a4e09faa8ab577866bbce43666537574119d4470000c58` | `apps/frontend/src/UiV2Integration.test.tsx` |
| `6c26e08e29190cf39bbb19c57e9905dfff8bc2b3f96b221378c3fb1db1a855ca` | `apps/frontend/src/pages/CaseDetail.tsx` |
| `edfc82f145429bddd6d94777643e019098dec0184f475b2c64d0fcba0fd18090` | `apps/frontend/src/pages/DeleteCaseDialog.tsx` |
| `f836c47ffa0628a4ea0cfd10a4013e22b38a2fdd7185e62f039531dc4ef18c8f` | `apps/frontend/src/pages/DocumentEvidencePanel.tsx` |
| `cfc09fe4a083edb58013059f8b6781fee4ca93e1bc5966f915d4a9dcef17396b` | `apps/frontend/src/pages/DocumentEvidencePanel.test.tsx` |
| `6a1e9a27bb8411b69c4a9057a9ddf3c1443dfd41cb9c1336cc03d4275db53a81` | `apps/frontend/src/pages/PriorityControl.tsx` |
| `fed28e1a9c58eff1a203a23f342ad0bcc02702b67e4eb772240ff3a72535437e` | `apps/frontend/src/styles.css` |

## 12. Finding dispositions

### F-01 — CLOSED

`canContinueRecoveredIntake` now rejects the entire control when any current document is
`FAILED`. Fresh component evidence includes the previously missing multi-document
counterexample: one valid recovered lineage plus a second unrelated current failed
record. Continuation remains bound to `PENDING_INPUTS / DOCUMENT`, the latest typed
timeline event, and bidirectional current-to-failed supersession lineage.

### F-02 — CLOSED

`CaseDetail` owns one synchronous `mutationPending` identity token and passes the shared
busy/blocked state into `PriorityControl`, `DeleteCaseDialog`, exception controls,
reconciliation, recovery, and the evidence panel. `deleteCase` and priority save also
recheck the token at dispatch, so same-tick actions and an already-open delete dialog do
not bypass serialization. Fresh navigation tests prove evidence-to-priority/delete and
priority-to-evidence/delete exclusion.

### F-03 — OPEN, NARROWED TO REQUIRED BROWSER STABILITY/EVIDENCE

The authored journey now contains the required supported final-review, replacement,
history, and reload assertions, but neither fresh independent guarded run completed that
journey. The first stopped before the document became observable; the second stopped in
the preceding clean-Mock test. Therefore UI-RR-03 and the real-browser portions of
UI-RR-05/UI-RR-13 remain unverified on this re-QG.

The failed-replacement retry/continue browser sub-lane is explicitly infeasible under
the guarded `demo_controls_enabled=False` composition. Fresh deterministic coverage is
proportionate and accepted for UI-RR-06/UI-RR-07; no product-only fault surface should be
added to manufacture a pass.

### F-04 — CLOSED

The file controls no longer use the HTML `hidden` attribute. Each visually hidden native
input remains in the accessibility tree and tab order, inherits an accessible name from
its wrapping label, and produces a visible `:focus-within` outline. Fresh component tests
focus both replacement and retry inputs and dispatch targeted retry through the native
input. The authored browser lane focuses replacement before upload, though that browser
assertion did not execute successfully in this independent gate because of F-03.

## 13. Acceptance re-assessment

| Acceptance | Fresh re-QG result |
|---|---|
| UI-RR-01, 02, 04, 08–12, 14, 15 | **PASS** — source inspection plus fresh focused/full evidence preserves valid actions, partial blocking, uncertainty handling, stale identity containment, cross-control serialization, truthful scope, safe navigation, and Mock/Local labels. |
| UI-RR-03 | **FAIL — required browser evidence incomplete**. The deterministic settlement path is sound and the authored lane is expanded, but no fresh independent browser run reached backend-authored final review. |
| UI-RR-05 | **PARTIAL** — deterministic current/history lineage and read-only controls pass; fresh browser reload/history reconstruction did not complete. |
| UI-RR-06 | **PASS WITH BOUNDED EVIDENCE CLASSIFICATION** — fresh deterministic tests dispatch the exact targeted retry and then perform three authoritative reads. The browser failure-state setup is unavailable under the guarded public runtime. |
| UI-RR-07 | **PASS WITH BOUNDED EVIDENCE CLASSIFICATION** — fresh positive/negative lineage matrices include F-01's multi-document failed-current case and preserve one explicit continuation owner. The guarded public runtime cannot create the prerequisite failed replacement. |
| UI-RR-13 | **PARTIAL** — source and deterministic remount ownership remain server-derived; fresh real-browser reload stability is not established. |

No backend route, API/model/type, cache key, authentication rule, persistence schema,
provider, configuration, business rule, mapping, target-ledger owner, or architecture
owner changed. Q-014/Q-015/Q-016 remain later sponsor dependencies and do not authorize
production reviewer, source-authority, assignment, approval, or Live claims.

## 14. Fresh independent execution evidence

| Check | Re-QG result |
|---|---|
| Focused Vitest: panel + UI V2 + Phase 15C navigation | **PASS — 3 files, 87/87 tests**. Initial sandboxed startup returned `spawn EPERM`; the identical approved child-process run passed. |
| Full frontend Vitest | **PASS — 10 files, 205/205 tests**; existing React Router SSR `useLayoutEffect` warnings only. |
| Frontend typecheck | **PASS** |
| Frontend production build | **PASS** — Vite 7.1.11, 109 modules; JS 355.07 kB / 103.22 kB gzip; CSS 61.04 kB / 13.02 kB gzip. |
| Guarded Playwright run 1 | **FAIL — 2/3 passed**; review journey timed out polling for the first document after case creation. |
| Guarded Playwright run 2 | **FAIL — 1 passed, 1 failed, 1 did not run**; clean Mock workflow timed out before completion, so the review/reload journey did not execute. |
| Canonical contract suite | **PASS — 44/44 tests** |
| `check_architecture.py` | **PASS** |
| `check_project_state.py` | **PASS** |
| `check_tooling_config.py` | **PASS** |
| `check_secrets.py` | **PASS** |
| `dev_context.py` | **PASS**; branch/SHAs/status remained as recorded. |
| `git diff --check` | **PASS**; only LF-to-CRLF working-copy notices. |
| Task-owned final-newline check | **PASS** |
| Guarded lifecycle cleanup | **PASS** — no listeners remained on ports 8867/4275 after either run. |
| Full backend pytest / Ruff / mypy / physical Mongo | **Not required / not run** for this frontend-only remediation; backend and persistence owners are unchanged. |
| `pre_pr_check.py` | **Not run by design**; the planner assigns it to the later clean committed PR-readiness state, which this uncommitted gate does not satisfy. |

## 15. Fresh re-QG verdict and readiness

**INDEPENDENT RE-QUALITY-GATE VERDICT: FAIL**

- F-01, F-02, and F-04 remediation: **accepted**.
- F-03 remediation: **not accepted as complete** because the required supported guarded
  browser journey remains unstable and independently unverified.
- Current bounded follow-up acceptance: **not accepted**.
- Governance/publication readiness: **not ready**. Publication requires an exact
  independent `PASS`; this report does not provide one.
- Required next action: a separately assigned, bounded browser/lifecycle stabilization
  remediation for the supported public journeys, followed by a fresh independent re-QG.
- The failed-replacement browser setup remains an explicit guarded-runtime limitation;
  stabilization must not add a product fault route, enable demo controls, or weaken the
  network guard merely to create evidence.
- This verdict authorizes no stage, commit, push, PR, merge, deployment, provider work,
  production claim, or next phase.

## 16. Re-QG safety and final Git state

The reviewed implementation aggregate remained unchanged throughout the re-QG. The only
authorized content write was this append to
`.ai-pipeline/reports/REVIEW_REWORK_UI_QUALITY_GATE.md`. No implementation, test,
configuration, planner, contract, decision, ordinary documentation, dependency, or Git
state was modified. No database, external provider, credential, protected artefact, or
remote service was accessed.

---

# Final Fresh Re-Quality Gate After F-03 E2E Stabilization

Date: 2026-09-20<br>
Role: final fresh independent scoped re-quality-gate reviewer<br>
Verdict: **FAIL**

## 17. Final re-QG executive result

The two earlier independent `FAIL` verdicts above remain preserved as historical
evidence. The final stabilization cycle changed the guarded E2E file and the
implementer's evidence report; every product, component-test, navigation-test, and style
file accepted by the preceding re-QG retained the exact previously reviewed SHA-256.
Source inspection confirms that the E2E change does not remove the final-review,
no-`/resume`, Mock/not-approval, replacement, read-only-history, or reload assertions.
It replaces the login wait on the separately queried Dashboard heading with the
authenticated `Main workspace` navigation, and replaces the clean lane's transient
live-view completion wait with a public case-status poll followed by the canonical Case
Detail projection.

The public case-status synchronization is aligned with the claimed authoritative
condition. The login synchronization diagnosis is not independently verified as a
complete stabilization, however: the first fresh permitted guarded run timed out for 30
seconds waiting for that new `Main workspace` boundary in test 1. The two remaining
serial tests did not run. Two immediately subsequent identical full-suite runs passed
3/3 in 10.5 seconds and 9.9 seconds. This pass/fail divergence reproduces the required
browser-evidence instability at the newly selected boundary rather than establishing the
requested repeatability.

The initial sandbox attempt failed before collection with the known Vite/esbuild
`spawn EPERM` restriction and is classified only as missing sandbox process-spawn
permission. The identical permitted run then reached Playwright and failed an assertion;
that execution is authoritative fresh evidence and cannot be replaced by later passing
runs. The assignment explicitly requires `FAIL` if any fresh run fails. Exact `PASS` is
therefore unavailable on this content identity.

## 18. Frozen final reviewed-content identity

- Worktree: `C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm-review-rework-ui`
- Branch: `followup/review-rework-ui`
- `BASE_SHA`, `HEAD`, local `origin/main`, and merge base:
  `cab05d7dc98d4c50c8fc096835fe49802d5896e2`
- Ahead/behind: `0/0`
- Staged paths: none
- Reviewed implementation state: uncommitted working tree
- Quality-gate report SHA-256 immediately before this authorized append:
  `fbef74bf7a79f5807d316b3f00aa9d3b011deec914767d55e01c7d504374930b`
- Deterministic aggregate SHA-256 over the sorted `SHA256  path` manifest below:
  `2022284f2e984b057edd2696677849bc3a803641f46e46162828bf050c45613e`

The aggregate was computed before execution and repeated after all implementation and
test checks. It was unchanged. This report is the sole excluded write.

| SHA-256 | Final reviewed path |
|---|---|
| `101828e18d25eeb11fc80b9cc934b7db4dfef9666aaf394261b50951ee26e01d` | `.ai-pipeline/001_planner/REVIEW_REWORK_UI_EXECUTION_ADDENDUM.md` |
| `c303eb67da894ee16bfa5f798f7023c7d327783a725d4c1223851d60d364e247` | `.ai-pipeline/001_planner/REVIEW_REWORK_UI_FOLLOWUP.md` |
| `1556f4b92b1460088012192a9df62b9b01e91bf48adbbd9253ff077761f2deb7` | `.ai-pipeline/reports/REVIEW_REWORK_UI_IMPLEMENTATION.md` |
| `623d040cb361d51839a51878a1402a279fbce4fbc3a434381b793d2541521fbc` | `apps/frontend/e2e/authenticated-zero-touch.e2e.ts` |
| `0faefa580f454cbda7664dde98aca27839860acca4e9df030b119a2452b248c0` | `apps/frontend/src/Phase15CNavigation.test.tsx` |
| `74c9687e321b5c84c1a4e09faa8ab577866bbce43666537574119d4470000c58` | `apps/frontend/src/UiV2Integration.test.tsx` |
| `6c26e08e29190cf39bbb19c57e9905dfff8bc2b3f96b221378c3fb1db1a855ca` | `apps/frontend/src/pages/CaseDetail.tsx` |
| `edfc82f145429bddd6d94777643e019098dec0184f475b2c64d0fcba0fd18090` | `apps/frontend/src/pages/DeleteCaseDialog.tsx` |
| `f836c47ffa0628a4ea0cfd10a4013e22b38a2fdd7185e62f039531dc4ef18c8f` | `apps/frontend/src/pages/DocumentEvidencePanel.tsx` |
| `cfc09fe4a083edb58013059f8b6781fee4ca93e1bc5966f915d4a9dcef17396b` | `apps/frontend/src/pages/DocumentEvidencePanel.test.tsx` |
| `6a1e9a27bb8411b69c4a9057a9ddf3c1443dfd41cb9c1336cc03d4275db53a81` | `apps/frontend/src/pages/PriorityControl.tsx` |
| `fed28e1a9c58eff1a203a23f342ad0bcc02702b67e4eb772240ff3a72535437e` | `apps/frontend/src/styles.css` |

Relative to the preceding re-QG identity, the final implementation-content delta is
limited to `authenticated-zero-touch.e2e.ts`. The implementation report was updated to
record that cycle. All other reviewed hashes match the preceding report. No product
source, component test, shared type/model, API, cache key, authentication rule,
persistence schema, connector, configuration, business rule, mapping, provider status,
or architecture owner changed in the final cycle.

## 19. Prior finding dispositions and acceptance

### F-01 — CLOSED

The accepted multi-document fail-closed continuation implementation and focused
counterexample are byte-identical to the preceding re-QG. Fresh focused and full suites
remain green.

### F-02 — CLOSED

The accepted single case-action mutation owner and cross-control serialization
implementation/tests are byte-identical to the preceding re-QG. Fresh focused and full
suites remain green.

### F-03 — OPEN: FINAL STABILIZATION NOT REPEATABLE

The final E2E file retains the supported final-review, replacement, history, reload, and
truthfulness assertions, and two fresh runs completed all three tests. A preceding fresh
permitted run nevertheless failed at the replacement login readiness boundary and
prevented the two substantive later tests from running. The requested multiple
consecutive guarded full-suite passes were not obtained after that failure. UI-RR-03 and
the real-browser portions of UI-RR-05/UI-RR-13 therefore remain unstable evidence on
this final gate. UI-RR-06/UI-RR-07 retain the preceding bounded deterministic acceptance;
the guarded runtime still cannot create failed-replacement state without an unauthorized
fault surface.

### F-04 — CLOSED

The accepted keyboard-operable native upload controls, focus treatment, and focused
tests are byte-identical to the preceding re-QG. Fresh focused and full suites remain
green.

No assertion, network guard, Mock/Local truth label, no-`/resume` check, or product
contract was weakened by the final E2E edit. The blocker is insufficient repeatable
execution evidence, not a newly identified product-contract defect.

## 20. Final fresh independent evidence

| Check | Final re-QG result |
|---|---|
| Guarded Playwright sandbox preflight | **NOT COLLECTED — missing sandbox permission**; Vite/esbuild returned `spawn EPERM`. Identical permitted command followed. |
| Guarded Playwright permitted run 1 | **FAIL — 1 failed, 2 did not run**; test 1 timed out after 30 seconds waiting for `Main workspace` after sign-in. |
| Guarded Playwright permitted run 2 | **PASS — 3/3 in 10.5 seconds**. |
| Guarded Playwright permitted run 3 | **PASS — 3/3 in 9.9 seconds**. |
| Required consecutive repeatability | **FAIL** — the fresh sequence contains an assertion failure and only two subsequent passes; it does not independently substantiate the reported three-pass stabilization. |
| Focused Vitest: panel + UI V2 + Phase 15C navigation | **PASS — 3 files, 87/87 tests**; existing React Router SSR warnings only. |
| Full frontend Vitest | **PASS — 10 files, 205/205 tests**; existing React Router SSR warnings only. |
| Frontend typecheck | **PASS**. |
| Frontend production build | **PASS** — Vite 7.1.11, 109 modules; JS 355.07 kB / 103.22 kB gzip; CSS 61.04 kB / 13.02 kB gzip. |
| Canonical contract suite | **PASS — 44/44 tests**. |
| `check_architecture.py` | **PASS**. |
| `check_project_state.py` | **PASS**. |
| `check_tooling_config.py` | **PASS**. |
| `check_secrets.py` | **PASS**. |
| `dev_context.py` | **PASS**; branch, revisions, and tracked task paths remained as recorded. |
| `git diff --check` | **PASS**; only LF-to-CRLF working-copy notices. |
| Task-owned final-newline and aggregate identity checks | **PASS**. |
| Guarded lifecycle cleanup | **PASS** — no listener remained on ports 8867/4275. |
| Full backend pytest / Ruff / mypy / physical Mongo | **Not required / not run**; the final delta is E2E-only and all backend/persistence owners are unchanged. |
| `pre_pr_check.py` | **Not run by design**; its clean committed PR-readiness prerequisite is absent. |

## 21. Final re-QG verdict and readiness

**INDEPENDENT FINAL RE-QUALITY-GATE VERDICT: FAIL**

- F-01, F-02, and F-04 remain **accepted and closed**.
- F-03 final stabilization is **not accepted as complete** because a fresh permitted
  guarded run failed at the new synchronization boundary and repeatability was not
  independently established.
- Current bounded follow-up acceptance: **not accepted**.
- Governance/publication readiness: **not ready**. Publication requires exact
  independent `PASS`; this report does not provide one.
- Required next action: a separately assigned bounded diagnosis/remediation of the
  intermittent authenticated-session E2E boundary, followed by a new fresh independent
  re-QG. A later pass must not erase or replace this fresh failure.
- This verdict authorizes no stage, commit, push, PR, merge, deployment, provider work,
  production claim, or next phase.

## 22. Final reviewer safety and Git state

The frozen reviewed-content aggregate remained unchanged throughout the final re-QG.
The only authorized write was this appended section in
`.ai-pipeline/reports/REVIEW_REWORK_UI_QUALITY_GATE.md`. No implementation, test,
configuration, planner, contract, decision, ordinary documentation, dependency, or Git
state was modified. No database, external provider, credential, protected artefact, or
remote service was accessed.
