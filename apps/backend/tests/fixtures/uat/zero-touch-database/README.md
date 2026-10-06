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
