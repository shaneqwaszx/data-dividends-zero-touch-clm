# Final Sponsor Demo Runbook

## 1. Purpose

Demonstrate the bounded Singapore onboarding POC with exactly three primary journeys:
Garden, Multiple Owner Demo, and Merlion cache reuse. Use the [UAT matrix](FINAL_UAT_ACCEPTANCE_MATRIX.md)
and [canonical blocker guide](BLOCKER_RECTIFICATION_GUIDE.md). Automated acceptance is separate
from a human sponsor demonstration; all manual matrix statuses begin NOT_RUN.

## 2. Evidence and provider truth

| Surface | Classification and authority |
|---|---|
| Garden identity/officers | Official ACRA API Marketplace **Mock** sample authority; F browser runs use an inert **synthetic offline protocol replay**, not a new official network observation |
| Garden ownership | Reviewed fictional 60/40: USER_SUPPLIED_DECLARATION / LOCAL / MANUAL_DECLARATION_POC; no official percentages, relationships or UBOs |
| Second company and Merlion | SYNTHETIC MOCK / MOCK_ACRA_SYNTHETIC_V1; neither is an official Marketplace sample |
| Document extraction | LOCAL labelled PDF/TXT/DOCX extraction, four identity fields; no OCR and no ownership graph extracted from PDF prose |
| Ownership | Existing deterministic Decimal engine; provisional candidates, not final legal UBO determination |
| Target | GoldTier Mock, process-local accepted D2 facts and ledger; no external GoldTier calls, approval or Ready-for-Approval |
| Policy impact | Synthetic prospective comparison under the existing policy owner; no production/customer impact simulation |
| Mongo | Optional explicit local durability; no distributed exactly-once guarantee |

Garden is PARTNERSHIP. Official Mock company shareholder retrieval is not authoritative
partnership ownership. The current bounded default ownership threshold/comparator is
sponsor-confirmed through D-062 (>=25%); complete legal/control policy remains open.

## 3. Prerequisites

Use the accepted candidate in its managed worktree, or the normal checkout **after human merge
and update**. Install the repository's pinned dependencies through its existing setup procedure.
The normal environment requires its already-provisioned local accounts and configured providers.
Do not put credentials in this runbook. Do not switch providers silently or use a production lane.
For cache demonstrations the existing registry cache must explicitly be enabled in Mock mode.

Assets live in apps/backend/tests/fixtures/uat. Its README is the single bounded index,
with purpose, fields, expected outcomes, generators and SHA256 for all 13 files. The
invalid/textless negative fixtures intentionally demonstrate rejection/unavailable evidence.

## 4. Startup

Normal development, in separate PowerShell terminals, after the candidate is integrated:

```powershell
cd "C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm\apps\backend"
..\..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

```powershell
cd "C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm\apps\frontend"
npm.cmd run dev -- --host 127.0.0.1 --port 5173
```

These use normal backend configuration, including configured dotenv loading. They do not
load unmerged worktree changes into the original checkout. Do not use start_demo_windows.bat
for the normal environment.

Controlled automated acceptance is different: scripts/run_e2e.py starts an isolated lifecycle,
disables dotenv, generates temporary test credentials, uses memory state, LOCAL extraction and
explicit offline Mock fixtures. From the candidate root:

```powershell
python scripts/run_e2e.py --registry-demo garden-partnership --grep "Slice B Garden partnership"
python scripts/run_e2e.py --registry-demo synthetic-cache --grep "Slice B second synthetic"
python scripts/run_e2e.py --registry-demo synthetic-cache --grep "Slice B Merlion fresh cache"
```

Each command owns and stops only its own processes. Do not combine fixture modes.
Running these scripts proves controlled automated behavior, not normal-environment startup.

## 5. Login role

Use your existing Client Onboarder or Relationship Manager account for cases. In isolated
tests maya-lim is the synthetic onboarder. HR Admin authors proposals; a distinct Director
(olivia-koh in isolated tests) decides. Backend capability/team checks remain authoritative.

## 6. Garden journey

1. New onboarding: Singapore, GARDEN BUSINESS, 11111999A.
2. Select garden-partnership-reviewed-client.pdf and create the case.
3. Inspect Registry identity: PARTNERSHIP, identity/officers present, PARTIAL acquisition;
   registry ownership/relationships unsupported. In F offline acceptance the inert operations
   are TOKEN, ENTITY_PROFILE, ENTITY_PROFILE; external requests are zero.
4. Inspect Documents & reconciliation: four matching fields auto-confirm. The PDF's ownership
   prose does not become registry evidence or an extracted graph.
5. Open ownership attention, Add structured ownership details. Enter fictional owners,
   exact economic interests 60 and 40, the current evidence-document binding and a review rationale.
6. Submit manual evidence; inspect LOCAL declaration receipt and Decimal candidates 60/40.
7. Save the case's allowed target classification (Company - Private / Corporate in the POC
   vocabulary) when requested; this does not reclassify Garden's legal form.
8. Review & Send last. Confirm the prepared Mock destination. Inspect completed readback/history.

No official partnership ownership or legal UBO conclusion is claimed. Do not invoke the
company shareholder API as a substitute.

## 7. Second-company journey

Use MULTIPLE OWNER DEMO PTE. LTD., 202400008H and multiple-owner-demo-client.pdf.
Inspect SYNTHETIC MOCK identity, four matching document fields and direct 50/30/20 synthetic
registry interests. Choose the current target classification and explicitly Review & Send.
Expected state: COMPLETED / MOCK_GOLDTIER_SUBMITTED, same-ID VERIFIED readback.
Four synthetic registry operations occur on the miss; completion adds no ACRA calls.

## 8. Merlion cache / no-ACRA journey

Use MERLION CIRCULAR LABS PTE. LTD., 202400001A and clean-company-profile.pdf.
Create a first trusted case to warm the existing cache; keep its target unsubmitted.
Start a **distinct** second case with the same identity/document. Inspect CACHE_HIT, binding
and unchanged acquisition provenance. The UI says “Reused fresh registry evidence — no ACRA
request required.” The second case adds zero ACRA operations. Finish its explicit Review & Send.
This cache journey differs from verified target hydration.

## 9. Blocker examples

Use the generator-checked blocker guide's exact trigger/action/owner/invalidation/history/call
columns. Sponsor subset: wrong UEN; entered/document UEN conflict; name; address; confidence;
missing field; replacement; ownership declaration; target classification; Review & Send;
failed/ambiguous Search. Unsupported external/hard-stop issues have no invented fix or retry.
Replacement uses clean-company-profile.pdf and the existing same-case document control.
Active issues disappear only when the owning backend accepts current evidence; retained history
does not become current again.

## 10. GoldTier Mock examples

| Scenario | Expected behavior and executable boundary |
|---|---|
| New customer | NO_MATCH -> Shell -> Policy -> required Amend -> readback -> completion. Five ledger markers correspond to six connector calls [search, search, shell, policy, amend, search] in backend recording evidence |
| Verified existing | Real prior finalized case + same-ID readback ledger proof; exact match; no duplicate Shell/Policy; Amend/readback. Backend recording: [search, search, amend, search] |
| Ambiguous | Two actual local candidates, review, no target mutations. Fixture setup's four Mock mutations are separate from the browser journey; independent synthetic registry evidence may continue |
| Policy failure | Typed technical stop; no Amend/readback/false completion; retained ledger prevents replay |
| Amend failure | Typed failure; no false completion, no blind redispatch |
| Process-local loss | Fresh Mock connector has no customers; missing facts cannot prove completion/reuse; uncertain ledger mutation cannot replay |

Focused commands:

```powershell
python scripts/run_e2e.py --registry-demo synthetic-target-reuse --grep "Slice F same-process verified target reuse"
python scripts/run_e2e.py --registry-demo synthetic-target-ambiguity --grep "Slice F ambiguous target match"
```

The reuse fixture now composes the existing registry ownership provider. Slice G acquires required
current registry evidence through the existing cache owner before ownership and validates its
identity against the earlier Search. Fresh complete cache adds zero source calls; missing/stale
supported evidence requires acquisition. No prior ownership analysis is silently copied.
F's earlier controlled graph fixture and normal-hydration failure remain historical evidence,
superseded by the G normal-owner regressions. Configured 202400005E alone is not verified proof.
Browser counters instrument ACRA only; target physical call counts above are cited backend
evidence, NOT_INSTRUMENTED in browser. Optional Amend omission belongs only to the explicitly
labelled Slice C SYNTHETIC_OFFLINE XPI fixture, not D2 Mock.
Mock is process-local; completion is POC submission, not Sandbox interoperability, approval or
Ready-for-Approval. Never retry a target mutation to improve a demonstration.

## 11. Policy impact / four-eyes sequence

1. HR Admin opens Policy Rules; create a proposal with rationale. Inspect current, default,
   retained base and proposed values. Safe accepted examples: document confidence .85 -> .92,
   ownership threshold 25 -> 30, registry freshness 90 days -> 30 days.
2. Simulate impact before submitting. Expand synthetic scenario transitions; inspect automation/
   review deltas, freshness boundaries, Decimal ownership thresholds and classifier metrics.
   NOT_ASSESSED/unknown stays unknown; no production data or approval is simulated.
3. Submit the exact current revision. HR cannot approve it.
4. Sign in as a distinct Director. Open the same proposal/revision, simulate and compare the
   same server evidence. Enter a decision reason; approve/activate or reject.
5. Inspect new ACTIVE version after approval; show the older in-flight case's frozen snapshot
   unchanged and a newly created case taking the new version. Rejection preserves ACTIVE.
   Stale-base approval is rejected; re-simulation does not make the stale proposal current.

Reference: slice-e-policy.e2e.ts “Slice E HR and Director same impact, stale approval, reject
and frozen cases”. Policy actions add zero provider calls.

## 12. Expected final states

COMPLETED means all required POC stages succeeded with target readback proof. Human approval
remains unresolved. WAITING_FOR_REVIEW means current evidence/action is required; TECHNICAL_FAILURE
means a typed technical stop; RECOVERY_PENDING permits only the existing ledger-owned safe
finalization action, never target replay. A negative/missing source is not success.

## 13. Known limitations

No Production ACRA, external GoldTier writes, production SSO/compliance/approval, related-party
or multi-level hierarchy creation, production OCR, OCDD, full MIS, or full Exception Workbench.
GoldTier Sandbox adapter is SANDBOX_PARTIAL. Portal labels cannot establish API/retry/idempotency/
atomicity/authentication/RFA contracts. Retained original clm_poc records need owner validation
after integration; a disposable clean-start test cannot verify those records.
See current contracts/questions and the final limitations report when Slice G is accepted.

## 14. Sponsor questions

OPEN_QUESTIONS.md retains the precise requested inputs: RFA transition, partnership/control and
related-party/hierarchy contracts, field authority/amend semantics, PingFed/auth/TLS access,
deployment/handoff, document retention/security, complete legal UBO policy and source precedence.
Do not resolve these by demo fixtures or screenshots.

## 15. Cleanup / rerun

Stop the two normal terminals using their own Ctrl+C. Do not delete normal cases/databases.
Controlled scripts clean up only their owned lifecycle. Start another fresh isolated lifecycle
for exact call-count evidence. Cache warm cases stay unsubmitted. Do not reuse synthetic target
facts across Mock process restarts, clear another user's cache, or touch clm_poc as test cleanup.
