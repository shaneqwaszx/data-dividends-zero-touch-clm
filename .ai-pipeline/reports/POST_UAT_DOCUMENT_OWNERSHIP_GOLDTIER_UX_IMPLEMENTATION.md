# Post-UAT implementation evidence and owner handoff

Date: 2026-10-05. Immutable implementation evidence snapshot at R1 content freeze.
The sole R0 P2 generated-guide finding has been repaired and verified. The later independent
POST_UAT_DOCUMENT_OWNERSHIP_GOLDTIER_UX_QUALITY_GATE.md records its final result and
records the fresh recheck verdict; this snapshot is not a live status.
Base/HEAD/current inspected origin main: ae27654a075f13354364e86ec8fe5a81d24777d4.
Branch: fix/post-uat-document-ownership-goldtier-ux.
Managed worktree: C:/Users/shane/.codex-clean2/worktrees/post-uat-document-ownership-goldtier-ux/data-dividends-zero-touch-clm.
No commit, push, PR or merge has occurred at this implementation evidence boundary.
The final Git receipt is reported separately after the authorized local commit.

## Behavior and owner boundaries

DocumentProcessingService remains the sole matching/auto-confirm owner. A current
unambiguous original value must normalize to MATCH against the current canonical
value; retained canonical comparison must also agree, score must be >= the frozen
case threshold, and unresolved current contradictory evidence prevents confirmation.
High-confidence mismatch, ambiguity, low score and superseded evidence remain review.
Orchestration evaluates admissible attach/intake documents while GOLDTIER_SEARCH
remains authoritative; all eligible identity fields can become REVIEWED/AUTO_CONFIRMED
without Shell/Policy/Amend or unrelated readiness advancement. Retained field events
distinguish AUTO CONFIRMED and HUMAN ACCEPTED; extraction scores are not probabilities.

Ownership reviewer notes accept omitted/null/blank-to-null input; supplied text retains
10-240 character, safe text/control-character/prompt-marker checks. Actor/time,
source/document/version/observations/as-of/graph/replacement/provenance remain structured
audit. Historical string notes and absent notes decode through existing schema9 without
read-time writes or invented prose. Existing-customer confirmation rationale remains
mandatory. A creator-owned graph replacement invalidates earlier local review even
after classification changed, then recomputes ownership/readiness before explicit send.

Normal official Marketplace Mock composition automatically enables the existing exact
eligible Garden11111999A fixture, independently of the deprecated legacy toggle.
Freshness/success/failed-operation/UEN/provenance guards and official quantitative
discrepancy/no-double-count behavior remain. Only official OFFICERS role rows are
descriptive when the exact validated supplemental graph is authoritative; other roles,
control/interests, conflicts and unbound evidence still block. Official identity,
officers and empty/unsupported evidence remain intact. Graph provenance is
LOCAL_SYNTHETIC_SUPPLEMENT/LOCAL, not official ACRA percentages or legal UBO authority.
The unchanged Decimal engine yields SIM LIM62.500000%, LIM CHOON HUAT37.500000%,
ABCD123 effective51.13636375%; withdrawn FORMER OWNER is excluded. Both named natural
persons meet the unchanged inclusive >=25% provisional POC threshold.

Completed details show retained GoldTier ID first and backend-projected actual customer
handling second, then provider/environment/status/readback/operations. Existing identity
reuse remains distinct from new local case creation: two same-entity cases retain143878
with no Shell; a different definitive NO_MATCH entity retains the Shell/new-ID path.
Human CONFIRMED_EXISTING remains separate from provider EXACT_MATCH. Downstream GoldTier
KYC/four-eye approval is not claimed.

The narrow case-scoped POST verify-goldtier endpoint accepts only expected_submission_id.
Existing case access reauthorizes under the lock; finalized successful current Sandbox
ledger facts supply the retained target ID. OnboardingService invokes one existing XPI
exact-ID Search with goldTierID, using its sanitized decoder. It returns ephemeral
bounded VERIFIED/REQUIRES_REVIEW/UNAVAILABLE, check time and safe verified identity only.
No mutation, replay, persistence/ledger write, target ID substitution or confirmed-state
rewrite occurs. No match/different ID/multiple/malformed/failed response preserves the
confirmed result. The UI uses an explicit action, separate scoped cancellable cache
entry, and discards navigated/session-incompatible results. Uncertain-submission status
checking retains its own semantics and automatic bounded observation behavior.

## Acceptance evidence map

| Owner tests | Evidence |
|---|---|
| 1-6,10 | test_post_uat_remediation threshold boundary/mismatch/ambiguity/contradiction/stale; document processing and semantic completion suites |
| 7-9 | independent attach/intake at unresolved Search: REVIEWED/AUTO_CONFIRMED, retained checkpoint/blocker, only Search call |
| 11-14 | omitted/null/blank/safe/unsafe declaration/request/receipt; physical schema9 optional/historical restart equality and raw read-without-write |
| 15-16,20-21 | normal composition with either legacy toggle; real official decoder roles; automatic Garden browser/Slice B; exact Decimal results/provenance/no manual receipt |
| 17-19 | existing failure/expiry/nonofficial/non-Garden eligibility and conflicting quantitative evidence suites; additional role/control/conflict remains review |
| 22-24 | S3SubmissionStatus rendering retained handling and ID-first order; new/existing/Garden completed browser details |
| 25-26 | XPI second same-entity distinct local/source case IDs, five GETs/no Shell; different entity new999123 with one Shell; CONFIRMED_EXISTING vs EXACT_MATCH |
| 27-29 | six verified/adverse completed endpoint responses: one exact-ID GET, equal retained case/CLM/timeline/version/submission/operations; Garden UI verifies143878 with zero writes |
| 30-31 | current case access denies Sophia/HR with404 before Search; stale/unconfirmed input409; extra client ID/invalid UUID safe constant422/no echo |

## Execution evidence

All commands ran in this managed worktree. Python runtime is the existing primary
venv exposed through an ignored worktree junction; installed versions were observed,
not inferred. Locked frontend dependencies were installed offline with no lockfile delta.
Tesseract is an actual provisioned local executable on PATH. Provider transports and
browser network guards are synthetic/offline; external ACRA calls0, external GoldTier0.

| Lane | Final execution/result |
|---|---|
| Full backend coverage | 2489 collected across the complete partition: all-except-orchestration2284 PASS/1 generated-guide FAIL/116 explicit skips (670.72s); complete orchestration88 PASS (308.30s), including both100-run stability checks. R1 changes no runtime/test content; corrected generated-guide catalogue suite16 PASS closes the sole failure, yielding2373 verified ordinary tests/116 guarded skips. |
| Focused backend | final auto-confirm/notes/Garden/verification38 PASS before added finalization regression; late-classification/repeated-edit finalization1 PASS; auth+Slice B81 PASS |
| Real OCR | test_s2_local_ocr.py -k real_local_ocr_acceptance with CLM_REAL_OCR_REQUIRED=1:6 PASS/0 skip (PNG/JPEG/TIFF/scanned PDF/mixed PDF/poor PNG) |
| Physical Mongo | existing guarded runner restricted to phase13, phase24c, S2 intelligence, S3 submission:4 suites/37 collected/37 PASS/0 failure/error/skip |
| Frontend | npm test -- --run:42 files/517 PASS |
| Guarded browser |15 distinct affected tests PASS: Garden happy/conflict/delay/navigation5, zero-touch Garden2, ownership edit/proposal2, Slice B Garden1, five separate S3 modes5 |
| Ruff | ruff check --no-cache scripts tests apps/backend/app apps/backend/tests: PASS |
| Strict mypy | backend-configured mypy app with temporary cache:124 source files PASS |
| TypeScript/build | npm run typecheck and npm run build: PASS |
| Contracts | unittest discover tests/contract:44 PASS |
| Tooling/lifecycle | complete unittest discover tests with contract helper path and worktree runtime:350 PASS, including executed Windows lifecycle safety |
| Browser discovery |61 configured selectors, five Sandbox modes; CI budget198min retains60s execution/120s bounded cleanup per lifecycle; actual Tesseract provisioned in CI |
| Governance/security | check_project_state, check_architecture, check_tooling_config, check_policy_authority, check_external_provider_readiness, check_secrets: PASS |

The earlier broad backend run had three obsolete route/Garden expectations, corrected
and independently exercised before this final full rerun. Earlier browser selectors/
fixtures/manual assumptions were corrected; a genuine stale-review transition defect
was reproduced and fixed through the existing owner. The final R0 broad run exposed
only the stale generated-guide artifact. R1 regenerated that guide from the unchanged
authoritative catalogue and passed both generator --check and the entire16-test owning
catalogue suite. All source/test/runtime hashes remain identical to the R0 freeze;
the new guide is directly verified. Temporary diagnostic instrumentation
was removed. A first broad all16 historical physical-suite run timed out at900s and is
not passing evidence; the four affected suites above completed through the same guarded
runner. Other historical physical suites are outside the affected persistence delta.
Full backend ordinary execution intentionally skips separately guarded physical and
explicit external smoke/production safety lanes; external smoke is not claimed.

Build retains the existing >500kB chunk warning; frontend tests retain existing SSR/act
warnings; backend TestClient deprecation and intentional malformed-DTO serializer
warnings are not test failures. No new dependency or lockfile change was introduced.

## Change classes and disclosure

API/types: changed (optional ownership input/nullable receipt, two additive target
projection fields, narrow completed verification request/response/endpoint).
Durable schema: compatible optional field in existing schema9; no schema version,
index/migration/repository/CAS semantics change. Connector: existing XPI Search is
called through a new read-only service action; endpoint family/auth/TLS/decoder/mappings
are unchanged. Configuration: Garden composition activation changed; legacy setting
is compatibility-only with its prior outside-lane validation. Business rule: only
owner-authorized automatic matching/fixture/optional-note and completed UX changes;
>=25% and downstream approval boundaries unchanged. Mapping: unchanged. Auth/security:
new case-scoped route uses existing backend access/session/lock ownership and safe
errors; no role/capability or authorization-owner change. Architecture: existing owner
extensions; no new service/provider/repository/calculator/dependency. Provider status:
unchanged Mock/Local/Partial/Dormant/Live classifications. Runtime: changed as described.
CI/tooling: offline Garden Sandbox mode/scanned fixture/discovery budget/Tesseract install.

## Freeze, risk and next authorized action

The reviewed-content manifest records every task-owned implementation/test/config/docs/
planner/evidence path with LF-normalized text SHA256 and exact binary SHA256. Manifest
and independent gate report are derivative identity/output artifacts outside their own
recursive hash; the final index must equal the reviewed payload and reviewed report.
No private or owner environment read, clm_poc access, confidential artifact, raw provider
payload log or external call was needed. Physical work used only newly generated
allowlisted disposable DBs in task container clm-postuat-mongo-20261005-01.

R0 independent review is FAIL with P0/P1/P2=0/0/1, solely QG-01 generated-guide drift.
Its exact report and manifest are preserved as QUALITY_GATE_R0.md and
REVIEWED_CONTENT_R0.json siblings. Independent R0 execution additionally passed263
focused backend tests,54 frontend tests, actual scanned Garden browser1, and three
current-composition/adverse guard assertions. No other finding was raised.

Dependent blocker at this R1 snapshot: fresh independent exact PASS with
P0/P1/P2=0/0/0. One of at most two remediation rounds has been used. Only then stage exact reviewed
paths/report, create the authorized local commit, prove index/worktree clean and stop
for owner review. Retain the branch/worktree; no publication gate, push, PR or merge.
