# Final pre-Phase 22 external-provider POC post-mutation Quality Gate

## Executive Result

**FAIL.** The frozen candidate's local implementation and regression evidence is strong,
and the real external run stopped at the correct no-replay boundary. It did not,
however, complete the user-authorized external acceptance sequence. Exactly one Shell
was attempted after a fresh `NO_MATCH`; its outcome became uncertain, only Search was
definitively completed in the ledger, and no Shell-returned ID was retained. Later
read-only Searches found GoldTier ID `143878`, but the response omitted the UEN,
country, and address needed for exact identity. Policy, Amend, post-Amend same-ID
read-back, and portal field verification therefore did not occur. This is a truthful
hard stop, not lifecycle success.

Two candidate defects also remain: the current sandbox reconciliation document falsely
states that no Shell request was executed, and the browser projection exposes an
editable GoldTier-classification form for legacy cases with no GoldTier target policy,
although the backend necessarily rejects that mutation. The candidate is not eligible
for an exact independent `PASS`, a local commit, publication, or Phase 22 progression.

### Findings first

1. **Acceptance blocker — external lifecycle incomplete.** The uncertain Shell outcome
   correctly forbids replay. ID `143878` cannot be promoted to the ledger's retained
   Shell result or an exact reusable Garden match from the available response.
2. **QG-PM-01 (High) — durable reconciliation evidence contradicts the run.**
   `docs/integration/GOLDTIER_XPI_SANDBOX_RECONCILIATION.md` says no Shell network
   request was executed and customer mutation evidence is pending. The current work
   evidence records one uncertain Shell attempt and the later read-only discovery of ID
   `143878`. The stale statement is material at a no-replay boundary because it could
   support an unsafe second Shell attempt.
3. **QG-PM-02 (Medium) — false editable UI affordance on cases without target policy.**
   `BrowserTargetClassification.from_case()` returns `editable=True` when
   `goldtier_target is None`; every case detail renders the panel. A fresh local probe
   reproduced this for the canonical legacy snapshot, while the owning service rejects
   the mutation as `GoldTier target policy is unavailable for this case`.

## Acceptance Checklist

| # | Required outcome | Result | Direct evidence |
|---:|---|---|---|
| 1 | Use the official ACRA Marketplace Mock Garden evidence truthfully | PASS | Garden remains `MARKETPLACE_MOCK`, `REVIEW_REQUIRED / PARTIAL`, with no provider relationships. No local registry fixture was substituted. |
| 2 | Bind Garden-only KYC `Partnership - Unregulated` and segment `Commercial SBB (Small Business Banking)` with `USER_AUTHORIZED_POC` authority | PASS | The work record and candidate bind both values per case as write-once selections. They are not ACRA-derived and are not global defaults; the complete approved 17-value KYC and 23-value segment vocabularies remain available per case. |
| 3 | Fresh real GoldTier Search through the application path, with no Mock fallback | PASS | Corrected preflight identified XPI `SANDBOX / SANDBOX_PARTIAL`, then the case Search returned `NO_MATCH / 0`. This gate made no external call. |
| 4 | On `NO_MATCH`, perform at most one ledger-owned Shell and retain its returned ID | **FAIL** | The ledger attempted exactly one Shell and did not replay it, but the connector raised mutation-outcome-uncertain. Attempted prefix was `SEARCH, SHELL`; definitively completed prefix was only `SEARCH`. No Shell-returned ID was retained. |
| 5 | Create Customer Policy | **FAIL** | No Policy request was sent after the uncertain Shell outcome. |
| 6 | Amend Customer | **FAIL** | No Amend request was sent. |
| 7 | Real post-Amend same-ID Search/read-back | **FAIL** | The later read-only Search found one `GARDEN BUSINESS` candidate, ID `143878`, and ID Search returned the same ID/name. These were recovery observations, not a post-Amend ledger read-back; omitted UEN/country/address forced `REVIEW_REQUIRED / NO_MATCH` rather than exact identity. |
| 8 | Portal verification where technically available | NOT VERIFIED | The authorized portal tab was at login with no active or autofilled credential. No password was accessed. No portal-visible fields were verified. |
| 9 | Preserve no-replay, call stopping, safe status, console/badge/inspector truth | PASS, with QG-PM-01 documentation defect | Runtime/ledger behavior stopped safely after uncertainty; Policy and Amend were not called. Local tests cover ordered calls, uncertainty, wrong/no/multiple read-back matches, status projection, and safe IDs. The stale reconciliation prose must be fixed. |
| 10 | Final security/regression verification | PASS for tested local surfaces | Fresh full backend reached 100% with exit 0 and 1,392 collected tests; frontend passed 291 tests in 24 files, typecheck, and a 117-module build. Static, contract, governance, readiness, policy, secret, and tooling checks passed. |
| 11 | Fresh independent Quality Gate returns exact `PASS` | **FAIL** | This independent gate returns **FAIL** because required external criteria 4-8 are incomplete and QG-PM-01/QG-PM-02 remain. |
| 12 | Commit only after exact independent `PASS`; do not push, PR, or merge | PASS as restraint; NOT READY | No commit, push, PR, or merge occurred. The candidate must remain uncommitted after this result. |

## Contract and Integration Findings

### External evidence disposition

The accepted provider boundary remains:

`untrusted provider DTO -> canonical evidence/model -> target mapper -> controlled connector`

The runtime correctly kept GoldTier `SANDBOX_PARTIAL`, preserved explicit write opt-in,
bounded responses to 131072 bytes and 10 seconds, and did not fall back to Local Mock.
The per-case Garden values have the precise user authority supplied for this POC; no
other provider value was invented. The later Search result does not override the
resolver: matching legal name and ID alone are insufficient when the provider omits the
registration number, country, and address.

The uncertain Shell is an attempted mutation with an unknown provider outcome. The
ledger's no-replay rule is controlling. ID `143878` is useful recovery evidence but is
not proven to be the Shell response, is not an exact canonical Garden identity, and
must not be copied into the ledger as though it were a definitive mutation result.

### QG-PM-01 — High — reconciliation chronology is unsafe and stale

The current integration record still carries outcome
`CUSTOMER_WRITE_NOT_EXECUTED`, says at line 93 that no Shell/Policy/Amend request was
executed, and says at line 130 that customer mutation evidence is pending a final run.
That contradicts the active work record, which records exactly one uncertain Shell
attempt and subsequent read-only Search/ID Search for ID `143878`. This is not a cosmetic
count drift: accurate attempt history is required to prevent replay. The reconciliation
record must distinguish attempted from definitively completed operations and must not
call the lifecycle successful.

### Quarantines and unresolved authority

Contradictory GoldTier examples remain invalid/quarantined. No second jurisdiction,
UEN-to-ABN substitution, related-party relationship, autonomous approval, or direct
ACRA-to-GoldTier mapping was introduced. Related-party child identity/relationship
semantics, Production authentication, and Live interoperability remain later sponsor
dependencies and do not authorize completing this customer recovery path.

## Tester and Adversarial Findings

Fresh independent evidence on the frozen identity:

- Focused external/security/backend selection: 204 items collected, 100% completed,
  exit 0.
- Full backend canonical suite: 100% completed, exit 0; separate fresh collection found
  1,392 tests. Only known Starlette/Pydantic warnings were emitted.
- Ruff: PASS.
- mypy: PASS across 108 source files.
- Full frontend: 291 tests passed in 24 files. Typecheck passed. Production build passed
  with 117 transformed modules.
- Contract suite: 44 passed.
- Project-state, architecture, external-provider readiness, policy-authority, tooling,
  direct-secret, and supporting governance checks: PASS. Secret unit suite: 8 passed.
- GoldTier example validation: 19 valid, 19 invalid/quarantined, 48 not validated;
  exit 0.
- `git diff --check`: PASS. Explicit trailing-whitespace scan of all six candidate-owned
  untracked files: PASS.

Current coordinator evidence on the same frozen identity, assessed but not rerun by this
reviewer: physical disposable Mongo 35/35 PASS and Playwright 14/14 PASS. This gate made
no network, external-provider, portal, or credential call.

The first sandboxed frontend attempt could not spawn esbuild (`EPERM`); the same command
was rerun outside that process restriction and passed. A governance test invocation
similarly encountered a sandbox temp-directory permission limit and passed when rerun
with the necessary process/filesystem permission. Neither failed attempt is presented
as passing evidence.

Fresh source inspection and the passing adverse tests confirm:

- Shell is attempted at most once and uncertainty stops Policy/Amend and replay;
- strict read-back requires `MATCH_FOUND`, exactly one candidate, and both candidate ID
  and returned party ID equal to the ledger-retained ID;
- missing, wrong-ID, or multiple read-back candidates fail closed;
- the processing inspector is backend-authored and exposes bounded safe summaries;
- Search IDs are shown only when they are exact-match Search evidence, not borrowed
  from an unrelated target-path result; and
- Garden's empty/partial ACRA operations do not become fabricated ownership evidence.

### QG-PM-02 reproduction

A read-only probe instantiated an `OnboardingCase` with the canonical
`legacy_phase13_policy_snapshot` and projected `BrowserTargetClassification`:

```text
LEGACY_TARGET_NONE=True
BROWSER_EDITABLE=True
KYC_SELECTED=None
SEGMENT_SELECTED=None
```

`CaseDetail.tsx` renders the panel whenever `target_classification` exists, and the API
summary always supplies it. Submitting the form reaches the owning service, where a
missing `goldtier_target` is rejected. This is a truthful-UI/regression defect; the
control should be absent or non-editable unless the case has an applicable mutable
GoldTier target policy. Add regression coverage for a legacy/non-target case as well as
the supported Sandbox case.

## Code and Architecture Review

Apart from QG-PM-02, the reviewed implementation preserves the project owners and
dependency direction. Search resolution remains in the canonical resolver, target
mapping does not read directly from ACRA DTOs, and the target ledger remains the only
write-order/no-replay owner. The candidate adds no route-to-Mongo bypass, duplicate
ownership engine, alternate authorization owner, or silent persistence/provider
fallback.

The fixed-field GoldTier mapping, exact vocabularies, case-scoped classification,
strict XPI DTOs, one-time classification binding, post-Amend read-back operation, and
browser processing projection are cohesive and substantially covered. The external
hard stop is not evidence of a code failure; it is the required behavior when mutation
outcome and entity identity are uncertain.

Change classification for this candidate: API/type changed; durable schema remained
additive/backward compatible without a schema-version bump; connector and mapping
behavior changed; per-case business-rule authority changed only for explicitly selected
values; authorization added the bounded target-classification mutation path without a
new permission owner; architecture ownership did not change; provider status remains
`SANDBOX_PARTIAL`; runtime target behavior changed to include strict read-back and
truthful processing projection. No Production/Live status changed.

## Security Review

No new high-risk security defect was found in the reviewed implementation.

- `.env` and private sponsor artefacts were not accessed by this reviewer.
- No credential, token, authorization header, private key/certificate, password, raw
  provider payload, document body, or private exception detail was printed or retained.
- Backend actor/team authorization remains authoritative; route-family security tests
  and direct security checks pass.
- XPI hostname/scheme validation, certificate verification, TLS posture, redirect
  rejection, request timeout, response-size bound, safe error mapping, and no-fallback
  behavior remain enforced.
- Mutation stays explicitly enabled, ledger-owned, ordered, and non-replayable after an
  uncertain dispatch. The browser cannot replay target operations.
- Secret scanning and secret-focused unit tests passed on the frozen candidate.

Production credential lifecycle, PingFed, mTLS/allowlisting, operational recovery
authorization, and Live interoperability remain outside this Sandbox POC and are not
claimed complete.

## Required Fixes

1. **QG-PM-01:** Update
   `docs/integration/GOLDTIER_XPI_SANDBOX_RECONCILIATION.md` to record exactly one Shell
   attempt with uncertain outcome, `SEARCH, SHELL` attempted versus only `SEARCH`
   definitively completed, no replay, later read-only ID `143878`, incomplete identity,
   and no Policy/Amend/read-back/portal success. Remove statements that no Shell request
   occurred or that mutation evidence is merely awaiting a first run.
2. **QG-PM-02:** Make target-classification availability/editability reflect whether
   the case actually has an applicable mutable GoldTier target policy; do not present a
   submit-capable form that the backend must reject. Add an adverse legacy/non-target
   regression test.
3. **External acceptance blocker:** Do not retry Shell. Obtain an authorized recovery
   determination that safely reconciles the uncertain attempt/ID `143878` with exact
   Garden identity, or other explicit provider recovery authority. Only then may the
   same ledger continue with Policy, Amend, strict post-Amend same-ID read-back, and
   portal verification where technically available.

After local remediation, all changed candidate content requires a fresh independent
gate. Even with QG-PM-01 and QG-PM-02 fixed, the original lifecycle acceptance cannot
receive exact `PASS` until the external blocker is resolved or the owner explicitly
changes the acceptance contract. This gate does not authorize such a change.

## Readiness

- **Local implementation/regression basis:** broadly verified, but QG-PM-01 and
  QG-PM-02 remain.
- **Official ACRA Marketplace Mock Garden:** truthful Mock/Partial evidence only; not
  Live ACRA verification.
- **GoldTier Search:** real bounded Sandbox Search demonstrated without fallback.
- **GoldTier customer lifecycle:** NOT COMPLETE. Shell outcome is uncertain; Policy,
  Amend, post-Amend same-ID read-back, and portal proof are absent.
- **Publication/local commit readiness:** **NO**. Exact independent `PASS` is absent.
- **Phase 22 readiness:** **NO**. No next phase is authorized by this report.

## Git Status and Frozen Reviewed Identity

- Worktree: `C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm`
- Branch: `feat/goldtier-sandbox-pipeline-inspector`
- `BASE_SHA = HEAD = origin/main = 463ecdcb4357bb44618cdd5b277671766543dbfc`
- Staged files: none.
- Reviewed tracked delta: 45 modified files, 2,671 insertions, 276 deletions.
- Frozen tracked binary-diff hash:
  `52715ca441ff6e893fb2706a74fbd398d5c16e04`.
- Candidate-owned untracked hashes:
  - `apps/frontend/src/pages/TargetClassificationPanel.tsx` —
    `1abfb23972351c74f840da5068aa9c3bd1f5fe9329e02fee06ad9fe498a3d44a`
  - `apps/frontend/src/pages/TargetClassificationPanel.test.tsx` —
    `9c3172f05c9c60272b2ce7b651c277d4b941b2433fe6ea3d2d05ae09417c5755`
  - `docs/aegis/work/2026-09-27-goldtier-sandbox-pipeline-inspector/10-intent.md` —
    `d0960345d57d29189409aa848e77ed947991711558c098036eeb8e0013d8a1a5`
  - `docs/aegis/work/2026-09-27-goldtier-sandbox-pipeline-inspector/20-checkpoint.md` —
    `12ab269b5b9bc613313dcd46341b2ba8c0a967f3d03cf6356150a1ef7cabefa0`
  - `docs/aegis/work/2026-09-27-goldtier-sandbox-pipeline-inspector/90-evidence.md` —
    `872b78e13a5dd34e1a29de26e83bccd6e4801e33639a71f7e205a573ada900cb`
  - `docs/aegis/work/2026-09-27-goldtier-sandbox-pipeline-inspector/99-reflection.md` —
    `709340953f6a6e7981a0c8f0005006c1f4ffa1f074b4d97ccb9557d6d8900a2f`

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

The seven pre-existing untracked Quality Gate reports are immutable historical inputs
and excluded from candidate identity. The sole intentional write by this independent
review is this report. Git status also emitted permission warnings for 19 repository-root
`tmp*` directories created by sandboxed temporary-file checks; they were not inspected,
treated as candidate content, or modified. No implementation, test, configuration,
ordinary documentation, work record, `.env`, or private artefact was changed by this
review. No commit, push, PR, merge, external call, portal mutation, or next phase
occurred.
