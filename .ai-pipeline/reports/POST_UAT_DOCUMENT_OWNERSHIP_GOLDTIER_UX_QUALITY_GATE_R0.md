# Post-UAT document, ownership and GoldTier UX independent quality gate

Date: 2026-10-05. Initial independent review (R0), using fyp-quality-gate.
The reviewer made no implementation, test, configuration or ordinary documentation
changes. The sole authored artifact is this assigned report.

## Executive result

**FAIL — P0/P1/P2 = 0/0/1.** The generated blocker rectification guide still tells
users to provide mandatory ownership rationale. Its synchronization regression fails
against the changed authoritative catalogue. This is a reproducible current P2
documentation/verification defect, not missing infrastructure or sponsor authority.
The user requires a passing full backend suite and zero P2 findings before a local
commit; those conditions are not met.

The reviewed product paths otherwise satisfy the bounded acceptance evidence below.
No local commit, publication, merge or next phase is authorized by this verdict.
Return to the implementation writer for the one required repair and fresh independent
recheck, within the owner's maximum of two remediation rounds.

## Exact reviewed identity

- Branch: `fix/post-uat-document-ownership-goldtier-ux`.
- Worktree: `C:/Users/shane/.codex-clean2/worktrees/post-uat-document-ownership-goldtier-ux/data-dividends-zero-touch-clm`.
- BASE_SHA, source HEAD and observed origin/main:
  `ae27654a075f13354364e86ec8fe5a81d24777d4`.
- Reviewed payload: all 52 paths in
  `POST_UAT_DOCUMENT_OWNERSHIP_GOLDTIER_UX_REVIEWED_CONTENT.json`.
- Payload SHA256:
  `599247e42b05f7b690867cc94613c4ebeab42633d2619cf8e3eda0311e5eebd7`.

The reviewer independently recomputed every per-path hash and the aggregate.
Text hashes replace CRLF with LF; the PNG uses exact bytes. The aggregate is SHA256
of the UTF-8 concatenation of sorted `path + NUL + sha256 + newline` rows.
Git's complete changed/new path set equals those 52 payload paths plus the derivative
manifest. The assigned gate report is the sole additional permitted path. The index
is empty; HEAD identifies the baseline, not the reviewed uncommitted content.
Hashes were checked before review and again at the report boundary.

Authority/read set: complete owner assignment and acceptance1-31, AGENTS, emitted
change classes and workflow, current task planner/evidence snapshot, quality-gate
skill/template and reviewer/security roles, relevant cache/security/persistence/provider
skills/checklist, current architecture/state and decisions/questions, IDP/ownership/
GoldTier/persistence contracts, prior POST_CLOSEOUT_EXISTING_CUSTOMER_QUALITY_GATE,
regression catalogue, complete changed/new content, and existing owning services,
authorization, XPI decoder, query/auth lifecycle and affected tests.
No private sponsor material or owner environment file was needed.

## Owner acceptance checklist

Results below are bounded offline implementation findings. They do not override the
overall FAIL from the required documentation/full-suite defect.

| Test | Requirement | Result and direct evidence |
|---|---|---|
| 1 | Exact MATCH above frozen threshold auto-confirms | PASS: independently executed test_auto_confirm_uses_frozen_inclusive_threshold at0.97; existing owner compares original/current canonical values. |
| 2 | Inclusive threshold boundary | PASS: same test at0.85 accepts;0.849999 stays pending. Frozen case policy supplies threshold. |
| 3 | High-score MISMATCH remains review | PASS: unsafe matching-field regression changes original value; retained PENDING/no REVIEWED. |
| 4 | Low-score MATCH remains review | PASS: threshold regression; existing document regressions preserve low-confidence blockers. |
| 5 | Ambiguous extraction remains review | PASS: explicit AMBIGUOUS guard and independently executed adversarial regression. |
| 6 | Current contradiction prevents unsafe confirmation | PASS: second contradictory document regression; current lineage/effective value checks inspected. |
| 7 | Auto-confirm at unresolved GOLDTIER_SEARCH | PASS: independently executed attach/intake variants and real scanned Garden browser. |
| 8 | Search remains authoritative blocker | PASS: attach/intake assert same checkpoint, WAITING_FOR_REVIEW/GOLDTIER_SEARCH and blocked CLM readiness. |
| 9 | No target mutations during independent auto-confirm | PASS: attach/intake call recording remains Search-only; browser counts SEARCH1/SHELL0/POLICY0/AMEND0/READBACK0. |
| 10 | All eligible fields can become automatically reviewed | PASS: REVIEWED/AUTO_CONFIRMED and all ACCEPTED assertions; no manual field clicks in actual OCR browser. |
| 11 | Omitted/null/blank ownership note accepted | PASS: independently executed declaration/request/receipt variants; UI empty note submits null with structured evidence. |
| 12 | Supplied safe note retained | PASS: model/request/provider/receipt equality and UI multi-level edit tests. |
| 13 | Unsafe supplied note rejected | PASS: prompt marker, C0 and script marker regressions; existing safe text and length validation retained. |
| 14 | Historical string rationale remains readable | PASS: historical receipt regression and coordinator physical restart/raw-record equality evidence; no read-time write. |
| 15 | Exact official Mock Garden automatically composes fixture | PASS: normal composition with both legacy-toggle values and actual official decoder-shaped four-officer evidence; offline Garden browser. |
| 16 | LOCAL_SYNTHETIC_SUPPLEMENT/LOCAL provenance | PASS: relationship provenance assertions; original official evidence retained separately. |
| 17 | Provider failure cannot activate fixture | PASS: existing failure/expiry/nonofficial regressions inspected and executed; independent failed-operation eligibility assertion also passed. |
| 18 | Other UEN cannot receive Garden fixture | PASS: independent current-composition guard assertions reject non-Garden requested UEN; exact requested/acquired UEN eligibility checks inspected; normal second-company regression retains its own graph. |
| 19 | Official quantity conflict/no double counting | PASS: existing nonempty70% official-edge regression retains one official edge and separate five local edges with CONTRADICTORY_OWNERSHIP_EVIDENCE/review; existing owner inspected. |
| 20 | Decimal results/withdrawn exclusion retained | PASS: independent tests and browser retain ABCD12351.13636375%, Lim37.500000%; fixture withdrawn holder excluded and one unchanged Decimal engine. |
| 21 | No manual declaration solely for absent official percentages | PASS: automatic graph ANALYZED/manual receipt null in normal composition, official decoder and browser. Additional other-role/control/conflict evidence still requires review. |
| 22 | Completed ID first | PASS: focused frontend ID-first order and independent browser firstdt=GoldTier ID/firstdd=143878. |
| 23 | Existing customer handling truthful | PASS: backend derives EXISTING_REUSED from retained shell status; frontend and scanned Garden browser show existing customer reused. |
| 24 | New customer handling truthful | PASS: backend derives NEW_CREATED from completed SHELL marker; independent rendering and completed-new endpoint tests. |
| 25 | Same entity distinct local case/reusedID/no Shell | PASS: independently executed XPI two-case regression, distinct case/source IDs, retained143878, five GETs only; CONFIRMED_EXISTING distinct from EXACT_MATCH. |
| 26 | Different definitive NO_MATCH creates Shell/new ID | PASS: independently executed second-entity regression, one Shell for202400008H, retained999123. |
| 27 | Completed verify performs one exact-ID Search | PASS: six independently executed endpoint variants assert one GET and exact goldTierID query; independent Garden browser adds one readback Search. |
| 28 | Verify never mutates/replays | PASS: connector call assertions and equality of case/CLM/timeline/version/submission/operations; service returns ephemeral evidence and performs no repository/ledger write. |
| 29 | Adverse verification preserves confirmed result | PASS: no-match/different-ID/multiple/malformed/timeout variants return review/unavailable and retain all confirmed state; UI does not relabel delivery uncertain. |
| 30 | Unauthorized actor cannot verify | PASS: inaccessible-team and HR actors404 before provider call; session/access reauthorization inside shared case lock inspected; route explicitly CASE_SCOPED. |
| 31 | Invalid request sanitized/non-echoing | PASS: invalid UUID/missing expectedID/extra arbitrary clientID422 constant safe body; stale/uncompleted409; no added Search. |

Additional assigned real-UAT path: **PASS** independently via
`scripts/run_e2e.py --sandbox-demo garden-existing-customer --grep 'post-UAT Garden scanned' --timeout-seconds180`.
Actual local Tesseract processed the retained synthetic scan. All four identity fields
were MATCH, ACCEPTED, LOCAL_TESSERACT_OCR and score>=0.85 without acceptance clicks.
Official-Mock Garden fixture composition calculated ownership automatically, the creator
confirmed retained candidate143878, explicit final send reused it without Shell/Policy/
Amend, completed details began with ID, and Verify in GoldTier produced verified safe
identity through one additional exact-ID Search. Guarded transport reported external
calls0; loopback process cleanup completed.

## QG-01 — P2: generated ownership action guide contradicts optional note

Affected file: `docs/demo/BLOCKER_RECTIFICATION_GUIDE.md:364` and `:970`.
The source catalogue in `apps/backend/app/services/blocker_decision_policy.py:1087`
now correctly says reviewer note is optional. The generated guide still says
"Provide rationale and current case/document/evidence versions".
This contradicts the owner-requested optional-note UX and the current catalogue.

Independent reproduction:
`python -m pytest apps/backend/tests/test_slice_c_blocker_catalogue.py -k rectification_guide -o addopts='' -p no:cacheprovider -q --tb=short`
returned **1 failed,15 deselected**, at assertion line175 comparing the tracked guide
to `scripts.generate_blocker_rectification_guide.render_guide()`.
The two stale rationale rows are the observed mismatch. The coordinator's exhaustive
backend execution independently surfaced this same sole failure.

Required repair: regenerate only this affected guide through its existing generator;
include the guide in the new frozen path set. Recheck generator --check, the affected
catalogue suite, documentation/governance/secret hygiene and new exact content identity.
Do not change product behavior, tests or acceptance to bypass this failure.
Fresh independent recheck is required after remediation.

## Testing and adversarial evidence

Independent execution on this frozen content:

| Command/surface | Actual result |
|---|---|
| pytest test_post_uat_remediation.py + test_s3_submission_status.py + test_goldtier_xpi_sandbox.py; addopts cleared/cache disabled |163 PASS,20.66s; one existing TestClient deprecation warning. |
| Focused frontend S3SubmissionStatus/ManualOwnershipEvidenceForm/DocumentEvidencePanel |3 files/54 PASS,2.22s. The additional CaseDetail filename in selector has no matching test file; it supplied no fourth-file execution claim. |
| Guarded scanned Garden browser with actual Tesseract |1 PASS,6.2s; runner exit0 and owned cleanup complete. |
| Independent ephemeral exact-UEN/failed-operation guards |3 assertions PASS; no provider transport; no implementation or test file written. |
| pytest S2 ownership intelligence + phase13 auth/RBAC + Slice B registry |100 PASS,32.72s; one existing TestClient deprecation warning. |
| Generated guide synchronization regression |1 FAIL/15 deselected,0.14s; QG-01. |
| check_secrets/check_architecture/check_project_state |All PASS. Scanner proves only its supported patterns, not universal secret detection. |
| git diff --check + explicit UTF-8 new/changed Markdown trailing whitespace |PASS. |
| Manifest per-file/aggregate and full Git path-set verification |52 hashes match; aggregate matches; empty index. |

Coordinator execution on the same frozen runtime content (separate from reviewer reruns):

- Exhaustive ordinary backend collection2489:
  all-except-orchestration2284 PASS/1 FAIL/116 SKIP in670.72s;
  orchestration88 PASS in308.30s, including both100-run deterministic ordering checks.
  Combined **2372 PASS/1 FAIL/116 SKIP**; current full backend is not passing.
- Real Tesseract six-format acceptance6 PASS/0 SKIP (PNG/JPEG/TIFF/scanned PDF/mixed
  PDF/poor PNG).
- Relevant guarded physical Mongo: phase13/phase24c/S2 intelligence/S3 submission,
  four suites/37 collected/37 PASS/0 error/failure/skip; optional/historical receipt
  restart equals original and raw collection record remains unchanged.
- Full frontend42 files/517 PASS; guarded affected browser15 distinct paths PASS.
- Ruff PASS; configured strict backend mypy124 files PASS; TypeScript/build PASS.
- Contract tests44 PASS; full repository/tooling/Windows lifecycle350 PASS.
- Browser discovery61 selectors/five isolated Sandbox fixture modes; actual CI Tesseract
  provisioning and outer budget changed without increasing each lifecycle execution limit.
- Governance/security checkers PASS before the guide synchronization failure surfaced.

The earlier16-suite historical physical run timed out900s and is **not** passing
evidence. It does not replace the four affected successful guarded suites. Ordinary
backend prerequisite skips cover separately guarded physical/external lanes; they are
not passing external interoperability evidence. No external smoke test was run.
No PR/remote CI readiness is claimed; pre_pr_check.py is appropriately not used for
this intentionally uncommitted local implementation gate.

## Contract, architecture and security review

No active P0/P1 or further P2 defect was identified in the reviewed product paths.
Auto-confirm stays in DocumentProcessingService with explicit ambiguity/currentness/
MATCH/frozen-threshold/conflict checks. Orchestration invokes it without granting
unrelated Search progression or target mutation. Retained events supply machine versus
human evidence labels; extraction score remains evidence, not probability.

Optional notes use the existing bounded audit model and schema9 codec; structured
actor/time/as-of/document/observations/source/graph/replaced-version bindings remain.
No migration, CAS weakening, source-owner duplication or read-time repair is introduced.
New notes are safe-text validated and absent notes are null, never fabricated prose.

Garden composition changes only the bounded official Marketplace Mock route. Exact
identity, provenance, freshness and failed-operation eligibility remain. The contextual
OFFICERS exception is constrained to the exact validated original supplemental graph;
other role/control/conflict and official quantitative discrepancies remain blockers.
Decimal path calculation, withdrawn exclusion and inclusive25% rule remain unchanged.
No legal/control UBO or official-percentage claim is added.

A successful creator graph edit invalidates earlier local review even after an intervening
classification version; existing ownership/readiness owners recompute before new explicit
send. The new regression covers repeated edits and multilevel recalculation/finalization.
The target ledger remains the sole ordering/no-replay owner.

Completed verification uses the finalized successful same-case Sandbox ledger, checks
current identity and retainedID, and calls the existing bounded XPI exact-ID decoder.
Request fields cannot choose a targetID; current session/team/case access is checked
under the existing lock. Errors are constant and non-echoing. No new provider family,
transport/TLS/auth assumption, mutation retry, raw payload retention or ledger write
appears. An adverse observation cannot invalidate already confirmed delivery.

Frontend observations are user/case/submission scoped, separated from uncertain checks,
manual-triggered for completion, cancellable and generation guarded. Session replacement/
logout/401 clears incompatible cache through existing owners; navigation aborts/discards
late completed verification. Backend capability/access remains authoritative.

The only new binary is synthetic offline scan evidence reproducible by the task-owned
renderer; no confidential sponsor artifact, credential, private document or dependency/
lockfile churn was introduced. Existing chunk/SSR/TestClient warnings are not successful
or failed acceptance substitutes.

## Required fixes and readiness

Required fix: QG-01 only. No other current repair was identified.
Later sponsor/production dependencies remain open as recorded: Live ACRA, Production/
PingFed, EDS runtime migration, full related-party/binary-upload/legal-controller paths
and downstream KYC/four-eye approval are outside this remediation. Mock/Local/Partial
provider classifications remain unchanged.

**Local commit readiness: BLOCKED** until repaired content has a fresh exact independent
PASS/P0/P1/P2=0/0/0. The owner permits at most two remediation rounds.
No product next phase, PR readiness, external interoperability or real-provider execution
is released by this report.

## Git/status boundary

At review:47 tracked modified files plus5 payload new files and1 derivative manifest;
zero staged paths. This assigned report adds one permitted derivative output.
The complete payload/path-set/hash identity remained unchanged through review.
The reviewer wrote only this report, made no fix/stage/commit/push/PR/merge, did not access
.env/private/clm_poc, and initiated no new phase or external provider call.
The branch and managed worktree remain for the coordinator's authorized remediation
and subsequent owner review.
