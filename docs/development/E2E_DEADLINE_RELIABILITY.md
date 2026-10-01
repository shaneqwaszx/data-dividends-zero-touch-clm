# PR65 E2E deadline reliability - bounded harness correction

## Scope and identity

New planner-authorized task, not a third remediation of the preceding publication. Branch `fix/demo-happy-path-stabilization`, parent `72ed7b96dd02e13dca3b399bb5f4ea8dc33087cf`, main/base `efc31f450f0103766fa812bc0aa80754f801dbe9`; clean local/remote baseline confirmed. Prior failed checkpoint and two-round history remain intact. This candidate requires fresh independent PASS before exact stage/commit/push; no merge.

## Proven cause and old ownership

Focused `run()` sets one monotonic deadline for backend readiness, frontend readiness and the Playwright child. Cleanup has separate existing bounded stop phases. Unfiltered `run_isolated_suite()` previously reused a single 240-second budget across discovery and all isolated lifecycles, passed decreasing remaining time into each later lifecycle, and refused dispatch when remaining was below30 seconds. Thus successful earlier tests could prevent valid undispatched tests from running.

The deterministic failing-first regression simulates26 successful ten-second selectors (260 seconds, no sleeping); the published runner returns1 and omits selectors. Existing tests covered child timeout, readiness, failure and cleanup, but none defined aggregate success beyond240. Historical PR36846661054 stopped before selector26 after25 successful tests, while same-tree push36846655538 completed27 tests/26 selectors. This proves unsafe aggregate timeout ownership; the exact reason for CI host speed variance remains unproved. Push success did not satisfy the historical failed PR.

## Narrow correction and finite contract

Each isolated lifecycle now gets its full `--timeout-seconds` allowance, as focused execution already did: default240, allowed30-900 seconds, shared by its own readiness and Playwright execution. No assertion timeout, retry, fixture, selection order, product source or isolation behavior changed.

Separate suite safety budget is `60 + discovered_selector_count * (lifecycle_timeout + 120)` seconds. Discovery is bounded60 seconds. The120-second per-lifecycle reserve covers three existing owned processes' at most six five-second POSIX stop phases each (90 seconds), bounded capture joins and orchestration slack; Windows cleanup is lower. Existing strict reverse-order cleanup and non-zero failure behavior remain intact. Suite exhaustion reports the undispatched selector explicitly and never returns suite PASS. Logs distinguish individual selection timeout, suite/job timeout, assertion/non-zero child, readiness and cleanup failures, and report effective bounds plus per-lifecycle/total/slowest elapsed.

Only CI's E2E job changes: explicit60-second lifecycle allowance and90-minute outer Actions timeout. Current26-selector suite budget is4740 seconds (79 minutes), leaving11 minutes for tool/browser installation. This bound is finite and derived from maximum allowed execution plus bounded cleanup, rather than observed average speed. Current slowest lifecycle is below20 seconds. Discovery growth scales the launcher budget and must trigger reassessment of the documented outer job bound. Unrelated five jobs/triggers remain unchanged.

Typing-only cleanup makes changed Python strict-mypy clean on Windows and Linux: capture IO, Popen options TypedDict, identity casts of platform modules and typed test doubles/JSON. Guards, runtime module objects, process signals and all original assertions remain unchanged; no ignores or check weakening added.

## Exact verification

- Failing-first aggregate regression: FAIL against published runner; GREEN after correction.
- Final runner units:38 PASS, including hung-browser deadline, first non-zero stop, readiness/cleanup failures, derived-suite failure with explicit unexecuted selector and CI bound validation.
- Runner/secrets/pre-PR/tooling subset:100 PASS. Additional unchanged governance/context/project/architecture checks:114 PASS (overlapping subsets, not additive unique-test claim).
- Ruff repository PASS; strict mypy for both changed Python files PASS on native Windows and Linux target. YAML parse/static comparison PASS; five unrelated jobs/triggers unchanged. Project-state, architecture and tooling-config PASS.
- Actual Playwright listing:27 tests in4 files; runner discovery26 selectors, final parameterized Garden selector holds2 tests.
- Final complete local isolated E2E:26/26 selectors,27 tests PASS, elapsed236.953 seconds; slowest19.297 seconds at `e2e/authenticated-zero-touch.e2e.ts:605`. Final selector `e2e/zero-touch-exception.e2e.ts:145` actually executes both Garden tests. Golden and all six Garden tests pass. First pre-typing complete run also passed240.266 seconds; final evidence binds to current runner source.
- Exact changed-path supported secret scan0 and whitespace checks; frozen raw identity under ignored `tmp/E2E_DEADLINE_REVIEW_MANIFEST.json`. Assigned independent gate is the sixth publication path.

## Preservation and next action

Only test harness, E2E job configuration, runner tests and directly relevant tooling documentation change. Application API/types, persistence/schema, connector/configuration, business rules, mappings, auth/security, owners, provider classifications and runtime behavior are unchanged. Clean auto-confirm, exception-only review, Garden ownership EMPTY/LOCAL60-40/Decimal/history/cache/finality, Golden zero exceptions plus one confirmation, reflow and no-replay assertions are retained.

External provider calls:0. No retained database/provider connection, initialization, mutation, replay, reconstruction, cleanup or shutdown. Preserved receipts retain ID143880 / PROVIDER_VERIFIED_RECOVERY, original Shell UNCERTAIN, replayed=false, Policy/Amend absent; no fresh ledger read is claimed. Historical physical38/38 is not current acceptance after a new commit; require fresh PR mongo:7 execution again.

Next: independent gate, exact six-path normal commit, clean committed pre-PR, normal push, fresh push and PR observation, then independent post-publication checkpoint. New-task remediation budget0/2 used at initial freeze; preceding task2/2 remains historical. Any fresh required CI failure must stop as instructed; no automatic rerun or merge.
