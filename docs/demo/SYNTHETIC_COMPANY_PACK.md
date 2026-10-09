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

The four byte-preserved native-text PDFs reside under
apps/backend/tests/fixtures/uat/zero-touch-database. Regenerate only these four using
python scripts/generate_synthetic_company_pack.py. Legal Name/UEN/Registered Address/
Country are the only identity fields; PDFs contain no ownership quantities. Quantitative
ownership comes from the LOCAL_SYNTHETIC_UAT_V1 registry seed.

Enter the exact company name/UEN, choose SG and upload its matching PDF. The four fields
reach MATCH/ACCEPTED/HIGH with deterministic0.97 evidence scores. The ordinary Decimal
engine produces the table's ownership results without manual ownership supplementation.
Select target classification explicitly (Company - Private / Corporate for the four new
companies), inspect the package and use Review & Send. Mock GoldTier remains supported;
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
provenance, four documents, explicit classification, Send and reload.
Executed counts and the fresh independent verdict belong to the CORRECTION implementation,
manifest and quality-gate reports. The earlier gate does not certify this candidate.

## Document byte identities

| PDF | SHA256 |
|---|---|
| meridian-synthetic-infrastructure-client.pdf | `b34c6894129f41e898ce54b04cc0a5927ae1d8f56b83be9e602348f49f1ba88c` |
| orion-synthetic-technologies-client.pdf | `87420d3b16467f157fafe16c59d05940dbfb2f7566eb34b1976193420bb07f38` |
| pacific-synthetic-ledger-client.pdf | `ab228e462648f022b5bf4c1a8262d919b7975d33e0114eb11da41c150f3eb30d` |
| straits-synthetic-holdings-client.pdf | `ed24243f5b7ad02d51222975b9348f61cb9091c17882ca8082d32f4eb3b09597` |
