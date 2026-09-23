# Pre-Phase 22 Manual-UAT Stabilization — Evidence

## Baseline Evidence

- Repository/branch start: canonical repository on clean `main` at `ef338c9b7926a298e8987acb975fd93c96ed2bfb`.
- Tree: `003c7b56685da22071fd31ec5a28b8bbf6f06e5b`.
- `origin/main`: exact match after fetch/pull.
- CI: run `35671556733`, event `push`, exact head, completed/success.
- Target branch: absent locally/remotely before creation; created at the accepted SHA.
- Demo: no launcher-owned session recorded; stop was idempotent.
- Runtimes: Python 3.12.10, Node 22.23.2, npm 10.9.8, GitHub CLI 2.101.0.

## Strict RED / GREEN evidence

- RED unit: unsupported Assign reviewer / Return for rework controls were present.
- RED browser: 360px dashboard root scroll width was 470px; scoped account hover was unowned.
- GREEN focused component tests: 17/17.
- GREEN full frontend suite: 19 files, 263/263 tests.
- Typecheck and production build: PASS; build transformed 111 modules.
- First independent QG: `FAIL`, PRE22-QG-001. The original focused responsive lane failed five fresh times at shifting later routes after repeated full document reloads.
- Responsive remediation: ordinary route changes now follow the same React Router workspace links used during manual UAT; explicit login/deep-link checks retain full reload coverage. Keyboard focus uses a real Tab transition, and the New onboarding assertion accepts the canonical retained-intake child route.
- Remediated responsive guarded Chromium: four fresh exact focused runs PASS in 12.9/13.1/12.9/12.9 seconds at 360/390/480/768/1024/1280/1440 across login and all primary authenticated/admin surfaces; account hover/focus, dialog bounds, supported action truth, root containment, and operable local table scroll were asserted mechanically.
- Current-document review: its initial deep link and final persistence reload remain; redundant intermediate reloads were removed so the live mutation/refetch owner is tested directly. Two fresh isolated guarded lifecycles PASS in 5.7/5.0 seconds. Case-portfolio mutation/deletion and activity explorer also PASS in isolated guarded lifecycles.
- Second independent re-QG: `FAIL`, PRE22-RQG-001, because focused/isolated passes did not replace the red exact unfiltered CI command.
- Runner RED/GREEN: new unit contract failed before `_list_test_selectors`/`run_isolated_suite` existed, then passes 18/18. Playwright's own configured list is the source of exact selectors; each receives a fresh owned lifecycle and the suite stops on first failure.
- Four original shared-lifecycle commands stalled (document review three, Cases one). After isolation, one exact command passed, a repeat exposed a remaining ordinary reload before second case creation, and the final same-pattern repair made two consecutive exact unfiltered commands PASS 7/7. Earlier failures remain evidence, not reclassified successes.

## Investigation evidence

- Read-only Mongo: reachable; `clm_poc.clm_case_snapshots` exists with 14 schema-v2 records; safe administration counts 2/6/1; current mode `memory`; no mutation.
- Historical Mongo diagnostic: `FYP.users` exists with count 2 and no case collection; Phase 12 introduced stable `clm_poc`/`clm_case_snapshots` defaults.
- ACRA all-ref history: Garden source fixture introduced only at unmerged `79e808f...`, deleted by `6bcea75...`; current main/acra-integration/CRUDoperations heads lack it; no provider file changed.

## Governance and tooling evidence

- Project-state, tooling-config, policy-authority, provider-readiness, secret checks: PASS.
- Architecture checker initially failed on Windows because `_tracked` replaced PATH and later because deleted tracked files were still enumerated. Strict regression tests now cover both; 14/14 checker tests and direct checker PASS.
- Phase 21 accepted state now points at `ef338c9...` while provider truth and every open question remain unchanged.
