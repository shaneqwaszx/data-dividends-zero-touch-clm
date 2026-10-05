# Current classification conflict binding — owner-authorized follow-up

Task start:2026-10-06. Existing branch fix/zero-touch-registry-reuse-happy-path,
worktree C:/Users/shane/.codex-clean2/worktrees/zero-touch-registry-reuse-happy-path/data-dividends-zero-touch-clm.
BASE/local origin-main771a9696e1e31e3865da4fbbb3f9b33b5959cb6a,
HEAD/previous accepted commit ccff7471fd23e64e87bf94a087a5540762276900.
Pre-existing uncommitted R2 payload preserved; historical gates/manifests immutable.

## Authority and scope

Owner's2026-10-06 follow-up explicitly starts a new bounded cycle (maximum2 remediation
rounds), addressing only TC-R2-001 and current isolation. Historical protected DB
non-access remains NOT_CERTIFIED; OWNER_ACCEPTED_HISTORICAL_LIMITATION=YES.
Historical TC-R2-002 is documented uncertainty, not a new product-gate blocker.
No protected/owner database investigation or dotenv read is authorized.

## Design / owner map

PROCEED: existing DocumentProcessingService assesses classification, OnboardingService
owns selections, CLM owns current readiness/snapshot guard, ZeroTouch owns local review
continuation, existing envelope owns persistence, backend projection owns browser state.
No new classifier/service/repository/dependency/approval stage. No new ADR owner boundary
required. Schema10 is still uncommitted and will coherently retain review binding.

Replace no-candidate ambiguity with typed per-field NO_EVIDENCE/SAFE_CANDIDATE/CONFLICT/
UNSAFE and aggregate PARTIAL. All current observations still constrain automatic
safety; only identity-trusted REVIEWED/HIGH/threshold-valid classification observations
enter the trusted evidence fingerprint for manual decision currentness. Adding unsafe
non-authoritative evidence does not stale an otherwise current USER review.

Fingerprint: deterministic SHA256 over bounded current trusted document identity/events,
normalized classification observations/source identity, case ID/UEN and frozen policy/
vocabulary identity. No raw document/provider body. USER receipt adds actor and reviewed
fingerprint; existing timestamp/value/policy/vocabulary remain. DOCUMENT receipts bind
the same evidence identity. Unknown historical binding remains absent and fails closed,
never fabricated on read. Fresh same-value review after changes records a new decision.

The public review action checks the browser's displayed evidence fingerprint before
binding trusted/conflicting evidence under the existing lock/reauthorization. No writes
to external providers. Unresolved conflict or stale review blocks readiness, current
package, confirmation, snapshot and attempted ledger mutation. Fresh explicit review
of current conflict is allowed; raw evidence can remain conflicting while effective
decision becomes current. A later trusted change invalidates it. No final-confirmation,
freeze, no-replay, NOT_STARTED or uncertainty-owner redesign.

## Steps / verification

1. Add exact ordinary authenticated two-document counterexample in both modes; prove RED.
2. Typed assessment, trusted fingerprint, fresh same-value receipt and all currentness
   callers; backend-authoritative projection and conflict review UI.
3. Adverse API cases: new third doc, auto then conflict, supersession, segment/type
   conflict, absent/unsafe inputs, stale browser token, local zero-call review.
4. Physical schema10 restart stale/fresh/changed review, no read-time write; strict1..9.
5. Guarded conflict plus Alpha/Partnership/Government/uncertainty browser; actual OCR.
6. Focused backend/CLM/no-replay, frontend full/typing/build, Ruff/mypy, contracts,
   hostile isolation, governance/security. Then ONE quiet sequential full backend run.
7. Exact freeze; NEW independent gate under owner historical disposition. Up to2 bounded
   remediation rounds with fresh review. Only exact PASS0/0/0 authorizes second local
   commit (no amend). Compare committed reviewed payload and prove clean index/worktree.
8. No push/PR/merge/next phase; stop for owner review.

## Current-session resources / isolation

Windows PowerShell, primary Python3.12 venv, Node22, existing task-isolated frontend
dependencies, local Tesseract, Docker mongo:7 and local guarded Playwright harness.
Worktree writes require escalation; coordinator owns all Git/source mutations.
Reserve loopback27185 Mongo and18765/14173 browser only for owned lifecycles.
Physical databases must be newly generated allowlisted disposable names, with exact
cleanup/absence proof. Before any app-importing invocation: APP_ENV=test, memory,
ACRA/GoldTier Mock, Gardenfalse, dotenv disabled via repository isolation owner.
No ambient URI is inspected; task-local Mongo only. Do not overlap broad backend with
browser/physical suites; previous WinError10055 must remain honest if it recurs.
