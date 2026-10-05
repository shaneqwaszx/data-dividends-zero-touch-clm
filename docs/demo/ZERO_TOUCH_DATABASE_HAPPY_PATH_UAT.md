# Four database-backed zero-touch happy paths

All names, addresses, officers, ownership and UENs below are fictional FYP test data.
Future-looking identifiers were generated to meet the repository's syntax validator;
they are not issued/verified ACRA registrations. No company is preseeded in GoldTier.
Actual Sandbox absence is unknown until owner-authorized Search.

## Seed and safe check

Use this branch's managed worktree and provision backend runtime secrets separately.
The utility never reads or edits .env. Create a new disposable target name, set the
same MONGO_DATABASE in the app process, and use the same configured registry collection.
MONGO_URI must already be provisioned in the process environment; do not print it.

```powershell
$env:APP_ENV = "development"
$env:CLM_PERSISTENCE_MODE = "mongo"
$env:MONGO_DATABASE = "clm_uat_registry_" + [guid]::NewGuid().ToString("N").Substring(0,24)
python scripts/seed_zero_touch_happy_path_companies.py --seed --database $env:MONGO_DATABASE
python scripts/seed_zero_touch_happy_path_companies.py --check --database $env:MONGO_DATABASE
```

Expected initial safe counts: FIXTURE_COUNT=4, CREATED=4. Check: FRESH=4, MISSING=0,
EXPIRED=0. Seed rerun: CREATED=0, REFRESHED=0, FRESH=4. Conflicting evidence aborts
without overwriting it. Expired matching seeds are refreshed using revision CAS;
refresh advances original seed timestamps explicitly. `--check` never writes.
The CLI accepts only clm_uat_registry_<24 lowercase hex> or guarded clm_p16_<24 hex>
databases, rejects production and clm_poc, and cannot drop a database.

Ordinary REGISTRY_CACHE_MODE defaults to auto. Remove an old explicit disabled process
override or deliberately select auto; no RM cache setting is required. Legacy mock
requires REGISTRY_CACHE_FRESHNESS_SECONDS=7776000. Approved frozen case freshness
(default90days, expiry exclusive) controls binding. Retained cases keep their bound
copy; missing/expired/incomplete shared seed evidence uses configured ACRA acquisition.
Corrupt persisted evidence remains fail-closed and must be repaired separately.

## Runtime and document pack

Configure the intended process with CLM_PERSISTENCE_MODE=mongo, the same disposable
MONGO_DATABASE, ACRA_CONNECTOR_MODE=api_marketplace_mock, GOLDTIER_CONNECTOR_MODE=sandbox,
GOLDTIER_SANDBOX_ALLOW_WRITES=true, IDP_CONNECTOR_MODE=local_pdf_text and installed
LOCAL_OCR_EXECUTABLE. Provision approved provider configuration/secrets through existing
backend handling. Implementation/testing made zero external provider calls.

Documents are in apps/backend/tests/fixtures/uat/zero-touch-database. They are image-only
PDFs with matching Legal Name, UEN, Registered Address and Country. The generator
uses an installed local Arial/DejaVu font; every page visibly labels fictional FYP data.
SSIC/business activity is unsupported by the current canonical domain and is omitted.
Each company is PRIVATE COMPANY LIMITED BY SHARES, SG, fictional LIVE status,
incorporation2026-01-05; one active DEMO Director and DEMO Secretary appointed that day.
No natural person has a registration identifier or real NRIC/PII. Corporate nodes
have separate generated synthetic identifiers.

| Company (exact legal name) | UEN | Document | Registered address | Effective people P1/P2/P3/P4 | PROVISIONAL UBO CANDIDATE >=25% |
|---|---|---|---|---|---|
| DEMO ALPHA CIRCULAR FYP TEST PTE. LTD. | 209990101A | demo-alpha-scanned.pdf | 11 DEMO ALPHA WAY, 000101, SG | 60 / 40 | ALPHA P1 60%, P2 40% |
| DEMO BETA HOLDINGS FYP TEST PTE. LTD. | 209990102B | demo-beta-scanned.pdf | 22 DEMO BETA WAY, 000102, SG | 42 / 28 / 30 | BETA P1 42%, P2 28%, P3 30% |
| DEMO GAMMA TECHNOLOGIES FYP TEST PTE. LTD. | 209990103C | demo-gamma-scanned.pdf | 33 DEMO GAMMA WAY, 000103, SG | 50 / 30 / 20 | GAMMA P1 50%, P2 30%; P3 below threshold |
| DEMO DELTA SUSTAINABILITY FYP TEST PTE. LTD. | 209990104D | demo-delta-scanned.pdf | 44 DEMO DELTA WAY, 000104, SG | 30 / 10 / 40 / 20 | DELTA P1 30%, P3 40%; P2/P4 below threshold |

Party names are DEMO <CODE> PERSON Pn; officers DEMO <CODE> OFFICER 1/2. All direct
parent totals are exactly100%. ALPHA root -> P1/P2 60/40. BETA root -> H1/P3 70/30;
H1 -> P1/P2 60/40. GAMMA root -> P1/P2/P3 50/30/20. DELTA root -> H1/P4 80/20;
H1 -> H2/P3 50/50; H2 -> P1/P2 75/25. The existing Decimal engine owns all calculations.
No hierarchy/related-party creation is dispatched to GoldTier.

## Manual journey

1. Sign in as the authorized RM and start a new case using the exact name/UEN/SG above.
2. Expect successful Sandbox Search with zero candidates -> NO_MATCH -> completed
   Existing-customer search. If a real candidate exists, follow truthful exact/candidate
   resolution; never force NO_MATCH. Rejection/timeout/malformed is a failure, not absence.
3. Expect registry CACHE_HIT/database reuse, COMPLETE normalized evidence, MOCK source,
   retained local-synthetic provenance and zero ACRA HTTP operations (including token calls).
4. Select the current per-case KYC Customer Type and Client Segment explicitly. For the
   tested package use Company - Private / Corporate. These remain owner case decisions.
5. Upload the matching scan and finish intake. Expect LOCAL_TESSERACT_OCR, exact identity
   matches and eligible fields AUTO_CONFIRMED at frozen score>=threshold (default0.85);
   no Accept clicks or manual ownership declaration. Investigate any OCR mismatch truthfully.
6. Inspect the complete graph and provisional candidates above. The remaining blocker
   should be final Review & Send confirmation only.
7. Review & Send once. NO_MATCH creates exactly one Shell, retains its returned GoldTier
   ID, then Policy, conditional Amend only if the existing plan requires it, and exact-ID
   readback. The tested identity-only package skips Amend.
8. Verify the completed case shows GoldTier ID, new customer created, readback verified
   and submission confirmed. Use the existing read-only Verify in Sandbox action to
   search that retained ID; provider response must identify the same customer. Never
   resend to verify. Completed or uncertain mutations cannot replay.

Marketplace sample UENs are operation-specific and are not coherent whole-company
fixtures by assumption. These four local synthetic fixtures are the controlled happy
paths; Garden remains its separately bounded partial/LOCAL supplement example.
Review & Send is final local approval; GoldTier KYC/four-eye approval, legal UBO,
Production/Live integration, and original-document transfer remain outside this demo.
