# Operator Blocker Resolution UX — Independent Quality Gate

## 1. Executive Result

**FAIL**

The candidate preserves the critical target-safety boundary: a failed GoldTier Search
is not converted to `NO_MATCH`, ACRA/document evidence can continue, and no Shell,
Policy, or Amend call occurs while target identity is unresolved. Director team
selection is blank and explicit, retained-case deletion uses the existing backend and
cache owners, pipeline stage truth is improved, and the exercised buttons are native
keyboard-operable controls.

The acceptance question is still answered **no** for this frozen content. Three
task-scoped defects remain:

1. the completed evidence path converts a technical Search failure into a business
   `ENTITY_RESOLUTION_REVIEW_REQUIRED / WAITING_FOR_REVIEW` exception, contrary to the
   current automation policy and POC regression catalogue;
2. several pipeline tiles do not navigate/focus an authoritative relevant panel and
   can focus an empty target or only open Case Detail at its default position; and
3. the completed Onboarded detail remains a case-owning surface with no Director/RM
   delete entry point or case-detail route.

These are current contract/status and required-UX acceptance defects, not optional
polish. Publication readiness is therefore blocked pending remediation and a fresh
independent re-quality gate.

## 2. Acceptance Checklist

| Workstream | Result | Direct evidence |
|---|---|---|
| A — Director delete consistency | **FAIL** | Cases and Case Detail preserve the existing Director/RM flow, and retained New onboarding adds `DeleteCaseDialog` plus `caseDeletedEffect`. `ClientDetail` still renders only disabled record actions and has no delete or Case Detail route (`apps/frontend/src/pages/ClientDetail.tsx:20`, `:99`). |
| B — Director team selection | **PASS** | `directorTeamId` starts blank, resets on actor change/start-new, creation and demo creation are disabled until selection, and only the explicit value is sent. Backend explicit-team and non-Director spoof tests plus the Director E2E passed. No seed-team fallback was found. |
| C — Search is target identity, not the whole case | **PASS** | Failed Search remains `FAILED`, not `NO_MATCH`; case/CLM stay retained; exact/no-match/review branches remain distinct. |
| D — Safe evidence continuation | **PASS** | Focused runtime evidence shows failed Search followed by actual ACRA completion and document retention, with target calls exactly `['search']`. |
| E — Pipeline status truth | **PASS** | A failed Search projects `GOLDTIER_SEARCH=FAILED`, actual successful ACRA projects `COMPLETE`, and target mutation projects `BLOCKED`; ambiguous Search continues to leave unattempted ACRA `NOT_REACHED`. Earliest actionable selection is now workflow-order based. |
| F — No-match semantics | **PASS** | `200 []` remains `NO_MATCH`, continues the normal new-customer ACRA path, and the safe text does not claim customer creation. Existing full regression passed. |
| G — Safe Search diagnosis | **FAIL** | Safe category normalization and redacted messaging are present, but the initial failed-Search tile targets an empty intervention wrapper before an exception exists; after evidence completion the technical failure is retyped as business review. |
| H — Clickable live stages | **FAIL** | Case Detail uses typed node IDs, but Search/Human Approval can target an empty `case-human-intervention` wrapper; retained New onboarding discards the selected node and only opens Case Detail (`HomeOnboarding.tsx:363`). |
| I — Accessible pipeline UX | **FAIL** | Rendered buttons meet native keyboard/44px/focus requirements and the two-browser E2E passed. However, navigability is based only on a static ID map, not status or actual target availability, so complete/not-reached tiles can advertise a resolution that does not exist. |
| J — Unified resolution surface | **FAIL** | Mutations remain owned by `HumanInterventionPanel`, but initial failed Search has no intervention (`HumanInterventionPanel.tsx:18`) while the tile points there; the later no-action explanation is created through a business exception for a technical outage. |
| K — Current-stage ownership | **PASS** | `currentProcessingNode` now chooses the earliest actionable node in backend workflow order. The simultaneous Search-failure/Target-classification regression passes. |
| L — Retained current-case actions | **PASS** | Start-new, open full case, and authorized delete are present; successful delete uses the existing endpoint/cache effect and returns to blank New onboarding. |

## 3. Contract and Integration Findings

### QG-OBR-01 — High — technical Search outage is reclassified as business review

After documents/reconciliation/ownership complete with Search still unresolved,
`ZeroTouchOrchestrator` creates `BusinessExceptionType.ENTITY_RESOLUTION_REVIEW_REQUIRED`
at `apps/backend/app/services/zero_touch_orchestration.py:1515`. The focused regression
then expects `WAITING_FOR_REVIEW` (`apps/backend/tests/test_zero_touch_orchestration.py:403`).

That classification conflicts with the still-current contract statement that business
exceptions and technical/provider failures are distinct
(`docs/contracts/ZERO_TOUCH_AUTOMATION_POLICY.md:89`) and the accepted catalogue entries
that Search failure is technical and technical/provider/target failures never become
reviewer work (`.agents/skills/poc-regression-check/references/regression-catalogue.md:84`
and `:346`). D-060 authorizes independent evidence continuation and continued target
blocking; it does not authorize converting a provider outage into an entity-resolution
business decision. The candidate amended ADR-006 and architecture but left the policy
and regression catalogue contradictory.

Consequence: the browser and portfolio can truthfully show the Search stage as failed
while falsely presenting the aggregate as human business review. Remediation must keep
the safe read-only/external dependency explanation without inventing a reviewer
decision or target bypass, and must reconcile every current durable authority changed
by that decision.

### Preserved integration boundaries

- `NO_MATCH` remains the only path that authorizes the new-customer target sequence.
- Failed/ambiguous Search never calls Shell, Policy, Amend, binds a party ID, or accepts
  a manual target ID.
- The target ledger remains the sole mutation/no-replay owner.
- No Search retry, historical Amend retry, child-ID behavior, provider-mode change,
  persistence/schema change, or Live claim was added.
- Failure projection uses fixed safe codes/messages; no raw body, request header,
  credential, stack trace, or synthetic private provider message reached the browser.

## 4. Tester and Adversarial Findings

### QG-OBR-02 — High — stage-to-resolution navigation has dead ends and loses node intent

`processingNodeFocusTarget` maps `GOLDTIER_SEARCH*` and `HUMAN_APPROVAL` to
`case-human-intervention` (`CaseStatePanels.tsx:228-236`) regardless of node status or
whether a panel exists. `HumanInterventionPanel` renders nothing when interventions are
empty (`HumanInterventionPanel.tsx:18`), which is exactly the initial retained Search
failure state: the backend test proves `PENDING_INPUTS / DOCUMENT` before the later
exception is created. The clickable failed Search tile therefore focuses an empty
wrapper instead of the required diagnostic/explanation panel. Normal no-match Search
and not-reached Human Approval can also look actionable without useful target content.

On retained New onboarding, `onStageActivate` ignores the typed node and simply opens
Case Detail (`HomeOnboarding.tsx:363`); it does not carry or focus the selected stage.
This fails the stable node-ID-to-authoritative-panel requirement on the screen where
the live tiles are rendered.

The new tests prove only static mapping plus ACRA/document focus after explicitly
opening Case Detail. They do not exercise failed Search, classification, Human Approval,
GoldTier target explanation, non-actionable statuses, reduced motion, or retained-view
node-preserving navigation. Passing native-button keyboard tests therefore do not prove
the required end-to-end stage-to-resolution behavior.

### QG-OBR-03 — Medium — Onboarded detail delete surface is omitted

The explicit surface audit includes Onboarded detail where applicable. `ClientDetail`
is a case-bound screen: it loads case/detail/document/ownership data and exposes the case
ID, audit trail, and client-record actions. It nevertheless exposes neither the existing
Director/RM delete flow nor a route to Case Detail. A Director viewing a completed case
there must leave the case-owning screen and rediscover it elsewhere. No changed test
covers this surface or documents why it is inapplicable.

### Executed evidence

- Focused backend: **210/210 passed** across zero-touch, CLM orchestration, and GoldTier
  sandbox suites.
- Canonical backend: **1,427 passed, 36 skipped**, with three existing Pydantic
  adversarial-serialization warnings, in 233.12 seconds.
- Focused contract/RBAC/delete selection: **249/249 passed**.
- Ruff: **PASS**.
- strict mypy: **PASS**, 108 source files.
- Focused frontend: **32/32 passed**.
- Full frontend: **314/314 passed** across 25 files; existing SSR/`act` warnings remain.
- Frontend typecheck: **PASS**.
- Production Vite build to a temporary directory: **PASS**, 118 modules transformed.
- Guarded local Playwright: **2/2 passed** for Director explicit-team/delete-reset and
  ACRA/document keyboard focus navigation.
- Architecture, project-state, external-provider-readiness, policy-authority, and
  secret checks: **PASS**.
- `git diff --check`: **PASS**; five untracked Markdown files were checked separately
  for trailing whitespace and passed.

The 36 backend skips cover configured environment/physical/external lanes. Physical
Mongo was not required because no schema, repository, CAS, index, or driver bytes
changed. External ACRA/GoldTier smoke tests were prohibited and were not run. The
uncommitted candidate intentionally did not run the clean-committed-state pre-PR gate.

## 5. Code and Architecture Review

The core positive architecture result is strong: changes stay within the existing
Onboarding, CLM, zero-touch, API-projection, React Query, page, and intervention owners.
There is no second authorization, cache, persistence, provider-routing, target-action,
or replay owner.

The main architecture defect is semantic ownership, not dependency direction:
technical target availability is forced through the business-exception owner solely to
obtain a no-action browser panel. A read-only diagnostic/external-dependency surface can
be derived from the typed backend node/checkpoint without converting the failure into a
business decision. The static frontend focus map also conflates “known node ID” with
“currently useful/actionable target,” producing dead links despite using typed IDs.

The touched backend services and `App.tsx` remain large hotspots. The delta is otherwise
bounded and contains no unrelated refactor or dependency churn.

## 6. Security Review

No critical security defect was found.

- Backend capability/RBAC/team scope and safe inaccessible-case `404` ownership remain
  authoritative.
- Retained deletion reuses the existing DELETE endpoint and centralized cache cleanup;
  it does not delete provider-side data.
- Search failure categories are allowlisted/sanitized. The synthetic private provider
  message used by the adverse test is absent from browser output.
- No `.env`, credential, token, authorization header, secret, certificate, confidential
  sponsor artefact, raw provider payload, document body, or private exception detail was
  accessed or newly tracked by this review.
- Mock/Sandbox/Partial/Live labels and the unresolved human-approval boundary remain
  explicit.

The technical-to-business classification in QG-OBR-01 is a truth/contract defect, not a
credential or direct data-exposure defect.

## 7. Required Fixes

1. Preserve technical Search-failure identity through the post-evidence stop. Provide
   the required external/admin no-action explanation without classifying the outage as
   entity-resolution business review, and update the current policy/catalogue/decision
   authorities consistently.
2. Make tile interactivity conditional on an actually available useful target. Add a
   dedicated Search diagnostic/explanation target, preserve the selected typed node
   across retained-view navigation, and prove GoldTier Search, target classification,
   target block, Human Approval, non-actionable status, reduced-motion, and keyboard
   behavior without duplicating intervention actions.
3. Add the existing authorized delete flow, or a direct route to that flow, on completed
   Onboarded detail for Director/RM and prove Director/RM/Client Onboarder/HR visibility
   plus successful cache/navigation cleanup.
4. Add the missing focused regressions around both Director team selections and resets,
   safe Search failure categories, no-match UI wording, failed-Search diagnostic focus,
   and non-actionable tiles. These tests must assert behavior, not only static HTML or
   mapping constants.

Garden Amend validation and related-party `childId` remain external sponsor
dependencies and are not required fixes for this task.

## 8. Readiness

- **LOCAL OPERATOR-BLOCKER-RESOLUTION UX: NOT ACCEPTED / FAIL.**
- **Governance/publication readiness: NOT READY.** Exact PASS on a fresh frozen
  candidate is required after remediation.
- Live ACRA verification: **NOT PERFORMED / NOT CLAIMED**.
- Real GoldTier production integration: **NOT READY / NOT CLAIMED**.
- No external provider call or mutation is authorized by this report.

## 9. Git Status and Frozen Reviewed Identity

- Repository: `C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm`
- Branch: `feat/operator-blocker-resolution-ux`
- `HEAD`: `3e517d3660de2fd64b1d491a59954cc24321144f`
- Base / `origin/main` / merge base:
  `3e517d3660de2fd64b1d491a59954cc24321144f`
- Staged paths: none.
- Reviewed tracked modified paths: 19.
- Reviewed task-owned untracked paths: 11.
- Tracked binary-diff Git identity:
  `4c185d1ee54482805f346a3f48ab32087100870e`
- Combined reviewed-content SHA-256:
  `61a5f41208c9263231adec4ef37bb0e796a055c8a175bdff8efa2fc61545bdf5`
- Identity method: SHA-256 over the labelled tracked binary-diff identity plus a sorted
  `path<TAB>sha256` manifest for all 30 reviewed tracked/untracked candidate paths. This
  assigned report is excluded.

### Complete reviewed tracked path set

```text
apps/backend/app/api_models.py
apps/backend/app/services/clm_orchestration.py
apps/backend/app/services/onboarding.py
apps/backend/app/services/zero_touch_orchestration.py
apps/backend/tests/test_clm_orchestration.py
apps/backend/tests/test_goldtier_xpi_sandbox.py
apps/backend/tests/test_zero_touch_orchestration.py
apps/frontend/e2e/authenticated-zero-touch.e2e.ts
apps/frontend/src/App.tsx
apps/frontend/src/Phase13AuthPriority.test.tsx
apps/frontend/src/pages/CaseDetail.tsx
apps/frontend/src/pages/CaseStatePanels.test.tsx
apps/frontend/src/pages/CaseStatePanels.tsx
apps/frontend/src/pages/HomeOnboarding.tsx
apps/frontend/src/styles.css
docs/ARCHITECTURE.md
docs/aegis/INDEX.md
docs/decisions/ADR-006_GOLDTIER_FIRST_PROVIDER_VERIFIED_RECOVERY.md
docs/decisions/DECISION_LOG.md
```

### Complete reviewed task-owned untracked path set

```text
docs/aegis/plans/2026-09-28-operator-blocker-resolution-ux.md
docs/aegis/work/2026-09-28-operator-blocker-resolution-ux/10-intent.md
docs/aegis/work/2026-09-28-operator-blocker-resolution-ux/20-checkpoint.md
docs/aegis/work/2026-09-28-operator-blocker-resolution-ux/90-evidence.md
docs/aegis/work/2026-09-28-operator-blocker-resolution-ux/99-reflection.md
docs/aegis/work/2026-09-28-operator-blocker-resolution-ux/baseline-read-set-hint.json
docs/aegis/work/2026-09-28-operator-blocker-resolution-ux/baseline-usage-draft.json
docs/aegis/work/2026-09-28-operator-blocker-resolution-ux/drift-check-draft.json
docs/aegis/work/2026-09-28-operator-blocker-resolution-ux/impact-statement-draft.json
docs/aegis/work/2026-09-28-operator-blocker-resolution-ux/task-intent-draft.json
docs/aegis/work/2026-09-28-operator-blocker-resolution-ux/todo-checkpoint-draft.json
```

The reviewer changed no implementation, test, configuration, contract, decision, or
ordinary documentation file. This assigned Quality Gate report is the sole repository
write by the reviewer. No implementation fix, commit, push, PR, merge, branch switch,
next phase, external Search, ACRA request, GoldTier mutation, or related-party request
occurred during this gate.
