# Phase 13 Evidence Draft

## Baseline

- `git status --short`: expected untracked planner and protected unrelated filename;
  pytest-cache permission warnings only.
- Branch/HEAD/origin-main/merge-base: exact expected branch and
  `36d0247befce04bbed85e3dced9f9c1c2b617855` for all SHAs.

Terminal implementation and verification evidence will be appended after each batch.

## Batches 1-4 focused evidence

- `python -m pytest tests/test_phase13_auth_rbac.py -k "login or session or logout or credential"`:
  8 passed.
- `python -m ruff check ...` over Batch 1 files: passed after two mechanical lint fixes.
- `python -m mypy app`: passed across 76 source files after Batch 1.
- `python -m pytest tests/test_phase13_auth_rbac.py`: 18 passed after global auth/CSRF,
  route classification, creation-team, spoofing, and IDOR coverage.
- `python -m pytest tests/test_phase13_auth_rbac.py tests/test_phase13_priority.py
  tests/test_phase12_persistence.py`: 54 passed after schema-v2, strict v1 compatibility,
  team immutability, priority, ordering, and memory/Mongo-adapter coverage.
- `python -m mypy app`: passed across 78 source files after Batches 2-4.

## Batches 5-8 and final evidence

- Focused auth/RBAC/priority/Phase 12/demo suite: 58 passed.
- Full backend suite from `apps/backend`: 802 passed, 12 skipped, three pre-existing
  malformed-provider Pydantic serializer warnings.
- Frontend: typecheck passed; 102 tests passed; production build passed; dependency tree
  command exited zero with optional-dependency notices only.
- Contract suite: 44 passed. Phase 07 delivery assets: 4 passed.
- Windows demo lifecycle: 17 passed after the harness provisioned process-random hashes
  and used login/cookie/CSRF for protected API calls.
- POC regression selection: 401 passed before the Phase 13 catalogue entry was added.
- Ruff passed; mypy passed across 78 source files; `pip check` passed.
- Secret-check unit suite: 5 passed. Repository secret scan passed.
- Pre-PR-check unit suite: 37 passed with required Windows permissions.
- GoldTier fixture validation retained `VALID=19`, `INVALID_QUARANTINED=19`, and
  `NOT_VALIDATED=48`.
- `git diff --check`: passed.
- Phase 12/13 genuine-Mongo modules: 12 skipped locally because no Mongo URI/service was
  configured. The existing Mongo 7 CI job now runs both modules; local PASS is not
  claimed.

## Security review effect

Review identified a same-profile concurrent-login race in the session dictionaries. A
focused regression reproduced multiple active sessions; an `RLock` around purge,
rotation, capacity, insert, authentication, logout, and count operations reduced the
result to exactly one active session. No unresolved critical/high/medium finding remains
inside the POC boundary.

## Completion boundary

The implementation report is `.ai-pipeline/reports/PHASE_13_EXECUTION.md`. The
independent Quality Gate, genuine Mongo CI result, latest-main integration check, and
clean-tree `scripts/pre_pr_check.py` remain separate follow-on gates.
