# Final pre-Phase-22 GoldTier-first recovery Quality Gate

## Executive Result

**Verdict: FAIL**

The authenticated-portal evidence is sufficient to classify GoldTier ID `143878` as
the exact Garden Business record: the ID, legal name `GARDEN BUSINESS`, UEN
`11111999A`, Singapore country, DSD cross-reference, shell state, and aligned creation
audit are mutually consistent. The one uncertain Shell was not replayed.

The requested acceptance nevertheless cannot pass. The original Shell checkpoint was
owned by an ephemeral in-memory acceptance-harness ledger and disappeared when that
process exited. There is no existing ledger row to transition. Recreating that row,
substituting `143878` into new persistence, or replaying Shell is expressly prohibited.
Consequently Shell was not safely recovered, and Policy, Amend, same-ID application
read-back, post-completion portal verification, and the second Garden onboarding were
not performed. Current source also remains ACRA/registry-first; the required
GoldTier-first orchestration, existing-customer ACRA zero-call path, corresponding
pipeline projection, and acceptance tests are not implemented.

This is not commit-ready. No local commit is authorized by this verdict.

## Phase Acceptance Checklist

| # | Acceptance criterion | Result | Direct evidence |
|---|---|---|---|
| 1 | Frozen candidate matches the assigned branch/base | PASS | Branch is `feat/goldtier-sandbox-pipeline-inspector`; `HEAD`, base, and `origin/main` are `463ecdcb4357bb44618cdd5b277671766543dbfc`; nothing is staged; tracked diff hash is `59f3d0167d2b6347515107682eb80128f1198e97`. |
| 2 | Portal evidence establishes exact Garden identity | PASS | Current-session evidence records one bounded `anz-nutmeg` result with ID `143878`, legal name `GARDEN BUSINESS`, UEN `11111999A`, Singapore, DSD linkage, `Shell Record`, and an aligned `Requested` audit event. The user's minimum exact-recovery threshold of ID + name + UEN is met. |
| 3 | Recovery provenance remains truthful | PASS | The evidence distinguishes the uncertain original Shell response from the later provider-side discovery. It does not claim that `143878` came from the Shell response. |
| 4 | Uncertain Shell was not replayed | PASS | Active evidence says attempted prefix `SEARCH, SHELL`, definitively completed `SEARCH`, and no later Shell. Focused no-replay tests passed. This gate made no provider mutation. |
| 5 | Safely recover the original Shell through the same ledger | **FAIL** | The ignored harness declares an ephemeral in-memory repository and no persistence outside its process. That process exited on uncertainty, so no original ledger checkpoint remains to transition. The brief prohibits reconstruction or manual substitution. |
| 6 | Create Customer Policy only after valid recovery | **FAIL** | No Policy request was sent. Portal policy scaffolding has blank status/request flags and is explicitly not application Policy-call evidence. |
| 7 | Amend Customer only after Policy | **FAIL** | No Amend request was sent. |
| 8 | Real same-ID application Search/read-back after Amend | **FAIL** | No post-Amend application read-back occurred. The earlier read-only discovery of `143878` is recovery evidence, not lifecycle read-back. |
| 9 | Portal verification after lifecycle completion | **FAIL** | Portal identity was verified before recovery, but no completed Policy/Amend state exists to verify. |
| 10 | GoldTier-first orchestration | **FAIL** | `ZeroTouchOrchestrationService._create_case_locked()` creates CLM/onboarding state first; `OnboardingService._create_staged_case_locked()` performs registry acquisition; `search_target_identity()` requires canonical registry identity. `_next_stage()` remains `REGISTRY -> GOLDTIER_SEARCH -> DOCUMENT`. |
| 11 | `NO_MATCH -> ACRA` proof | **FAIL** | The required branch is absent. Current implementation acquires ACRA before Search, so no new-flow proof exists. |
| 12 | `EXACT_MATCH -> zero ACRA acquisition` proof | **FAIL** | The lower-level target ledger can reuse an exact ID, but end-to-end case establishment has already acquired registry data before Search. No zero-call test for the clarified bootstrap flow exists. |
| 13 | `EXACT_MATCH -> Shell skipped` proof | PARTIAL / **FAIL overall** | Existing lower-level tests prove exact-match ledger seeding skips Shell, but only after the current registry-first bootstrap. The required GoldTier-first end-to-end behavior is unproved. |
| 14 | Ambiguous Search -> review, zero ACRA acquisition, zero target mutation | **FAIL** | Existing tests prove ambiguous target candidates stop Shell, but the clarified zero-ACRA early branch does not exist. |
| 15 | Second Garden onboarding uses a new CLM case and the same GoldTier ID | **FAIL** | No second onboarding was executed. |
| 16 | New synthetic document evidence reconciles and amends the same customer | **FAIL** | No second-run document update, reconciliation decision, Amend, or read-back occurred. |
| 17 | Pipeline inspector truthfully reflects GoldTier-first new/existing branches | **FAIL** | Backend stage order and architecture remain registry-first, so the requested new/existing pipeline cannot be projected from backend facts. |
| 18 | Sandbox console and provider badge remain truthful | PASS for retained implementation | Current code/evidence keeps XPI as `SANDBOX / SANDBOX_PARTIAL`, safe host `portal.gt.deltacapita.net`, environment `anz-nutmeg`, and no configured local-Mock fallback. Focused composition and HR API tests passed. |
| 19 | Garden classifications remain case-bound | PASS | Existing tests and current evidence retain the two Garden-only values under `USER_AUTHORIZED_POC`; the full approved vocabularies remain available per case. |
| 20 | Required new tests and complete final verification | **FAIL** | No tests implement GoldTier-first ordering, exact-match ACRA zero-call bootstrap, second Garden onboarding, or document-driven same-ID update. The gate ran 23 focused tests successfully, but absent acceptance coverage cannot pass. |
| 21 | Security boundaries | PASS for implemented surface; recovery criterion absent | HR sandbox API controls, bounded responses, no-fallback behavior, no-replay behavior, and secret hygiene passed focused checks. No RBAC/idempotent provider-verified recovery operation exists to review. |
| 22 | Fresh independent exact `PASS` before commit | **FAIL** | This report is an independent `FAIL`; commit readiness is denied. |

## Contract and Integration Findings

### QG-GFR-01 — Critical — original uncertain ledger checkpoint is unavailable

The acceptance harness states that it promotes Garden only inside an ephemeral
in-memory repository and that the probe is not persisted outside the process. It exits
immediately when `MutationOutcomeUncertainError` occurs. The active evidence confirms
that only a sanitized attempted/completed prefix survived. Portal evidence can prove
customer identity, but it cannot recreate application-owned target-execution state or
retroactively make the original response definitive.

This is a retained-state blocker, not a current GoldTier outage and not missing portal
identity. Under the explicit no-recreation/no-substitution/no-replay authority, it is
not locally remediable. Continuing to Policy or Amend through a newly constructed row
would violate the acceptance contract and ledger-ownership invariant.

### QG-GFR-02 — High — GoldTier-first orchestration is not implemented

Current application ownership remains internally coherent but implements the old
sequence. Case creation accepts UEN/country, creates registry-backed onboarding state,
retrieves ACRA, then permits Search only when canonical registry identity exists. The
automation order and architecture documentation both retain Registry before Search.
There is no bounded initial legal-name/country intake owner, no pre-ACRA Search branch,
and no exact-match bootstrap that proves zero ACRA acquisition.

This is a local unmet acceptance criterion, separate from QG-GFR-01. Existing
lower-level exact-match behavior correctly skips Shell once an exact Search checkpoint
already exists, but it does not prove the clarified end-to-end sequence.

### QG-GFR-03 — High — required lifecycle and two-run acceptance evidence is absent

Because the original ledger cannot be recovered, Policy and Amend correctly remain
stopped. There is no post-Amend same-ID read-back, completed-state portal verification,
second Garden case, ACRA zero-call proof, same-ID reuse proof, or bounded document
reconciliation/update proof. No duplicate Garden record was created. This safety stop
is correct, but the requested acceptance remains incomplete.

### Evidence authority and quarantines

- Portal evidence is provider-side read-only identity evidence. It is not an API
  response, ledger row, Policy result, Amend result, or post-Amend read-back.
- The visible Singapore policy rows are shell-time scaffolding with blank status and
  request flags; they are quarantined from any Policy-success claim.
- Registration type and booking entity were not independently visible in the portal;
  they are not needed for the user's ID + name + UEN exact-recovery threshold and are
  not claimed as portal-confirmed.
- `Partnership - Unregulated` and `Commercial SBB (Small Business Banking)` remain
  Garden-only user-authorized POC values, not ACRA-derived or global defaults.
- Local Mock connectors remain isolated deterministic test seams and are not evidence
  for the configured external-provider path.

## Tester and Adversarial Findings

### Fresh commands and results

- `git diff --binary | git hash-object --stdin` ->
  `59f3d0167d2b6347515107682eb80128f1198e97`.
- `git diff --check` -> exit zero; only Git LF-to-CRLF notices were emitted.
- Staged-path check -> empty.
- Explicit whitespace/final-LF scan of all 16 task-owned untracked files -> pass.
- Focused target/ledger/pipeline test selection -> **17 passed**, one dependency
  deprecation warning. This covered explicit XPI composition/no fallback, no-match
  execution, strict post-Amend read-back validation, exact-match Shell skipping,
  ambiguous-candidate call stopping, uncertain-Shell no replay, persisted uncertain
  resume, and current pipeline projection behavior.
- `apps/backend/tests/test_provider_sandbox_api.py` -> **6 passed**, one dependency
  deprecation warning. This covered HR access, bounded status/Search/dry-run behavior,
  Mock labelling, forbidden-role zero-call behavior, and blank-Search rejection.
- `scripts/check_secrets.py` -> pass: no supported secret patterns found.
- `.env` and `private/sponsor-artifacts-v2` are ignored; neither is tracked.

All tests were run with bytecode and pytest cache writes disabled and with temporary
output outside the repository. No external provider mutation, Shell replay, Policy,
Amend, or browser mutation occurred during this gate.

The canonical full backend/frontend/Mongo/Playwright/pre-PR matrix was not rerun after
the decisive acceptance failures. Historical broad checks remain useful provenance for
the earlier candidate, but they cannot supply missing tests or evidence for the newly
required GoldTier-first and two-run behaviors. A full final matrix is required only
after those behaviors exist and the lifecycle blocker is lawfully resolved.

### Adversarial conclusions

- Treating portal name alone as recovery would be unsafe; the evidence correctly uses
  ID + legal name + UEN, with Singapore/DSD/audit corroboration.
- Treating portal identity as the missing ledger row would violate the single-owner
  invariant.
- Marking Shell complete in a new repository would rewrite history.
- Reissuing Shell would risk a duplicate customer and violate explicit at-most-once
  authority.
- Calling Policy or Amend without the original recovered row would bypass ledger order.
- Existing lower-level exact-match tests cannot be relabelled as ACRA zero-call proof
  because the application acquired ACRA before producing their canonical identity.
- Portal policy scaffolding cannot be promoted to Policy success.

## Code and Architecture Review

The existing candidate preserves one target execution owner, strict XPI mapping,
case-bound classifications, call stopping, and explicit Mock/Sandbox separation. No
new alternate ledger or browser-owned business state was introduced.

For the clarified requirement, however:

- `ZeroTouchOrchestrationService.create_case()` accepts UEN and optional country only;
- `_create_case_locked()` calls `ClmOrchestrationService.create_case_with_identity()`;
- that calls `OnboardingService.create_staged_case_with_identity()`;
- `_create_staged_case_locked()` routes and acquires registry evidence;
- `search_target_identity()` rejects cases without canonical registry identity; and
- `_next_stage()` orders `REGISTRY`, then `GOLDTIER_SEARCH`.

No backend-owned initial legal-name/country intake, pre-registry Search state,
existing-target-state hydration, zero-ACRA exact-match branch, or provider-verified
uncertain-Shell recovery command exists. The pipeline inspector therefore cannot
truthfully display the requested GoldTier-first topology from current backend facts.

The absence of those features is not accepted technical debt: each is a current
acceptance requirement. No unrelated refactor or scope expansion was observed.

## Security Review

No new security defect was identified in the implemented surface.

- The gate did not inspect `.env`, credentials, passwords, cookies, authorization
  headers, browser storage, or raw provider payloads.
- The tracked evidence omits the opaque DSD external ID and unrelated customer data.
- Secret scanning passed across tracked and non-ignored untracked files.
- XPI sandbox configuration remains HTTPS/safe-host bounded, backend-only for the user
  identifier, explicitly write-gated, and classified `SANDBOX_PARTIAL`.
- Focused API tests confirm HR-only access and zero provider calls for forbidden or
  invalid requests.
- Uncertain mutation handling remains non-replayable.

The requested recovery endpoint's RBAC, exact-evidence validation, idempotency, audit,
and overwrite protection are unverified because no such operation exists. This is an
absent required feature, not evidence that an exposed insecure endpoint exists.

## Required Fixes

1. Do not replay Shell, reconstruct the missing row, or substitute `143878` under the
   current authority. Completion requires either the actual original ledger checkpoint
   or explicit new user authority that changes the no-recreation/no-substitution
   boundary. A Quality Gate cannot grant that authority.
2. Implement the user-authorized GoldTier-first orchestration through the existing
   owners: bounded initial identity, pre-ACRA Search, exact/no-match/ambiguous branches,
   existing-target-state reuse, exact-match ACRA zero-call and Shell skip, and truthful
   backend pipeline projection.
3. Add direct tests for GoldTier-first order, no-match-to-ACRA, exact-match zero ACRA,
   ambiguous zero ACRA/zero mutation, second onboarding, same-ID reuse, and document
   reconciliation/amendment of that same customer.
4. Only after lawful same-ledger recovery, execute Policy, Amend, strict same-ID
   application read-back, post-completion portal verification, and the second Garden
   run. Keep the two evidence lanes separate.
5. Freeze the resulting content, run the complete required verification matrix, and
   request a fresh independent Quality Gate. Do not commit before exact `PASS`.

## Readiness

- **Portal identity recovery classification:** `EXACT_RECOVERY_PROVED`.
- **Shell recovery readiness:** BLOCKED; identity is sufficient but the original ledger
  checkpoint no longer exists.
- **GoldTier customer lifecycle:** NOT COMPLETE; no valid recovery, Policy, Amend, or
  post-Amend read-back.
- **GoldTier-first product behavior:** NOT IMPLEMENTED.
- **Two-run Garden acceptance:** NOT EXECUTED.
- **Configured provider truthfulness:** retained as official ACRA Marketplace Mock and
  GoldTier XPI `SANDBOX / SANDBOX_PARTIAL`; no Live claim and no local-Mock fallback.
- **Commit/publication readiness:** NOT READY. This `FAIL` forbids the requested local
  commit. Push, PR, and merge remain prohibited.

The portal removed the former external identity ambiguity. The remaining hard stop is
loss of local process-owned ledger state under an explicit no-reconstruction rule; it
is not a provider outage. Local GoldTier-first implementation work also remains
outstanding.

## Git Status and Frozen Reviewed Identity

- Branch: `feat/goldtier-sandbox-pipeline-inspector`
- `HEAD`: `463ecdcb4357bb44618cdd5b277671766543dbfc`
- Base / `origin/main`: `463ecdcb4357bb44618cdd5b277671766543dbfc`
- Staged paths: none
- Tracked reviewed diff identity:
  `59f3d0167d2b6347515107682eb80128f1198e97`
- Task-owned untracked reviewed-content manifest SHA-256:
  `3f8d9a4fbe5751ce39af5d854271381b7526b7bd4d17ea0b714b6e5fe4e972d3`
- Tracked reviewed paths: all 45 modified paths reported by `git diff --name-only`,
  spanning the backend provider/domain/orchestration/API code and tests, frontend
  inspector/console/types/tests/styles, and the architecture/project-state/contracts/
  decisions/integration/open-question records.
- Task-owned untracked reviewed paths: the ten prior immutable Quality Gate reports;
  `TargetClassificationPanel.tsx` and its test; and the four active work records
  `10-intent.md`, `20-checkpoint.md`, `90-evidence.md`, and `99-reflection.md`.
- The ignored local acceptance harness was inspected for composition/state-lifetime
  evidence but is not part of the tracked candidate identity.
- During this gate, reviewed implementation, tests, configuration, and ordinary
  documentation were not edited. The only write is this assigned report.
- No implementation fix, commit, push, PR, merge, provider mutation, or next phase was
  performed.
