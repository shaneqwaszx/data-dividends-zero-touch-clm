# Onboarding intelligence Session 2 independent quality gate

Date: 2026-10-04. Initial review, remediation rounds used: 0 of the owner's maximum 2.
Reviewer: independently assigned GPT-6.1 Sol / xhigh gate agent. The reviewer implemented
none of the Session 2 candidate and made no implementation or remediation changes.

## 1. Executive Result

**FAIL.** One reproduced **P2** violates original ownership observation preservation:
duplicate normalized ownership columns in a supported pipe table overwrite an earlier
explicit value before the remaining proposal is marked ambiguous. Review remains
blocking, but the discarded original cannot be inspected or retained in later receipts.
This is a current Session 2 contract defect, not accepted technical debt.

P0: 0. P1: 0. P2: 1. P3: 0. No other concrete defect was found in the cumulative review.
Session 3 is **not ready to start** until bounded remediation receives fresh exact
independent PASS. Passing execution lanes below do not override the preservation defect.

### Frozen content and evidence identities

- Worktree: C:\Users\shane\.codex-clean2\worktrees\onboarding-intelligence-goldtier-sandbox\data-dividends-zero-touch-clm.
- Branch: feat/onboarding-intelligence-goldtier-sandbox.
- BASE_SHA, HEAD and locally recorded origin/main:
  1d426e0ceddc32d80b0aaec293c62fb761f2fecf.
- Reviewed cumulative scope: 111 tracked changed paths plus 33 task-owned new paths,
  **144 paths**. This is uncommitted Session 1 + Session 2 content; HEAD alone does
  not identify it.
- Exact path list and per-file raw-byte hashes:
  [.ai-pipeline/reports/ONBOARDING_INTELLIGENCE_S2_MANIFEST.json](ONBOARDING_INTELLIGENCE_S2_MANIFEST.json).
- Manifest raw SHA256:
  4926880658ea26447c433b8594fc5d3807aa11bac4daf71e2e9d531031f6a23d.
- Reviewed/tested candidate SHA256:
  0a002f10fc37244cd009854aab8b6e007d2de3d4112a98dca4d48304c0008d20.
- Aggregate algorithm: SHA256 of UTF-8 json.dumps(files, sort_keys=True,
  separators=(',', ':')); records sorted by case-sensitive relative POSIX path,
  containing path and raw-byte SHA256.
- Manifest itself and this assigned gate report are excluded. At entry and final
  checks, the manifest path set exactly matched tracked changes plus nonignored
  task-owned new files after those exclusions, every file hash matched, and the
  index was empty. Product/test/doc bytes remained frozen throughout this review.
- The historical Session 1 exact PASS belongs to its recorded 60-path candidate.
  It does not certify the current 144-path bytes. Current cumulative behavior and
  changed source/tests were independently reviewed here.

## 2. Phase Acceptance Checklist

The explicit owner's Session 2.1–2.13 request, Session 2 mini-gate, global safety
instructions and current planner control scope. Session 3 transport work is later.

| Requirement | Result | Direct current evidence |
| --- | --- | --- |
| S2.1 Native-first and actual local OCR | PASS | Existing local IDP owns native PDF/DOCX/TXT and local Tesseract scanned/mixed PDF/PNG/JPEG/TIFF. Independent current-source hardened container: 31/31, no skips. Native behavior and explicit OCR_RUNTIME_UNAVAILABLE passed on Windows without host Tesseract. No vendor OCR composition or runtime installation. |
| S2.2 Bounded safe processing and provenance | PASS | Actual malformed/signature, page/frame, dimension/pixel, encrypted/action/remote-resource, output, subprocess deadline, temp cleanup and safe-error tests passed. Backend-built argument arrays, generated paths and page-local metadata reviewed. Local process containment is described accurately below. |
| S2.3 Extraction quality, score, agreement and verification | PASS | 211 focused backend and 477 frontend tests passed. Native/OCR quality, raw TSV confidence, deterministic score/formula, source MATCH/MISMATCH and human verification remain separate. Ambiguous identity candidates retain no picked value and require replacement; UI never labels the score a probability. |
| S2.4 Supported field extraction and immutable originals | FAIL — P2-01 | Four existing identity fields and bounded ownership proposals carry server IDs/version/pages/method/quality/decision provenance, and forged typed DTOs fail revalidation. However duplicate table columns lose an explicit original scalar, reproduced through the current local IDP. |
| S2.5 Proposed ownership, no automatic ambiguous graph choice | PASS with P2-01 overlap | Source types, identifiers, explicit counts/percentages/classes/parent/date remain PROPOSED. Unknown quantities/types stay unknown. The reproduced duplicate-column output is AMBIGUOUS/PROPOSED and does not autonomously supply a canonical edge; its incomplete original set is the S2.4/S2.6 failure. |
| S2.6 Source comparison and creator-only deliberate decision | FAIL — P2-01 | Current and prior graphs, source selections, selected IDs, actor/time/rationale and exact current document event bindings otherwise passed. MATCH proposals also require a decision, DOCUMENT selection must cover every edge, foreign/unknown creator is denied inside the lock/CAS. The original table value 250 is absent after the duplicate-column extraction. |
| S2.7 Calculable evidence editable before target; freeze afterward | PASS | Independent API/domain/browser checks edit current calculable evidence, retain prior graph/receipt, invalidate readiness/confirmation and resume without target mutation. Retained target attempt/submission freezes editing. Exact obsolete confirmation bindings retire while independent target guards remain active. |
| S2.8 One existing Decimal ownership engine | PASS | Independent 172-case accepted engine/policy/S1 pack plus Garden/manual S2 checks passed. Inclusive >=25%, direct/indirect aggregation, multilevel paths, cycles/incomplete evidence and explicit denominator behavior remain owned by the existing engine. Parser performs no percentage inference; browser uses retained server calculations. |
| S2.9 Governed optional policy parameters | PASS | No new industry-practice business default was introduced. Existing HR proposal, independent Director decision, audit/version and frozen case policy were retained and independently tested. Existing 25/0.85 project values retain their current authority/classification; safety bounds are separate. |
| S2.10 Explicit known Garden composite | PASS | Default-false opt-in, successful compatible fresh official Marketplace Mock/cache prerequisite, unchanged official identity/officers and distinct LOCAL_SYNTHETIC_SUPPLEMENT reviewed. Independent known-case, disabled/nonofficial/expired/failed/tampered and nonempty-official discrepancy/no-double-count tests passed. No provider-error fallback or generalized equal-share rule. |
| S2.11 Ownership details and calculation tree | PASS | Original/current/prior sources, parties/type/country, direct/effective values, exact paths/calculations, candidates and unresolved evidence are shown from retained server data. Existing bounded path pagination is preserved; no legal UBO determination claim. |
| S2.12 Collapsed keyboard/responsive presentation | PASS | Independent guarded real HTTP Chromium S2 journeys: 2/2. Native collapsed summary/Enter and 320/720/1280 layout checks passed, plus current full frontend suite. Source details and long tables remain within bounded scrolling. Existing print CSS repair and test assertions were reviewed. |
| S2.13 Known fixture source and provenance | PASS | Current garden_business.py has no cumulative source diff. Exact local 5000/3000 root units over explicit 8000, SIM LIM 900/100/100 over 1100 and the withdrawn contradictory 10000 denominator remain distinguished in current source/profile. Independent resulting 51.13636375% and 37.500000% assertions passed through the sole engine. |
| S2 mini-gate and hard safety | FAIL solely for P2-01 | Required native/scanned/mixed/poor/ambiguous/conflicting/quantity/multilevel/manual/policy/tree lanes obtained current evidence; auth, legacy schema, physical Mongo, call stopping and false-success checks passed. One current original-evidence defect remains. No external provider call, private .env access, production database, Git mutation or Session 3 work occurred. |

## 3. Contract and Integration Findings

### P2-01 — Preserve every explicit value in duplicate ownership table columns

Location:
[document_ownership_parser.py:129](../../apps/backend/app/connectors/document_ownership_parser.py#L129),
lines 129–134; the affected mapping is immediately followed by the ambiguous-row flag.

Authority: owner's S2.4/S2.6 original-observation requirements and current
[OWNERSHIP_UBO_PROFILE.md:134](../../docs/contracts/OWNERSHIP_UBO_PROFILE.md#L134)–146,
which retain original proposed values and immutable source bindings. Raw upload/full
text remains transient, so preserving only a warning does not preserve the discarded
structured observation.

Independently executed synthetic counterexample through LocalPdfTextIdpProvider:

~~~text
Shareholder | Type | Shares | Shares
SYNTHETIC OWNER | NATURAL_PERSON | 250 | 300
~~~

The current dictionary comprehension keys both columns as share_count; the second
cell overwrites the first. The current provider returns:

~~~json
{"retained_count":1,"shares":["300"],"quality":["AMBIGUOUS"],"states":["PROPOSED"],"source_refs":["PAGE_1_OWNERSHIP_ROW_2"]}
~~~

The supported alias header Shares | Share count produces the same loss. The existing
labelled duplicate-scalar regression at
[test_s2_local_ocr.py:234](../../apps/backend/tests/test_s2_local_ocr.py#L234)
retains both 250 and 300, but does not exercise duplicate table headers. Parent
implementer independently reproduced the exact table defect while retaining the freeze.

Impact is bounded evidence loss, not demonstrated false target success or automatic
canonical selection. Nevertheless a creator cannot inspect/select the discarded
original, and no subsequent persistence/history can recover it from this result.
A FAIL is required because original retention is an explicit current contract.

Correction: preserve each distinct conflicting table-column value with the remaining
explicit row facts and page/source provenance, marked AMBIGUOUS/PROPOSED; do not choose
a winner, fabricate percentages/denominators or infer arithmetic. Enforce the existing
128-observation/output bounds before retention. An explicit safe rejection before
retaining a picked partial row is also acceptable if the supported input cannot be
represented without loss. Add duplicate exact-header and normalized-alias regressions
plus original server-ID/version/binding retention and overflow checks. Then rerun the
failed focus and affected OCR/document/persistence lanes and obtain fresh independent
review of a newly frozen manifest. The reviewer made no fix.

### Authority and later dependencies

Untrusted source DTO -> canonical evidence -> target mapping remains intact. No direct
ACRA-to-GoldTier mapping, related-party dispatch, child-ID lifecycle, sponsor enum,
Ready-for-Approval or Live behavior was added by Session 2. Current D-062/D-066/D-067
and ADR-009 consistently label provisional numeric candidates, source decisions and
schema9 behavior. Contradictory sponsor examples remain outside fixtures/contracts.

Production/legal/control/source-precedence, calibrated accuracy, retention and
maker-checker questions remain Q-003/Q-004/Q-005/Q-012/Q-013/Q-014/Q-015/Q-016 as
applicable. These later authority dependencies do not explain or excuse P2-01.

## 4. Tester and Adversarial Findings

All independent commands ran against the frozen current candidate from its worktree.
Python used the task .venv Python 3.12 with -B / no bytecode; pytest cache was disabled.
No full 15-minute backend repeat was necessary once exact current implementation
receipts, focused execution and raw content identities agreed.

| Independent execution | Observed result |
| --- | --- |
| pytest test_s2_ownership_intelligence.py test_s2_persistence_security.py test_s2_local_ocr.py -q -p no:cacheprovider -o addopts= --tb=short | 211 passed, 6 skipped, 1 FastAPI/Starlette httpx deprecation warning; 44.18s. Six skips require real Tesseract absent on this Windows host and were independently covered below. |
| Actual OCR: docker run --rm with --network none, read-only current apps/backend mount, PYTHONPATH=/workspace/apps/backend, CLM_REAL_OCR_REQUIRED=1, task image clm-s2-ocr:20261004; python -B -m pytest apps/backend/tests/test_s2_local_ocr.py -q -p no:cacheprovider -o addopts= --tb=short | 31 passed, 0 skipped, 1 same deprecation warning; 14.78s. Image ID independently inspected: sha256:39fe52fc0d8c58bf1b5cbafe6a9b99decb1600ac20ece259293c5dfd99e0caec. Nonroot, read-only root, dropped caps, no-new-privileges, bounded tmpfs/PIDs/memory/CPU. |
| Accepted calculator/policy and cumulative S1: pytest test_ownership_analysis.py test_phase24_ownership_evidence.py test_phase24c_policy.py test_s1_date_filters.py test_s1_pipeline_projection.py with the same no-cache options | 172 passed, 1 same deprecation warning; 6.44s. No skip. |
| Guarded scripts.run_physical_mongo_tests.run(timeout_seconds=300), selected existing test_s2_intelligence_real_mongo.py suite in memory | 18 collected, 18 passed, 0 errors/failures/skips, 1 suite; 8.197s. Internally constructed localhost URI was never printed/persisted. Fresh allowlisted disposable databases only; cleanup asserted absent. Existing production runner unchanged by reviewer. |
| Guarded scripts.run_e2e.run(backend_port=18765, frontend_port=14173, timeout_seconds=60, grep='S2 ', garden_protocol=True) | 2 actual current-source HTTP Chromium journeys passed; 7.9s. Existing timeout, guards, services and assertions retained. Browser outputs redirected only to an owned OS temporary directory; finally stopped owned processes. |
| Full Vitest run, cache disabled | 477 passed across 40 files; 7.72s. Existing React act/server-layout warnings remain, with no failing test. |
| TypeScript --noEmit --incremental false, tsconfig.app.json and tsconfig.node.json | Both passed, exit 0. |
| Backend Ruff check app tests --no-cache; mypy app --no-incremental --cache-dir=nul | Both passed; strict mypy 124 files. |
| Contract unittest discovery, tests/contract | 44 passed; 1.412s. |
| Governance unit modules: check_architecture, check_project_state, check_policy_authority, check_secrets, check_tooling_config, check_external_provider_readiness, run_physical_mongo_tests | 108 passed; 25.415s. |
| Six corresponding architecture/state/policy/secrets/tooling/external-readiness scanners | All passed. |
| Read-only synthetic parser/provider duplicate exact-header and alias-header probes | Both reproduce P2-01: only 300 retained, original 250 lost; remaining observation AMBIGUOUS/PROPOSED. |
| Raw manifest, complete path set, branch/HEAD/index and whitespace checks | All 144 raw hashes and aggregate matched at entry and final checks; 0 whitespace issues across all 144 text files; git diff --check passed; no staged paths. |

The first OCR invocation omitted PYTHONPATH despite mounting current source. Tracebacks
showed imports from the image's older site-packages application: 28 passed / 3 failed.
That invocation error is retained here and is not attributed to the current candidate.
The corrected read-only current-source command above passed all 31 without skips.

Adversarial evidence covers constructed/copied DTO bypasses; malformed media/signatures;
encrypted/unsafe PDF actions and remote-resource references; native/OCR deadlines/output;
poor OCR; ambiguous multiple candidates with no selected value; missing denominator/type;
MATCH still requiring source choice; mismatched source and incomplete selected-edge
coverage; changed/current/prior document versions; immutable creator; same-team noncreator
403 and cross-team/absent indistinguishable 404; session/team/creator changes inside lock;
strict schema1..8 reads and explicit later-field rejection; physical two-adapter CAS,
restart preservation, corrupt originals and no resurrection after deletion; retained
target freeze, no new target mutation and independent target-guard preservation.

### Attributed current implementation evidence, not newly executed by this reviewer

[Implementation receipt](ONBOARDING_INTELLIGENCE_S2_IMPLEMENTATION.md) records final full
backend 2252 passed / 114 skipped / 4 warnings in 986.55s; skipped lanes were 108 physical
and 6 actual OCR cases covered separately. Its full physical pack was 108/108 across
15 suites, actual OCR 31/31, frontend 477/typecheck/build, mypy124/Ruff, contracts44,
affected tooling69 and non-Windows root273. Both unchanged 100-run stability tests passed.
The reviewer independently exercised focused real drivers/runtime rather than converting
these attributed broad results into independently executed results.

Its final full browser run passed 56 configured isolated selectors / 63 actual test
executions, exit 0, no skips, 565.656s, under original 60-second case bounds; slowest
26.266s. Changed E2E fixture, enum, copy and nesting assertions were inspected for
weakening. Explicit source decisions replace removed invented defaults; ambiguous
legal-name suggestions require correction/replacement; no-call, no-replay, stale-response,
authority, print/A4 and actual-enum checks remain.

Windows discovery was 31. The complete run was 29 passed / 2 unchanged five-second
health deadline failures, not PASS. Both failures passed an exclusive unchanged
two-case recheck (103.020s) after browser work stopped; the evidence is 29 full-run
passes plus 2 focused passes, not a freshly passing complete 31-case run. Earlier
mixed/backend/browser/physical failures in the implementation receipt remain failures;
they are not rewritten as passing runs.

[Actual OCR browser receipt](ONBOARDING_INTELLIGENCE_S2_OCR_BROWSER_RECEIPT.md) supplies
one authenticated genuine local OCR Chromium journey / 50 counted assertions, zero
skips, 10.218s complete lifecycle, normal current provider/services/UI with no API
substitution/external request or target mutation. This is attributed specialist evidence,
not this reviewer's second execution. The reviewer independently recomputed its exact
217-file current application source fingerprint:
f08d4fd94b393ebc0c5e0bcb97e3c634d803e4af147bee81dafe3ba51fab4c67.
Its WindowsPath sorting plus path/NUL/binary-file-digest algorithm is distinct from
the 144-path candidate JSON algorithm.

## 5. Code and Architecture Review

Cumulative tracked diff and task-owned new source/tests/docs/planner/receipts were
inspected. Existing document, ownership, authorization, orchestration, persistence,
query-client and target-ledger owners remain canonical. New bounded parsing/media
helpers extend the local provider; they do not decide ownership arithmetic or precedence.
Document comparison helpers retain proposed evidence and feed the existing analysis.

Schema9 adds extraction/creator/source metadata within the same envelope. Explicit old
schema guards preserve unknown legacy metadata/creator without read-time rewrite.
Existing insert-only create, update-only mutation, identity/revision CAS and immutable
creator checks are retained. New document-bound analysis replacement compares exact
source inputs, archives prior analyses and fails stale/foreign originals.

Frontend authority booleans are presentation only. Server authorization and fresh
bindings remain decisive. Case/actor/analysis revisions reset drafts; server queries
remain authenticated/session scoped and use cancellation/invalidation. Existing stale
response and logout/session isolation tests remain meaningful.

Changed classes: API/type, durable schema, local connector/runtime configuration,
bounded evidence/source-decision behavior, auth/security and architecture documentation.
Provider classification stays Local/Mock; no external transport or target mapping was
changed. Existing Decimal threshold semantics and governed policy authority are retained.
No second calculator, repository, auth owner, orchestration framework or target bypass
was introduced. P2-01 is required remediation, not maintainability debt.

## 6. Security Review

No additional security finding was reproduced. Media requests cannot select executable,
shell options, file paths or URLs. Native PDF/image decoding runs in a backend-controlled
child under deadlines; generated temporary paths retire on success/error. PDF scripting,
actions, embedded/remote resources, encrypted media, MIME/signature spoofing and processing
bounds fail closed. Safe fixed errors suppress engine stderr, document content and
arbitrary private provider error codes.

The inspected subprocess boundary uses shell=False, stdin/stderr DEVNULL, bounded
stdout and kill/wait on timeout. It inherits the backend process environment; no minimal
environment allowlist or production OS network sandbox is claimed. Current controlled
Python-worker/Tesseract code has no external fetch operation. Hardened offline Docker
is actual acceptance-test containment, not evidence that a Windows/native deployment
has that same OS sandbox. Production parser hardening and confidential document
retention/access policy remain later deployment authority rather than newly invented
Session 2 guarantees.

Server-created immutable creator plus existing access/team/capability are reauthorized
inside lock/CAS. Accessible noncreators cannot decide source evidence; inaccessible
cases reveal the same safe 404 as absent cases. Legacy creator is unknown and never
guessed. Review never read private .env, confidential artifacts, provider credentials,
or original clm_poc and never printed/persisted a Mongo URI or document/provider secret.

Task-owned OCR container clm-s2-gate-ocr-20261004 was absent after --rm completion.
Both assigned browser ports 18765/14173 were independently bindable at final checks.
Physical runner proved generated database cleanup. Parent-owned Mongo container/image
and unrelated listeners were preserved; no broad enumeration or cleanup occurred.

## 7. Required Fixes

1. Correct P2-01 at document_ownership_parser.py:129–134, preserving or safely rejecting
   duplicate normalized table-column originals without retaining a picked partial row.
2. Add focused exact/alias duplicate-table preservation, immutable binding and existing
   output-cap regressions; run affected evidence against repaired bytes.
3. Freeze a new complete candidate/manifest and assign fresh independent remediation
   review. Keep this initial FAIL and its exact candidate identity in the gate history.

No additional implementation, policy, dependency, transport or production hardening
change is required by this finding.

## 8. Readiness

**Session 2 acceptance: FAIL. Session 3 readiness: NOT READY pending P2-01 and fresh
exact independent PASS.** Remediation round 1 is the next bounded action under the
owner's existing program authorization; no new owner checkpoint is required.

Live ACRA verification and current-program external GoldTier/PingFed Sandbox delivery
remain unexecuted by this gate. Local/Mock and genuine local OCR success establish
their recorded scope only. Prior Garden Amend external failure remains failed and is
not fresh interoperability evidence. No target mapper or external GoldTier change was
reviewed as part of Session 2. Later authorized Session 3 must satisfy its current
contract, safety and external evidence criteria after Session 2 exact PASS.

## 9. Git Status

The branch/base/HEAD/local origin-main identities above remained unchanged. The frozen
candidate contained 111 tracked modifications and 33 task-owned new paths; its manifest
is an additional excluded untracked file. Staged paths: 0. The gate adds only the
assigned excluded ONBOARDING_INTELLIGENCE_S2_QUALITY_GATE.md.

All 144 candidate hashes/path identities remained unchanged before and after review
and report publication. Report-only modification: this exact file. No implementation,
test, configuration, ordinary documentation, dependency or manifest fix; no commit,
push, PR, merge, fetch or subsequent phase was performed. The reviewed candidate is
intentionally uncommitted, so no clean-committed pre-PR publication gate was substituted
for this independent implementation review.
