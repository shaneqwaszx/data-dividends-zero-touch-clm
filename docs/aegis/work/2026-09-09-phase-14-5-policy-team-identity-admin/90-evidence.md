# EvidenceBundleFinal

## Baseline and safety

- Start and final branch/HEAD/origin/main/merge-base all equal the assigned baseline
  `aba264af3b4088a9a10fe682ee6fc0cb418d550d`; `HEAD..origin/main` is empty.
- Index remained empty. No stage, commit, amend, push, merge, rebase, reset, stash,
  clean, or branch switch was performed.
- `.env` was not opened. Shared `clm_poc` was neither inspected nor written.
- A first unscoped Python test command resolved the `app` package through ambient
  import state to the prohibited concurrent Phase 14 worktree. No implementation file
  there was opened, inspected, copied, or modified. Every later Python invocation used
  the explicit Phase 14.5 workspace backend path.

## Functional and regression evidence

- Focused administration/policy/case-access plus Phase 13 auth, Dashboard, and priority:
  135 passed.
- Runtime policy chain across document, ownership, reconciliation, CLM, and zero-touch:
  235 passed.
- Full backend: 919 passed, 13 skipped; three existing Pydantic serialization warnings
  in Phase 06 provider-conformance adversarial tests.
- Frontend: typecheck passed; 120 tests passed; production build passed.
- Contracts: 44 passed. Secret scanner units: 5 passed. Pre-PR helper units: 37 passed
  without executing `scripts/pre_pr_check.py`.
- Windows lifecycle: final fresh run 17 passed. The original regression was traced to
  the lifecycle harness injecting five bootstrap hashes after the application began
  requiring six; the harness now injects the HR hash. Two transient reset probes in an
  intermediate long run passed on focused rerun and the final full run.
- Ruff lint passed; mypy passed for 88 source files; pip check passed; `git diff --check`
  passed.
- Changed Python files pass Ruff format. The full repository check remains red on 36
  pre-existing unrelated files, which were intentionally not reformatted.
- Physical Phase 14.5 Mongo test skipped because `PHASE12_MONGO_URI` is not configured.

## Security evidence

- Repository-backed authentication, security-version invalidation, explicit session
  revocation, HR case denial, policy/admin capability enforcement, mass-assignment
  rejection, safe audit metadata, and non-serialization of credential hashes are
  covered by the focused and full suites.
- Targeted changed-file secret scanning emitted seven syntactic findings: typed
  password fields, variable forwarding, and test-only credentials. Values were
  suppressed; manual line review confirmed no embedded secret or credential hash.
- No dependency manifest or lockfile changed.

## Evidence boundary

- Confidence: B. Direct target and broad regression evidence are green.
- Uncovered: physical Mongo behavior was not executed locally; independent quality gate
  and later Phase 14 integration are outside this implementation-owner pass.

## Independent-QG remediation evidence — 2026-09-11

- P145-QG-001: repository-owned atomic authority mutation; barrier-synchronized memory
  cross-demotion left exactly one HR. Mongo shares one process-local administration
  lock across HR count and target CAS. Self-demotion and session revocation pass.
- P145-QG-002: backend-derived `normalized_client_scope_label`; memory create/update
  collision coverage; unique Mongo index and bounded duplicate mapping; Alpha/Beta
  stable.
- P145-QG-003: 22 production policy workflow cases cover custom edit, accessible single
  and whole reset confirmation, zero-mutation cancel/Escape/open, single-flight confirm,
  409 refetch without retry, server-state synchronization, and read-only roles. The
  focused file has 26 total passing tests including four existing admin/filter cases.
- P145-QG-004: 22 focused validator/injection tests pass; hostile scalar/list values
  reject and documented normal plain text accepts; runtime remains limited to the two
  fixed policy IDs.
- P145-QG-005: current evidence uses `test_phase11_reconciliation.py`; the canonical
  five-file runtime command passed 235 tests. The stale planner path is preserved as
  historical task input and explicitly superseded in the execution report.
- Broader proof: full backend 955 passed/13 skipped/3 known warnings; full frontend 142
  passed; contracts 44, Windows lifecycle 17, secret units 5, pre-PR helper units 37;
  Ruff, 11-file Ruff format, mypy (88 source files), pip check, typecheck, build, and
  diff check passed.
- Physical Mongo: skipped because `PHASE12_MONGO_URI` is not configured. No `.env` or
  shared database was accessed.
