# PR85 physical Mongo recovery test correction

Implementation verification is complete; independent acceptance and publication remain
separate gates. This is the NEW owner-authorized two-test assignment, not an extension
of historical AM or blocker cycles2/2. One corrective implementation pass is used.
AM18 remains OPEN / NOT_REPRODUCED. No next feature or owner merge is performed.

## Identity and scope

Start2026-10-14T14:56:09Z; four-hour ceiling18:56:09Z. Existing worktree
C:/Users/shane/Desktop/FYP/am-w1-1014-0132, branchfeat/am-wave1-20261014-0132.
Starting/current HEAD93534b0b5bead1d78a113fbf25b99375f15c8e90;
committed tree601305d3285799dc8943c6565832f1af6beb995b.
Fetched main/basea497793be2615306bc7cfbd3104fd4352dead96d,
main tree8845949f4f76400678a5ebb041629dc8b96dde26. No index/commit/push yet.
The starting36-path candidate raw aggregate is
f584ba0c88d56f6ffad8eb8bfffc5c939e54934d1c421a88401168ee68a4131f;
all36 raw bytes still match. New full cumulative raw/native manifest is frozen separately
including this report; HEAD tree is not substituted for current reviewed content.

Only two named functions in apps/backend/tests/test_phase12_real_mongo.py change:
test_real_mongo_failed_replacement_restart_requires_retry_without_replay and
test_real_mongo_interrupted_document_recovers_to_bounded_same_case_retry.
An AST/source-span check verifies everything outside those functions is byte-identical.
Root/backend/frontend instructions, current CI_TOOLING/DOCS_ONLY and cumulative
BACKEND_DOMAIN/FRONTEND_UI union, current owner/contracts, PR83 acceptance and previous
immutable independent FAIL/cycle reports were inspected. No new architecture boundary
or ADR is required. User section5 forbids application changes; none is made.

## Failing-first cause and authority

Fresh unmodified two-case reproduction:0PASS/2FAIL/0SKIP,7.203seconds;
original assertion lines514/941. Original canonical151/149PASS/2FAIL remains FAIL.
Sanitized read-only durable probes verify both started_at values are present, current
failed/retried document lineage is retained, registry4 and target1 are unchanged,
IDP increments once per explicit retry, ownership evaluates exactly once, and the case
reaches WAITING_FOR_REVIEW/READINESS with TARGET_CONFIRMATION_REQUIRED. Zero target
executions and no confirmation exist. This is recognized started-workflow recovery.

MULTI_DOCUMENT_INTAKE_PROFILE explicitly permits final successful targeted retry
after failed siblings are replaced to continue to the next blocker. Current owning
retry_intake_document uses started_at to distinguish initial count-bound intake from
started recovery; that PR83 implementation is inherited unchanged from main832ff77.
The old physical fixtures originated in PR75/529efea. Count disagreement alone did not
justify the repair: retained state, lineage, stage and target boundary all corroborate it.
TestB deliberately persists an interrupted RUNNING/DOCUMENT record with started_at;
TestA legitimately completes initial intake once before the failed replacement.

## Corrected assertions and preserved adverse proof

TestA retains pre-restart evidence and failed/original chain, stale exception409, and
exact counters. It verifies retried case identity, REVIEWED current document, exactly
three retained records and the original->failed->retry chain. The obsolete second
initial-intake completion is removed. Actual GET must expose READINESS and the sole
target-confirmation blocker. Explicit resume leaves version and counters unchanged;
durable started_at remains identical and no ledger/confirmation exists before Send.
Explicit guarded Send reaches COMPLETED with counts registry4/IDP3/ownership1/target6.
Repeat retry returns409 INTAKE_NOT_OPEN; a third composition restart/resume preserves
completed version, confirmation, documents and every counter with no replay.

TestB retains durable interrupted FAILED/reupload recovery, the completed sibling and
unrelated-upload409. Retry is on the same case. Exactly three records retain failed
supersession, current REVIEWED replacement and unchanged sibling events/currentness.
Registry/target do not increment; IDP and ownership each increment exactly once.
READINESS/sole target-confirmation blocker, retained started_at, zero pre-Send ledger,
stable repeated GETs and idempotent resume are asserted. Repeated retry is denied before
Send without a provider call. Explicit Send adds exactly five target operations;
third composition restart/resume preserves completed state, versions, confirmation,
document history and counts. No count tolerance, skip, exclusion or product patch.

Existing test_initial_intake_continuation adverses are reused, including partial
retry/confirmation/replacement, wrong expected count and count-free resume refusal,
plus failed initial replacement. They independently forbid unstarted auto-advance.
One104-character line was wrapped AST-identically within this pass; owning RuffPASS.
Focused and canonical physical verification were repeated on final raw bytes.

## Verification

- FRESH focused physical final:2PASS/0FAIL/0SKIP,12.75seconds outer.
- FRESH final canonical physical:PHYSICAL_MONGO_RESULT=PASSED; SUITES=24; COLLECTED=151; PASSED=151; FAILED=0; ERRORS=0; SKIPPED=0;320.469seconds outer.
- Earlier corrected canonical151PASS/0SKIP324.609seconds is separately retained,
  not substituted for final raw-byte evidence after the formatting-only wrap.
- FRESH count/recovery/replacement/freeze regressions:42PASS.
- FRESH full backend:========= 2698 passed, 151 skipped, 4 warnings in 1021.06s (0:17:01) ==========. Physical guarded skips are covered by the
  independently recorded real151-case zero-skip lane, not silently relabelled.
- FRESH full frontend:Test Files  53 passed (53); Tests  682 passed (682). Types/buildPASS.
- FRESH security/governance139, runner/archive
  112, contracts44, assets4PASS.
- FRESH configured CI backend Ruff, changed Python tests Ruff, strictmypy127files,
  all11 exact Python pins/pipcheck, locked npm tree and six governance/secret scannersPASS.
- ATTRIBUTED complete browser pair:104selectors/128records,0fail/skip. The previous
  complete67+61record shard receipts, original budgets and per-fixture cleanup remain
  immutable. All relevant frontend/backend runtime, fixture, runner/configuration,
  contract/assets and dependency inputs are unchanged; only the physical test file is
  edited and it is outside browser runtime. e2e-attribution.json binds these raw/native
  inputs and the same installed toolchain/official Mongo7.0.40 image. User7H explicitly
  permits exact-input attribution. These are not new-task browser execution.

Current rootwide RuffFAIL15 inherited diagnostics in seven unchanged scripts exactly
equals the prior baseline. Configured mandatory backend CI lint passes; no suppression
or unrelated repair. Existing React act, bundle>500kB and backend deprecation/fixture
warnings remain disclosed. DockerOCR/Windows-launcher NOT_EXECUTED and private archive
validation NOT_VALIDATED; actual host OCR cases execute with child-only existingPATH.

## Isolation, hygiene and acceptance boundary

Cached officialmongo:7 imagea887b589a601923f6ae405f3f76c17984218971ced2ca59f05840b1f5a7c44c2,
actual7.0.40. Unique own container314874f177be6a1da5efa386aff09e35bd41379cfc2a95c2953646609ef443b8,
labelpr85-physical-recovery-20261014-01a138d5, loopback27186, nonroot999:999,
ALL capabilities dropped/no-new-privileges/no restart, two exclusive tmpfs mounts.
Protected-name refusal and generated allowlisted smoke/database cleanupPASS; post-suite
readback proves zero disposable leftovers. Runtime stays available only for independent
verification; exact ownership cleanup will stop/remove only this container at closeout.
Desktop was already running, no startup/pull/install/machine settings or PATH changes.
Other worktrees, writers, containers and protected data are preserved. No .env, Atlas,
owner database, clm_poc, credential or real provider access. No URI/private trace retained.

Every candidate/raw/native identity and new-file whitespace/secret scope is checked
before freeze. Ignored format-proof metadata initially shared its command-receipt name;
the actual command receipt is preserved and AST-equality is separately reconstructed
and hash-verified in format-identity.json. An ignored initial helper shell expression
failed parsing and a waiting verification helper had a nonexistent unexecuted filename;
both setup limitations are preserved, not product failures or passing evidence.

New API/type, schema, connector, configuration, business rule, mapping, auth/security,
architecture/provider classification and application runtime behavior changes: NONE.
Cumulative original PR85 Singapore-calendar/date/UI/draft behavior remains disclosed
in its unchanged reports and guide. Fresh independent gate must inspect the FULL
cumulative candidate, original FAILs and these new assertions. Only exact PASS permits
authorized scoped commit, clean committed pre-PR and same-PR normal push. New-head review
and separate push/PR CI observations remain required; billing-refused CI is NOT_EXECUTED.
The owner alone performs manual squash merge. No additional corrective pass is granted.
