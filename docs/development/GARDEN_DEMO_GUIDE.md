# Garden operator demo

## Evidence and composition

The normal complete POC composition is explicit ACRA API Marketplace Mock plus local
Mock GoldTier and local document extraction. This is not Live, customer/compliance
approval or Ready-for-Approval. Existing Sandbox Garden target state is not replayed.
Name-only GoldTier Search candidates remain ambiguous; ID 143878 is not auto-selected.

Repeatable browser tests use the real Marketplace connector/token decoder with a strict
offline synthetic transport. The banner says **ACRA Marketplace protocol · synthetic
offline test evidence**. No request leaves the test process. Profile/officers are
synthetic protocol input, shareholders are genuinely simulated empty, and Relationships
is unsupported with no call/provenance. This is distinct from observed official Mock
interoperability. No synthetic address, officer, ownership or document is an official
provider observation.

The two versioned PDFs under `apps/backend/tests/fixtures/uat` are fictional client
documents for that offline fixture. `python -m scripts.generate_garden_demo_pdfs`
reproduces them. Their supported labels are Legal Name, UEN, Registered Address and
Country. Their ownership declaration is client-supplied synthetic evidence requiring
structured operator review. A current official-Mock demonstration needs a client profile
matching that case's actually observed canonical fields; do not assume the offline
synthetic address is official evidence.

S2 candidate: explicitly enable GARDEN_SUPPLEMENT_ENABLED only with the official
Marketplace Mock lane to combine successful compatible official/cache evidence with
the unchanged known Garden local fixture. This is separately LOCAL_SYNTHETIC_SUPPLEMENT,
never official ownership or network failure fallback. Current exact counts/derivation
are in OWNERSHIP_UBO_PROFILE. A current uploaded conflicting proposal requires the case
creator's rationale and version-bound source choice. Calculable ownership may be edited
before final Send; original graphs/receipts remain. The structure/calculation disclosure
starts collapsed. Manual forms require deliberate type, date, country and percentage;
no silent 60/40 or date/type default is supplied. OCR setup is in LOCAL_OCR_SETUP.md.

## Clean journey

1. Sign in as an authorized case operator and choose New onboarding.
2. Choose Singapore, enter GARDEN BUSINESS / 11111999A, upload the clean PDF and create.
3. Open full case. Canonical identity is validated while acquisition retains PARTIAL;
   empty shareholders do not establish ownership. The clean local document follows
   existing automatic match review and source-neutral reconciliation.
4. Select a current KYC customer type and client segment. Save target classification.
   Mock permits these POC choices but does not add a new required backend gate.
5. Review the synthetic declaration. In the existing manual ownership form bind the
   current reviewed document, enter rationale and the two fictional owners with exact
   economic interests 60 and 40. Submit structured evidence. It remains
   USER_SUPPLIED_DECLARATION / LOCAL / MANUAL_DECLARATION_POC with a review receipt.
6. Inspect Review and Send, warnings, destination and exact server-authored preview.
   No target write occurs until explicit Confirm and send to Mock GoldTier.
7. Confirm. The existing ledger performs the Mock target sequence. The completed case
   remains in Cases and appears in Onboarded; those views overlap by case identity.

## Human review journey

Upload the conflicting PDF instead. Inspect all four discrepancies. Accept the original
suggestions as document observations, then explicitly Keep registry value for each
backend-authorized reconciliation action. Acceptance records evidence; it does not pick
a source winner. Canonical identity stays unchanged and the four decisions are retained.
The last decision returns the case to the actual ownership blocker. Continue through
reviewed manual evidence and classification; this scenario need not submit to a target.
If reconciliation was decided first, pending current fields remain reviewable during
pre-confirmation incomplete ownership; relevant review recomputes reconciliation.

## Provider consoles

HR ACRA Diagnostics is read-only and has no case access. Open What this tab does for
safe configuration/lookup/receipt limits. Entity Profile, Officers and Shareholders are
implemented. LLP Highlights, Capital Details and Relationships stay UNSUPPORTED because
their strict dependent contracts are not established. Generic static-header auth is
not applicable to Marketplace Mock's OAuth/token mechanism.

GoldTier's collapsed How to test this console guide covers Search, candidates,
KYC/segment, accepted POC constants and offline preview. One criterion suffices for
Search; legal name and country are required for preview. Dry-run maps and validates
Search/Shell/Policy/Amend without a provider mutation. Related-party operations remain
BLOCKED_CONTRACT / BLOCKED_CHILD_ID_LIFECYCLE until Q-006 establishes provider-issued
child identity, creation/reuse, binding, vocabulary and safe retry semantics.

## Verification commands and boundaries

Focused offline browser acceptance:

```powershell
.\.venv\Scripts\python.exe scripts/run_e2e.py --grep 'Garden (happy|discrepancy)' --garden-protocol
```

The complete configured browser suite selects a fresh protocol fixture lifecycle only
for the Garden test file; all existing tests retain their local Mock composition.
Timing output records browser action intervals and counts, with zero external calls.
It includes UI waits and is not a provider latency benchmark.

Physical Mongo acceptance remains required. On 2026-10-01 the owner authorized one
disposable local `mongo:7` container after Docker availability was established. The
canonical nine-suite runner passed all 38 physical tests with zero skips/errors; the
owned container was removed. Normal Atlas/MONGO_URI was not used. Existing GitHub CI
physical verification still runs after separately authorized publication; no remote CI
result is claimed by local evidence.

D-062 confirms the current aggregated ownership threshold of >=25% inclusive.
Incomplete evidence still requires review. KYC is evidence preparation in this POC;
Review & Send is RM/onboarder submission confirmation, with no second local compliance,
KYC, four-eyes or regulatory approval stage. EDD remains outside current scope and
Ready-for-Approval is not a local prerequisite without a required external transition.
Local risk remains advisory. PEP/sanctions/adverse-media ownership is unresolved.

An actual GoldTier XPI Sandbox synthetic Search returned HTTP 200 / NO_MATCH on
2026-10-01 without Mock fallback. This proves connectivity only. Conditional external
write permission remains undispatched because the independent pre-mutation safety gate
failed on unproved current mapping/screening, active durable ledger and XPI idempotency
prerequisites. Keep the complete Garden demonstration on local Mock GoldTier and retain
historical Garden Sandbox no-replay state. See the overnight readiness report for the
exact source/evidence identity and current network-backed Garden outcome.

The overnight continuation reproduced and fixed a completion-cache race: a detail GET
captured before confirmation could overwrite the completed response. Confirmation now
cancels the exact scoped detail query before publishing, and the shared publisher
rejects older automation revisions. Deterministic offline tests retain completion after
the late response. The authorized network run exhausted its 1/2/1 ACRA budget with all
HTTP 200 but its verifier timed out without retaining the exact-case journey receipt.
Do not present replay completion as proof of that network-backed case. A new actual
acceptance session needs a separate operation budget; the improved harness checkpoints
sanitized progress continuously so a timeout cannot erase its last observed stage.

A fresh bounded official-Mock verification, if required, needs an approved operation
budget before dispatch: one token request, two entityBasicInformation requests (profile
and officers), one coShareholdersDetails request; zero Relationships, GoldTier reads or
external writes. No external verification is implied by these offline tests.
