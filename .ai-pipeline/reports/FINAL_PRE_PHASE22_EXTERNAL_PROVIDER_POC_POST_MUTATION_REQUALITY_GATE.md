# Final pre-Phase 22 external-provider POC post-mutation re-Quality Gate

## Executive Result

**FAIL.** QG-PM-01 and QG-PM-02 are closed on the frozen remediated candidate. The
integration reconciliation now records exactly one uncertain Shell attempt and no
replay, and legacy cases without a GoldTier target policy are now projected
non-editable with focused backend/frontend regression coverage.

The overall acceptance contract still cannot pass. The sole Shell attempt has an
uncertain outcome, no Shell-returned ID was safely retained, and read-only discovery of
ID `143878` does not prove exact Garden identity because the provider omitted UEN,
country, and address. Policy, Amend, post-Amend same-ID read-back, and portal field
verification remain absent. Replaying Shell would violate the accepted ledger
invariant.

This re-gate also found one remaining task-scoped evidence defect: the active checkpoint
and reflection retain obsolete statements that no Shell was sent, Garden classification
was still pending, and mandatory business vocabulary remained unresolved. Later text
in the same records gives the correct chronology, but the contradictory earlier status
is unsafe at a no-replay boundary. The candidate is not ready for an exact independent
`PASS`, commit, publication, or Phase 22 progression.

### Findings first

1. **External acceptance blocker — lifecycle incomplete.** One Shell was attempted and
   became outcome-uncertain. Correct no-replay behavior prevents Policy, Amend, and
   lifecycle completion until authorized recovery establishes exact identity safely.
2. **QG-PM-01 — CLOSED.** The owning sandbox reconciliation now distinguishes
   `SEARCH, SHELL` attempted from only `SEARCH` definitively completed; it records no
   replay, ID `143878` as incomplete recovery evidence only, and the missing downstream
   operations/portal proof.
3. **QG-PM-02 — CLOSED.** `BrowserTargetClassification.from_case()` now requires a
   non-null target policy before returning `editable=True`; backend and frontend tests
   cover the legacy/non-editable case.
4. **QG-PM-RQ-01 (High) — contradictory active work status remains.** The current
   checkpoint still says external execution awaits the Garden selection and “no Shell
   has been sent,” while the current reflection says the goal is blocked by missing
   mandatory vocabulary. Both claims are superseded later in those same files, but
   remain materially false and could encourage an unsafe replay or wrong recovery plan.

## Acceptance Checklist

| # | Acceptance requirement | Result | Direct evidence |
|---:|---|---|---|
| 1 | Official ACRA Marketplace Mock Garden remains truthful | PASS | Garden remains `MARKETPLACE_MOCK`, `REVIEW_REQUIRED / PARTIAL`, with no fabricated relationships or local-registry substitution. |
| 2 | Garden-only KYC/segment values are case-scoped with `USER_AUTHORIZED_POC` | PASS | `Partnership - Unregulated` and `Commercial SBB (Small Business Banking)` are bound write-once to this case, are not global defaults or ACRA-derived, and the full 17/23 approved vocabularies remain available per case. |
| 3 | Fresh real Search runs through configured XPI without Mock fallback | PASS | Retained external evidence records corrected `SANDBOX / SANDBOX_PARTIAL` preflight and a fresh `NO_MATCH / 0` case Search. This re-gate made no external call. |
| 4 | At most one ledger-owned Shell and retain its returned ID | **FAIL** | Exactly one Shell was attempted and not replayed, but its outcome is uncertain. Attempted prefix is `SEARCH, SHELL`; definitively completed prefix is only `SEARCH`; no Shell-returned ID was safely retained. |
| 5 | Create Customer Policy | **FAIL** | No Policy request was sent. |
| 6 | Amend Customer | **FAIL** | No Amend request was sent. |
| 7 | Real post-Amend same-ID Search/read-back | **FAIL** | Read-only recovery Search found ID `143878` and ID Search returned the same ID/name, but these are not post-Amend ledger read-back evidence and omitted identity fields force review rather than exact match. |
| 8 | Portal verification where technically available | NOT VERIFIED | Portal remained at login without an active/autofilled credential; no password was accessed and no portal field was verified. |
| 9 | Preserve call stopping, no replay, safe status, console/badge/inspector truth | PASS in runtime; **FAIL in active work-record truth** | Runtime and tests stop after uncertain mutation and do not invent lifecycle success. QG-PM-RQ-01 leaves contradictory current work-record status. |
| 10 | Close QG-PM-01 | PASS | Reconciliation outcome, observations, mutation decision, and classification now accurately record the uncertain Shell and later incomplete recovery Search. |
| 11 | Close QG-PM-02 | PASS | The projection checks `target is not None`; a legacy-case backend test and non-editable frontend test pass. |
| 12 | Final proportional security/regression/hygiene verification | PASS for executed local lanes | Fresh independent backend XPI suite 69/69, frontend panel 3/3, Ruff, mypy 108 files, diff/explicit untracked whitespace checks, and context validation pass. Prior full-gate evidence remains predecessor evidence and is not mislabeled as a fresh full run. |
| 13 | Fresh independent Quality Gate returns exact `PASS` | **FAIL** | Required external lifecycle criteria remain unmet and QG-PM-RQ-01 remains. |
| 14 | Commit only after exact `PASS`; do not push, PR, or merge | PASS as restraint; NOT READY | No commit, push, PR, or merge occurred. This result does not authorize any of them. |

## Contract and Integration Findings

### External evidence disposition

The provider boundary remains correct:

`untrusted provider DTO -> canonical evidence/model -> target mapper -> controlled connector`

GoldTier remains `SANDBOX_PARTIAL`; no Local Mock fallback or Live claim was introduced.
The authorized Garden values are correctly case-scoped. The later Search result does
not supersede canonical identity resolution: same legal name and returned ID are
insufficient when UEN, country, and address are absent. ID `143878` is recovery evidence
only, not a proven Shell response or ledger-retained exact match.

### QG-PM-01 closure

The owning `GOLDTIER_XPI_SANDBOX_RECONCILIATION.md` now states:

- one Shell network request was attempted after `NO_MATCH`;
- the ledger attempted `SEARCH, SHELL` but definitively completed only `SEARCH`;
- the outcome is uncertain and Shell must not be replayed;
- no Policy, Amend, post-Amend read-back, or related-party request was sent;
- later read-only Searches found ID `143878` with incomplete identity; and
- portal verification was unavailable at the login boundary.

The document no longer presents the lifecycle as unattempted or successful. QG-PM-01
is independently verified closed.

### QG-PM-RQ-01 — High — active work record contradicts final evidence

The current `20-checkpoint.md` still contains these obsolete status statements:

- lines 27-30: S6 remains pending an explicit Garden selection and “no Shell has been
  sent”;
- lines 31-32: portal verification is not applicable because no customer exists;
- lines 40 and 71: external case selection remains/preserve the pre-Shell selection
  boundary; and
- lines 90-92: preparation stopped before ledger reservation/Shell because four
  mandatory fields remain unresolved.

The current `99-reflection.md` line 42 likewise says the whole goal is blocked by
missing mandatory business vocabulary. Later sections in both files contain the correct
post-mutation chronology, but append-only correction does not make mutually exclusive
current status truthful. Because “no Shell has been sent” can directly support replay,
this is High at the accepted no-replay boundary.

### Quarantines and later dependencies

Conflicting GoldTier examples remain invalid/quarantined. No ABN substitution, second
jurisdiction, automatic KYC/segment mapping, relationship mutation, or alternate ledger
owner was introduced. Related-party child-ID/relationship semantics, Production
authentication, and Live interoperability remain later sponsor dependencies; they do
not resolve or authorize this recovery.

## Tester and Adversarial Findings

Fresh independent commands on the frozen remediated identity:

- `.venv\Scripts\python.exe -m pytest -p no:cacheprovider apps/backend/tests/test_goldtier_xpi_sandbox.py -q`
  — **69 passed**, one known Starlette deprecation warning.
- `npm.cmd test -- --run src/pages/TargetClassificationPanel.test.tsx`
  — **3 passed in 1 file**. It was run with the required process permission because the
  known sandboxed esbuild path returns `EPERM`.
- `.venv\Scripts\python.exe -m ruff check apps/backend/app/api_models.py apps/backend/tests/test_goldtier_xpi_sandbox.py`
  — **PASS**.
- `.venv\Scripts\python.exe -m mypy --no-incremental apps/backend/app`
  — **PASS, 108 source files**.
- `scripts/dev_context.py` for `EXTERNAL_PROVIDER`, `BACKEND_DOMAIN`, and `FRONTEND_UI`
  — PASS and confirmed branch/HEAD/main identity plus `SANDBOX_PARTIAL` target status.
- `git diff --check` — **PASS**.
- Explicit trailing-whitespace scan of all six candidate-owned untracked files —
  **PASS**.

The remediation run's direct mypy invocation that included the test module produced
pre-existing test-typing diagnostics. It is not counted as passing evidence; the
repository-defined application target above passed independently.

The immediately preceding full gate on the pre-remediation candidate recorded backend
exit 0 over a 1,392-test collection, frontend 291/291 in 24 files, frontend typecheck,
117-module build, contract 44/44, physical disposable Mongo 35/35, Playwright 14/14,
and architecture/state/readiness/policy/tooling/secret checks passing. Those broad
results are relevant predecessor evidence, not fresh execution on this changed hash.
The fresh focused checks cover the two bounded remediation changes.

Adversarial source/test inspection confirms that mutation uncertainty remains
non-replayable; downstream calls stop; read-back requires exactly one same-ID candidate;
wrong, absent, or multiple candidates fail closed; and an unresolved non-target legacy
case now displays no submit-capable classification form.

No external provider, portal, network, credential, or physical Mongo call was made in
this re-gate.

## Code and Architecture Review

### QG-PM-02 closure

`BrowserTargetClassification.from_case()` now returns editable only when all of the
following hold: an applicable GoldTier target policy exists, the case is not frozen,
and at least one required classification remains unresolved. The service remains the
mutation owner and independently rejects absent/frozen policies. This removes the false
browser affordance without introducing frontend authorization or a second policy owner.

The backend regression builds a canonical legacy case with no target policy and asserts
`editable is False` with both values unresolved. The frontend regression asserts that
an unresolved backend projection marked non-editable exposes no form or Save control.
Both focused suites passed. QG-PM-02 is closed.

No additional implementation defect was found. Search resolution, target mapping,
ordered target ledger/no-replay behavior, backend-authored processing projection,
authorization, persistence boundaries, and the sole Decimal ownership engine remain
intact. QG-PM-RQ-01 is a work-record truth defect, not a runtime architecture change.

## Security Review

No new implementation security finding was found.

- `.env` and private sponsor artefacts were not accessed.
- No credential, password, token, authorization header, private key/certificate, raw
  provider payload, document body, KYC/PII, or private exception detail was emitted.
- The corrected projection does not weaken backend actor/team authorization or expose a
  new mutation route.
- XPI TLS/hostname/certificate, redirect, timeout, response-size, safe-error, and
  no-fallback controls are unchanged from the passing prior security review.
- Most importantly, the uncertain Shell remains non-replayable; this re-gate did not
  perform any provider or portal operation.

The contradictory “no Shell” work-record statement is classified under evidence and
integration integrity because its security consequence is replay risk. It must be
corrected before publication.

## Required Fixes

1. **QG-PM-RQ-01:** Rewrite the obsolete current-status passages in `20-checkpoint.md`
   and `99-reflection.md` so each file consistently records the Garden values as already
   authorized, exactly one uncertain Shell attempt, no replay, ID `143878` as incomplete
   read-only recovery evidence, and no Policy/Amend/post-Amend read-back/portal proof.
   Do not merely append another correction while retaining a current “no Shell sent”
   claim.
2. **External blocker:** Do not retry Shell. Any continuation requires explicit
   sponsor/provider recovery authority that safely establishes exact Garden identity or
   otherwise resolves the uncertain mutation. Only the owning ledger may then continue
   to Policy, Amend, strict same-ID read-back, and portal verification where available.

After QG-PM-RQ-01 remediation, changed candidate content requires another fresh
independent gate. Even with all local findings closed, the original external lifecycle
acceptance cannot receive exact `PASS` while the uncertain-mutation recovery remains
unresolved, unless the owner explicitly changes the acceptance contract.

## Readiness

- **QG-PM-01:** CLOSED.
- **QG-PM-02:** CLOSED.
- **Local remediated implementation:** focused verification PASS; work-record truth fix
  still required.
- **Official ACRA Marketplace Mock Garden:** truthful Mock/Partial evidence only, not
  Live ACRA verification.
- **Real GoldTier Search:** demonstrated in bounded Sandbox without fallback.
- **GoldTier customer lifecycle:** NOT COMPLETE; Shell outcome uncertain and all later
  mutation/read-back proof absent.
- **Commit/publication readiness:** **NO**.
- **Phase 22 readiness:** **NO**.

## Git Status and Frozen Reviewed Identity

- Worktree: `C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm`
- Branch: `feat/goldtier-sandbox-pipeline-inspector`
- `BASE_SHA = HEAD = origin/main = 463ecdcb4357bb44618cdd5b277671766543dbfc`
- Staged files: none.
- Reviewed tracked delta: 45 modified files, 2,715 insertions, 282 deletions.
- Frozen tracked binary-diff hash:
  `4ae72cb20893af77c14987d8f8e4cd8e9dda86a7`.
- Candidate-owned untracked hashes:
  - `apps/frontend/src/pages/TargetClassificationPanel.tsx` —
    `1abfb23972351c74f840da5068aa9c3bd1f5fe9329e02fee06ad9fe498a3d44a`
  - `apps/frontend/src/pages/TargetClassificationPanel.test.tsx` —
    `9c3172f05c9c60272b2ce7b651c277d4b941b2433fe6ea3d2d05ae09417c5755`
  - `docs/aegis/work/2026-09-27-goldtier-sandbox-pipeline-inspector/10-intent.md` —
    `d0960345d57d29189409aa848e77ed947991711558c098036eeb8e0013d8a1a5`
  - `docs/aegis/work/2026-09-27-goldtier-sandbox-pipeline-inspector/20-checkpoint.md` —
    `fe319bf77dc5f3c437e65beca51061d62a3174fd2815f47b7c5ca59bc2745a8f`
  - `docs/aegis/work/2026-09-27-goldtier-sandbox-pipeline-inspector/90-evidence.md` —
    `efca146992a0c0d0ac0b6fb4d76197d527155d24d95dce006b7c34315358fbd1`
  - `docs/aegis/work/2026-09-27-goldtier-sandbox-pipeline-inspector/99-reflection.md` —
    `79c17dc7d3e6183b1aafc96e169855ec0f7d85dfb867f2cb181d29a79a92b316`

Complete reviewed tracked path set:

```text
apps/backend/app/api_models.py
apps/backend/app/api_provider_sandbox.py
apps/backend/app/connectors/goldtier.py
apps/backend/app/connectors/goldtier_xpi_models.py
apps/backend/app/domain/clm.py
apps/backend/app/domain/models.py
apps/backend/app/domain/policy.py
apps/backend/app/domain/target_preparation.py
apps/backend/app/domain/target_submission.py
apps/backend/app/domain/zero_touch.py
apps/backend/app/main.py
apps/backend/app/mappers/goldtier.py
apps/backend/app/mappers/goldtier_xpi.py
apps/backend/app/services/authorization.py
apps/backend/app/services/clm_orchestration.py
apps/backend/app/services/onboarding.py
apps/backend/app/services/policy_management.py
apps/backend/app/services/zero_touch_orchestration.py
apps/backend/tests/phase13_test_settings.py
apps/backend/tests/test_garden_business_fixture.py
apps/backend/tests/test_goldtier_xpi_sandbox.py
apps/backend/tests/test_phase13_auth_rbac.py
apps/backend/tests/test_phase14_5_policy.py
apps/backend/tests/test_provider_sandbox_api.py
apps/frontend/src/App.test.tsx
apps/frontend/src/App.tsx
apps/frontend/src/GoldTierSandbox.test.tsx
apps/frontend/src/api.ts
apps/frontend/src/pages/CaseDetail.tsx
apps/frontend/src/pages/CaseStateExplanationPanel.tsx
apps/frontend/src/pages/CaseStatePanels.tsx
apps/frontend/src/pages/GoldTierSandbox.tsx
apps/frontend/src/pages/PolicyRules.tsx
apps/frontend/src/styles.css
apps/frontend/src/types.ts
docs/ARCHITECTURE.md
docs/PROJECT_STATE.md
docs/aegis/INDEX.md
docs/contracts/EXTERNAL_PROVIDER_ACTIVATION_CONTRACT.md
docs/contracts/POLICY_AUTHORITY_MATRIX.md
docs/decisions/ADR-004_GOLDTIER_XPI_SANDBOX_ADAPTER.md
docs/decisions/DECISION_LOG.md
docs/integration/GOLDTIER_XPI_MAPPING_MATRIX.md
docs/integration/GOLDTIER_XPI_SANDBOX_RECONCILIATION.md
docs/sponsor-questions/OPEN_QUESTIONS.md
```

All pre-existing untracked Quality Gate reports are immutable historical inputs and are
excluded from candidate identity. The sole intentional write by this independent run is
this re-Quality Gate report. Git status continues to emit permission warnings for the
same repository-root `tmp*` directories created by sandboxed temporary-file checks;
they were not treated as candidate content or modified. No implementation, test,
configuration, ordinary documentation, work record, `.env`, or private artefact was
changed. No commit, push, PR, merge, external/provider/portal call, or next phase
occurred.
