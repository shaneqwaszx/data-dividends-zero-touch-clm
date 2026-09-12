# Phase 14.5 Re-Quality Gate

## Result

**BLOCKED — PHASE 14.5 PRE-INTEGRATION IMPLEMENTATION ACCEPTED; PHYSICAL MONGO PROOF AND PHASE 14 INTEGRATION REMAIN OUTSTANDING.**

This is an independent re-review of the claimed remediation on the required Phase 14.5 worktree. No implementation, test, existing report, or ordinary documentation was changed by this review.

## Baseline and worktree isolation

| Check | Observed result |
|---|---|
| Branch | `phase/14-5-policy-team-admin` |
| HEAD | `aba264af3b4088a9a10fe682ee6fc0cb418d550d` |
| `origin/main` after `git fetch origin` | `aba264af3b4088a9a10fe682ee6fc0cb418d550d` |
| Merge base | `aba264af3b4088a9a10fe682ee6fc0cb418d550d` |
| `HEAD..origin/main` | empty |
| Phase 14 on main | NO |
| Worktree import isolation | PASS — `app`, `app.main`, `app.services.authentication`, and `app.services.authorization` resolve beneath this Phase 14.5 worktree only |

The tree contains the expected unstaged Phase 14.5 implementation delta; no paths were staged. `git diff --check` passed (Git emitted only CRLF advisory warnings). The re-QG report is the only review-created path.

## Remediation findings

### P145-QG-001 — CLOSED: atomic last-HR invariant

`MemoryProfileRepository.mutate_authority` holds the repository-wide lock across target/version load, self-demotion decision, HR population decision, authority candidate construction (including `security_version` and audit event), and record persistence. `MongoProfileRepository.mutate_authority` holds one `MongoAdminStore` process-local lock across target load, HR count, candidate construction, and the expected-version `replace_one` CAS. This meets the stated supported single-process POC boundary; it does not claim distributed IAM semantics.

The barrier-based independent adversarial selection passed: two HR accounts concurrently attempted cross-demotion; exactly one succeeds, one safely rejects, the final HR population is one, and the remaining account is an HR. The same focused selection also passed self-demotion protection and authority-change session revocation. Authentication reloads the profile and rejects a session whose stored security version no longer matches, so the old session receives 401 and a new login obtains current authority.

### P145-QG-002 — CLOSED: normalized coverage-label uniqueness

`normalized_client_scope_label` is constructed in the administration service, excluded from the browser team request/response surface, and tested as a mass-assignment rejection. Memory repository uniqueness compares backend-derived normalized display name and coverage label. The collision tests cover `Gamma Coverage` versus whitespace/case-normalized alternatives and the existing Unicode-equivalent normalization coverage.

Mongo startup strictly decodes team records before creating indexes. It declares the unique `normalized_client_scope_label_unique` index, stores the field through the strict `TeamRecord`, and maps `DuplicateKeyError` to the bounded `AdministrationConflictError`, not driver detail. `TEAM_A` and `TEAM_B` remain canonical identifiers and seed as Alpha and Beta.

### P145-QG-003 — CLOSED: policy administration UI

Production `PolicyRules` permits RM/Director mutation of backend-permitted runtime and showcase rules, while Client Onboarder and HR are read-only. Custom showcase rules remain labelled display-only/non-runtime.

Single reset and reset-all both open an accessible `alertdialog`. Opening, Cancel, and Escape send no mutation; confirmation is guarded by one in-flight ref and sends only one mutation. The reset-all explanation explicitly identifies project/POC defaults, preserved custom showcase rules, and immutable future-case snapshot semantics. A 409 edit or reset fetches the authoritative catalogue once, does not retry the stale mutation, exposes a bounded conflict message, and synchronizes local `PolicyRow` fields from changed authoritative props.

### P145-QG-004 — CLOSED: showcase string validation

The canonical validator applies the claimed grammar `^[A-Za-z0-9][A-Za-z0-9 _./:+%-]{0,127}$` plus case-insensitive code-like-prefix rejection to user-authored string and string-list showcase values. The focused hostile-input tests reject the required import/eval/exec, script, JavaScript, comparison/template, lambda, command, pipe, logical-and, and semicolon forms; normal display values including `Enhanced Review`, `MANUAL_REVIEW`, `Level-2`, `SG`, `ACRA`, `25%`, `Risk: Medium`, and `application/pdf` remain accepted.

Source review found no `eval(` or `exec(` runtime path in backend application policy code. Only the two approved IDs are consumed to produce immutable case runtime snapshots; custom rules remain `DISPLAY_SHOWCASE_ONLY`.

### P145-QG-005 — CLOSED: runtime-policy regression evidence

The current durable Phase 14.5 execution evidence and Aegis evidence name `apps/backend/tests/test_phase11_reconciliation.py`. The obsolete `test_reconciliation.py` reference is confined to the historical planner and preceding historical QG, where it is explicitly superseded; it is not presented as the current executable path. The corrected five-file runtime-policy command passed.

## Executed verification

| Check | Exact result |
|---|---|
| Focused backend | `171 passed in 28.54s` |
| Last-HR adversarial selection | `4 passed, 14 deselected in 1.38s` |
| Policy injection/validator selection | `27 passed, 11 deselected in 1.66s` |
| Runtime-policy regression | `235 passed in 21.54s` |
| Full backend | `955 passed, 13 skipped, 3 warnings in 83.42s` — existing Phase 06 malformed-provider Pydantic serializer warnings |
| Ruff | `All checks passed!` |
| Ruff format | `32 files already formatted` for explicit added/modified Phase 14.5 Python paths |
| Mypy | `Success: no issues found in 88 source files` |
| Pip check | `No broken requirements found` |
| Focused frontend | `1 file, 26 tests passed` |
| Frontend typecheck | PASS |
| Full frontend | `5 files, 142 tests passed` |
| Frontend production build | PASS — 49 modules transformed |
| Contract suite | `Ran 44 tests ... OK` |
| Windows lifecycle | `Ran 17 tests in 209.402s ... OK` |
| Secret-scanner unit suite | `Ran 5 tests ... OK` |
| Pre-PR helper unit suite | `Ran 37 tests in 34.761s ... OK` |
| GoldTier examples | `NOT VALIDATED: sponsor OpenAPI/example archives are absent; no private file was read.` |

The initial sandboxed frontend and isolated Git-fixture test attempts were blocked by process permission (`esbuild` spawn EPERM / isolated Git temp fixture access). The identical commands were rerun with the required local process permission and passed. `scripts/pre_pr_check.py` was not run, as directed.

## Security review

No new Critical, High, Medium, or Low implementation finding was identified. Focused source and execution review confirms: route authorization remains central; unsafe new admin/policy routes remain behind session CSRF and Origin/Referer controls; HR lacks case scope and non-HR lacks administration; dynamic team filtering remains server-authorized; profile API projections omit password hashes, normalized keys, and audit events; authority mutation increments security version and invalidates stale sessions; Mongo duplicate errors are bounded; and custom policy values have no evaluation path. Full Phase 13 authentication/RBAC regression coverage passed.

No real ACRA, PingFed, GoldTier, or private sponsor artefact was accessed. The Phase 14.5 implementation remains explicit Mock/POC behavior and does not claim sponsor-approved production IAM, policy, or integration semantics.

## Physical Mongo

`PHASE12_MONGO_URI` was checked only for presence and was absent; its value was neither opened nor printed. Therefore physical Mongo is **SKIPPED**. Static Mongo review is satisfactory, but physical proof of the coverage-label index, bootstrap hash persistence/no-overwrite, Gamma isolation, catalogue/audit/snapshot persistence, restart, and allowlisted database cleanup remains outstanding.

## Data-safety receipt

| Item | Result |
|---|---|
| `.env` accessed | NO |
| Shared `clm_poc` inspected | NO |
| Shared `clm_poc` written | NO |
| Phase 14 worktree accessed | NO |
| Protected/private artefacts accessed | NO |
| Implementation modified | NO |
| Files staged | NO |
| Committed/amended/pushed/merged/rebased/reset/stashed/cleaned | NO |
| Branch switched | NO |

## Readiness

- Pre-integration implementation accepted: **YES**.
- Ready for owner checkpoint commit: **YES**.
- Ready for Phase 14 integration: **NO**.
- Ready for PR: **NO**.

### Remaining blockers

1. Configure `PHASE12_MONGO_URI` and run only the allowlisted generated Phase 14.5 physical Mongo suite, including cleanup and final absence verification.
2. Phase 14 is not yet accepted on `origin/main`. After it is, perform an explicitly authorized merge/integration pass and a fresh post-integration quality gate; do not rebase or claim PR readiness before that work.
