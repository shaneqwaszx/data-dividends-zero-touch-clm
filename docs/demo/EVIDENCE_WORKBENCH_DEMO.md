# Case Evidence & Explainability Workbench — five-minute synthetic demo

## Boundary

This demo uses synthetic ACRA Mock evidence, the local deterministic Decimal ownership
engine, and Mock GoldTier only. It does not demonstrate Live ACRA/GoldTier/PingFed,
production OCR, Camunda, approval, compliance clearance, or a legal UBO decision. Use
only the tracked synthetic fixture and locally configured synthetic sign-in credentials;
never put a password or confidential document in screenshots, logs, or evidence.

## Prepare and start

From the repository root, enable the opt-in Mock cache for this disposable process and
start the supported launcher:

```powershell
$env:REGISTRY_CACHE_MODE = "mock"
$env:REGISTRY_CACHE_FRESHNESS_SECONDS = "7776000"
.\scripts\start_demo_windows.bat
```

Wait for `Demo started and verified healthy`, then open `http://127.0.0.1:5173` and sign
in with a configured synthetic case-capable account. If the launcher reports an owned or
unowned port conflict, stop and follow `docs/demo/DEMO_RUNBOOK.md`; do not terminate an
unverified process.

## Five-minute path

1. Open **New onboarding**, select Singapore, enter synthetic UEN `202400001A`, attach
   `apps/backend/tests/fixtures/uat/clean-company-profile.pdf`, and create the case.
2. When the case completes, open its detail view. In **Registry provenance**, verify the
   source is explicitly Mock, the original operation timestamps remain visible, and the
   case-use disposition is `PROVIDER_FETCH`. The retained 7,776,000-second expiry is
   labelled provisional and is not presented as current ACRA validity.
3. Create a second case with the same synthetic UEN and fixture. Its case-bound
   disposition should be `CACHE_HIT`. Compare the two cases: the first case's binding
   remains unchanged even though the shared cache was reused. If caching was left at its
   default disabled mode, the panel truthfully says the binding was not recorded and
   makes no miss/fetch/freshness inference.
4. In **Ownership path explorer**, choose a candidate and retained path. Point out the
   exact backend Decimal strings, threshold result, classification, calculation, and
   “owned entity is owned by owner” direction. The selected visual is bounded and says
   it is not a complete hierarchy; cycle/incomplete/limit issues make the view explicitly
   non-definitive.
5. In **Why this case is in its current state**, read the automation stage, stage
   readiness, server-authored blockers/warnings, retained target-operation order, and
   Mock/Ready-for-Approval disclaimer. Use one evidence-focus button. It moves keyboard
   focus to an existing section or reports that evidence is unavailable; it does not
   retry, resolve, refresh, submit, or replay anything.

Candidate/path/focus exploration is browser-local presentation. The only normal network
activity on initial case detail is the existing authorized case, document, and ownership
reads (plus existing polling while a workflow is active). Existing review, replacement,
recovery, priority, and deletion controls retain their previous behavior and authority.

## Stop and clean up

```powershell
.\scripts\stop_demo_windows.bat
Remove-Item Env:REGISTRY_CACHE_MODE -ErrorAction SilentlyContinue
Remove-Item Env:REGISTRY_CACHE_FRESHNESS_SECONDS -ErrorAction SilentlyContinue
```

The stop script terminates only launcher-owned processes after identity validation.
