# Phase 06 POC Regression Check — Final Closure Remediation

**Check date:** 2026-08-15

**Result:** PASS

**Scope:** bounded implementation-side Phase 06 regression evidence; not a new independent quality gate

## Final closure scenarios

| Scenario | Verified result | Downstream behavior |
|---|---|---|
| ACRA control matrix | 117/117 combinations across 13 modeled fields × LF/CR/TAB × leading/trailing/embedded return `TECHNICAL_FAILURE / ACRA_RESPONSE_INVALID` | no canonical entity, document, ownership, readiness, target call, or intervention |
| Exact former bypass | trailing LF in legal name fails at `REGISTRY` | target calls `0/0/0/0`; interventions `0` |
| Raw provider result | fresh strict reconstruction rejects malformed original string | no downstream work |
| Ordinary typed DTO | malformed construction is rejected | no downstream work |
| Mutated typed DTO | service-side fresh reconstruction rejects post-construction mutation | no downstream work |
| `model_construct` DTO | service-side fresh reconstruction rejects bypass-created instance | no downstream work |
| Valid surrounding spaces | normalized only after original-value validation | `COMPLETED / MOCK_GOLDTIER_SUBMITTED`; zero interventions; exact target sequence once |
| Equal document timestamps | repository and blocker order follows first-save sequence in 100/100 journeys | all blockers retained; zero target calls |
| Former flaky multi-conflict test | stable in 100/100 repetitions | same blocker order and semantics |

The affected ACRA field matrix is UEN; entity/legal name; entity status; entity type;
top-level country code; source environment; source endpoint; and address block, street,
unit, building name, postal code, and country code. No city/locality field exists in the
current provider DTO.

## Preserved Phase 06 behavior

| Scenario | Verified result |
|---|---|
| Straight through | `COMPLETED / MOCK_GOLDTIER_SUBMITTED`; `human_interventions_after_start = 0`; `search, shell, policy, amend` once |
| Document source conflict | `WAITING_FOR_REVIEW`; current `KEEP_REGISTRY_VALUE` closes only that conflict and automatically resumes when safe |
| Low confidence | remains `WAITING_FOR_REVIEW` with no unconfirmed resolution action and zero target calls |
| RECOVERY_PENDING | repeated finalization fault remains nonterminal; later typed Phase 05 reconciliation does not replay target work |
| Requested UEN mismatch | `ACRA_RESPONSE_IDENTITY_MISMATCH`; downstream work stopped |
| Unsafe provenance | HTTP, userinfo, query, and fragment forms fail before canonical mapping |
| Mock/SANDBOX adapters | environment labels and not-found behavior preserved |

P06-QG-001 stale evidence, 002 state/input safety, 003 unexpected-failure finality,
004 blocker-specific resolution, 005 semantic all-document evaluation, 006
RECOVERY_PENDING, 007 demo fail-closed, 008 stable provider binding, 010 frontend
polling, 011 frontend navigation, and 012 truthful labels remain green. Historical
Phase 01–05 scenarios also remain green; Phase 03 manual review behavior was not
rewritten.

## Global invariants

- Required document and ownership blockers stop all target calls.
- All case-owned documents are evaluated and retained in deterministic journey order.
- Only target search `NO_MATCH` permits shell creation.
- Technical failures cannot become reviewer work or false completion.
- Exception authority remains case/exception/version/fingerprint bound.
- Completion remains Mock-only and never implies Ready-for-Approval.
- Provider bindings, repositories, insertion sequences, locks, and replay evidence are
  process-local; no durable restart or exactly-once claim is made.

## Verification evidence

- Backend: 485 passed.
- Phase 01–06 focused: 28 / 81 / 59 / 77 / 61 / 179 passed.
- P06-QG-009-R2 focused: 122 passed; P06-QG-013 focused: 2 passed with 100/100 + 100/100 internal repetitions.
- Core straight-through/HITL/low-confidence/recovery group: 5 passed.
- Contract tests: 41 passed; repository unittest discovery: 51 passed.
- Frontend: typecheck passed, 30 tests passed, production build passed; dependency tree completed.
- Ruff, strict mypy, `pip check`, five secret tests, and standalone secret scan passed.
- GoldTier validator tests passed; classification remains 19 valid, 19 quarantined, and 48 not validated; expected fail-on-invalid exit was 1.
- Tracked, cached, and explicit untracked-file whitespace checks passed.

The canonical regression catalogue was evolved only for the two implemented and
verified final-closure scenarios. This report records the pre-re-gate position; the
later `PHASE_06_QUALITY_GATE.md` final closure **PASS** dated 2026-08-15 supersedes its
historical re-gate requirement.
