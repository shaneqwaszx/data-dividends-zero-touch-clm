# Synthetic company pack bounded EOF remediation

Owner-authorized scope: one redundant terminal LF removed from `scripts/synthetic_company_pack.py`. Exactly one ordinary final newline remains. Python AST is identical; no statements, imports, comments, indentation, or behavior changed.

- Authorized base and fetched origin/main: `21124498cb1b8fd47b1406534d6fd9c24af0e2ea`.
- Branch: `feat/synthetic-happy-path-company-pack`.
- Before SHA256: `185e222be54081ccb3cadca2b0075d4edbc66aac89641519da5453188972d73e` (3640 bytes).
- After SHA256: `716b00f50c1f686bd57d964333ddaae6b669814ee152ef255dfdb3fb9dc0bc1f` (3639 bytes).
- Complete byte proof: corrected bytes plus one `0a` byte equal the original staged bytes.
- All 32 other accepted product/support files and all eight prior evidence files remain raw-byte identical to their accepted identities.
- Prior aggregate: `12cf9e2606161e7436d6b0bf105c4d8a5e8ba458e4343a52bce12fcd811d841c`.
- Corrected 33-path aggregate: `d575482838ab74cf245ea69882f056fa4fa998304b2024bb51610f85bfdb7fea`.
- Old manifests and Quality Gate PASS remain unchanged historical evidence for their original bytes. The new EOF manifest and independent EOF Quality Gate identify the current candidate.
- Explicit git add re-staged only the corrected product path; necessary new derivative evidence is staged separately.
- Staged whitespace check PASS; explicit UTF-8/BOM/NUL/final-newline/trailing-whitespace checks apply to all publication text paths (PDFs excluded as binary).
- Command-local `core.autocrlf=false` preserves accepted raw bytes. `core.whitespace=blank-at-eol,blank-at-eof,space-before-tab,cr-at-eol` recognizes existing valid CRLF while retaining trailing whitespace and redundant EOF checks. No persistent Git configuration changed.
- Existing accepted functional evidence remains applicable because every executable byte except the redundant EOF LF is identical, and Python AST is identical. Fresh independent review is required before commit; full expensive regression is not rerun solely for this correction.

Scope and behavior remain the previously accepted database-first synthetic company pack. The additive nullable synthetic provenance browser field is part of the already accepted implementation. This remediation changes no API/type, schema, connector, configuration, business rule, mapping, auth/security, architecture, provider status, or runtime behavior.
