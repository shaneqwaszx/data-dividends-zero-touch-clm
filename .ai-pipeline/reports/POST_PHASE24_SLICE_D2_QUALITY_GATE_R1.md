# Post-Phase24 Slice D2 independent quality gate R1

Date: 2026-10-03. **Verdict: PASS for the frozen, bounded D2 candidate.**
D2-QG-001 is repaired and independently falsified in memory and strict Mongo restart.
No current D2 required fix remains. This is not whole-tree CI or publication readiness.

## Reviewed identity and independence

Reviewer dispatch: gpt-6.1-sol / xhigh, fork_turns=none; no separate runtime
self-attestation API was available. This reviewer neither implemented nor remediated D2,
spawned another agent, nor changed acceptance. Applied fyp-quality-gate and the relevant
provider/security/persistence review instructions.

Worktree: C:/Users/shane/.codex-clean2/worktrees/post-phase24-stability-provider-hardening/data-dividends-zero-touch-clm.
Branch: feat/post-phase24-stability-provider-hardening.
BASE_SHA = HEAD = main = observed local origin/main:
707765b1d51172c64b851c9e46e68b3c23006789. No fetch or remote-freshness claim.

Frozen inventory: [POST_PHASE24_SLICE_D2_CANDIDATE_R1.json](POST_PHASE24_SLICE_D2_CANDIDATE_R1.json),
20 reviewed paths; manifest SHA256
eb13ad5ab98be7b8dcc03a2f5bba21d6f49b85e018c602c1fe9837e8a68937ac;
aggregate SHA256 1decaa4f93cfdf6a2af8eeaa2be31e3b39effde353e450d93c00c9b7785387a4.
Algorithm: SHA256 of sorted UTF-8 path + space + sha256 + LF entries.

Independently checked before/after review: current hashes; all81 accepted start
before-images; all20 preserved round0 images; all75 unchanged accepted paths and six
deliberate D2 overlaps; both D1 documents; A/B/C anchors; eight evidence receipts;
initial manifest/FAIL; full D2 and repair deltas. Repair delta SHA256:
4ef48e00af0ffee8bc79ed7408c425043a949ab265a96734cce2ad2c1784f43e.
The original FAIL remains immutable, SHA256
0e1065405ce3ff502e2d26d100b4f53f0090d8d5017c242804a4b2c7335cb637.
Its findings are historical evidence, not current PASS authority.

## Authority and acceptance

Read the owner authorization, AGENTS/workflow/context selector, active planner,
D1 reconciliation, original gate, current EDS contract, XPI matrix, D-061/D-063,
ADR-006/007, persistence recovery contract, owning code/tests and complete D2 delta.

New provider facts, registration Search/Policy binding, accepted Shell/result fields and
mandatory Mock Amend use EXISTING_ACCEPTED_CONTRACT. Bounded process-local storage,
truthful loss, prior-proof reuse/readback and ledger lookup/integrity use
EXISTING_PROJECT_DECISION and explicit D2 authority. D1 established only the exact
synthetic Legal Name UI NO_MATCH; it opened no record and supplied no API rule.
UNKNOWN/INFERENCE and quarantined examples were not promoted into behavior.

| Owner criterion | Independent result/evidence |
|---|---|
| 1. Existing NO_MATCH | PASS; exact registration semantics preserved |
| 2. Configured exact provider match | PASS; seed alone remains review-only |
| 3. Accepted Shell fields | PASS; validated ID/name/country/role/type only |
| 4. Policy registration binding | PASS; accepted ACRA external key |
| 5. No case-ID-to-UEN derivation | PASS; source inspection and executed negative test |
| 6. Required successful Amend | PASS; ledger then requires READBACK |
| 7. Partial/validation Amend | PASS; truthful technical state and stopping |
| 8. Truthful readback | PASS; same retained ID and existing identity comparison |
| 9. Same-process state | PASS; actual local facts support readback |
| 10. Fresh connector loses state | PASS; absent facts cannot become success |
| 11. Loss cannot cause replay | PASS; memory and physical adverse paths |
| 12. Provider seed cannot verify a case | PASS; missing/incomplete/contradictory proof stops |
| 13. Same identity requires real proof | PASS; resolver, prior case, finalized ledger and recomputed fingerprints |
| 14. Different identity/customer | PASS; current identity and retained-ID conflicts stop |
| 15. Unsupported XPI registration query | PASS; separate unchanged dialect, fail-closed tests |
| 16. No portal workflow fields | PASS; full private-state/source inspection |
| 17. No new HTTP/auth | PASS; source and forbidden-network tests |
| 18. No cross-mode fallback | PASS; both existing CLM mode-drift cases executed |
| 19. No duplicate persistence owner | PASS; defensive read-only existing ledger repositories |
| 20. Setup/reset stays local | PASS; constructor/test helpers, no generic runtime endpoint |

## Repair, architecture and 14 owner risks

The guard in onboarding.py binds receipt/outcome case, submission and target-correlation
IDs to the immutable input and actual prior case; recomputes input/idempotency
fingerprints; requires matching resolved/readback IDs, successful classifications,
VERIFIED readback and completed READBACK; compares ledger/receipt/outcome technical
progress, result/state/error/infrastructure facts and the prior case projection.

The existing target-outcome model independently forbids success with errors,
infrastructure failure or invalid terminal states. Proof reads compare typed fields
directly, without rich receipt mapping or finalization callbacks. Case correlation and
target-submission correlation retain their distinct accepted scopes. Strict historical
decode and original finalization/no-replay ownership are preserved.

| Explicit owner risk | Disposition |
|---|---|
| Second workflow owner | Absent; connector holds technical facts, ledger/service own progression |
| Provider state as verified-case evidence | Rejected without matching case and finalized ledger proof |
| source_case_id to UEN | Absent; Policy supplies registration |
| False reuse | Repaired; structured and coupled contradictions fail closed |
| Restart/state loss | Truthful failure/review; retained outcomes alone permit finalization |
| Uncertain replay | Attempts remain retained; fresh providers make no subsequent mutation |
| Policy approval mislabel | POLICY_CREATED stays technical, no KYC/RFA/approval claim |
| Amend drift | EDS Mock remains mandatory; D-063 optional XPI stays separate |
| UI fields leaking into contracts | Absent; no new DTO/filter/portal vocabulary |
| Hidden Sandbox assumptions | Absent; explicit LOCAL/IN_PROCESS/NO_HTTP/NO_AUTH/PROCESS_LOCAL |
| Generic seed/reset | No route/control/API added |
| Mode fallback | Both drift directions stop under existing owner |
| Duplicate persistence | No schema/collection/repository owner or read-time rewrite added |
| Fixtures in runtime | Verified-case builders/private mutations remain test-local |

The connector's bounded dictionary/RLock owns no intent, retry policy, idempotency
cache, audit actor, task queue, CLM state or finalization. Existing memory/Mongo
list_for_case returns defensive snapshots; physical lookup/probe consumption leaves
prior envelopes/ledger content unchanged. No ADR-sized owner replacement was found.

## Fresh execution and adversarial evidence

Application/test bootstrap disabled dotenv before pytest/application imports:
Settings.model_config['env_file']=None; ordinary runs removed PHASE12_MONGO_URI.
PYTHONDONTWRITEBYTECODE=1, PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 and worktree PYTHONPATH
were used. Non-loopback socket.connect was blocked; actual blocked attempts:0.
Pytest arguments: -q -p no:cacheprovider -p anyio.pytest_plugin --tb=line
--show-capture=no --disable-warnings. Raw output stayed in memory; reported facts are
counts, safe statuses and test IDs.

| Fresh independent lane | Actual result |
|---|---|
| Focused and every changed ordinary consumer suite | 609 collected/passed, 0 skips/failures; 74.563s |
| New D2 plus complete Phase12 physical | 32 collected/passed, 0 skips/failures; 46.125s |
| Additional structured memory contradictions | 10 rejected after strict model validation; no prior-proof rewrite |
| Additional coupled physical contradictions | 4 rejected after strict persistence and reopening; no prior-proof rewrite |
| Positive valid reuse with distinct correlations | PASS while mapper/finalization callbacks were forbidden during proof reads |
| Root contract discovery | 44 passed, 0 skips/errors |
| Ruff app/tests; format of three new/replaced files | Exit0, --no-cache |
| Strict mypy app | Exit0, 115 files; temporary cache removed |
| Six governance/security scanners | secrets/state/architecture/policy/provider/tooling all exit0 |
| Whitespace/encoding | git diff --check exit0; all20 paths valid UTF-8, no replacement characters or trailing whitespace |
| Supplementary Phase07 delivery assets | 3 passed, 1 inherited failure; assessed below |

The 609 suite includes new Mock47 (17 repair additions), identity/evaluation,
Phase24 identity, XPI, CLM, zero-touch, onboarding resilience, provider conformance,
reconciliation, persistence, UAT/input-driven and multi-document consumers. It executes
legitimate reuse, both mode drifts and four rich-result/error mapping-fault recoveries.

Extra memory probes covered coupled wrong correlations/fingerprints, changed source
case/idempotency input and contradictory ledger/receipt shell, policy-ID and Amend
progress. Extra physical probes changed both receipt/outcome case IDs, both submission
IDs, both input fingerprints, and ledger resolved/readback IDs together. All pass the
structured model; persisted variants survive strict reopening but cannot hydrate reuse.
An initial exploratory probe used an unsupported field and strict validation rejected
it; corrected probes use the actual idempotency.shell field. Only final completed
probes are counted.

Frozen implementer evidence is attributed, not independently rerun broad evidence:
full backend1957 passed/87 skipped/2044 collected on final repaired Python bytes;
focused202; physical32; scanner tests8/example tests5; frontend415 across35 files,
typecheck/build/dependency checks. Receipt hashes were verified. No full-suite,
frontend/build/browser or remote CI rerun is claimed; unchanged frontend content adds
no D2 browser-rendering claim. Skips are not passes or a substitute for fresh physical
proof.

## Physical containment and security

Fresh reviewer resource: clm-d2-r1-qg-12c70372aa0a,
label codex.task=d2-r1-qg-12c70372aa0a412db959e7611c9d96e2,
container ID 8b12f12298b069850b252c4d66cc086e70f257f854087c05df7b6d58b0aa5530.
Observed Docker29.8.1, Python3.12.10; cached mongo:7.0, --pull never.
Checked-free port27043 bound only127.0.0.1. Inspected only safe identity/label,
binding/mount/running metadata. Ordinary Docker access was permission-denied;
narrow authorized escalation used an absent task-specific CLI config. No automatic
approval review rejection occurred.

All physical databases were newly generated allowlisted clm_p12 names. No clm_poc or
unrelated service was contacted. URI stayed in process memory and was neither printed
nor persisted. After both lanes: allowlisted DB count0; exact label/binding and two
exclusive anonymous volumes reverified; owned container/volumes removed; label,
container and both volume counts0; fresh listener verified port release.

No .env, owner/sponsor authentication material, portal, cookies/storage/headers,
raw private provider payload or protected document body was accessed. Existing tests may generate
synthetic local auth internally; no value was retrieved/reported. No newly tracked
secret/confidential artifact was found within scanner coverage.
Reviewer external counters: Sandbox UI/API/mutation0, GoldTier Production0, ACRA0,
other providers0. Disposable local Mongo is the sole authorized database activity.

## Findings, change dimensions and readiness

No current D2 finding or required fix remains. The inherited failure is
test_synthetic_document_pack_is_explicit_and_bounded: its old exact allowlist excludes
garden-partnership-reviewed-client.pdf and multiple-owner-demo-client.pdf.
Independently verified the test unchanged versus HEAD after newline normalization,
both assets present in the accepted pre-D2 snapshot, and their bytes unchanged.
D2 changes no delivery asset or allowlist; this does not defeat bounded provider
acceptance. It remains unresolved repository/CI debt requiring separately authorized
integration disposition. This report does not waive it or declare blanket CI PASS.

API/type: internal ledger list_for_case and constructor-only Mock parameters change;
HTTP routes/DTO schemas do not. Durable schema/index/CAS semantics: unchanged.
Connector/runtime: local facts, safe missing/collision/capacity handling, mandatory
readback and proof-bound reuse change. Configuration/composition: unchanged.
Business-rule/mapping: no new sponsor rule; existing dialect/mappers retained.
Auth/security: external auth/RBAC unchanged; retained-proof integrity tightened.
Architecture/provider status: existing owners preserved; Mock remains PROJECT_OWNED /
LOCAL / IN_PROCESS / NO_HTTP / NO_AUTH / PROCESS_LOCAL; Sandbox remains Partial.

Process-local loss, bounded capacity, existing optional-field comparison semantics
and single-instance concurrency remain explicit limits. No distributed exactly-once,
provider persistence, real Sandbox behavior, KYC/compliance approval, RFA or Live
interoperability is proved. Applicable sponsor questions remain open.

D2 acceptance is complete for this exact candidate. D3/E/F/G readiness is not granted
or started. Real ACRA/GoldTier readiness is not established. Publication remains
unauthorized and not ready; no clean-committed pre_pr_check was appropriate here.

## Git and write boundary

Before report:98 dirty paths (51 tracked modifications,47 untracked), empty index.
This report adds exactly one untracked path; frozen reviewed/accepted content remains
unchanged. Sole durable reviewer write: this assigned R1 report. Necessary temporary
mypy/resource data was cleaned. No source/test/config/ordinary-doc/manifest/old-report
fix, Git mutation, fetch, staging, commit, push, PR, merge or next-phase work occurred.

Next authorized action: return this exact bounded D2 verdict and owner handoff, preserve
the candidate, and STOP. Any later content change needs fresh independent review.
