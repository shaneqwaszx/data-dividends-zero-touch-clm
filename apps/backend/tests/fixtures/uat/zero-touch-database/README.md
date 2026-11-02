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
LOCAL_SYNTHETIC_UAT_V1 database-first owner. Their four native-text PDFs with explicit Company - Private / Corporate labels
are indexed in the parent README with exact SHA256 values. See
[the corrected operator guide](../../../../../../docs/demo/SYNTHETIC_COMPANY_PACK.md).
Existing Beta's current effective percentages are30/25/17/14/8.5/5.5 (P1/P2 candidates);
Gamma's are30/25/20/10/10/5 (P1/P2 candidates). Current fixture source/tests supersede
the historical simplified values in the table above. Seed all eight with the existing
seed_zero_touch_happy_path_companies.py manager; configure api_marketplace_mock/mongo/auto.

## Separate sponsor demo native documents

Aurora202400019S, Pacific202400015O, Straits202400016P and Meridian202400017Q have separate
*-sponsor-demo-registry-annex.pdf files. Each includes native identity/classification
labels and an informational LOCAL registry annex matching its seed graph. The annex is
neither official ACRA evidence nor an independent client declaration. Regenerate these
four only with generate_synthetic_company_pack.py --sponsor-demo. Explicit seed/check
--sponsor-demo selects these four; the ordinary eight-fixture default is unchanged.
Aurora's fictional natural owners are65/35. Existing Pacific/Straits/Meridian graphs,
Orion files and the negative018R neighbor fixture remain. Exact bytes and journey evidence
are indexed in DEMO_FIXTURE_AND_DOCUMENT_MANIFEST.md under .ai-pipeline/reports.

## D-101 partnership agreement and Government status letter

Two image-only, single-page fictional PDFs, each visibly labelled FICTIONAL FYP TEST DATA.
Written by `scripts/generate_zero_touch_happy_path_documents.py` (default run writes only
these two; `--company-scans` is needed to regenerate the four company scans above, whose
bytes are unchanged). Verdana-style glyphs are used so local Tesseract reads the partner
tokens exactly.

| Document | SHA256 | Content |
|---|---|---|
| demo-gamma-partnership-agreement.pdf | e45feb3aad2a02f9c493cfd7601acd0ec01774f4d8f1a46829f222344c08cd54 | Gamma identity labels, `Agreement Date: 2026-01-05`, one `Partner Share: DEMO GAMMA PERSON Pn: NN percent: NATURAL_PERSON` line per partner (30/25/20/10/10/5) and the signing partners |
| demo-parks-government-status.pdf | bbd0fd4d7c08e40d74fa9e777902343ac5f7465d41262b1fd00c066c5b118e96 | DEMO PARKS FYP TEST AUTHORITY, T99GB0105G (fictional: year 2099; D-114 PQ code GB = statutory board, so it routes to the government register), `Founding Instrument:`, `KYC Customer Type: Government`, `Client Segment: DI - Government`, two display-only authorised signatories; not ACRA-registered |

Gamma's registry seed now lists P1-P6 as partners by name and role only, with no ownership
links; the split comes only from the agreement, confirmed by the RM (D-101). The earlier
classification-only `demo-government-scanned.pdf` (209990105E) is retired. No real
ministry, agency, crest, partnership or person appears in either document.
