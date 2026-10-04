# Final P2 remediation independent quality gate

P2_REMEDIATION: PASS

Findings first: no remaining or new P0/P1/P2 finding in the assigned two-finding
remediation and adjacent regression scope. Counts: P0=0, P1=0, P2=0.
FINAL-P2-01 and FINAL-P2-02 are CLOSED on the frozen content below. This is a fresh
independent GPT-6.1 Sol High review, not an implementer verdict or a replacement
whole-program Live/production claim. No implementation fix was made by this reviewer.

## Reviewed identity and boundary

Date: 2026-10-04. Worktree:
`C:/Users/shane/.codex-clean2/worktrees/onboarding-intelligence-goldtier-sandbox/data-dividends-zero-touch-clm`.
Branch: `feat/onboarding-intelligence-goldtier-sandbox`.
BASE_SHA, HEAD and cached origin/main:
`1d426e0ceddc32d80b0aaec293c62fb761f2fecf`.
No remote fetch or publication-readiness gate was run; cached main is not a new remote observation.

Frozen manifest:
`.ai-pipeline/reports/ONBOARDING_INTELLIGENCE_P2_REMEDIATION_MANIFEST.json`.
Raw SHA256: `7e1579e0f8725f0e911692cfcb066e4cf0bfe4f7ebd3610e79cfb926163cef11`.
Candidate aggregate SHA256:
`643432542b672bece500bad06eec87fe2ab874b7f6fae1857173b0ddfdfe3c19`.
Algorithm: SHA256 of UTF-8 JSON of the path-to-raw-SHA256 mapping, sorted keys and
separators `(',', ':')`. The manifest enumerates the complete 190-path current
candidate. Its own manifest and this sole new gate are the two excluded bookkeeping paths.

The independently reviewed behavioral delta is six paths, not a new review of all
pre-existing program behavior:

- `apps/backend/app/services/manual_ownership_evidence.py`
- `apps/frontend/src/pages/ManualOwnershipEvidenceForm.tsx`
- `apps/frontend/src/pages/S2OwnershipReview.test.tsx`
- `docs/contracts/OWNERSHIP_UBO_PROFILE.md`
- `scripts/run_s3_sandbox_acceptance.py`
- `apps/backend/tests/test_p2_remediation.py` (new)

The reviewer checked the complete six-file delta against current owners/contracts,
inspected the cumulative changed-path inventory and adjacent source/tests, and verified
all 190 raw hashes, aggregate, exact path set and empty index before and after review.
All 183 unchanged task-start paths match `.runtime/p2-remediation-start.json`.
Four raw-before code/test copies match their recorded task-start hashes; the complete
normalized six-file diff independently reconstructs `.runtime/p2-delta.diff` exactly.
The contract before-copy is normalized-text reconstruction only: its original mixed
newline layout was not recovered. This limitation does not weaken the verified raw
current contract identity or the reviewed text change.

The preceding final gate remains immutable FAIL with its original two findings and
SHA256 `09e735f67faf3e62e61bf5caf2b631938450e391ddf959377b28b0f84acc01f1`.
Its manifest, check index, external/durable receipts and cleanup record were included in
the unchanged current-path verification. This report records their bounded remediation;
it does not rewrite that historical failure or transfer old execution to new content.

## Prior finding closure

### FINAL-P2-01: exact retained partial ownership - CLOSED

`manual_ownership_evidence.py:214-225` restricts CURRENT_EVIDENCE parent totals to at
most 100 while preserving the exact-100 rule for USER_SUPPLIED_DECLARATION and
DOCUMENT_OBSERVATIONS. Individual finite positive Decimal and six-decimal bounds,
unique parties/edges, legal parents, endpoint/root/identity validation, cycle rejection
and connectedness remain in the existing model. No missing percentage is inferred.
The form at `ManualOwnershipEvidenceForm.tsx:159` no longer rejects partial retained
current evidence; its graph remains disabled for that selection and submission uses the
retained parties/edges. Help text and OWNERSHIP_UBO_PROFILE clarify the same distinction.

OwnershipAnalysisService remains the source/exactness/currentness owner: current root,
parties and endpoint/Decimal graph comparison and current document bindings precede
replacement. The existing creator-bound route reauthorizes within the owning case lock;
automation/ownership/event revisions, target freeze and repository CAS remain unchanged.
Accepted decisions retain prior analysis/receipt and invalidate confirmation through the
existing owners. One Decimal graph/path/candidate engine remains authoritative.

Executed tests retain INDIRECT_OWNER, MULTIPLE_PATHS and BELOW_THRESHOLD current
percentages, candidates and history. Creator API tests exercise both partial graph
variants: a forged lower percentage or stale version returns 409 without document,
ownership/automation mutation or target replay; valid retention returns 200 and retains
the creator receipt/history. The unchanged adjacent security pack covers noncreators,
unknown legacy creator, cross-team safe404, session/team/creator changes inside the lock,
submission freeze and complete document-edge coverage. Frontend tests retain exact
partial/multipath edges and still reject partial edited declarations.

The reviewer's separate in-memory probe accepted exact root interests30/10, then rejected
15 adverse CURRENT_EVIDENCE/input/source cases: zero, negative, over100, NaN, infinity,
excess precision, Boolean and binary float; self-edge, duplicate edge, unknown endpoint,
disconnected party and legal-entity cycle; partial manual and document declarations.
No provider/persistence operation occurred in that probe. Overfull parent totals are
also covered by the executed new test. The original source-validation/currentness and
security boundaries were not loosened by allowing a supported exact partial graph.

### FINAL-P2-02: post-completion acceptance exit - CLOSED

`run_s3_sandbox_acceptance.py:509-525` sets ACCEPTANCE_VERIFIED only after the successful
try has completed baseline reads, any uncertainty check, applicable restart/evidence/
call-count proof and both client context shutdowns. Exit0 now requires that marker AND
application COMPLETED. An AcceptanceBlocked or ordinary exception sets BLOCKED and
returns2 even when the application result is already COMPLETED. Preserving that
application fact in the receipt is truthful; it no longer implies overall proof success.
Receipt serialization/write/print failure cannot reach a success return; the unchanged
module-level safe exception boundary produces a nonzero result.

The new tests compile and execute the actual main post-confirmation AST, retaining
baseline/restart validation, exception handlers, receipt serialization and return logic.
Memory-only API doubles replace the external infrastructure; expected exit behavior is
not reimplemented in the test. Seven failure injections cover baseline, restart startup,
login, API, changed document, changed ownership and changed call counts. Every path
retains COMPLETED, records BLOCKED and returns nonzero. Separate external/offline-mode
success probes require ACCEPTANCE_VERIFIED and0, and three incomplete application
states return nonzero. These tests do not prove actual restart or an external API call.
The coordinator's separately executed real offline module CLI supplies whole offline
setup/dispatch evidence; this reviewer did not rerun an external acceptance attempt.

No target execution, transport/authentication, ledger, provider budget, database driver
or process ownership was changed. No new current blocker, duplicate owner, fallback,
architecture drift, contract/mapping assumption or missing ADR was found in this delta.

## Independent execution and hygiene

Python: existing worktree `.venv/Scripts/python.exe -B`, PYTHONDONTWRITEBYTECODE=1.
Pytest used `-p no:cacheprovider -o addopts=` and the explicit task-owned ignored
`.runtime/p2-independent-tests` basetemp. Frontend test cache was disabled.
Approved worktree runtime escalation supplied the permitted test-directory/runtime
access. No infrastructure error or skip affected the completed independent test runs.

| Independently executed check | Result |
|---|---|
| Relevant backend pack, including all22 new P2 cases | 258 passed, zero skipped/errors/failures, one existing Starlette/httpx deprecation warning;55.95s;exit0 |
| S2OwnershipReview and ManualOwnershipEvidenceForm frontend | 26 passed across2 files;2.28s;exit0 |
| Separate current-evidence adverse probe | Exact partial40 retained;15 adverse cases rejected;exit0 |
| Six current scanners | check_secrets, check_architecture, check_project_state, check_policy_authority, check_tooling_config, check_external_provider_readiness each exit0/PASS |
| Frozen content/log identity | 190/190 raw hashes, aggregate/manifest, exact changed/new set, empty index and all indexed current safe log hashes matched |
| Before/delta identity | 183 unchanged starting paths,4 exact raw-before copies and independently reconstructed normalized six-file diff matched |
| Whitespace/encoding | git diff --check exit0; all190 candidate files explicitly decoded UTF-8 and checked for trailing whitespace, including task-owned new Markdown |
| Reviewer report closeout | Sole new report; post-write frozen content/path/index verification and explicit report hygiene passed |

Exact backend command from worktree root:

```powershell
$env:PYTHONDONTWRITEBYTECODE='1'
.venv/Scripts/python.exe -B -m pytest apps/backend/tests/test_p2_remediation.py apps/backend/tests/test_manual_ownership_evidence.py apps/backend/tests/test_s2_ownership_intelligence.py apps/backend/tests/test_s2_persistence_security.py apps/backend/tests/test_s3_acceptance_safety.py apps/backend/tests/test_s3_retained_recovery.py apps/backend/tests/test_s3_submission_status.py apps/backend/tests/test_phase24_identity.py -q -p no:cacheprovider -o addopts= --basetemp .runtime/p2-independent-tests --tb=short
```

Exact frontend command from `apps/frontend`:
`npm.cmd test -- --no-cache --run src/pages/S2OwnershipReview.test.tsx src/pages/ManualOwnershipEvidenceForm.test.tsx`.

Two reviewer diagnostic attempts failed before their corrected checks: an import typo
(`deepcopy` as module) and an incorrect assumption that the new-file diff used
`/dev/null` rather than `before/<path>`. Corrected reviewer commands passed as recorded;
no reviewed content changed and neither initial attempt is counted as passing evidence.

## Current coordinator evidence, separately attributed

The reviewer verified the manifest-indexed safe log raw hashes and relevant summaries.
These are executed coordinator lanes on the frozen repaired content, not independent
reruns. Full/regression evidence satisfies the affected workflow classes without
claiming the opt-in lanes were rerun:

| Current coordinator lane | Verified summary |
|---|---|
| Focused backend | 238 passed, one existing warning;includes22 new P2 cases |
| Whole backend | 2300 passed,119 opt-in skipped,4 existing warnings;858.70s;exit0 |
| Whole frontend | 502 passed across41 files;exit0 |
| Guarded browser/HTTP | S2 two journeys and S3 normal offline-XPI journey PASS; original60s lifecycle bound; cleanup reports ports15680/15673 bindable |
| Actual offline module CLI | exit0;OFFLINE_XPI_PROTOCOL/COMPLETED/ACCEPTANCE_VERIFIED;simulated Search2/Shell1/Policy1/readback1, zero actual external calls |
| Static/contracts | Ruff backend/root, strict mypy124 files, typecheck/build, contracts44, pip check PASS |
| Root tooling/governance | 301 passed, one existing dependency warning;exit0 |

Offline CLI receipt raw SHA256:
`2d5524d05f03936c46867adda039c5a65ebf5cab092a4d49b1856de0eff53205`.
Detailed reproducible commands/log paths/hashes are in the frozen manifest.
Existing build warning remains:544.38kB JS exceeds500kB. Scanners provide supported
pattern/syntax coverage, not guarantees about every possible secret or semantic bypass.

No physical Mongo or actual OCR was rerun in this remediation review. All119 current
backend opt-in skips remain skips. Prior113 physical and6 actual OCR cases belong to
their historical identities, not this review. The two-finding delta changes no schema,
repository/CAS/auth owner, driver, OCR, runtime process or provider execution, so new
physical/real-OCR proof is not required for the bounded corrected predicates. The
AST external-mode tests cannot substitute for future genuine external/restart proof.
No browser service, database/container or network/provider invocation was started by
this reviewer. Current browser evidence above is coordinator execution only.

## Authority, impact and closeout

For this six-file remediation: API request validation and runtime behavior CHANGED;
API fields/types UNCHANGED; schema/persistence UNCHANGED; connector/provider contract
UNCHANGED; configuration UNCHANGED; business defaults/approval rules UNCHANGED;
target mapping UNCHANGED; auth/security ownership and enforcement UNCHANGED;
architecture owners/dependencies UNCHANGED; provider status UNCHANGED.
The retained-source validation rule is corrected within the existing project-owned
contract; the tooling acceptance success predicate is corrected. No new sponsor rule,
source precedence, hierarchy, related-party, compliance or legal-UBO behavior is added.
GoldTier parent route remains PARTIAL Sandbox; Mock/Local/Sandbox/Partial/Dormant are
not Live. Production identity/PingFed, legal/control/reviewer policy, RP child lifecycle,
original-document transfer, GoldTier KYC/approval/RFA and Live interoperability remain
outside this verdict. No broader program readiness or publication authorization follows.

Final working-tree inventory:120 tracked modified +72 task-owned new paths =192,
including this sole reviewer report and its manifest. Index remains empty. Worktree,
branch, HEAD/base/cached-main and all frozen content remain unchanged. This reviewer
read AGENTS.md, the quality-gate/findings-first procedures, selected current workflow/
context, planner/remediation/prior gate, ownership contract/decision/owner and relevant
tests. The sole persistent reviewer write is this assigned report. Task-owned ignored
pytest temporary files remain; no reviewer-owned running service exists. No private
.env/configuration, confidential artefact, original clm_poc, provider/network mutation,
Git mutation, commit, push, PR, merge, implementation fix or next phase was performed.

Next authorized action: release this report and exact raw hash to the coordinator;
verify unchanged content and STOP for owner review. Publication/pre-PR work requires a
separate explicit assignment and its own exact-content/integration checks.
