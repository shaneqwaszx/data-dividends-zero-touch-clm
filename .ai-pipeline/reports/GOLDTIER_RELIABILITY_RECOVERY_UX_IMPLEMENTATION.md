# GoldTier reliability and recovery UX — owner handoff

2026-10-07. Implemented in an isolated checkout. Final verification passed; the
independent re-review verdict is recorded separately below. Stop for owner review.

1. **Revision.** BASE_SHA, HEAD and refreshed `origin/main` are
   `5c54c9af896585764d1e4ed809056d1deb576629`. The source is that revision plus the
   uncommitted task delta. Tested source identity:
   `f628a31fbc3cee3ac035ff7b0ddcd0527ec3d10fbe58dfbdafcdd50f8ed22dae`.
   The manifest identifies all 23 frozen paths and its normalization algorithm.

2. **Checkout.** Branch `codex/goldtier-submission-reliability-recovery-ux`;
   worktree `C:/Users/shane/.codex-clean2/worktrees/goldtier-reliability-recovery/data-dividends-zero-touch-clm`.
   Original evaluation checkout/branch, camunda checkout, evaluation artifacts and
   other sessions' resources were preserved. Broad verification began only after
   the evaluation chat completed and was idle at revision 8.

3. **Cause classification.** The original screenshot case was not supplied or
   inspected, so its specific cause remains unknown. Fresh baseline success was
   preserved. Genuine dispatched Shell/Policy transport uncertainty (B) and a
   completed server operation with an aborted/truncated browser response (D) were
   reproduced offline. Compatible retained uncertainty (C) is covered by existing
   retained/persistence regressions. Do not label all uncertainty false positive.
   The defects corrected were the missing actionable browser recovery path,
   lost-response handling and incomplete retained Search-only dispatch guarding.
   Sanitized UUIDs, prefixes, states, reasons and actual call counts are in
   `GOLDTIER_RELIABILITY_RECOVERY_UX_DIAGNOSTICS.json`.

4. **Changed files.** The exact inventory is in the manifest. Product owners:
   `api_models.py`, `main.py`, `clm_orchestration.py`, `onboarding.py`,
   `zero_touch_orchestration.py`; frontend `api.ts`, `types.ts`, `CaseDetail.tsx`,
   `TargetRecoveryPanel.tsx`, `submissionObservation.ts`, `styles.css`.
   Tests: `test_policy_provider_recovery.py`, new
   `test_target_reliability_recovery_ux.py`, `S3SubmissionStatus.test.tsx`, new
   `submissionObservation.test.ts`, `s3-sandbox-submission.e2e.ts`.
   Offline harness: `run_e2e.py`, `s3_sandbox_fixture.py`.
   Durable documentation: architecture, project state, Policy recovery, the new
   reliability/recovery runbook and task planner. Four excluded report receipts
   do not participate in the frozen source hash.

5. **Guardrail.** Existing confirmation-time forced Search is the single bounded
   read-only preflight. Its failure creates no attempted write or uncertainty;
   the browser exposes version-bound Check GoldTier availability. Existing frozen
   snapshot/currentness and valid original confirmation checks now also cover a
   retained Search-only intent immediately before the first write. Reauthorization
   occurs after preflight before retention/progression. Lost confirmation responses
   trigger at most eight authoritative GETs, using the existing progress cadence
   and deadline ceiling, with cancellation/session/case guards. Confirmation is
   sent once; bounded exhaustion keeps it disabled and offers an explicit GET-only
   observation. Backend uncertainty permits the existing one-shot read-only check.

6. **Recovery flow.** The submission package opens a prominent GoldTier submission
   needs verification panel with attempted/completed/resolved work, blocked work,
   direct status check and plain-language observations. Technical code/UUID/reason
   and ledger prefixes are under Technical details. Backend-authored eligibility
   controls mutation availability. Successful recovery refreshes authoritative
   state, retains RECOVERY_PENDING and exposes Complete safe recovery after reload.

7. **RM.** May inspect permitted case evidence and run Check GoldTier status. Sees
   Director verification required, with no recovery mutation control. Server
   capability/team checks reject unauthorized recovery; HR still has no case access.

8. **Director.** May resolve only current, supported retained uncertainty with
   TARGET_RECOVERY. UUID, snapshot, original confirmation, scope and evidence are
   checked under the owning lock. Complete legacy attestation requests receive the
   same currentness protections. Wrong UUID rejects before provider calls;
   conflicting supplied identity cannot replace frozen backend identity.

9. **Shell.** Read-only status checking exposes an exact singleton candidate only
   after legal-name/UEN/country verification. Director confirms that candidate;
   the existing service freshly searches again, rejects ambiguity/contradiction,
   validates retained identity and records separate recovery evidence. It does
   not create the customer again. Optional missing upstream fields retain the
   existing service contract; the browser requires a full triple match.

10. **Policy.** Customer Search never proves Policy success. Read-only customer ID
    and retained Policy are prefilled. Director independently verifies GoldTier,
    selects only Requested and explicitly attests Verified against GoldTier.
    Existing evidence validation retains recovery without a provider write.
    Requested does not mean completed KYC or final approval; Policy ID stays unknown.

11. **No replay proof.** Browser scenarios assert one confirmation, one Shell,
    one Policy, zero Amend and zero external calls. Read-only checks leave the
    ledger unresolved. Recovery itself dispatches no write; explicit continuation
    keeps the original UUID, confirmation and idempotency keys and skips the
    recovered operation. Repeated activation, reload, stale results and unauthorized
    recovery are covered. Matching target failure alone can be reconciled;
    unrelated technical failure remains visible and cannot be cleared.

12. **Verification on the final frozen content.**

    | Check | Result |
    | --- | --- |
    | Full backend | 2,521 passed; 131 skipped; 4 warnings; 832.14 seconds |
    | Focused backend | 188 passed; independent reviewer additionally ran 32 |
    | Full frontend | 557 passed across 47 files |
    | Focused frontend | 48 passed, including seven observation tests |
    | Actual affected Playwright scenarios | Eight passed; 76 discovered, not all executed |
    | Prescribed physical Mongo | 19 suites; 125 collected/passed; zero skips/failures/errors |
    | Contract tests | 44 passed |
    | Governance/harness unit tests | 174 passed |
    | Ruff / configured mypy | Passed; mypy checked 126 source files |
    | Frontend typecheck/build | Passed |
    | Project-state, architecture, tooling, policy, provider readiness, secrets | Passed |
    | Dependency consistency / diff / new Markdown whitespace | Passed |

    The 131 ordinary backend skips comprise 125 physical tests without the opt-in
    Mongo environment and six real OCR cases because Tesseract was unavailable on
    PATH. Real OCR is not claimed. Ordinary skips do not count as physical evidence.
    The separately required physical suites actually ran against newly generated allowlisted
    disposable databases. Those databases were removed; only the task-owned Mongo
    container was removed after exact container ID and ownership-label verification.
    No protected DB or real provider was accessed.

    Initial broad checks exposed two existing-customer regressions introduced by
    the first guard version; both were fixed and passed in the final full suite.
    Earlier local HTTP seeder runs timed out. Isolated baseline and candidate runs,
    then the final full run, passed without changing its timeout/assertions.
    One diagnostic stack probe caused a Windows native crash and was abandoned;
    it is not passing evidence. Initial browser helper failures and a native Policy
    label issue were corrected before the final eight passing scenarios. Inherited
    FastAPI/Pydantic, frontend SSR/act and Vite chunk-size warnings remain.

13. **Independent gate.** Initial review FAIL identified legacy-request currentness,
    truncated successful-response observation, unrelated-failure eligibility and
    static/whitespace defects. All were remediated and independently re-probed.
    Final independent verdict: **PASS** on the exact 23-path identity in point 1.
    See `GOLDTIER_RELIABILITY_RECOVERY_UX_QUALITY_GATE.md` for the exact reviewed
    identity and all 12 requested falsification attempts; initial findings remain
    preserved. No source edits occur after the final frozen identity.

14. **Limits and surface declaration.** API/types, auth/currentness safeguards and
    runtime/browser recovery behavior changed. Durable schema/repository/CAS,
    connector transport, configuration/timeouts, business-policy vocabulary,
    target mappings, capability grants, architecture owners/dependencies and
    provider status did not change. Amend and incompatible/missing historical
    evidence remain safely blocked with Director escalation. This is local/mock
    offline evidence; it makes no Live/interoperability or autonomous approval claim.
    Publication readiness was not run on this intentionally uncommitted handoff.

15. **Commit/publication.** No new commit; HEAD remains the base SHA above. Nothing
    staged, pushed, opened as a PR or merged. Next authorized action is owner review.

16. **Exact manual commands.** Run from the isolated worktree. The runbook
    `docs/integration/GOLDTIER_RELIABILITY_RECOVERY_UX.md` contains the synthetic
    document, identities, steps and additional headed lost-response scenarios.

    Backend terminal:

    ```powershell
    Set-Location 'C:\Users\shane\.codex-clean2\worktrees\goldtier-reliability-recovery\data-dividends-zero-touch-clm'
    $env:CLM_E2E_PASSWORD = Read-Host 'Choose an ephemeral offline test credential'
    $env:CLM_E2E_BACKEND_PORT = '8865'
    $env:CLM_E2E_FRONTEND_ORIGIN = 'http://127.0.0.1:4273'
    $env:CLM_E2E_SANDBOX_DEMO = 'uncertain-shell' # or uncertain-policy
    $taskPython = 'C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm\.venv\Scripts\python.exe'
    & $taskPython scripts/e2e_backend_server.py
    ```

    Frontend terminal:

    ```powershell
    Set-Location 'C:\Users\shane\.codex-clean2\worktrees\goldtier-reliability-recovery\data-dividends-zero-touch-clm\apps\frontend'
    $env:VITE_BACKEND_PROXY_TARGET = 'http://127.0.0.1:8865'
    npm run dev -- --host 127.0.0.1 --port 4273 --strictPort
    ```

    Open http://127.0.0.1:4273. Use the chosen ephemeral credential for maya-lim,
    ethan-tan or olivia-koh. Follow the runbook's synthetic case setup. Confirm once,
    check as RM, verify/recover as Director, reload, then Complete safe recovery once.
    To automate the same path in a visible browser, after closing those owned servers:

    ```powershell
    Set-Location 'C:\Users\shane\.codex-clean2\worktrees\goldtier-reliability-recovery\data-dividends-zero-touch-clm'
    $taskPython = 'C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm\.venv\Scripts\python.exe'
    & $taskPython scripts/run_e2e.py --headed --sandbox-demo uncertain-shell --grep 'Director recovers uncertain shell' --backend-port 8865 --frontend-port 4273 --timeout-seconds 180
    & $taskPython scripts/run_e2e.py --headed --sandbox-demo uncertain-policy --grep 'Director recovers uncertain policy' --backend-port 8865 --frontend-port 4273 --timeout-seconds 180
    ```

Related receipts: source manifest, sanitized diagnostics and independent gate, all in
`.ai-pipeline/reports/`. Exact final commands and acceptance evidence are retained in
this chat's tool receipts and the gate. No commit/push/PR/merge is authorized.
