# Measurement-driven performance program

Outcome: seven sequential internal gates in one session, beginning at exact main
198341b059ebf500252ce93d72eb099d2585c60b. Local checkpoint commits only after each
independent PASS; no push, PR, merge or worktree cleanup.

Branch: feat/performance-computational-throughput-optimization.
Worktree: C:/Users/shane/.codex-clean2/worktrees/performance-computational-optimization/data-dividends-zero-touch-clm.
Coordinator owns all implementation/Git mutations. Reviewers are independent and write
only their assigned reports while implementation is frozen.

## Scope and sequence

1. Gate 1: reproducible synthetic control group, separate memory/Mongo lanes, >=20
   measured repetitions, separate warmup/profile, correctness and operation assertions.
2. Gate 2: retain only measured repeated-work reductions within existing owners.
3. Gate 3: independent persistence profiling; preserve strict schema10/legacy1..9/CAS.
4. Gate 4: dependency/state map; concurrency only with independence/resource proof.
5. Gate 5: measure browser/API requests/projection first; preserve scoped cache lifecycle.
6. Gate 6: local synthetic concurrency1/5/10,20 only if stable; recovery recheck.
7. Gate 7: identical cumulative benchmark/regression and fresh independent final QG.

Per gate: measure -> causal diagnosis -> smallest justified delta -> focused/affected
regression -> identical remeasurement -> independent review -> checkpoint only on PASS.
No empty commits or unmeasured optimization. Failed experiments are removed.

## Owners and invariants

Existing orchestration, registry coordinator/cache, document/IDP, reconciliation,
Decimal ownership, CLM and target ledger, repository adapters, API projection and
frontend auth/query owners remain authoritative. Ordered target mutations/no replay,
immutable intent/confirmation/currentness, in-lock authorization, scope and safe404,
strict decode/CAS/create/update/deletion, exact Decimal results and provider labels
remain unchanged. No new major owner/dependency without explicit authority.

Gate1 is CI_TOOLING/documentation. Later prospective classes are BACKEND_DOMAIN,
BACKEND_API, PERSISTENCE, FRONTEND_STATE_CACHE; actual retained deltas determine checks.

## Evidence and resource boundary

Fresh source baseline is the exact required main. Owner manual observation is functional
smoke only and belongs to Lane C; no performance number borrows that evidence.
Lane A uses deterministic Mock/local and offline fake transport only. Lane B uses the
new task-owned mongo:7 container at loopback port27861, memory1GiB/cpus2 and freshly
generated allowlisted databases. Never read/copy .env or connect to clm_poc; never make
external provider calls. Raw timing/profile samples stay in ignored
.runtime/performance-optimization; tracked reports contain bounded sanitized aggregates.

Observed runtime: Windows, Python3.12.10, Node22.23.3, npm10.9.9, PyMongo4.15.1,
Pydantic2.13.5, FastAPI0.141.1, pytest8.4.2, Ruff0.16.2, mypy1.20.2, psutil7.0.0.
Docker29.8.1 was started; task container has no host data volume. Native extraction
and configured browser/lifecycle paths must be verified before their acceptance claim.
Tools: local exec, managed worktree lifecycle, collaboration reviewers, browser tools.
Worktree exec needs sandbox escalation; accepted fetch/status/branch/container operations
are recorded, and sandbox-denied status was rerun successfully outside the sandbox.

## Stop / final handoff

Stop dependent work for baseline drift, unavailable reproducible environment, required
real access/shared DB, correctness/security weakening, missing sponsor/architecture
authority, repeated P0/P1, or no meaningful safe optimization. Missing evidence is
BLOCKED, never PASS. Final report identifies source/tested/reviewed content separately,
all gates/checkpoints/deltas and limitations. Owner publication review requires exact
fresh independent PASS; never create publication readiness from self-review.
