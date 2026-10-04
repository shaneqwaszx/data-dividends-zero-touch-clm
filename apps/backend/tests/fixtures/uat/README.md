# Bounded Synthetic Demo Asset Index

This is the single asset index. All 13 files are generated synthetic client/test evidence,
not copied sponsor/customer documents or ACRA extracts. Garden current entity-level fields
come from already-recorded safe normalized Mock observations; supplementary owners are fictional.
The older Garden pair is preserved Slice A protocol regression evidence, not the current
PARTNERSHIP profile. Its adverse document's boilerplate does not override its conflicting fields.

Merlion four-field baseline: MERLION CIRCULAR LABS PTE. LTD.; 202400001A;
18 INNOVATION WAY, #04-01, 018956, SG; Country SG. A unique labelled field has parser
confidence .97; duplicate/ambiguous .40; missing 0. Four identity fields only are extracted.
PDF ownership prose is not an automatically accepted ownership graph.

Every row is safe to publish as controlled synthetic evidence. Valid text PDFs pass current
structure validation; no-text.pdf intentionally has valid structure without a text marker and
returns unavailable evidence. invalid-document.pdf intentionally fails before provider dispatch.
Do not turn negative fixtures into completion documents. Unknown files remain rejected by the
exact Phase07 allowlist. Hashes bind current bytes; regenerate only the named generator's
owned assets and review changes. All assets are mapped in FINAL_UAT_ACCEPTANCE_MATRIX.md.

| Filename | Purpose | Classification | Expected entity / UEN | Journey | Expected fields / comparison | SHA256 | Generator / source | Safe to publish? |
|---|---|---|---|---|---|---|---|---|
| `clean-company-profile.pdf` | Merlion clean evidence / cache warm and replacement | SYNTHETIC CLIENT | MERLION CIRCULAR LABS PTE. LTD. / 202400001A | F-C; rectification | Four Merlion fields; MATCH | `befaea4d3fcc1c3c10ed3ce7b39156cb3341a522dc2d2b7986834d6c82cd700f` | scripts/generate_phase08_synthetic_pdfs.py | YES — controlled synthetic evidence |
| `address-mismatch.pdf` | Address conflict | SYNTHETIC ADVERSE | Merlion / 202400001A | F-rect-address | Merlion; address 25 ROBINSON ROAD, SINGAPORE 048547; address CONFLICT | `1c8946aae2029ae42f17dc5dbc20256dbaabdbd98fb1a2f778afbc099136e751` | scripts/generate_phase08_synthetic_pdfs.py | YES — controlled synthetic evidence |
| `legal-name-mismatch.pdf` | Legal-name conflict | SYNTHETIC ADVERSE | Merlion / 202400001A | F-rect-name | INCORRECT SYNTHETIC NAME PTE. LTD.; other Merlion fields; name CONFLICT | `f1e293890955dd07b84441d1afc4e7029cc84808cbabc7c0a66d7f360c83a5e7` | scripts/generate_phase08_synthetic_pdfs.py | YES — controlled synthetic evidence |
| `missing-field.pdf` | Missing required field | SYNTHETIC ADVERSE | Merlion / 202400001A | F-rect-missing | Merlion identity/address; Country absent, confidence 0; required-field review | `7eef95d5d7fc738a9544f2592d6f1fcf1f89537e12927173a7454cc3978e51d4` | scripts/generate_phase08_synthetic_pdfs.py | YES — controlled synthetic evidence |
| `low-confidence.pdf` | Ambiguous labelled value | SYNTHETIC ADVERSE | Merlion / 202400001A | F-rect-confidence | Merlion plus SECOND SYNTHETIC NAME PTE. LTD.; name confidence .40; review | `3b24e3aa5daa1f2da7dcb986e53f60caa54b4d52cd197c7716c330b5b6446aa4` | scripts/generate_phase08_synthetic_pdfs.py | YES — controlled synthetic evidence |
| `no-text.pdf` | No OCR / text unavailable | SYNTHETIC TEXTLESS NEGATIVE | No extracted identity | F-negative-text | Four fields unavailable; DOCUMENT_TEXT_UNAVAILABLE; valid structure | `22d74234c8512ab55ee16eec45865c8c642c69bd70df0245049a670c744945d8` | scripts/generate_phase08_synthetic_pdfs.py | YES — controlled synthetic evidence |
| `cycle-uen-clean.pdf` | Document passes before cycle stop | SYNTHETIC ADVERSE | CYCLIC HARBOUR HOLDINGS PTE. LTD. / 202400006F | F-negative-cycle | 18 CYCLE STREET, #01-01, 049001, SG; Country SG; document MATCH then OWNERSHIP_CYCLE | `e45585eb38b1e52d5d0ec4836b9d6facb436b7f0c18127d5923f071ccd776468` | scripts/generate_phase08_synthetic_pdfs.py | YES — controlled synthetic evidence |
| `second-case-isolation.pdf` | Independent configured target-review case | SYNTHETIC CLIENT | LION CITY EXISTING CUSTOMER PTE. LTD. / 202400005E | F-negative-seed | 18 CUSTOMER ROAD, #05-02, 068914, SG; Country SG; identity MATCH, target review; no verified reuse proof | `e872c442a1bc110d3cf1f3b51c770e9097acd752f00073395d9b2a5f0cde006c` | scripts/generate_phase08_synthetic_pdfs.py | YES — controlled synthetic evidence |
| `invalid-document.pdf` | Pre-provider invalid format rejection | SYNTHETIC INVALID NEGATIVE | No identity | F-negative-format | DOCUMENT_STRUCTURE_INVALID; no extraction/provider call | `cb56d90fc6952b0c96f0f67760434d25bdff6e5b3a976f65386263e992202c2c` | Inherited Phase07 controlled fixture; no current generator identified | YES — controlled synthetic evidence |
| `garden-business-clean-onboarding-profile.pdf` | Preserved Slice A protocol regression | SYNTHETIC HISTORICAL CLIENT | GARDEN BUSINESS / 11111999A | A-regression only | 18 GARDEN WALK, #01-01, 018919, SG; Country SG; MATCH only against old COMPANY protocol fixture | `075bc3979d00e80a29dafe1b6cc078a7b9427ff9178f7b417b12edc224259544` | scripts/generate_garden_demo_pdfs.py | YES — controlled synthetic evidence |
| `garden-business-conflicting-onboarding-profile.pdf` | Preserved explicit four-field conflict | SYNTHETIC HISTORICAL ADVERSE | GARDEN DEMO TRADING / 11111998B | A-conflict regression | 25 DEMO ROAD, #02-02, 048547, SG; Country MY; all four conflicts against old Garden fixture | `572b0ddb8cab05ce5f619e0acd97618808f11afc6da4e3afc1d165b430c8ab45` | scripts/generate_garden_demo_pdfs.py | YES — controlled synthetic evidence |
| `garden-partnership-reviewed-client.pdf` | Current Garden supplementary reviewed declaration | SYNTHETIC CLIENT; safe normalized entity fields | GARDEN BUSINESS / 11111999A | F-A | 306C XYZ LINK, #03-21, ABC GARDEN, 333333, SG; Country SG; four MATCH; fictional 60/40 entered manually | `13f8d74a84bb5acd84f03c38c91cb6aadbc676c9652d051c5117aa20bc96fc6a` | scripts/generate_slice_b_demo_pdfs.py | YES — controlled synthetic evidence |
| `multiple-owner-demo-client.pdf` | Second complete independent happy path | SYNTHETIC CLIENT | MULTIPLE OWNER DEMO PTE. LTD. / 202400008H | F-B | 18 SHAREHOLDER ROAD, #03-01, 049003, SG; Country SG; four MATCH; synthetic registry 50/30/20 | `ff7b89563b6ac4767d695dffc09e7aa947eba66481a57cb312f0b81c3522d870` | scripts/generate_slice_b_demo_pdfs.py | YES — controlled synthetic evidence |
