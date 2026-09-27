# ACRA API Marketplace Mock Runtime — Checkpoint

## Completed slices

1. Mandatory Git and ignored-`.env` pre-flight passed at the assigned base.
2. Supplied Postman exports were classified and reconciled outside the repository.
3. One bounded token response was observed and strictly reconstructed without retaining
   credential or token values.
4. A fixed-host, verified-TLS, no-redirect token client and thread-safe memory-only cache
   were implemented.
5. A distinct official Mock connector now performs only entity-basic and shareholder
   GET operations with raw `token` authentication and no fallback.
6. Strict identity binding, shareholder source evidence, response bounds, and explicit
   empty semantics are covered by fake-transport tests. No percentage is derived.
7. The authorized Mock smoke and real application check completed with sanitized output.
8. Current contracts, readiness state, Q-012, decision D-054, configuration guidance,
   and the accepted regression catalogue were updated.
9. Focused, backend, contract, static, governance, evidence, secret, and application
   checks were executed.
10. The first independent Quality Gate returned `FAIL`: the dedicated receipt validator
    did not bind outcome fields as one coherent record, HTTP 404 was interpreted as
    absence without provider authority, and the exact tree lacked a green backend run.
11. Remediation now binds all successful receipt outcomes to HTTP 200, schema result,
    and identity equality; binds failure to failed schema validation; treats HTTP 404 as
    malformed/unresolved; and isolates ordinary tests from the selected local `.env`
    provider mode.
12. The first socket-owner repair passed locally but the second independent gate
    reproduced the Phase 13 timeout and found incomplete evidence-operation binding;
    its verdict was `FAIL` while confirming the 404 remediation.
13. The evidence schema and validator now bind each operation to its exact endpoint and
    permitted outcome matrix.
14. A clean accepted-main worktree reproduced the Phase 13 loopback failure in 7 of 20
    isolated executions, classifying it as `BASELINE_REPRODUCED`, not ACRA-specific.
15. The deepest confirmed repository cause was the in-thread Windows Uvicorn harness
    selecting the default Proactor loop. A read-only Selector-loop counterfactual passed
    20 of 20; the smallest permanent repair makes the harness choose Selector explicitly.
16. The repaired exact test passed 20 consecutive executions, its containing module
    passed 10 consecutive executions, and the adjacent Windows lifecycle selection
    passed all 25 tests without sleeps, retries, timeout inflation, skipped coverage, or
    weakened assertions.
17. Strict mypy exposed four accepted-main type regressions. The same diagnostics were
    reproduced on clean main and repaired with type-only enum/Literal annotations; strict
    mypy now passes all 108 source files.
18. Three consecutive complete backend runs, the supported repository runners, frontend
    tests/typecheck/build, static checks, governance checkers, the bounded official-Mock
    smoke, and the process-level application check are green.

## Current source truth

- Official mode: explicit opt-in `api_marketplace_mock`, classification `MOCK`.
- Garden application result: `REVIEW_REQUIRED / REGISTRY_EXPECTED_DATA_MISSING` with
  partial acquisition and operation statuses `COMPLETE`, `COMPLETE`, `EMPTY`, `EMPTY`.
- Garden shareholder chain: absent from the observed official Mock response.
- Ownership denominator: not established; no provider percentage or relationship.
- Local synthetic Mock: unchanged default in repository configuration and test runs.
- Generic sandbox: separate; BizFile connector: dormant; Production/Live: absent.

## Verification state

- Focused auth/provider/mode tests: pass.
- Focused Phase 09/10 and ownership tests: pass under process-only synthetic Mock mode.
- The ordinary-test settings owner explicitly selects synthetic `mock`, while
  official-mode tests opt in explicitly; this prevents the intentionally active local
  official Mock `.env` from contaminating legacy tests.
- Three consecutive complete backend runs passed the same 1,379 collected cases:
  1,344 passed, 35 skipped, and 4 known warnings on every run. Run 1 exited zero in
  approximately 89 seconds of runner wall time (its numeric summary was suppressed by
  the repository's duplicate quiet flags); runs 2 and 3 completed in 95.68 and 95.15
  seconds respectively.
- Ruff and strict mypy: pass.
- Contract tests: 44 pass.
- Focused final selection: 284 pass; frontend: 286 pass; supported non-contract root
  runner: 275 pass; contract runner: 44 pass. A raw combined root pytest invocation is
  not a supported runner because two contract modules depend on contract-runner path
  setup; it was not counted as evidence.
- Governance/evidence checks and direct secret scan: pass.
- Project-state, architecture, policy-authority, provider-readiness, and dedicated
  evidence validators: pass.

## Drift and stop decision

- Scope, host, Mock classification, owner, and no-fallback boundaries remain aligned.
- The missing same-entity denominator and Garden shareholder data are recorded as
  evidence gaps, not repaired with synthetic data.
- No commit, push, PR, merge, Production call, provider mutation, GoldTier/PingFed call,
  or unrelated `.env` edit occurred.
- Decision: the baseline regression has been repaired at its test-harness owner and all
  required repeatability evidence is green. The exact final candidate is ready for a
  fresh independent Quality Gate; no publication action is authorized before `PASS`.
