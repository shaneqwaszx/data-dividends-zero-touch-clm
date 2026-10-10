# Four complete database-first synthetic companies

The owner correction supersedes the previous MockAcraConnector candidate and its
historical Quality Gate PASS. These are LOCAL PROJECT SYNTHETIC MOCK records, never
Marketplace-returned ownership, legal UBO findings or regulatory approval.

| Company / UEN | Registered address / SG | Exact direct/effective natural-person results | Provisional >=25% candidates |
|---|---|---|---|
| ORION SYNTHETIC TECHNOLOGIES PTE. LTD. / 202400014N | 18 ORION PARK, #06-01, 049014, SG | Avery70% direct; Blair30% direct | Avery70%; Blair30% |
| PACIFIC SYNTHETIC LEDGER PTE. LTD. / 202400015O | 18 LEDGER QUAY, #07-02, 049015, SG | Casey40%; Dana35%; Ellis25%, all direct | Casey40%; Dana35%; Ellis25% (inclusive boundary) |
| STRAITS SYNTHETIC HOLDINGS PTE. LTD. / 202400016P | 18 STRAITS VIEW, #08-03, 049016, SG | Fiona0% direct/48% indirect; Jordan40% direct; Gabriel0% direct/12% indirect | Fiona48%; Jordan40% |
| MERIDIAN SYNTHETIC INFRASTRUCTURE PTE. LTD. / 202400017Q | 18 MERIDIAN DRIVE, #09-04, 049017, SG | Hannah0% direct/30% indirect; Ian0% direct/20% indirect; Iris30% direct; Julian20% direct | Hannah30%; Iris30% |


The exact ownership graphs feed scripts/zero_touch_happy_path_fixtures.py and its
existing normalized bundle/snapshot owner. Decimal calculations and the inclusive25%
provisional threshold are unchanged. Fictional corporate identifiers SYN-STRAITS_HOLDING
and SYN-MERIDIAN_HOLDING are evidence identifiers, not actual UENs. Seeded officers
remain distinct from owners. Entity status LIVE is fictional; source environment is MOCK.

## Warm and run the normal application

Privately provision the existing Marketplace credentials and Mongo connection as usual.
The seed manager reads process environment; it never loads .env or prints a URI.
Only development/test and dedicated clm_uat_<24 lowercase hex> (or generated clm_p16
acceptance databases) are allowed. The protected clm_poc database is refused before
connection. No automatic application-start seeding, HTTP seed endpoint or direct BSON
writer exists.

```powershell
$env:APP_ENV = 'development'
$demoDatabase = 'clm_uat_' + [guid]::NewGuid().ToString('N').Substring(0, 24)
python scripts/seed_zero_touch_happy_path_companies.py --seed --database $demoDatabase
python scripts/seed_zero_touch_happy_path_companies.py --check --database $demoDatabase
# Start the ordinary application against that SAME warmed dedicated database.
$env:CLM_PERSISTENCE_MODE = 'mongo'
$env:MONGO_DATABASE = $demoDatabase
$env:ACRA_CONNECTOR_MODE = 'api_marketplace_mock'
$env:REGISTRY_CACHE_MODE = 'auto'
$env:IDP_CONNECTOR_MODE = 'local_pdf_text'
```

The existing manager populates all eight fixtures: Alpha209990101A, Beta209990102B,
Gamma209990103C, Delta209990104D, Orion202400014N, Pacific202400015O, Straits202400016P,
Meridian202400017Q. All use local_synthetic_registry_identity():
ACRA / MOCK / PHASE10_ACQUISITION_V1 / LOCAL_SYNTHETIC_UAT_V1.
It preflights every known key before writes, rejects conflicting content, inserts missing
seeds, leaves fresh matching seeds untouched and CAS-refreshes expired matching seeds.
Check is read-only and does not initialize indexes. A batch is not a multi-key transaction.

GoldTier initial Search retains its ordinary behavior. The existing SG/ACRA coordinator
checks the exact-UEN approved local seed before configured provider acquisition. A fresh
COMPLETE seed gives CACHE_HIT and zero Marketplace token/entity/officer/shareholder HTTP
operations. Original seed times/references remain local synthetic. Missing, incomplete
or stale seed evidence is not served or mixed; the ordinary configured Marketplace
provider is used instead. Malformed cache content continues to fail closed.
Neither MOCK_ACRA_SYNTHETIC_V1 nor ACRA_API_MARKETPLACE_MOCK_V1 is a seed alias.

The configured provider remains Official ACRA API Marketplace Mock. Case evidence shows
Local Synthetic Seed, LOCAL PROJECT SYNTHETIC MOCK, CACHE_HIT and LOCAL_SYNTHETIC_UAT_V1.
The browser gets only this allowlisted seed label; private cache keys and arbitrary
provider namespaces remain hidden. Production/Live ACRA is outside this task.

## Documents and journey

The four classification-bearing native-text PDFs reside under
apps/backend/tests/fixtures/uat/zero-touch-database. Regenerate only these four using
python scripts/generate_synthetic_company_pack.py. Legal Name/UEN/Registered Address/
Country remain the identity fields. Explicit KYC Customer Type: Company - Private and
Client Segment: Corporate labels are also present; PDFs contain no ownership quantities. Quantitative
ownership comes from the LOCAL_SYNTHETIC_UAT_V1 registry seed.

Enter the exact company name/UEN, choose SG and upload its matching PDF. The four fields
reach MATCH/ACCEPTED/HIGH with deterministic0.97 evidence scores. The ordinary Decimal
engine produces the table's ownership results without manual ownership supplementation.
The matching updated PDF supplies Company - Private / Corporate automatically through
two DOCUMENT-source selections. Check "Automatically classified from document"; no
manual classification save is needed for these four trusted current fixtures. Missing,
conflicting or stale classification still requires the indicated explicit review.
Inspect the package and use Review & Send. Mock GoldTier remains supported;
use its existing configuration or the separately approved target configuration.
No target mutation precedes confirmation. Expected completion is COMPLETED /
SUBMISSION_CONFIRMED with verified exact-ID readback; reload/reopen causes no Marketplace
request or target replay. Completion does not imply GoldTier KYC or final approval.

## Corrected acceptance

Actual api_marketplace_mock composition tests use fail-on-request network/token seams
and the existing seeded repository, proving all four graphs/PDFs/confirmation flows and
all four existing companies. An eligible neighboring unseeded UEN and an expired seed
reach the ordinary Marketplace seam without synthetic evidence. Physical Mongo checks
exercise eight-record CLI/idempotence/restart and four new normal-runtime completions.
Browser tests exercise actual HTTP and Mongo with configured Marketplace, local seed
provenance, four documents, automatic DOCUMENT classification, Send and reload.
Earlier database-first acceptance remains attributed to the CORRECTION reports. The
2026-10-10 classification-bearing documents and grouped-review candidate have their own
BLOCKER_RESOLUTION implementation, simulation, performance, IDP, manifest and independent
quality-gate evidence. The earlier gate does not certify these changed bytes.

## Document byte identities

| PDF | SHA256 |
|---|---|
| meridian-synthetic-infrastructure-client.pdf | `2f7935ab8304f9770b25f66087bda17caf4dfcf08b2269c357312c15d6438055` |
| orion-synthetic-technologies-client.pdf | `37b38963c5f0f7bf06811327e8107164920bc92bf8316751e870a8f1c751a579` |
| pacific-synthetic-ledger-client.pdf | `e72533ae8c1fe03f0813985c9db922fc79213e21c3e3bab79da07c359c8c75be` |
| straits-synthetic-holdings-client.pdf | `72a48301de57715b05a9fcace2faac7683ab4b2534072c70bdc52793a9eda648` |

## Separate sponsor demo shortlist - 2026-10-10

The owner addendum selects Aurora202400019S (new fictional Morgan65%/Rowan35% direct),
Pacific202400015O, Straits202400016P and Meridian202400017Q. The last three keep the exact
table graphs above. Orion and its original document/seed/history remain available.
The earlier negative unknown-neighbor202400018R fixture is preserved.

Generate only the four new annex documents with
python scripts/generate_synthetic_company_pack.py --sponsor-demo. Seed/check the shortlist
with the existing commands above plus --sponsor-demo. Both flags are explicit: ordinary
startup does not seed and the manager's default eight records are unchanged. Each new
native PDF supplies the six explicit labels and identifies its ownership appendix as
an informational LOCAL_SYNTHETIC_UAT_V1 registry annex. The current parser does not treat
that annex as independent declaration evidence. The authoritative quantitative source
remains the exact complete LOCAL registry seed and the single Decimal engine.

The sponsor acceptance uses actual browser HTTP/Mongo and strict offline XPI Sandbox
transports. Ordinary configured Sandbox Search and human final Send remain required.
Real Sandbox UAT is NOT_VERIFIED; successful offline readback is not a provider approval
or Live claim. See .ai-pipeline/reports/SPONSOR_DEMO_OPERATOR_RUNBOOK.md and the separate
fixture/document manifest for exact bytes, seeds and eight journey evidence. The prior
blocker quality gate does not accept the expanded content.
