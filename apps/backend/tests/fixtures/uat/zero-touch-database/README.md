# Fictional FYP database happy-path scans

These four image-only PDFs exactly match the normalized local seeds; no real ACRA
record, personal identifier or HTTP payload is included. GoldTier is not seeded.
See [manual UAT and complete expected-result mapping](../../../../../../docs/demo/ZERO_TOUCH_DATABASE_HAPPY_PATH_UAT.md).

| Company | UEN | Document | Registry | Effective ownership | Provisional candidates >=25% | Expected GoldTier path |
|---|---|---|---|---|---|---|
| DEMO ALPHA CIRCULAR FYP TEST PTE. LTD. | 209990101A | demo-alpha-scanned.pdf | CACHE_HIT / local synthetic | P1 60, P2 40 | P1/P2 | Successful NO_MATCH -> one Shell -> Policy -> exact-ID readback |
| DEMO BETA HOLDINGS FYP TEST PTE. LTD. | 209990102B | demo-beta-scanned.pdf | CACHE_HIT / local synthetic | P1 42, P2 28, P3 30 | P1/P2/P3 | Same new-customer path |
| DEMO GAMMA TECHNOLOGIES FYP TEST PTE. LTD. | 209990103C | demo-gamma-scanned.pdf | CACHE_HIT / local synthetic | P1 50, P2 30, P3 20 | P1/P2 | Same new-customer path |
| DEMO DELTA SUSTAINABILITY FYP TEST PTE. LTD. | 209990104D | demo-delta-scanned.pdf | CACHE_HIT / local synthetic | P1 30, P2 10, P3 40, P4 20 | P1/P3 | Same new-customer path |

ACRA operations0 while fresh/complete. Actual Sandbox absence is not claimed.
All source graphs total100% per owned entity. Decimal engine only; candidates are not
legal UBOs. Conditional Amend follows the existing target plan and is skipped for the
tested identity-only package. Regenerate with scripts/generate_zero_touch_happy_path_documents.py.

## Native-text company pack extension

Orion202400014N, Pacific202400015O, Straits202400016P and Meridian202400017Q use the same
LOCAL_SYNTHETIC_UAT_V1 database-first owner. Their four identity-only native-text PDFs
are indexed in the parent README with exact SHA256 values. See
[the corrected operator guide](../../../../../../docs/demo/SYNTHETIC_COMPANY_PACK.md).
Existing Beta's current effective percentages are30/25/17/14/8.5/5.5 (P1/P2 candidates);
Gamma's are30/25/20/10/10/5 (P1/P2 candidates). Current fixture source/tests supersede
the historical simplified values in the table above. Seed all eight with the existing
seed_zero_touch_happy_path_companies.py manager; configure api_marketplace_mock/mongo/auto.
