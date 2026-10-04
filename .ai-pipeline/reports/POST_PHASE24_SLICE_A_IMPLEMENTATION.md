# Post-Phase24 Slice A implementation evidence

Date: 2026-10-02 (Asia/Singapore).
Assignment: approval attachment 2837163a-73e6-4bff-9ea6-7d6ed1d35c72.
Status: implementation verified; frozen candidate awaits the separately authored independent mini-gate.
This is an uncommitted implementation handoff, not publication or Slice B authorization.

## Identity, scope and decision

- Worktree: C:/Users/shane/.codex-clean2/worktrees/post-phase24-stability-provider-hardening/data-dividends-zero-touch-clm.
- Branch: feat/post-phase24-stability-provider-hardening.
- BASE_SHA, HEAD and fetched origin/main: 707765b1d51172c64b851c9e46e68b3c23006789.
- Normal main checkout remained clean at that SHA. The approved planner remains an unchanged historical checkpoint.
- Requested coordinator route: GPT-6.1 Sol / Ultra. Exact current chat model/effort cannot be independently read or switched by the coordinator.
- Two GPT-6.1 Sol / Extra High read-only advisers inspected coverage and browser fixtures; neither wrote implementation.
- Independent review is assigned to a fresh GPT-6.1 Sol / Extra High agent after this freeze.
- Coordinator is the only implementation and Git mutation owner. No commit, push, PR, merge, reset, stash or branch switch.
- Slice A only: PERSISTENCE compatibility, backend projection punctuation, focused browser expectation and regression/reporting.
- TDD Route: strict, by explicit user failing-first instruction.
- Change Necessity: code-change. Public serialization discards mandatory durable evidence; configuration cannot recover that evidence.
- Owner fit: existing DurableCaseSnapshotV7 conversion owner, following v5/v6. No new state, repository, converter fallback, schema or responsibility.
- Patch shape: explicit validated typed constructor, with unchanged legacy guards and storage/read ownership.

## Root cause, failing-first and repair

Before production edits, the retained synthetic regression constructed a populated v7 envelope with storage serialization,
validated DurableCaseSnapshotV7 successfully, and asserted that the public automation dump excludes its ownership binding.
The actual RED then failed at legacy.to_current(), in the old public model_dump conversion, with a required-field error at
automation.ownership_provider_binding_id. This was the expected defect, after correcting the fixture helper's keyword argument.

The fix passes every declared aggregate field directly into the normal DurableCaseSnapshot constructor. Nested typed
records retain ownership binding, exception authoritative evidence digest, reconciliation record/discrepancy/decision
fingerprints, and raw/source observation identity. Normal model validation and all existing decode guards remain.

Schema stays 8. No model_construct, defaults for missing mandatory evidence, ACTIVE policy lookup, read migration,
storage serializer change, schema weakening or repository ownership change. Public/browser model shapes remain unchanged.
The discrepancy fingerprint continues to be the existing API action token; it is not newly exposed by this change.

## Files and behavior

| Path | Change |
|---|---|
| apps/backend/app/persistence/models.py | v7 typed-field conversion, 16 lines replacing one lossy line |
| apps/backend/app/api_models.py | six classified source lines: three em-dash and three middle-dot corrections |
| apps/backend/tests/test_slice_a_legacy_compatibility.py | retained RED regression, schemas 1..8, populated v7, historical policy, identity, strict adverse paths |
| apps/backend/tests/test_phase12_persistence.py | existing provider-verified recovery test now runs actual schema6/7/8 |
| apps/backend/tests/test_phase12_real_mongo.py | four populated actual-v7 no-rewrite cases and one actual-v7 uncertainty/no-replay case |
| apps/backend/tests/test_active_text_encoding.py | scoped tracked-source UTF-8 guard, five bad-sequence cases, valid Unicode and decoded API title |
| apps/frontend/e2e/zero-touch-exception.e2e.ts | exact rendered title replaces permissive regex in both Garden scenarios |
| docs/contracts/ZERO_TOUCH_AUTOMATION_POLICY.md | classified header em-dash correction only |

Task-owned planning/evidence paths: unchanged approved planner, this report, candidate identity JSON, and separately authored
POST_PHASE24_SLICE_A_MINI_GATE.md. The candidate JSON records every frozen path and SHA256.

API/type shape: no. Schema fields/version: no; legacy conversion behavior repaired. Connector: no. Configuration: no.
Business rules: no. Target/registry mapping: no. Auth/security policy: no. Architecture/owner/dependencies: no.
Provider classifications: no. Runtime behavior: populated v7 converts successfully in memory and seven corrupt punctuation
sites render intended Unicode. No broader refactor, cache change, dependency change or happy-path fixture change.

## Compatibility and adverse evidence

- Explicit schema1..8 successful reads retain IDs, revision and timestamps; no input mutation or collection write operation.
- Versions1/2 retain the documented LEGACY_PHASE13_DEFAULTS_V1 behavior. Versions3..8 keep synthetic frozen 0.81 IDP,
  27 percent UBO and old GoldTier values; Phase24C parameters remain absent. No current policy substitution.
- Version-specific absent onboarding/intelligence/recovery fields retain their historical defaults.
- Six populated actual-v7 scenarios compare complete domain aggregates and exact storage serialization except in-memory version:
  reconciliation history, pending confirmation, confirmed dispatch, ownership review, low-confidence review and identity repair.
- Mandatory ownership binding, exception digest and three levels of reconciliation fingerprint deletion reject.
- Across schemas1..8: missing binding, unknown nested metrics, cross-case automation and noncanonical UUID reject.
- Invalid/missing discriminators, forbidden Phase24C parameters in old versions, forbidden semantic-v2 values and forged target
  provider bindings reject. A genuine typed semantic-v2 tag is valid in v8 and rejected in v7.
- Existing full backend evidence covers CAS, insert-only/update-only, strict identity, deletion/no resurrection, terminal
  automation invariants, ledger order and no replay. No assertion or validation rule was loosened.

Fixture boundary: the reconciliation history fixture composes a resolved discrepancy through its owning reconciliation service
with retained paused automation. It certifies conversion of valid persisted evidence, not an end-to-end partial reconciliation
mutation journey. During fixture construction, the fully orchestrated alternative produced exception-decision metadata rejected
by current serialization. That separate existing behavior was not changed or diagnosed as part of Slice A and remains a later
bounded investigation; it is not evidence about the original four records.

## Encoding evidence

Classified before replacement: api_models.py lines818/939/982 used corrupt em-dash sequences; lines1900/1958/1959 used corrupt
middle-dot sequences. The current automation policy header had the same em-dash corruption. Only these seven lines changed.
Historical evidence/report typography was not rewritten.

The encoding RED identified exactly those seven paths/lines and rejected the decoded ownership API title. The guard checks
only tracked apps/backend/app, apps/frontend/src and the current automation policy contract. Strict UTF-8 decoding rejects
invalid bytes. The five demonstrated corrupt sequences are constructed from codepoints in tests; valid em dash, middle dot
and CJK text pass. Historical reports, protected paths, unrelated files and untracked content are not scanned.

Decoded API and configured Playwright both assert: Ownership and UBO \u2014 needs input.
Both clean and conflict Garden browser scenarios passed in separate task-owned lifecycles with the existing strict offline
synthetic Marketplace transport and zero external calls. The exact heading was also visually inspected in the synthetic screenshot.

## Verification on the final implementation content

Runtime executables reused from the normal checkout without using its configuration; imports and test code came from this worktree.
Python3.12.10, Node22.23.3, npm10.9.9. Offline npm ci used the unchanged lockfile; no dependency source/lockfile change.

| Check | Result |
|---|---|
| Required persistence RED | legacy validation passed; conversion failed at missing excluded ownership binding |
| Encoding RED | 2 failed / 6 passed; guard and decoded API title failed as expected |
| Initial focused persistence/reconciliation/encoding | 173 passed |
| Strengthened focused persistence/encoding run | 158 passed before final missing-discriminator test; final full run includes that final test |
| Full backend pytest, no cache, contained traceback | 1875 passed, 75 opt-in physical skips, 4 existing warnings; 379.98 seconds |
| Current nine-suite physical harness | 64 collected, 64 passed, zero skipped/failed/errors |
| Separate Phase24C physical guard suite | 11 passed |
| Focused new actual-v7 physical cases | 5 passed, before broader physical evidence |
| Browser clean Garden | 1 passed; exact rendered heading; external_calls=0 |
| Browser conflict Garden | 1 passed; exact rendered heading; external_calls=0 |
| Ruff apps/backend scripts tests, --no-cache | PASS |
| Strict mypy current backend, explicit backend config, --cache-dir nul | PASS: 115 source files |
| pip check | PASS |
| secrets scanner on tracked/nonignored task-owned paths | PASS |
| project-state and architecture checkers | PASS |
| dev_context/project-state/architecture/secrets unit bundle | 63 passed in 36.813 seconds on fresh narrow escalated run |
| git diff --check | PASS; original unchanged mixed line endings preserved |
| task-owned new-file whitespace/UTF-8 | checked before candidate freeze |

All 75 physical tests skipped in the ordinary backend run were executed separately: 64 harness plus 11 Phase24C.
The full backend warnings are existing Starlette deprecation and deliberately malformed conformance-fixture serialization warnings.

Operational attempts do not count as passing evidence: the first anchored browser selector selected no test; corrected tagged-title
selections passed. Initial physical fixture assertions failed on team scope and an intentionally absent public Search-history field;
test-only corrections were followed by clean focused and full physical runs. The first non-escalated governance unit run consumed
CPU without completing and was interrupted through its owned session; no pass was claimed. The narrow escalated verbose rerun passed
all63. Restricted temporary-fixture cleanup is only a hypothesis; no checker/source repair was made.

## Physical safety and original records

Only cached mongo:7 in task-owned container clm-slice-a-20261002-955534d3, bound to local port27027, no host volumes, no image pull.
Every physical database came from generate_ephemeral_mongo_database and was cleaned with cleanup_ephemeral_mongo_database,
which validates the allowlist and verifies absence. A separate server inventory after all coordinator tests found zero CLM databases.

Four stable v7 cases retain the complete stored document unchanged after fresh store initialization, store reads, fresh application
composition and GET. No provider calls (registry/IDP/ownership/target all zero), revision changes or version-only writes occurred.
The uncertainty case permits the existing deliberate startup recovery checkpoint write and proves retained IN_PROGRESS ledger,
confirmation, repeated RECOVERY_PENDING and zero provider/target replay. This is distinct from an ordinary read rewrite.

Original main checkout: untouched and clean. Original .env: never read. Original clm_poc: never connected to, started against,
read, edited, deleted, archived or migrated. Original four records: UNVERIFIED UNTIL USER VALIDATION.
The source defect is deterministically reproduced with synthetic evidence; attribution to those exact real records remains unverified.

## Independent handoff and stop

The candidate is frozen by POST_PHASE24_SLICE_A_CANDIDATE.json. The fresh reviewer must independently check A-M from the approval,
run focused execution/physical/browser evidence, and write only POST_PHASE24_SLICE_A_MINI_GATE.md. Any current in-scope P0/P1/P2
means FAIL. Coordinator must seek fresh review after any changed candidate; maximum two bounded remediation rounds.

Remediation rounds used before initial review: 0. Publication gate/pre_pr_check intentionally not run on this uncommitted handoff.
No current provider readiness or sponsor interoperability claim. After independent PASS, stop and wait for Slice B approval.

Manual original-data validation is available only after the owner integrates the accepted fix into the normal checkout.
The normal checkout currently still has the old source. Do not execute its startup command before that integration:

~~~powershell
Set-Location 'C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm'
.\scripts\start_demo_windows.bat
~~~

This manual startup uses normal configuration and may perform its existing recovery writes. The coordinator did not run it.
Next authorized action after acceptance: wait for the owner's Slice B approval; commit/integration/publication require separate authorization.
