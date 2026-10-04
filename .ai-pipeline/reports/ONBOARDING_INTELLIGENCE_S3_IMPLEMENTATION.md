# Session 3 implementation and acceptance evidence

Branch: feat/onboarding-intelligence-goldtier-sandbox. BASE_SHA/HEAD/cached origin/main:
1d426e0ceddc32d80b0aaec293c62fb761f2fecf. Worktree is the fresh managed
onboarding-intelligence-goldtier-sandbox checkout. All changes are intentionally
uncommitted; normal main and original retained records remain untouched.

S1 independent PASS and S2 fresh round1 independent PASS authorize this sequential
Session 3. Historical gates remain byte-identical. This report is an implementation
handoff, not independent acceptance. The actual bounded synthetic Sandbox delivery
completed after exact fresh PRE_MUTATION: PASS; final combined review remains pending.

The existing case/target ledger and XPI mapper now project truthful retained
NOT_SUBMITTED, SENDING, SUBMISSION_CONFIRMED, SUBMISSION_FAILED,
SUBMISSION_OUTCOME_UNCERTAIN and FINALIZATION_PENDING states. Active-call metadata
is volatile within the existing owner. Final Review & Send stays visible after
confirmation. No second local human approval exists. An uncertain Policy cannot be
confirmed by customer Search. One automatic user/session/case/submission-scoped
read-only check aborts stale publication and never resumes or repeats writes.

The new API enforces expected submission UUID, CSRF, safe case-scoped 404 and fresh
reauthorization inside the case lock; provider-mode/current identity drift fails
before Search. It changes no durable ledger, customer ID, Policy or recovery state.
Normal composition's optional transport injection uses the existing port; default
Mock and real Sandbox transports remain separate with no fallback. Preview street2
now exactly matches transmitted Shell values; canonical provenance can include
authorized reconciled document evidence.

The complete field inventory separates business data, explicit policy,
system bindings and provider responses. No supported parent enrichment requires
Amend. RP child creation/retrieval/binding and original-document upload remain
unsupported. Policy technical success is not KYC, approval or Ready-for-Approval.

Current local evidence:

- Focused mapper, XPI ledger/status/adverse paths and tooling: 189 passed in9.34s.
- Physical Mongo: 16 suites,112 collected/executed/passed,zero skipped/failed/errors.
  Three new normal-API Sandbox success/uncertain/failed cases preserve exact document,
  creator-reviewed ownership and target state across restart; confirmation stays409,
  no additional provider calls. Every database is generated/allowlisted and cleaned.
- Full frontend:500 passed in41 files; typecheck and build passed. JS544.24kB/CSS89.30kB;
  existing >500kB build warning remains.
- New real-HTTP offline Sandbox browser journeys:3/3 passed, original60s per-test bound;
  success4.9s, uncertainPolicy3.9s, definitivePolicyfailure10.4s. Each verifies
  Shell1/Policy1/Amend0/external0, frozen review/retainedID and responsive320/720/1280.
  Uncertain automatic check runs once; remount makes no additional provider call.
- Strict configured mypy:124 source files passed. Backend Ruff and root scripts/tests
  Ruff passed. Configured unittest contract discovery:44 passed. Six governance
  scanners passed at the recorded local checkpoint; later report/doc changes require
  final recheck. Tracked diff whitespace passed; new-file hygiene is checked at freeze.

Initial diagnostic commands with an incorrect console test filename, incorrect
contract entry point and wrong Ruff package context did not execute their intended
checks. Correct configured invocations above passed; no unrelated lint fixes were made.
The new safety test reproduced a missing-ID wrapper stop before its fix; now all14
focused safety/activity cases pass and the connector retains uncertainty truthfully.
These are implementation verification corrections before the first independent S3 gate.

The acceptance harness requires exact historical S1/S2 gate hashes, current local
mapper/ledger proof, authorized configuration, one on-disk synthetic identity reservation,
normal evidence preparation and exact fresh independent PRE_MUTATION: PASS before
final confirmation. It reserves Search<=2/Shell<=1/Policy<=1/readback<=2 before calls,
rejects Amend for the current unenriched package and stops all writes after uncertainty
or provider rejection. It never edits private configuration or prints private values.
One actual bounded external Search returned HTTP200 / NO_MATCH for the reserved
synthetic identity. This paragraph records the pre-mutation checkpoint; the completed
actual attempt and final verification delta below supersede its execution status.

The first complete backend execution had2276passed/118opt-in skipped and one failure
in847.63s: the explicit route-inventory test retained81/41 counts after the deliberately
classified status-check route increased them to82/42. Runtime inventory equality and
authorization classification already passed. The fresh independent R0 gate reproduced
P2-01 and returned PRE_MUTATION: FAIL. R0 report/manifest are archived unchanged.
Bounded remediation round1 corrects only that test's exact totals and adds explicit
CASE_SCOPED coverage for the new route; production/package/harness remain unchanged.
The fresh R1 independent gate passed on exact173-path candidate d17f17017d7839e3722161bafe2d2e1b3c4ba9511d34be6d57370b450cfe39f6.
Gate SHA256 a839edfccebde7ab6eaf144a64bd1b4c766eef4034d5beaee12f2d5a4ba7a5a7
and every candidate byte/path were reverified before releasing the held SEND.

The sole reserved actual case74af14cb-c691-485a-bfc0-ca89de40dc65 used synthetic
ZERO TOUCH POC ACCEPTANCE9CD9A457 /202655266Z, reviewed document
ed3b0b9a-36c0-41d2-b09c-56249217d527 and creator-reviewed explicit70/30 ownership.
Real XPI calls were Search2, Shell1, Policy1, Amend0 and exact-ID readback1; every
dispatched call returned HTTP200. Retained customer143887, SHELL_CREATED,
POLICY_CREATED, AMEND_NOT_REQUIRED and VERIFIED same-ID readback establish the
successful FINALIZED ledger and SUBMISSION_CONFIRMED/COMPLETED application state.
Policy ID was absent and remains null. Technical Policy success does not establish
GoldTier KYC, approval or Ready-for-Approval. No RP/document-upload call was made.

Normal application restart/new login retained exact document/ownership evidence and
submission/operation state, with provider call counts unchanged. The safe external
receipt SHA256 is2a06fe9e1682fa833794de6e678f919bedf8ba45fc5b457e9ebd0de35d9a29c1.
Read-only strict durable proof SHA256 is658355aa2b2ec40fec9a0c621453f363b8b342fbfab7a7d7369aa6c3d325cf4e;
case schema9/revision68, final success receipt and original record digests are retained.
No raw provider body, credential, header or original-document bytes are archived.

R1 verification before the final recovery repair: complete backend2277PASS/118 opt-in skips/
4 existing warnings/834.48s. The112 physical tests across16 suites and36 real-OCR
tests separately execute the physical/host-OCR paths. R1 actual scanned-PNG
browser proof passes1journey/87assertions with zero substitutions, writes or external
calls; its218-file application fingerprint3205d3b4f1e47772e3e0d3b80eb8e5829185b01a2af0744bf18635efcf374e72
matches the R1 application bytes; the R2 presentation delta changes that fingerprint
and requires a fresh current receipt. Focused R1 authorization/S3 checks91PASS26.42s;
six scanner unit files: 89 PASS in31.59s. Full frontend: 500 tests/41 files;
typecheck/build, strict mypy124, Ruff and44 contracts passed. The first whole final
browser attempt stopped after52 selector passes at selector53's original60s limit;
an unchanged focused rerun passed6.0s. The fresh whole run then passed all59 selectors/
66 executions in562.250s, zero skips; original deadlines and all13 E2E files unchanged.
R1 browser source aggregate SHA256:
1d4fd11002dc01ad0084c85297beb412f7d918ba2c1aaba876abd69faa8957d4.
All118 assigned E2E ports plus OCR ports38765/34173 and Mongo27078 were released and
bindable. Complete Windows lifecycle passed31/31 in393.569s, original assertions/
deadlines unchanged. Six scanners pass after the provider documentation delta.

The Ultra reviewer independently read only the exact successful disposable case and
verified its strict receipt, record digests, revision and retained operation facts
before releasing read ownership. Root reverified archive hashes, dropped only
clm_p12_ab341ce202b34b36a112ea10 and removed its exact task-owned Mongo container.
The owned OCR image/tag was removed after completed evidence collection. The external
customer and original clm_poc are untouched by cleanup. A bounded offline challenge
of retained safe-recovery presentation confirmed P2-02. The final permitted
[round2 repair](ONBOARDING_INTELLIGENCE_S3_REMEDIATION_R2.md) changes only derived
state/copy for fully resolved retained prefixes; execution/authorization remains in
the existing owners. Genuine uncertainty stays read-only.

Current R2 verification: complete backend 2,278 passed / 119 explicit opt-in skips /
zero failures / four existing warnings. Double quiet pytest settings omit the timed
footer; all 2,397 completed progress markers agree with independent collection,
and the full process exited 0. No duration is invented. The explicit physical pack
passes 113 tests across 16 suites, zero skips/errors. Current real OCR passes 36 tests
and the scanned-PNG browser passes 87 assertions, with unchanged application identity
fd18199cf4bbb90892dab8b5d58327733d19c068d12e2feb97f7afb455bace8c. The new R2 OCR receipt
is separate from the immutable earlier R1 receipt. Full frontend 500 / 41 files,
typecheck/build, Ruff, strict mypy 124 and 44 contracts pass. The complete current
non-Windows tooling suite initially failed one stale discovery stub (300 pass), then
passes all 301 after a test-only signature/assertion correction within round2.
The complete current E2E passes 59 isolated selectors / 66 executions in 558.766
seconds, zero skips, under unchanged 60-second per-lifecycle limits. All 13 E2E files
remain byte-identical before/after aggregate e4b55065ba6b85b019c562c87f8f7432abc860639505d021905cd319cd9b85df.
Complete current Windows lifecycle passes 31 tests in 395.660 seconds on task-owned
ports 15800/15173, unchanged original assertions/deadlines. Final cleanup verifies
all 123 assigned ports bindable, launcher state absent, exact owned containers/
networks/image tags absent and both R2 Mongo anonymous volumes removed. Original
data, unrelated resources and other worktrees are preserved. The final check index,
cleanup report and program handoff retain exact log/source identities; the separate
fresh independent Ultra combined gate determines acceptance. This implementation
report cannot grant it.

Change classes: API/type additive; existing schema9 unchanged by S3; connector
transport-port injection/status observation changed, provider contracts unchanged;
explicit acceptance process configuration added, private/default settings unchanged;
business rules/threshold/source precedence unchanged; mapping preview/provenance
corrected; auth/security additive fail-closed checks; existing architecture owners
preserved; frontend state/status/check cancellation changed; tests/tooling/docs changed.
Runtime behavior changed. Provider remains PARTIAL Sandbox, never Live.

Next authorized action after the final indexed checks/freeze and fresh combined review:
owner review only. No additional provider call or publication is authorized. The reserved
receipt must not be deleted/reused to create another synthetic customer.
