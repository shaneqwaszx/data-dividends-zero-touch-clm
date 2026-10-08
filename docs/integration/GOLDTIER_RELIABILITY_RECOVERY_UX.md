# GoldTier submission reliability and browser recovery

Originally assigned 2026-10-07 from main
`5c54c9af896585764d1e4ed809056d1deb576629`.
Merged through [PR #77](https://github.com/shaneqwaszx/data-dividends-zero-touch-clm/pull/77)
on 2026-10-08 at main `8fb5a43c26efd5ef9f513b37fd9478e555cb4eb4`; the recovery behavior
below is current main behavior. Independent acceptance and CI evidence remain in the
[implementation report](../../.ai-pipeline/reports/GOLDTIER_RELIABILITY_RECOVERY_UX_IMPLEMENTATION.md),
[recovery gate](../../.ai-pipeline/reports/GOLDTIER_RELIABILITY_RECOVERY_UX_QUALITY_GATE.md)
and [final Round 2 gate](../../.ai-pipeline/reports/PR77_E2E_ISOLATION_ROUND2_QUALITY_GATE.md).
Post-merge main CI [37742194816](https://github.com/shaneqwaszx/data-dividends-zero-touch-clm/actions/runs/37742194816)
completed SUCCESS at that merge SHA. Original evidence identities are preserved;
provider classifications are unchanged and no real provider calls are authorized.

## Reliability and retained authority

The existing confirmation-time forced Search remains the single bounded read-only
preflight. Failure or a materially changed result retains an unconfirmed review with
zero target write markers; the submission package exposes Check GoldTier availability
through the existing version-bound identity Search recheck. This does not confirm/send.
No extra liveness endpoint or provider timeout/retry policy is introduced.

CLM now applies its existing immutable-snapshot/current-evidence and confirmation
predicate to a retained Search-only intent before the first write as well as to an
absent ledger. Read-only progress can advance CLM version while the original frozen
review remains valid; retained intent still checks current snapshot and confirmation
digest. The mapper/provider-mode, preview, frozen policy and ledger checks remain
inside existing owners. Confirmation reauthorizes after the read-only preflight before
retaining confirmation and entering target progression. Direct incremental dispatch
can propagate its current request reauthorization inside the case lock.

A browser timeout, lost transport/decoding response or gateway error after the confirmation POST
starts **case-summary observation**, never another confirmation. The UI uses at most
eight GETs, the existing one-second progress cadence and eight-second backoff ceiling
as a per-GET observation deadline. These are UI observation bounds, not a provider
freshness/timeout policy. Confirmed, definitive failed, uncertain and finalization
states come from the backend. Uncertainty permits the existing one automatic read-only
status check per authenticated session/submission. Exhausted observation preserves the
unknown result, suppresses further confirmation, and offers another explicit GET-only
observation. Abort/generation guards discard old case/session results. Session caches
are cleared by the unchanged auth/query owners; no browser durable storage is added.

The browser also bounds waiting for confirmation response headers/body to the existing
eight-second UI observation ceiling. A response that never settles therefore enters the
same GET-only observation path. Stopping the browser wait does not cancel or prove the
outcome of a server/provider operation. The browser never retries that confirmation.

## Browser recovery

The GoldTier submission package opens a prominent verification panel for backend
SUBMISSION_OUTCOME_UNCERTAIN, including affected operation, write attempt, definitive
and lifecycle-resolved prefixes, blocked work, status check and concrete next action.
The technical code, UUID, safe uncertainty category and ledger details are secondary.
Repeated rendering never dispatches a recovery, confirmation or provider write.

When the same case transitions to verification, retained recovery continuation, or a
definitive submission result, the view reveals and focuses its corresponding heading.
Initial load, role/case navigation and ordinary re-renders do not steal focus. Verified
recovery leads with "Verified work is saved" and the same-submission continuation action;
the existing target-operation explanation remains in Technical details. A matching
customer observation on a Policy case explicitly leaves the Policy result unverified.

RM/onboarder can inspect permitted evidence and use the read-only status check. They
see Director verification required and no disabled recovery mutation. HR still has no
case access. TARGET_RECOVERY remains Director-only and is rechecked under the case lock.

The existing onboarding ledger owner derives supported recovery operation/currentness;
the API adds presentation-only eligibility/prefix/reason fields and the one exact
verified candidate ID on status-check success. No-match, ambiguous, failed and incomplete
identity results contain no verified ID and never resolve an operation.

The new minimal recovery request names expected_submission_id, operation, recovered ID
and the existing UNCERTAIN_DURABLE_LEDGER origin. The server obtains identity from the
frozen submission and checks snapshot/current confirmation before calling the existing
recovery owner. Those guards apply to every accepted request shape. Complete legacy
identity attestations remain compatible and strictly
validated; browser-supplied conflicting identity is rejected. A wrong UUID rejects
before any provider call. Identical retained recovery remains locally idempotent.

For Shell, the Director checks and confirms the exact observed candidate. The service
freshly searches that ID again, validates the singleton/name and all supplied provider
identity fields against retained identity, then retains the separate no-replay recovery
fact. An ambiguous or contradictory fresh response is rejected. Missing upstream
identity fields retain the existing service contract; the browser selects a candidate
only from a full legal-name/UEN/country status-check match.

For Policy, customer Search is never Policy evidence. The Director independently
inspects GoldTier and uses the Verified provider evidence form: retained customer ID
and Policy name are read-only; only Requested is accepted and explicit verification is
required. Existing backend evidence validation owns the decision. No provider call
occurs during Policy recovery, Policy ID stays unknown, and Requested does not mean
completed KYC or approval.

Both recoveries reconcile only the matching target-stage uncertainty through the
existing legal transitions to RECOVERY_PENDING. Recovery does not dispatch. Reload
reads retained state and exposes Complete safe recovery. Explicit resume uses the
original immutable intent, confirmation and idempotency keys, skips recovered writes,
and performs only remaining approved operations/readback. Finalization-only recovery
and ordinary success/failure remain separate.
The automation owner's matching-failure predicate also controls presentation eligibility;
an unrelated technical failure remains visible and cannot be cleared by recovery.

Unsupported Amend and incompatible/missing historical evidence remain uncertain with
a safe status-check/Director escalation presentation. They cannot be silently cleared
or replayed. Historical compatible ledger records use the same panel and owners.

## Surface changes

API/types and browser behavior: additive changes. Existing Shell automation recovery
coordination and pre-dispatch currentness are extended. Durable schema, repository/CAS,
connector transport, mappings, configuration/timeouts, business-policy vocabulary,
capability grants, owner/dependency architecture and provider classifications: unchanged.
No Live, upstream idempotency, production approval or interoperability claim is added.

## Offline browser/manual commands

From this isolated worktree with locked frontend dependencies installed, use the
repository's owned-process browser harness. It supplies synthetic credentials and
offline ACRA/XPI responses; it cleans only its own processes. Choose unused ports.

```powershell
$taskPython = 'C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm\.venv\Scripts\python.exe'
& $taskPython scripts/run_e2e.py --headed --sandbox-demo uncertain-shell --grep 'Director recovers uncertain shell' --backend-port 8865 --frontend-port 4273 --timeout-seconds 180
& $taskPython scripts/run_e2e.py --headed --sandbox-demo uncertain-policy --grep 'Director recovers uncertain policy' --backend-port 8865 --frontend-port 4273 --timeout-seconds 180
& $taskPython scripts/run_e2e.py --headed --sandbox-demo success --grep 'Lost confirmation response.*aborted' --backend-port 8865 --frontend-port 4273 --timeout-seconds 180
& $taskPython scripts/run_e2e.py --headed --sandbox-demo success --grep 'Lost confirmation response.*truncated' --backend-port 8865 --frontend-port 4273 --timeout-seconds 180
```

Use a Python environment with the locked backend dependencies (the current host's
interpreter is C:/Users/shane/Desktop/FYP/data-dividends-zero-touch-clm/.venv/Scripts/python.exe).
For interactive use, in a backend terminal at this worktree:

```powershell
$env:CLM_E2E_PASSWORD = Read-Host 'Choose an ephemeral offline test credential'
$env:CLM_E2E_BACKEND_PORT = '8865'
$env:CLM_E2E_FRONTEND_ORIGIN = 'http://127.0.0.1:4273'
$env:CLM_E2E_SANDBOX_DEMO = 'uncertain-shell' # or uncertain-policy
$taskPython = 'C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm\.venv\Scripts\python.exe'
& $taskPython scripts/e2e_backend_server.py
```

In a second terminal at apps/frontend in this worktree:

```powershell
$env:VITE_BACKEND_PROXY_TARGET = 'http://127.0.0.1:8865'
npm run dev -- --host 127.0.0.1 --port 4273 --strictPort
```

Open http://127.0.0.1:4273. Use the chosen credential for maya-lim (onboarder),
ethan-tan (RM), or olivia-koh (Director). Do not save or publish the credential.
Create Singapore onboarding with legal name ZERO TOUCH POC ACCEPTANCE TESTS3 and UEN
202698765Z. Upload a text file containing the following synthetic content:

```text
Legal Name: ZERO TOUCH POC ACCEPTANCE TESTS3
UEN: 202698765Z
Registered Address: 1 SYNTHETIC ACCEPTANCE WAY, #01-01, 018956, SG
Country: SG
Shareholder | Type | Percentage | Owned entity registration number | As of
POC Synthetic Owner A | NATURAL_PERSON | 70% | 202698765Z | 2026-10-04
POC Synthetic Owner B | NATURAL_PERSON | 30% | 202698765Z | 2026-10-04
```

Open the full case. In Submission readiness save Company - Private / Corporate.
In Ownership & UBO select CURRENT_EVIDENCE, use as-of 2026-10-04 and submit the matching
ownership evidence. Confirm the final review once. The configured uncertain fixture
opens the recovery panel. RM checks status; Director verifies the exact Shell candidate
or independently attests Requested Policy, then uses Complete safe recovery once.
Reload before continuing to prove retained recovery. The headed commands above automate
the same interactions and assert one Shell and one Policy with zero external calls.
Never point these offline scenarios at a real GoldTier/ACRA provider or protected DB.
