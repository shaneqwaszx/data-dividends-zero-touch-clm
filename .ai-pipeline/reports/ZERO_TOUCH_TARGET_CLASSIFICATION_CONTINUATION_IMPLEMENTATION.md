# Target classification continuation — implementation handoff

Date: 2026-10-06. R2 is the second and final authorized remediation round.

## Outcome and Git identity

The candidate implementation remains uncommitted on the existing branch. Independent R2
review found a remaining product P1 plus the historical safety P1: FAIL, P0/P1/P2=0/2/0.
The broad regression was exercised but its first partition had one Windows socket-resource
failure; the failed case and owning suite passed independent isolated reruns. No clean full-run
PASS, phase completion or second commit is claimed.
The historical requirement-T safety blocker remains visible and cannot be undone by source changes.

- BASE_SHA / inspected local origin/main: 771a9696e1e31e3865da4fbbb3f9b33b5959cb6a.
- Previous accepted HEAD / current HEAD: ccff7471fd23e64e87bf94a087a5540762276900.
- New commit: none; commit is conditional on exact independent PASS0/0/0.
- Branch: fix/zero-touch-registry-reuse-happy-path.
- Worktree: C:/Users/shane/.codex-clean2/worktrees/zero-touch-registry-reuse-happy-path/data-dividends-zero-touch-clm.
- Reviewed R2 content: HEAD plus72 paths in REVIEW_MANIFEST_R2.json.
- Raw aggregate SHA256: 2ac3a5b29e5501da9eb34bd69dd3324e9ce45a30fb25f5e675eb6642abbd501a.
- Formula: lexically sorted UTF-8 path + NUL + raw SHA256 + NUL, then SHA256.
- Index empty;65 modified tracked paths and7 new reviewed paths, plus derivative reports/manifests.
- Primary main checkout clean. No branch creation, amendment, push, PR, merge or worktree removal.
- Main was inspected locally; no latest-remote fetch, remote CI or publication gate claim.

R0/R1 manifests and gate reports remain immutable. Reports/manifests are derivative
evidence excluded from source identity. The source actually tested and independently
reviewed is uncommitted R2 content, not a future commit.

## Readiness and submission settings

The old Readiness check meant: are current authoritative case evidence, ownership,
target identity/classification and required target fields complete/current enough to
prepare submission? The new primary label is Submission readiness. It is not KYC,
four-eye, GoldTier approval or Ready-for-Approval.

With prerequisites ready, Submission readiness is Complete; GoldTier submission
package is Prepared/Complete; only Final review & send is Review required. Final
confirmation remains mandatory. Twelve nodes remain. Current blockers prevent stale
Prepared copy and final-send review; actual frozen package history remains distinct.

POC configuration authority previously displayed case-bound target configuration and
its governance authority. GoldTier submission settings now groups System-set Singapore
values, Automatically classified from evidence, User input required and Unavailable /
not transmitted. Technical authority/provenance remains in disclosure details.
DSD/ACRA/Singapore/ANZBGL remain system-owned; unsupported account/product fields remain unavailable.

## Automatic classification, provenance and manual fallback

The existing document/IDP owner extracts two explicit labelled observations separately
from the unchanged four-field identity profile. Automatic KYC supports only Company -
Private, Partnership - Unregulated and Government. Broader sponsor vocabulary remains.
Client Segment requires explicit exact sponsor-vocabulary text; fictional Corporate /
DI - Government profiles do not create a universal legal-form mapping.

Safe automatic selection requires a current identity-trusted document, current version,
normalized exact value, HIGH extraction quality, score >= frozen case threshold,
unambiguous extraction and no contradictory current classification observations.
The existing case binder retains safe partial values and requests only unresolved input.
Deterministic private-company/Government mismatch is blocked. Explicit prior USER choice
and disagreeing safe current document require review; neither silently overrides the other.

Separate DOCUMENT/USER selections retain document ID, version/event count, page/reference,
method/quality, deterministic score, exact value, timestamp, case policy/vocabulary versions.
Browser labels distinguish Automatically classified from document and Selected by user.
Automatic policy metadata is PROJECT_DERIVED_POC, user fallback USER_AUTHORIZED_POC;
policy authority is not substituted for source evidence.

R1 fixed prior USER disagreement, snapshot-start and NOT_STARTED currentness, and stale
prepared/final-action projection. R2 closes Mock mode's remaining gate: currentness is
required in every mode; explicit current observations or retained selections require a
complete compatible profile. Legacy Mock without classification input remains optional.
Independent R2 found a residual conflict: a prior USER choice survives two later trusted
documents with contradictory KYC labels because the assessor returns no automatic candidate
and the USER-currentness check does not recognize that conflict. Both modes falsely remain
ready; explicit confirmation can freeze/execute the stale choice through local fake transport.
The source is frozen and the two allowed remediation rounds are exhausted. This defect
remains for owner disposition; the passing authored tests do not certify full F/G compliance.
No provider family, sponsor mapping rule, final approval rule or >=25% threshold changed.

## Fictional fixtures and existing-engine expected results

| Fixture | Explicit profile | Exact ultimate percentages | Provisional >=25% candidates |
|---|---|---|---|
| Alpha | Company - Private / Corporate | 60,40; exactly two people | P1,P2 |
| Beta | Company - Private / Corporate | 30,25,17,14,8.5,5.5 | P1,P2 |
| Gamma | Partnership - Unregulated / Corporate | 30,25,20,10,10,5 | P1,P2 |
| Delta | Company - Private / Corporate | 30,10,40,20 | P1,P3 |
| Separate Government | Government / DI - Government | No fabricated share graph | Unsupported ownership review |

Beta root H1/H2/P1=50/30/20; H1 P1..P6=20/50/10/10/5/5; H2 P3..P6=40/30/20/10.
Every direct parent totals100 with exact Decimal values; the existing sole engine
aggregates direct/indirect paths. Gamma has six explicit synthetic economic interests,
not official ACRA facts. Government control/legal UBO completeness is unsupported by
current numeric-share semantics. Delta remains coherent; a separate Government fixture
and browser test demonstrate classification without invented ownership or full submission.

Five regenerated image-only PDFs show FICTIONAL FYP TEST DATA, identity, explicit
classification and fixed system profile. Actual local Tesseract extracts identity and
classification. Five rendered pages were independently inspected as readable without
clipping; native-text extraction is empty. No real personal fixture data was introduced.

Guarded Atlas-safe database name: clm_uat_<24 lowercase hex>,32 bytes.
Seed is idempotent and rejects protected/production/unsafe/old overlong names.
The updated guide covers separately provisioned Mongo/authSource and fresh application
authentication bootstrap prerequisites without copying credentials.

## Target safety and uncertainty diagnosis

Classification PUT and automatic binding perform provider calls0 and attempted target
mutations0. Initial read-only Search belongs to the separate target-search owner.
Before final Send: Shell0/Policy0/Amend0/readback0 and attempted ledger mutations0.
Only explicit final confirmation authorizes existing ordered ledger execution.

Controlled reproduction established a pre-send projection defect: an empty NOT_STARTED
intent reached the catch-all uncertain status. It now remains NOT_SUBMITTED. True
retained Shell/Policy uncertainty displays the actual earlier operation, freezes edits,
removes Send/retry and retains authorized read-only verification. Repeated confirmation,
classification changes and mutation replay are refused. No raw provider body is exposed.

The owner's original UAT ledger was not accessed. Its precise historical root cause
remains unknown; controlled results do not establish classification-triggered writes in
that historical session. The former provider-capable generic classification continuation
was replaced by local preparation to guarantee zero provider calls by classification save.

## Verification by content actually tested

Current frozen R2:
- Focused continuation:42 passed. Five final Mock regressions first reproduced4 failures
  with1 legacy control passing; all pass after the bounded source correction.
- Full backend:2566 collected/2443 passed/122 conditional Mongo skips/1 environmental
  startup failure. Exact disjoint exhaustive partitions1242/1236/88; no case deselected.
  Group1:1222 passed/19 skipped/1 failed,563.21s; group2:1133 passed/103 skipped,242.69s;
  group3:88 passed/0 skipped,343.24s, including both100-run stability tests. Group1 failed
  with WinError10055 in asyncio/socketpair at TestClient startup before application
  assertions, plus a partial-loop teardown warning. After host quiet, the independent
  exact failed parameter passed1/0 skips in2.27s and owning recovery suite passed19/0
  skips in23.53s. Initial full execution remains failed; reruns are separate evidence.
- Affected physical Mongo:10 passed/0 skipped,37.73s. Newly generated allowlisted databases
  only in owned loopback Mongo7; cleanup verifies absence.
- Full frontend:42 files/520 tests passed,10.15s. TypeScript and production build pass;
 128 modules,551.15KB minified bundle, existing >500KB warning.
- Browser:4/4 pass. Alpha9.8s, Partnership9.9s, Government6.6s, uncertain Policy6.0s.
  Real local HTTP/Tesseract, actual disposable Mongo for database paths, local fake XPI.
  Network-policy violations0. Pre-Send Search1/writes0/attempts0/classification PUT0;
  post-Send Alpha/Partnership Search2/Shell1/Policy1/Amend0/readback1 and synthetic ID.
  Government stops at unsupported ownership review. Exact-name parent DB cleanup VERIFIED
  after child shutdown and before E2E PASS.
- Ruff backend PASS; strict mypy126 source files PASS.
- Contracts44 plus hostile isolation1 and governance97: combined142 passed,40.50s.
  An initial combined invocation failed collection because the contract helper directory
  was absent from PYTHONPATH; corrected isolated invocation passed. Failure is not PASS evidence.
- Direct project-state, architecture, policy-authority, provider-readiness and secret
  checkers PASS. No supported new secret pattern or confidential artifact found.
- Tracked whitespace plus explicit reviewed text/new-Markdown UTF-8/trailing whitespace PASS.

Earlier evidence with exact unchanged surfaces, attributed to its execution revision:
- R1 full backend2561 collected:2439 passed/122 conditional physical-Mongo skips, exit0
  across1237/1236/88 disjoint partitions. R1 fresh physical10 and browser4 passed.
- R0 full physical17 suites/122 passed/0 skipped. Persistence/schema/fixture/harness bytes
  are unchanged through R2; fresh R2 affected physical/browser checks supplement this.
- R0 Windows lifecycle31 passed,601.999s, isolated43210/43211 ports; owner8000 preserved.
- Affected tooling73 plus hostile import1 passed. Parent cleanup/startup/assertion failure
  containment, Playwright discovery71 tests/14 files/64 lifecycles verified.
- R0 security/governance170 passed; installed dependency pip check/npm ls passed after
  task-isolated exact-lockfile offline npm install. Primary shared dependencies preserved.
- Legacy actual OCR6 cases executed via Tesseract PATH in full backend.
- No full64-lifecycle browser execution or remote CI result is claimed.
- No actual pre_pr_check publication gate was run on intentionally uncommitted content.

## Independent gate and historical safety blocker

R0 FAIL0/3/1: two P1 product currentness findings, one P2 projection finding and historical
requirement-T P1. R1 FAIL0/2/0: one residual Mock product P1 and historical-T P1.
Fresh R2 independent verdict: **FAIL — P0/P1/P2=0/2/0**, in
ZERO_TOUCH_TARGET_CLASSIFICATION_CONTINUATION_QUALITY_GATE_R2.md. Independent R2 reports a new P1 product counterexample: create Alpha,
save USER private/Corporate before intake, then complete two current trusted identity-matching
documents labelled private/Corporate and partnership/Corporate. No automatic type candidate
exists; the prior USER choice remains accepted, ready and Prepared. Confirmation200 creates
a frozen snapshot/confirmation/ledger; Sandbox fake transport performs GET,GET,POST,POST,GET.
There was no classification review after the conflicting observations. Classification PUT
itself still makes zero provider calls; this is a stale conflict/readiness defect at later Send.
Both current trusted documents are REVIEWED/HIGH/above frozen threshold and postdate
the USER selection. Final fake execution reaches COMPLETED/SUBMISSION_CONFIRMED and ledger
FINALIZED without explicit classification review after the conflict. Independent71 focused
tests and16 other adversarial cases passed, but this separately falsified path remains broken.
The remaining product finding is reported for owner disposition:
the two permitted remediation rounds are exhausted; no third round is inferred.

An early focused invocation encountered ambient dotenv/Garden configuration. A separate
early standalone contract invocation used ambient Mongo settings and failed application
startup with PersistenceDataInvalidError. Mongo initialization can create indexes or
recover earlier records before a later invalid record fails. The exact namespace and
side effects cannot be certified without additional prohibited access. Whole-session
owner .env/protected database non-access is therefore NOT CERTIFIED. No further owner
database investigation was performed. No URI/secret/raw payload was disclosed or retained.

Current ordinary pytest, test-mode settings and standalone contract startup disable
dotenv before composition. Hostile environment isolation independently proves no
MongoClient construction. These controls prevent recurrence in tested paths; they do not
erase historical uncertainty or waive requirement T. Only the owner can decide the
acceptance consequence. An investigation would need separate explicit authorization.

All controlled execution used local/fake adapters: external ACRA0, external GoldTier0.
No Production/PingFed, provider-family switch, live interoperability, legal UBO or
KYC/four-eye/Ready-for-Approval claim. Whole-session historical protected non-access
remains separate from these controlled provider-operation counts.

## Change classes, retained owners and next action

API/type: changed selection audit and pipeline/status projections. Durable schema:9->10,
strict read-only1..9 compatibility without inferred provenance or rewrite. Connector:
existing local IDP observations changed; GoldTier mappings/family/endpoints unchanged.
Configuration: explicit test isolation and CI disposable Mongo only. Business behavior:
bounded automatic/manual currentness and ready/frozen/uncertain projection changed.
Auth/security: test/source binding strengthened; RBAC/team/session/locked reauthorization
and CAS owners retained. Architecture: owners/dependencies retained, one pure selection
model, no second service/repository/persistence/ownership calculator. Provider status:
unchanged. Runtime behavior: local binding/preparation, truthful status and test cleanup changed.

Final task-owned database count0 was verified before stopping the owned Mongo container;
it auto-removed on stop, and exact-ID absence was verified. The redundant subsequent rm
returned No such container; it is not represented as a successful rm command. All owned
ports18765/14173/27185/43210/43211 are free. Unrelated owner resources remain preserved.

No second commit is eligible: exact independent PASS0/0/0 is unmet. Preserve the uncommitted
worktree and all acceptance evidence. Stop for owner review; no push, PR, merge, amendment,
worktree deletion, protected-database investigation or next phase is authorized.
