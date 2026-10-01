# CI publication remediation - round 1

## Outcome and identity

Bounded remediation of PR #65's initial candidate `8ae2f2a74b89a02f1387ecbe91ae9e9645c099aa` on `fix/demo-happy-path-stabilization`.
Integration baseline remains `efc31f450f0103766fa812bc0aa80754f801dbe9`.
The original 112-path commit, publication manifest, accepted gates and provider chronology remain historical evidence; this is a separate remediation commit requiring fresh independent PASS.

## Causes and delta

- **C - test defects:** the initial PR browser job expected every field to remain pending. Current accepted auto-confirmation accepts three matching high-confidence fields, leaving the low-confidence or mismatched legal name pending. Browser assertions now require that exact split, one manual review request despite double-click, backend-refreshed counts, and unchanged read-only history. The responsive test now requires the backend-projected document evidence action, focus without mutation, and absence of target replay controls.
- **C - physical test defects:** initial CI and guarded local reproduction both returned 35 passed / 3 failed. Replacement tests used event counts from upload, preceding automatic review events; they now read current authoritative counts and assert those counts advanced. Restart review assertions require three already-accepted fields, one corrected field, independent ownership progress and no further connector calls or target execution. Failed replacement/retry and stale-decision assertions remain intact.
- **A - product defect:** the newly reachable history assertion exposed a cache guard rejecting a legitimate supersession: the original document advanced from 9 to 10 events while its historical projection cleared reconciliation version 2 to null. The centralized guard now permits that transition only with an advancing event count and an incoming replacement whose reverse lineage matches the original. Missing evidence, older events, unbound supersession and equal-event reconciliation regressions remain rejected. No stale reversal or resurrection is permitted.
- **B - fixture integration defect:** the final selection executes two Garden tests in the shared zero-touch file, but filename-only routing composed them as normal Mock instead of the offline Garden fixture used in prior focused evidence. Explicit `@garden-protocol` metadata now drives fixture selection using installed Playwright JSON tags; Golden retains normal Mock. Duplicate selectors are deduplicated and mixed fixture modes at one selector fail closed. Two failing-first regression tests and all 34 runner unit tests pass. Sanitized installed discovery proves 27 actual tests / 26 selectors / five Garden selectors executing six Garden tests.
- **D - local output failure:** two complete browser reruns failed writing different existing tracked screenshots on Windows (`UNKNOWN` from file open). Screenshots now use Playwright's per-test `outputPath`; screenshot/layout assertions remain enabled. The unchanged complete suite succeeds with isolated output. All 28 regenerated tracked assets were restored byte-for-byte from the accepted commit; three new task-generated images were preserved under ignored task tmp. No accepted evidence asset is included in this remediation delta.

## Verification

Final changed-content evidence:

- New cache regression: failing-first (1 failed / 5 passed), then full frontend 393 passed / 33 files.
- Complete configured isolated browser lifecycle: 26 selections / 27 tests passed, including Golden and all six Garden tests, recorded/offline synthetic protocol only. The supported 900-second local overall deadline was used after a 240-second run passed its first 25 tests but exhausted the overall Windows deadline; no tests or assertions were skipped.
- Genuine physical Mongo: 38 passed / 0 skipped against a newly created disposable `mongo:7` service. Normal Atlas, application database and retained provider acceptance service were never used for tests.
- Configured contract discovery: 44 passed; focused zero-touch backend: 18 passed; changed backend test Ruff, frontend typecheck/build, full 34 harness unit tests, architecture/project-state checks and supported secret scanner passed.
- An extra, non-configured strict mypy check of the runner reports the same eight pre-existing Windows/static-typing errors as the original committed runner (identical error messages, zero new findings). This optional check is not passing and was not used as acceptance evidence; required backend mypy remains separately verified.
- Local physical PASS does not replace the current PR's required physical CI lane. Current remediation commit CI remains pending publication.

Payload-free logs and raw-content freeze are task-owned under ignored `tmp/PUBLICATION_*`. Runtime backend bytes are unchanged, so prior independently accepted full backend evidence remains explicitly reused; CI executes the configured full backend again.

The successful full lifecycle used the prior success label (tests); afterward only that label was corrected to selectors and the runner unit suite rerun. Runtime acceptance execution and fixture routing were unchanged.

## Scope and safety

Application API/types, schema, connectors, runtime configuration, business rules, target mapping, authentication/security, architecture owners and provider classifications: unchanged by this remediation. Frontend runtime behavior changes only to display authoritative replacement history without reload. Query identity, session/team scope, AbortSignal, cancellation, mutation retries and deletion effects remain unchanged; full frontend adverse tests and browser network guards pass.

No ACRA, GoldTier, PingFed or Production calls. Retained recovery stays ID 143880 / PROVIDER_VERIFIED_RECOVERY, original Shell uncertain, replayed=false, Policy and Amend absent. No retained Mongo access/mutation/cleanup or service shutdown. No full external lifecycle or Live claim.

## Next authorized action

Freeze this delta; obtain independent quality-gate PASS; stage exact reviewed paths plus its assigned gate; create a normal remediation commit; run clean committed pre-PR; push normally and require all current push/PR CI lanes, including physical Mongo. Independent post-publication checkpoint determines human merge-review readiness. No merge is authorized.
