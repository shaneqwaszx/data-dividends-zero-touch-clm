# Phase 14 Physical Verifier Re-Quality Gate

## Executive Result

**RESULT: PASS.**

This intentionally narrow independent gate assessed only `P14-FRQG-001`.
The repaired verifier correctly reflects the current production upload, durable
unrelated-record preservation, and Mongo revision/CAS contracts. The owner subsequently
ran the accepted opt-in physical module against an explicitly approved Mongo Atlas URI:
`1 passed in 82.37s`. Its paired structural/safety run passed twice (`14 passed in
0.58s`; repeat `14 passed in 0.60s`). The physical Mongo proof is therefore PASS.

`P14-QG-001`, `P14-QG-002`, and `P14-QG-003` were not reopened.

## Phase Acceptance Checklist

| Requirement | Result | Direct evidence |
| --- | --- | --- |
| Upload contract | PASS | Production demo route reads raw `Request` bytes, obtains the display name from `X-Document-Name`, and the verifier posts `content=DOCUMENT`, `Content-Type: text/plain`, `X-Document-Name: evidence.txt`, and session CSRF header through `RawTestClient`. |
| Unrelated durable record preservation | PASS | Verifier creates distinct target and unrelated cases, deep-copies the unrelated raw Mongo envelope before target deletion, verifies target absence and unrelated application access after deletion, then compares the unrelated raw envelope exactly. |
| Revision/CAS conflict | PASS | Verifier captures R1, invokes the production priority PATCH to establish R2, supplies R1 to `MongoCaseStore.delete`, expects `PersistenceConflictError`, verifies target remains at R2, and then uses the authorized DELETE route. |
| Generated database isolation and cleanup | PASS (structural) | The verifier generates `clm_p14_<24 lowercase hex>` through the p14 generator, cleanup only accepts the allowlisted physical-test pattern, rejects unsafe names, and drops then verifies generated database absence in `finally`. |
| Isolated physical Mongo execution | PASS | Owner-executed accepted physical module: `1 passed in 82.37s`; no `MongoCleanupFailure` occurred. |

## Contract and Integration Findings

### Upload route and browser boundary

The production demo route is `POST
/api/demo/clm/zero-touch/cases/{case_id}/intake/documents`. It passes the actual
request to the shared intake handler, which validates the `X-Document-Name`-derived
display name and current `Content-Type`, then reads bounded raw request bytes. The
current `.txt` contract accepts `text/plain`; the verifier's `evidence.txt` uses that
exact type. It does not use multipart or call an application service directly.

The test's `RawTestClient` is FastAPI's real TestClient before the test-suite's
auto-auth client substitution. It logs in through `/api/auth/login`, retains the
session cookie, and explicitly passes `X-CSRF-Token`. The production `/api` middleware
requires an authenticated session and validates Origin/Referer trust plus session-bound
CSRF for unsafe requests. Thus the verifier does not bypass route middleware.

### Durable deletion and CAS boundary

`MongoCaseStore.delete(case_id, expected_revision=...)` deletes only when both `_id`
and `revision` match and raises `PersistenceConflictError` when `deleted_count != 1`.
`MongoCaseDeletionRepository` reads the current snapshot under its store lock and
passes that revision into the same production delete contract. `CaseDeletionService`
maps persistence conflict/unavailability to safe application-level exceptions rather
than exposing Mongo driver detail.

No contract or integration defect was reproduced.

## Tester and Adversarial Findings

| Command | Exact result |
| --- | --- |
| `python -m pytest apps/backend/tests/test_phase14_real_mongo_structure.py -p no:cacheprovider --tb=short` | `6 passed in 0.81s` |
| `python -m pytest apps/backend/tests/test_phase13_mongo_test_safety.py -p no:cacheprovider --tb=short` | `8 passed in 0.37s` |
| `python -m pytest apps/backend/tests/test_phase14_real_mongo.py -p no:cacheprovider --tb=short` | `1 skipped in 0.70s` |
| `python -m pytest apps/backend/tests/test_phase14_case_management_performance.py -p no:cacheprovider --tb=short` | `17 passed in 1.59s` |
| `python -m ruff check apps/backend/tests/test_phase14_real_mongo.py apps/backend/tests/test_phase14_real_mongo_structure.py` | `All checks passed!` |
| `python -m ruff format --check apps/backend/tests/test_phase14_real_mongo.py apps/backend/tests/test_phase14_real_mongo_structure.py` | `2 files already formatted` |
| Owner: `python -m pytest tests/test_phase14_real_mongo.py -p no:cacheprovider --tb=short -v` | `1 passed in 82.37s` |
| Owner: structural/safety paired command | `14 passed in 0.58s`; repeat `14 passed in 0.60s` |

The Mongo-free structural suite independently guards raw-body/filename/CSRF assembly,
unrelated-case envelope selection, stale expected-revision propagation, and rejection
of unsafe database names. The existing Mongo safety suite additionally verifies
allowlisted generated names, shared/arbitrary-name rejection, retried cleanup with
final absence verification, and redaction of driver connection detail from cleanup
errors. The earlier local skip remains a historical unavailable-environment receipt only.
The subsequently supplied owner evidence establishes the physical execution PASS, using
the independently reviewed generated-database restriction
`^clm_p14_[0-9a-f]{24}$`; no `MongoCleanupFailure` occurred.

## Code and Architecture Review

The verifier's target and unrelated case IDs are separate values throughout the
physical path. It captures `collection.find_one({"_id": unrelated_case_id})` before
target deletion, then reads and compares that same unrelated ID after target absence
is verified. It also proves the ordinary authorized read of the unrelated case returns
200, rather than relying on a collection count.

The stale revision proof is correctly repository-level because the deletion service
intentionally re-reads the current revision under the lifecycle lock. R1 and R2 are
genuinely distinct: the test reads R1, performs production HTTP priority mutation,
then reads and asserts a greater R2. The direct store call deliberately supplies stale
R1 and expects a typed conflict; it cannot silently report deletion because the test
subsequently reads the target at R2. The normal DELETE then supplies the live revision
through the production deletion repository and removes the target envelope.

No Critical, High, Medium, or Low finding was reproduced for `P14-FRQG-001`.

## Security Review

The verifier does not use a multipart upload or a helper that bypasses the HTTP/auth
boundary. Its physical database name is generated only for p14 and cleanup is bounded
by the physical-test allowlist; the shared `clm_poc` database was not accessed. The
physical test's settings pass `_env_file=None`, and ordinary test configuration also
constructs settings without the repository dotenv file.

No `.env`, shared `clm_poc`, Phase 14.5 worktree, or protected artefact was accessed by
this gate. No secret, URI, database host, or credential value was printed. Historical
ambient-database and prior `.env` incident receipts remain historical only; this update
did not investigate them or treat them as new blockers.

## Required Fixes

None for `P14-FRQG-001`.

The required physical execution evidence is complete. PR readiness remains false until
an owner-controlled commit exists and `python scripts/pre_pr_check.py` has been run on
the actual clean tree.

## Readiness

- `IMPLEMENTATION ACCEPTED = YES`
- `READY FOR OWNER-CONTROLLED COMMIT = YES`
- `READY FOR PR = NO`
- `READY FOR MERGE = NO`

The isolated physical-Mongo proof is complete. No conclusion about live ACRA
verification or real GoldTier integration is changed by this narrow verifier gate.

## Git Status

- Branch: `phase/14-case-management-performance`
- HEAD: `aba264af3b4088a9a10fe682ee6fc0cb418d550d`
- origin/main: `aba264af3b4088a9a10fe682ee6fc0cb418d550d`
- Merge base: `aba264af3b4088a9a10fe682ee6fc0cb418d550d`
- Main drift: none (`git log HEAD..origin/main` was empty).
- Staged paths: none.
- The supplied physical verifier test files were already untracked when this gate
  inspected them; this gate did not create, edit, stage, or otherwise modify them.
- This report is the sole file modified by this evidence update. Existing tracked Phase
  14 working-tree changes were preserved.

No implementation fix, test edit, prior-report edit, commit, amendment, push, merge,
rebase, reset, stash, clean, or branch switch occurred.
