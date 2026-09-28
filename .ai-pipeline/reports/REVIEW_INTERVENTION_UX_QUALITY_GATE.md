# Review/intervention UX independent Quality Gate

## 1. Executive Result

**Verdict: FAIL**

The bounded change passes its deterministic backend, frontend, contract, static,
governance, secret, and guarded browser checks, and most of the requested behavior is
implemented correctly. The frozen candidate nevertheless violates two current
operator-truthfulness requirements:

1. Case Detail renders a reconciliation decision twice: once through the shared
   backend-authored intervention panel and again through the existing reconciliation
   panel.
2. An exact-existing-customer reconciliation conflict is still described as a
   Registry/document disagreement even though that branch skips ACRA and the retained
   baseline is `EXISTING_CASE`.

The requested local UX task therefore cannot receive an exact pass on this frozen
content. These are local, remediable findings; they are separate from the retained
GoldTier Amend validation blocker and the sponsor-dependent related-party `childId`
lifecycle.

- **LOCAL UX TASK = FAIL**
- **OVERALL EXTERNAL GOLDTIER ACCEPTANCE = SANDBOX_PARTIAL / blocked**

No external provider call or mutation was made by this gate.

## 2. Acceptance Checklist

| Requirement | Result | Independent evidence |
|---|---|---|
| Prominent `+ Start a new case` CTA | PASS | `HomeOnboarding` uses a full-width primary button; guarded Playwright proved a height of at least 44 px, sidebar-width presentation, visible focus, and unchanged route reset behavior. |
| GoldTier Search owns pre-ACRA ambiguity | PASS | Backend focused tests and API projection show `GOLDTIER_SEARCH=REVIEW_REQUIRED`, `ACRA_REGISTRY=NOT_REACHED`, and no ACRA-failure claim. |
| Backend-authored intervention projection | PASS with finding below | The API supplies stage, blocker, explanation, required input, actions/no-action reason, expected next step, and bounded candidate fields. Browser action rendering consumes this projection. |
| Browser never invents actions; unsafe target replay absent | PASS | Actions are copied from typed exception `available_actions`; ambiguous identity, uncertain mutation, and provider validation remain no-action/fail-closed. Guarded browser coverage found no replay/retry target control. |
| Registry blanket exclusion removed without duplicate presentation | **FAIL** | Home avoids duplicate reconciliation controls, but Case Detail passes `onResolve` to `ConfirmDetailsPanel` while also rendering `HumanInterventionPanel`, producing two controls for one backend-authorized reconciliation action. |
| Initial identity, registry partial, document/reconciliation, target classification, and technical blocker patterns remain truthful | PARTIAL / **FAIL overall** | Registry partial versus unavailable and target non-replay paths pass. Exact-existing conflicts still emit false Registry-owned explanation text. |
| Ambiguous target retains case evidence while mutations stop | PASS | Focused backend tests retain IDP-processed document evidence and make zero Shell/bind/Amend calls while identity review remains active. |
| Exact existing customer remains a distinct case and reuses one target identity | PASS | Focused regression proves different case IDs, separate documents/reconciliation/event histories, the same retained target ID, no second ACRA acquisition, and only one Shell/Policy creation across both cases. |
| No-match remains the ACRA/new-customer branch | PASS | Full regression and architecture inspection preserve the existing no-match path. |
| Onboarded is the accessible completed-case projection, not a client master | PASS for behavior; test gap below | The view fetches exactly `status=COMPLETED`, defaults to no frontend filter, keeps case rows distinct, and documents the future target-ID grouping boundary. |
| Official ACRA sample guidance is operation-specific | PASS | Docs distinguish Garden entity/basic with empty shareholders, SIM LIM shareholder-only, capital-only, and local `20240000x` fixtures. |
| HR GoldTier console separates customer capability from related-party contract block | PASS | Backend exposes `PARTIAL`, `BLOCKED_CONTRACT`, `BLOCKED_CHILD_ID_LIFECYCLE`, and `SPONSOR_CONFIRMATION`; frontend explains the contract gap without claiming connectivity failure. |
| Related-party execution stays zero-call | PASS | Status/dry-run/guarded-write tests preserve no related-party dispatch, no parent-ID substitution, and no fabricated child ID. |
| Required focused/broad verification | PASS except authored filter regression | All executed commands below passed after the noted sandbox-permission rerun. No focused authored test exercises the Onboarded jurisdiction/search filters requested by the assignment. |

## 3. Contract and Integration Findings

### QG-RIU-01 — Medium — duplicate reconciliation action on Case Detail

`apps/frontend/src/pages/CaseDetail.tsx:501` renders `HumanInterventionPanel`, whose
buttons invoke the existing exception-resolution endpoint. The same page then renders
`ConfirmDetailsPanel` at line 534 with `onResolve`, causing that component to render its
existing discrepancy decision buttons as well. For a reconciliation conflict with an
allowed action, the operator receives two copies of the same decision in the same case
view. This directly violates the assigned rule that the shared intervention panel must
not duplicate an exception/control.

The Home view correctly suppresses the second button set by omitting `onResolve`, so
the defect is limited to Case Detail. The current focused test proves one action only by
rendering `HumanInterventionPanel` in isolation and does not exercise the composed Case
Detail surface.

### QG-RIU-02 — Medium — exact-existing conflict is falsely labelled Registry-owned

`apps/backend/app/services/reconciliation.py` correctly emits an `EXISTING_CASE`
baseline when exact target reuse skips ACRA. However,
`apps/backend/app/services/zero_touch_orchestration.py:1799` searches only for a
`REGISTRY` observation, and line 1846 unconditionally explains a conflict as
“Registry and document observations disagree.” On the exact-existing branch there is
no Registry observation or ACRA call, so this safe browser exception text contradicts
the actual source and the newly documented `EXISTING_CASE` contract.

The candidate must derive source-neutral wording or explicitly identify the retained
existing-customer baseline, while preserving no implicit source precedence and no
unauthorized action.

### QG-RIU-03 — Low — requested Onboarded active-filter regression is absent

Existing tests prove the `COMPLETED` request and no-detail-fan-out behavior, but no
owned frontend test drives the Onboarded jurisdiction/search controls and proves that
active filters still filter while the no-filter state shows every accessible completed
case. This is an explicit test requirement of the assignment. Add bounded regression
coverage; do not redesign the list into a client master.

### Authority, quarantines, and later dependencies

- No external request, connector, mapper, authentication, TLS, or provider composition
  change is introduced. The GoldTier XPI classification remains
  `SANDBOX / SANDBOX_PARTIAL`; official ACRA API Marketplace evidence remains Mock,
  not Sandbox, Production, or Live.
- The supplied related-party DTOs require an existing `childId`, while its creation,
  retrieval, binding, relationship vocabulary, and retry/idempotency lifecycle remain
  sponsor-controlled. `BLOCKED_CHILD_ID_LIFECYCLE` is therefore a deliberate current
  contract stop, not a network fault.
- The retained Garden Amend outcome remains provider-verified
  `PROVIDER_VALIDATION_FAILED` after one uncertain attempt. Sponsor/API-owner
  clarification remains required; no retry is authorized. This later external blocker
  does not itself fail the local UX task.
- Contradictory GoldTier examples remain quarantined and no mapping, enum, fixture, or
  assertion was inferred from them.

## 4. Tester and Adversarial Findings

Fresh independent execution against the frozen identity:

- Focused backend orchestration/provider/reconciliation selection: **PASS — 88 tests**;
  one known Starlette/httpx deprecation warning.
- Focused frontend intervention/registry/sandbox/auth selection: **PASS — 76/76** after
  the first sandboxed attempt failed to start esbuild with Windows `spawn EPERM`; the
  approved host-permission rerun passed. The first failure is runner infrastructure,
  not a candidate defect.
- Full backend suite: **PASS — 1,377 passed / 36 skipped / 4 warnings**.
- Full frontend suite: **PASS — 308/308 across 25 files**; existing React test warnings
  remained non-failing.
- Ruff: **PASS**.
- Strict configured mypy: **PASS — 108 source files**.
- Contract discovery: **PASS — 44/44**.
- Frontend typecheck: **PASS**.
- Frontend production build to a disposable system-temp output: **PASS — 118 modules**.
- Guarded isolated Playwright lifecycle: **PASS — 16/16**. The harness used owned
  loopback processes, an ephemeral test credential, stripped inherited provider
  configuration, and default local Mock providers; it made no external provider call.
- Architecture, project-state, external-provider-readiness, policy-authority, and
  tooling-configuration checkers: **PASS**.
- Secret scanner: **PASS**.
- `git diff --check`: **PASS** with line-ending conversion notices only.
- The task-owned untracked `HumanInterventionPanel.tsx` has no trailing whitespace,
  conflict marker, or missing final newline. Broader whole-file inspection found only
  pre-existing whitespace outside changed lines in tracked files; the changed lines
  are clean.

Adversarial inspection challenged pre-ACRA ownership, false ACRA failure, ambiguous
identity call stopping, target replay, exact-existing source truth, duplicate action
presentation, child-ID fabrication, no-match continuity, same-customer case isolation,
and browser-owned actions. The two findings above survived that review. The passing
tests do not erase them because neither affected composed path is currently asserted.

Physical Mongo was not run: this task changes no durable schema, repository, CAS,
index, startup, deletion, or driver boundary. `pre_pr_check.py` was intentionally not
run because this is an uncommitted implementation candidate, not the clean committed
publication gate.

## 5. Code and Architecture Review

The implementation otherwise keeps the intended owner map:

- active exceptions and reconciliation owners remain the only action authorities;
- the new API model is a bounded browser projection, not a second resolution engine;
- early Search ownership and ACRA not-reached state remain backend-authored;
- exact existing customer state reuses the current CLM/reconciliation/target-ledger
  owners without creating a duplicate persistence or customer owner;
- target ordering, call stopping, and no replay remain ledger-owned;
- case identity remains case-scoped while target party identity is reusable;
- the frontend does not authorize target binding or accept a manually typed GoldTier ID;
- no architecture, persistence, connector, configuration, or auth owner is added.

Finding QG-RIU-01 is a presentation-owner duplication, and QG-RIU-02 is a stale
Registry-specific explanation in a newly source-neutral branch. Both are bounded fixes;
neither authorizes broader refactoring or provider activity.

## 6. Security Review

No security finding was identified.

- The intervention candidate projection is bounded to retained safe identifiers and
  candidate identity fields already authorized for the browser; no raw provider body,
  authorization material, endpoint, request payload, token, secret, document body, or
  private exception text is introduced.
- Provider status remains backend-authored and mode-labelled. Related-party execution
  stays blocked and customer diagnostic availability does not grant write authority.
- No `.env`, sponsor credential, quarantined authentication collection, raw confidential
  artefact, or external provider payload was accessed or added by this gate.
- Secret scan, no-replay inspection, and zero-call related-party/provider boundaries
  passed. TLS/auth behavior is unchanged.
- `COMPLETED` remains a POC workflow outcome and is not presented as Ready-for-Approval,
  production approval, or Live interoperability.

## 7. Required Fixes

Before a fresh independent re-gate:

1. Make Case Detail expose each backend-authorized reconciliation decision in one place
   only. Preserve the rich read-only reconciliation evidence while routing the action
   through the shared intervention panel.
2. Make exact-existing-customer reconciliation exceptions source-truthful. Do not say
   Registry/ACRA when the baseline is `EXISTING_CASE`; preserve fail-closed source
   authority and do not invent an action.
3. Add focused regressions for both fixes and the explicitly requested Onboarded
   active-filter behavior. The composed Case Detail regression must prove one accessible
   action, not merely the shared panel in isolation.

The retained Amend validation failure and `childId` questions are sponsor dependencies,
not local fixes. They must remain blocked and must not be retried or bypassed.

## 8. Readiness

- **LOCAL UX TASK = FAIL** pending the three bounded required fixes above.
- **OVERALL EXTERNAL GOLDTIER ACCEPTANCE = SANDBOX_PARTIAL / blocked** by the retained
  Amend validation failure and unresolved sponsor-controlled capabilities. No retry or
  related-party execution is authorized.
- Official ACRA API Marketplace observations remain bounded Mock evidence only;
  Production/Live ACRA is not integrated.
- Publication/commit readiness: **NOT READY**. A changed candidate requires a fresh
  independent Quality Gate. This verdict does not authorize commit, push, PR, merge,
  external activity, or another phase.

## 9. Git Status and Frozen Reviewed Identity

- Repository: `C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm`
- Branch: `feat/review-intervention-ux`
- `HEAD`: `b7cca1f8ae4dfe70d1b3cfe262c527c80f94c1a4`
- Base / `origin/main` / merge base:
  `b7cca1f8ae4dfe70d1b3cfe262c527c80f94c1a4`
- Staged paths: none
- Reviewed tracked modified paths: 29
- Reviewed task-owned untracked paths: 1
- Tracked binary-diff Git identity:
  `742dfe983a2919bbab1192024db089bcf3854db8`
- Untracked file SHA-256:
  `apps/frontend/src/pages/HumanInterventionPanel.tsx` =
  `1d606628e851c8fa374c6572ee8aac3a9ffca34efb67302e3d50b4ef1e704b3b`
- Combined reviewed-content SHA-256:
  `1290c03d2e07705c7636d858e0fc1d54faeed1858e7a3edb28ca8c886eaedd3a`
- Identity method: `git diff --binary | git hash-object --stdin`; the sorted untracked
  manifest contains `path<TAB>sha256<LF>`; the combined hash covers labelled tracked and
  untracked identities. This report is excluded from the reviewed-content identity.

### Complete reviewed tracked path set

```text
README.md
apps/backend/app/api_models.py
apps/backend/app/api_provider_sandbox.py
apps/backend/app/domain/reconciliation.py
apps/backend/app/services/clm_orchestration.py
apps/backend/app/services/reconciliation.py
apps/backend/app/services/zero_touch_orchestration.py
apps/backend/tests/test_provider_sandbox_api.py
apps/backend/tests/test_zero_touch_orchestration.py
apps/frontend/e2e/authenticated-zero-touch.e2e.ts
apps/frontend/e2e/responsive-layout.e2e.ts
apps/frontend/src/App.tsx
apps/frontend/src/GoldTierSandbox.test.tsx
apps/frontend/src/Phase13AuthPriority.test.tsx
apps/frontend/src/UiV2Integration.test.tsx
apps/frontend/src/design-system.css
apps/frontend/src/pages/CaseDetail.tsx
apps/frontend/src/pages/CaseStatePanels.test.tsx
apps/frontend/src/pages/CaseStatePanels.tsx
apps/frontend/src/pages/GoldTierSandbox.tsx
apps/frontend/src/pages/HomeOnboarding.tsx
apps/frontend/src/pages/OnboardedClients.tsx
apps/frontend/src/styles.css
apps/frontend/src/types.ts
docs/PROJECT_STATE.md
docs/integration/ACRA_API_MARKETPLACE_MOCK_READINESS.md
docs/integration/API_HANDOFF.md
docs/integration/GOLDTIER_XPI_SANDBOX_RECONCILIATION.md
docs/sponsor-questions/OPEN_QUESTIONS.md
```

### Complete reviewed untracked path set

```text
apps/frontend/src/pages/HumanInterventionPanel.tsx
```

The reviewer made no implementation, test, configuration, contract, decision, or
ordinary documentation change. This assigned report is the sole intentional repository
write. No commit, push, PR, merge, branch switch, next phase, external Search, ACRA
request, GoldTier mutation, or related-party request occurred during this gate.
