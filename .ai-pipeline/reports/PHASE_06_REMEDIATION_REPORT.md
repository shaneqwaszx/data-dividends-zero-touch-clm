# Phase 06 Quality-Gate Remediation Report

**Final closure remediation date:** 2026-08-15

**Branch:** `phase/06-zero-touch-orchestration`

**Scope:** P06-QG-009-R2 and P06-QG-013 only, while preserving the eleven previously closed Phase 06 findings

**Implementation result:** COMPLETE; ready for a final independent closure gate, not Phase 07

## Preserved gate history

The 2026-08-12 remediation closed or narrowed the original Phase 06 findings, but the
final independent gate remained `FAIL`. That gate proved that P06-QG-009-R2 was still
open because ACRA source text was stripped before prohibited Unicode controls were
inspected, and identified P06-QG-013 because equal `created_at` timestamps fell back to
random UUID ordering. This report records the bounded follow-up. It does not replace,
erase, or convert the independent `FAIL` into a `PASS`.

## P06-QG-009-R2 — original-value ACRA validation

The former order was effectively:

`raw provider string -> strip -> Unicode category check -> field validation`

The implemented order is:

`raw provider string -> reject any character whose Unicode category starts with C -> strip permitted ordinary surrounding whitespace -> length/grammar/domain validation -> trusted DTO`

The shared `_normalize_source_text` now applies this order to UEN, legal/entity name,
entity status, entity type, top-level country code, source environment, source endpoint,
and every modeled nested address string: block, street, unit, building name, postal
code, and address country code. City/locality is not present in the current ACRA DTO.
Optional text delegates to the same raw-value validator before blank-to-`None`
normalization. The rule is category-based rather than a newline/tab special case.

Permanent full-orchestrator tests cover all 13 modeled paths with leading, trailing,
and embedded LF, CR, and TAB: 117/117 permutations fail safely. The exact former
bypass, `entity_name = "MERLION CIRCULAR LABS PTE. LTD.\n"`, now produces
`TECHNICAL_FAILURE / ACRA_RESPONSE_INVALID` at `REGISTRY`: canonical entity absent,
no document record, no ownership, no readiness event, target calls
`search/shell/policy/amend = 0/0/0/0`, and zero human interventions.

Provider-form evidence is explicit:

- an ordinary raw provider mapping is freshly reconstructed and rejected;
- ordinary typed construction rejects the malformed value at construction;
- a valid typed DTO mutated after construction is freshly reconstructed and rejected;
- a `model_construct` bypass DTO is freshly reconstructed and rejected.

Valid surrounding ASCII spaces remain intentionally normalized. A full local
SANDBOX-shaped journey with spaces around all modeled text fields completes as
`COMPLETED / MOCK_GOLDTIER_SUBMITTED`, with zero interventions and exactly one
`search, shell, policy, amend` sequence. Requested-UEN identity binding,
`ACRA_RESPONSE_IDENTITY_MISMATCH`, query-free HTTPS provenance, no userinfo/query/
fragment, not-found behavior, Mock ACRA, and SANDBOX-shaped adapter behavior remain
covered.

## P06-QG-013 — deterministic document journey order

`InMemoryDocumentProcessingRepository` now assigns a process-local monotonically
increasing insertion sequence on the first save of each document. Subsequent saves
retain the original sequence. Repository reads are protected by a lock and
`list_for_case` sorts only by this sequence. UUID remains a globally unique identity
but no longer influences blocker presentation order; equal timestamps are harmless.

A permanent fixed-clock regression creates two reviewed conflicts with identical
`created_at` values across 100 journeys. Repository listing and emitted blocker order
follow first/second insertion in 100/100 runs, with every blocker retained and zero
target calls. The formerly flaky
`test_P06_QG_005_MULTIPLE_REVIEWED_CONFLICTS_ARE_RETAINED` also passed 100/100
programmatic repetitions. Blocker semantics, KEEP_REGISTRY_VALUE behavior, and
low-confidence safety were not changed.

## Historical closure preservation

P06-QG-001 stale evidence, 002 state/input safety, 003 unexpected-failure finality,
004 blocker-specific resolution, 005 all-document semantics, 006 RECOVERY_PENDING,
007 demo fail-closed, 008 provider binding, 010 frontend polling, 011 frontend
navigation, and 012 truthful labels all remain green in the full Phase 06 suite.

## Verification

- Backend: 485 passed.
- Phase 01–06 focused: 28 / 81 / 59 / 77 / 61 / 179 passed.
- P06-QG-009-R2 focused: 122 passed, including the 117-case field/control/position matrix and raw/typed/mutated/bypass plus valid-normalization cases.
- P06-QG-013 focused: 2 passed; their internal evidence is 100/100 equal-timestamp journeys and 100/100 repetitions of the formerly flaky conflict test.
- Core straight-through, exception/resume, low-confidence, finalization recovery, and RECOVERY_PENDING group: 5 passed.
- Contract tests: 41 passed; repository unittest discovery: 51 passed.
- Ruff, strict mypy over 53 source files, `pip check`, five secret-scanner tests, and the standalone secret scan passed.
- GoldTier validator tests passed. Classification remains 19 valid, 19 intentionally quarantined, and 48 not validated; `--fail-on-invalid` returned the expected exit 1.
- Frontend typecheck passed; 30 tests passed; production build passed; `npm ls --all` completed with only platform/feature optional dependencies unmet.
- Tracked, cached, and explicit untracked-file whitespace checks passed after replacing two Markdown hard-break spaces in the independent gate header with blank-line formatting; the gate content and `FAIL` are unchanged.

No sponsor policy, live connector, hierarchy behavior, approval behavior, or new phase
was introduced. A final independent closure gate is the next step.
