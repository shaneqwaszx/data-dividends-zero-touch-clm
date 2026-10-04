# Fresh G6 official ACRA Mock acceptance

Date: 2026-10-04 (Asia/Singapore). Owner-authorized one fresh run; no product source edits, fetch, rebase or publication during acceptance.

**PASS — G6_TARGET_CLIENT_TIMEOUT_WITH_VERIFIED_RETAINED_COMPLETION.** This is the bounded acceptance receipt, not an independent final A-G verdict.

| Required field | Observed evidence |
|---|---|
| MODEL USED | Coordinator requested GPT-6.1 Sol / Extra High. Primary runtime model/effort metadata is not exposed; no unverifiable self-attestation. |
| BASE SHA | 707765b1d51172c64b851c9e46e68b3c23006789 |
| CANDIDATE BEFORE G6 | 64e76a1b9a673ad09050794321b58fbc9eeeb0945e2dbfddf23bc9a929981cc6 |
| DISPOSABLE DATABASE | clm_p19_f14e7cc2e1a64f428b071420 |
| ORIGINAL CLM_POC TOUCHED | NO; no retained original record inspected or mutated |
| ACRA PROVIDER CLASSIFICATION | ACRA API Marketplace Mock / MOCK / NON-PRODUCTION |
| PREVIOUS G6 REQUESTS | 3 |
| ADDITIONAL TOKEN REQUESTS | 1 |
| ADDITIONAL PROFILE REQUESTS | 1 |
| ADDITIONAL OFFICERS REQUESTS | 1 |
| ADDITIONAL TOTAL | 3 |
| CUMULATIVE G6 TOTAL | 6 |
| OTHER ACRA REQUESTS | 0 |
| PROFILE RESULT | COMPLETE; canonical Garden identity matches |
| OFFICERS RESULT | COMPLETE; canonical evidence, no personal payload retained |
| GARDEN LEGAL FORM | PARTNERSHIP |
| OWNERSHIP PROVIDER RESULT | UNSUPPORTED; empty parties; no fabricated percentage or UBO |
| RELATIONSHIPS PROVIDER RESULT | UNSUPPORTED; empty relationships; no HTTP operation |
| DOCUMENT EXTRACTION | LOCAL / AUTO_CONFIRMED; four identity observations; reviewed Garden PDF |
| RECONCILIATION | MATCHED; four MATCH outcomes |
| LOCAL OWNERSHIP | USER_SUPPLIED_DECLARATION / LOCAL / MANUAL_DECLARATION_POC; reviewed synthetic 60/40 |
| UBO | Existing Decimal engine; 60/40 PROVISIONAL_UBO_CANDIDATE; no legal UBO claim |
| REVIEW_AND_SEND_POST_COUNT | 1 |
| REVIEW_AND_SEND_HTTP_RESULT | CLIENT_READ_TIMEOUT at existing 30-second read deadline |
| TARGET LEDGER RESULT | Exactly one FINALIZED entry; SUCCESS outcome/receipt; captured submission matches; no uncertain active mutation |
| GOLDTIER MUTATION COUNTS | SEARCH 2; SHELL 1; POLICY 1; AMEND 1; READBACK 1; FINALIZATION 1 |
| NO_REPLAY | YES; one server-observed target-confirmation POST; no second Shell/Policy/Amend |
| READBACK | VERIFIED; retained after fresh authenticated summary |
| FINAL WORKFLOW STATUS | COMPLETED; no active exceptions |
| POST-TIMEOUT READS | 5 |
| POST-TIMEOUT EXTERNAL CALLS | 0 |
| DATABASE CLEANUP | Terminal proof -> sanitized receipt -> candidate/checkpoint hashes -> cleanup -> database/process absence and free ports verified |
| P0/P1/P2 | 0 established in this acceptance; final independent cumulative gate remains pending |
| G6 VERDICT | PASS / G6_TARGET_CLIENT_TIMEOUT_WITH_VERIFIED_RETAINED_COMPLETION |
| RESIDUAL RISK | Client timeout remains possible and is not fixed by this acceptance. Historical transport residuals and original retained-record validation remain separate. |
| NEXT ACTION | G20 freeze -> fresh independent final A-G gate -> conditional authorized publication -> human merge stop |

The observed two SEARCH calls are the initial identity Search and the mandatory confirmation Search recheck. The retained D2 logical plan is SEARCH -> SHELL -> POLICY -> AMEND -> READBACK. Its SEARCH checkpoint reuses validated existing Search evidence; each mutation and readback executes once. Finalization records one successful retained result.

Submission: `d006399b-9403-4e9a-8037-d2eb50b2f986`; target correlation: `b8209235-7b02-4f90-ae4d-bbefc4caec06`; case: `19c74719-4a11-4777-ae36-5ceac4f34531`. The server captured the immutable submission identity before target dispatch; it matches the retained ledger and fresh summary.

All terminal proof, fresh authenticated summary/readback and repository-safe ledger observation completed within the unchanged 30-second post-timeout observation window. No deadline was inflated. Exactly three additional ACRA HTTP requests succeeded; no refresh, retry, shareholder, ownership, relationship, Production or other provider request occurred. GoldTier stayed PROJECT_OWNED / LOCAL / MOCK / NO EXTERNAL HTTP; Sandbox calls/mutations and Production calls were zero.

Receipt hashes:

| Task-owned ignored evidence | SHA256 |
|---|---|
| tmp/fg_20261003/g6_fresh_20261004_0be4dab4/parent.py | 710079b8f1c6085afe5255f06447b17f98ddd9e4fe7dc187acaacfcd6b9cfa3b |
| tmp/fg_20261003/g6_fresh_20261004_0be4dab4/server.py | 9c55fdc1815686b3bf491c9a389b870d2c7e52cf64fb5a5fa4203ef9981cac46 |
| tmp/fg_20261003/g6_fresh_20261004_0be4dab4/g6_preflight.json | 24851f172cd47fb0338af0903052c3115022fe753bef82353406e370f0ed6884 |
| tmp/fg_20261003/g6_fresh_20261004_0be4dab4/g6_terminal_proof.json | 8ebcf1b4dbd51532bc484bde54fbe970b7055b9e05749fbe61a079cbcaf69a54 |
| tmp/fg_20261003/g6_fresh_20261004_0be4dab4/g6_evidence_freeze.json | 6617e1defea9f6e64f875220710c63f63dd67ac75eca98c1fe4a54f67936c500 |
| tmp/fg_20261003/g6_fresh_20261004_0be4dab4/g_normal_cleanup.json | 3e664a0e230316326ba2877c4e9029bdeccf17c5af3911f3ca785c9e966eb3b4 |
| tmp/fg_20261003/g6_fresh_20261004_0be4dab4/g_normal_network_counts.json | de6206e60dd02c7ab3af183244a07bcc6eb40258a528f06c26722985800e0880 |
| tmp/fg_20261003/g6_fresh_20261004_0be4dab4/g6_target_counts.json | 5266190aaa4e0a1da7b208140708ee065e5bff916927ebe43e672b0fe8ce3c75 |
| tmp/fg_20261003/g6_fresh_20261004_0be4dab4/g6_target_sequence.json | 93fefc7e6e22ebd7698372b7af5376b438df9c805ae78a1eafaa8793a6c40e24 |
| tmp/fg_20261003/g6_fresh_20261004_0be4dab4/g6_ledger_dispatch_identity.json | 736157032aa2b75419dc755ef75a772f983893bf89695d481983cf78ac2ad57a |

The original incomplete three-request G6 and its UNKNOWN terminal result remain preserved in G6_OWNER_CHECKPOINT.json; this fresh successful run does not rewrite them. The pre-run155-path content and all preserved checkpoint receipts were verified byte-identical. Prior owned databases were absent, the original main checkout was clean, the index was empty, and no worktree-owned process/container remained. Only MONGO_DATABASE was overridden; normal configuration was loaded through its runtime loader without printing private contents.

This acceptance changes no API/type, schema, connector, configuration name, business rule, mapping, auth/security, architecture owner, provider classification or product runtime behavior. Only ignored observation harnesses and sanitized acceptance documentation are added. Cumulative A-G change dimensions remain recorded in the final manifest.
