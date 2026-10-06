# Provider-verified Policy recovery implementation

## Outcome and identity

Owner-assigned remediation, 2026-10-06. Branch
`fix/goldtier-policy-provider-recovery`; base and pre-commit HEAD
`529efea3966fb561027973e6d932cecb0e8f6bb8`, also inspected origin/main.
Worktree: `C:/Users/shane/.codex-clean2/worktrees/goldtier-policy-provider-recovery/data-dividends-zero-touch-clm`.
Implementation is uncommitted pending the fresh independent gate. This report is
implementation evidence, not an independent verdict or authorization to mutate UAT.

## Delta

The old Policy predicate required separately recovered Shell evidence. The existing
OnboardingService now accepts both that historical predecessor and definitive
SEARCH/SHELL success before one attempted, unresolved Policy. The exact frozen input,
current identity/policy/catalogue, retained/case ID and ordered nonterminal prefix must
match. Normal Shell stays SHELL_CREATED; definitive completion stays SEARCH/SHELL.
Requested Policy proof is separately retained with original uncertainty and no replay,
projects PROVIDER_VERIFIED_REQUESTED and creates no invented Policy ID.

The existing target-recovery API delegates Policy recovery to ZeroTouchOrchestrator
under locked TARGET_RECOVERY reauthorization. Only the matching target uncertainty
technical failure is reconciled through existing legal local states to RECOVERY_PENDING.
Its historical failure event stays intact. Identical recovery can complete a failed
local checkpoint idempotently. Recovery makes zero target calls. Explicit resume uses
one submission intent, identical frozen input and original final confirmation, then
Amend once if required and readback. Shell/Policy never replay and Final Review & Send
does not repeat. Unrelated failure, capability denial and HR access remain blocked.
The existing manual CLM recovery path is also preserved without requiring or
fabricating automation; its existing CLM submit action owns explicit continuation.

The XPI boundary classifies future mutation uncertainty as TIMEOUT, TRANSPORT,
RESPONSE_DECODE, RESPONSE_TOO_LARGE, UNEXPECTED_STATUS or UNKNOWN. Existing case event
codes retain only that bounded reason and a fixed message; blocked retries preserve
the first reason. No private exception, provider body, headers or secret is retained.
Replay semantics and the ten-second default remain unchanged. The original Delta
cause remains unknown; portal timing does not establish a timeout.

No browser evidence form is added. The API limitation and owner operating boundary
are recorded in `docs/integration/GOLDTIER_POLICY_PROVIDER_RECOVERY.md`. Current
architecture, project-state and persistence profile record this bounded candidate.
The new physical suite is registered in the existing guarded Mongo runner.

## Acceptance coverage

- Both Shell predecessor forms; no-Amend/required-Amend continuation; truthful separate
  definitive and lifecycle resolution; repeated recovery with zero calls.
- Conflicting ID/name/UEN/country/Policy/status, unattempted/already resolved Policy,
  later Amend/readback and terminal outcome/receipt rejected without provider calls.
- Current canonical identity, frozen policy/catalogue and locked authorization bound
  by the owning service; API capability denial and HR safe inaccessible-case 404.
- End-to-end fake-transport technical failure -> recovery -> explicit resume, unchanged
  intent/input/final confirmation, historical failure retained, Shell/Policy called
  exactly once total and only readback following no-Amend recovery.
- Fail each of the two automation saves, then retry identical recovery locally without
  provider calls or duplicate ledger evidence; unrelated technical failure rejected.
- Genuine manual CLM cases (no automation deletion) cover both Shell predecessors
  through the recovery API, identical retry, no synthesized automation, zero calls
  during recovery and original explicit CLM continuation with one Shell/Policy call.
- Generated disposable Mongo: recovery persisted across normal runtime reconstruction,
  repeated raw-store reads and application open/recovery without document rewrite,
  explicit same-intent completion and a second restart; fixture cleanup verified.
- All six bounded reason causes, private-sentinel exclusion and blocked retry without
  replay or alteration of retained ledger evidence.

## Verification

Primary repository virtualenv Python; APP_ENV=test; bytecode/cache writes disabled
where supported. Ordinary tests enforce memory/fake providers and disable dotenv.
Physical evidence uses only the task-owned loopback mongo:7 container and the existing
generated allowlist fixture; no shared database or .env access.

| Check | Executed result |
|---|---|
| Round 1 recovery/XPI/retained-recovery/API, hostile environment and physical-runner unit checks | 178 passed |
| New physical Mongo restart/read-without-rewrite suite | 1 passed |
| Initial full backend regression | Reached completion, zero assertion failures; 14 tmp-path setup errors |
| All affected setup suites plus current recovery suite | 57 passed using fresh task-owned basetemp |
| Round 1 manual compatibility/current recovery suite | 33 passed |
| Current backend inventory | 2,637 tests; fresh full execution assigned to independent gate |
| Ruff application/tests/changed runner | PASS |
| Strict mypy application | PASS, 126 sources |
| Contract unittest suite | PASS, 44 tests |
| Secret, architecture and project-state checks | PASS |
| Tracked whitespace | PASS; new-file hygiene checked at freeze |
| Frontend tests, browser E2E, TypeScript/build | Not required/not run: no frontend changes |

Fake-transport API continuation is backend E2E evidence, not a browser or Live claim.
Known Starlette TestClient deprecation warning does not alter test results. No POC
regression catalogue entries or accepted provider classifications are changed.

The initial broad run could not create fixtures in the sandbox-denied shared
`pytest-of-shane` temporary directory. No source fix was required: both affected
modules and the current new recovery module passed with a fresh task-owned temporary
directory (57 tests). The independent gate runs the full frozen backend inventory
with that isolation, and owns its final executed/pass/skip counts. The final round 1
focused and physical checks above executed the remedied source; strict mypy and Ruff
also passed after the compatibility fix.

## Changes and limitations

API/type: existing envelopes and request/response fields preserved; internal typed
reason and owner method added. Schema: unchanged. Connector: bounded uncertainty
classification added. Configuration/timeout: unchanged. Business rule/mapping:
Requested support preserved, no Active or new sponsor rule/mapping. Auth/security:
existing locked capability/access boundaries preserved, sanitized evidence only.
Architecture: existing owners extended, no new dependency or persistence owner.
Provider status: unchanged PARTIAL Sandbox and Mock/Local classifications. Runtime:
provider-verified normal-Shell Policy recovery and explicit same-intent resume added.

External ACRA calls = 0; external GoldTier calls = 0. Real UAT reads/writes = 0.
Implementation evidence cannot establish the original provider failure reason or
authorize a real case recovery. The initial independent gate found one P2: the new
mandatory automation lookup rejected existing manual CLM recovery. Remediation round
1 uses an optional lookup inside the same locked orchestrator method, still requires
the frozen CLM snapshot, and returns after case/ledger recovery when automation is
absent. Both genuine manual predecessor API tests now pass. The original FAIL is
retained in the assigned gate report; fresh independent verdict and commit are pending.

## Next authorized action

Freeze all task paths; fresh independent combined
quality gate must independently reproduce normal Shell -> uncertain Policy -> zero
replay recovery -> exact-prefix continuation, with P0/P1/P2 = 0/0/0. Only after PASS,
commit locally. No push, PR or merge. Stop for owner review and separate UAT authority.
