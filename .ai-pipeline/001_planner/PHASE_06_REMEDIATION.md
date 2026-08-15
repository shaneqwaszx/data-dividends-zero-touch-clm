# Phase 06 Remediation — Independent Quality Gate FAIL

## Authority and bounded goal

This handoff records the Phase 06 remediation assignment supplied on 12 August 2026.
It is subordinate to `AGENTS.md`, preserves the original Phase 06 planner, and is
limited to closing the findings in `.ai-pipeline/reports/PHASE_06_QUALITY_GATE.md`:

- HIGH: `P06-QG-001` through `P06-QG-008`.
- MEDIUM: `P06-QG-009` through `P06-QG-011`.
- LOW: `P06-QG-012`.

The already-proven clean path must remain:

`Start -> Registry -> Document -> Ownership -> Readiness -> Mock GoldTier -> COMPLETED`

Happy-path human interventions after Start remain exactly zero.

## Required remediation

1. Bind every exception to current authoritative case/canonical evidence, document
   evidence, automation version, exception type, and blocker set. Under the case lock,
   re-read and re-evaluate all relevant evidence before any resolution. Canonical legal
   name, UEN, address, or country mutation must return typed 409 stale conflict with no
   resolution, metric increment, resume, or target call.
2. Validate/accept the initial PDF before entering `RUNNING`. A rejected upload retains
   the previous valid state and creates no start event. A registry review exception
   remains blocking after document attachment. Centralize and test legal automation
   status transitions; completed and technical terminal states cannot silently restart,
   and unresolved exceptions cannot coexist with progress past their checkpoint.
3. Give the advancement owner a top-level unexpected-failure boundary. Unexpected
   faults in document assessment, ownership load/analysis, readiness, exception/stage,
   and safe event/metric construction must persist sanitized
   `TECHNICAL_FAILURE / AUTOMATION_UNEXPECTED_FAILURE`, never strand `RUNNING`, never
   expose exception text, and never replay target work.
4. Make document resolutions blocker-specific. `KEEP_REGISTRY_VALUE` may address only
   source conflict; low confidence, missing, malformed, or another blocker remains open
   after complete authoritative re-evaluation. One accepted action increments one human
   intervention, while stale/duplicate/unsupported/technical actions do not.
5. Evaluate every relevant case-owned document deterministically. Until an explicit
   supersession contract exists, any unresolved document business blocker prevents
   progression. A later clean document cannot hide an earlier unresolved document, and
   zero-touch must surface the business blocker before Phase 05 readiness.
6. Preserve Phase 05 as the sole target recovery authority. Treat
   `CLM_FINALIZATION_RETRY_REQUIRED` as bounded recoverable work, re-enter Phase 05
   idempotent finalization, reconcile its terminal success/review/failure outcome, and
   make no new target calls. Bound repeated recovery failure with the existing loop
   guard or an explicit internal recovery transition.
7. Apply one shared backend demo guard to every scenario catalogue and `/api/demo/*`
   HTTP surface. With `DEMO_CONTROLS_ENABLED=false`, every route fails closed using one
   safe status/code; with it true, intended synthetic functionality remains available.
8. Bind a stable provider-neutral execution profile/provider key to each journey so
   provider selection survives start, pause, resolution, and resume. Composition/demo
   code resolves the key; the generic orchestrator must not persist provider objects or
   branch on scenario names. Missing bindings fail safely rather than fall back.
9. Prove adapter replacement with alternate local/stub Registry, IDP, Ownership, and
   GoldTier implementations through the complete zero-touch orchestrator, including
   success, absence/incomplete evidence, malformed/mutable typed output, review, and
   call-stopping outcomes.
10. Make frontend polling a resilient read-only observation loop. While authoritative
    state is `RUNNING` or `RESUMING`, a transient error or in-flight skip must schedule
    a later bounded-backoff poll without triggering Start/Resume/business actions.
11. Make case navigation atomic. Immediately invalidate/disable old-case actions,
    reject late response overwrite through a request-generation token (or equivalent),
    and bind resolution to the currently rendered case/exception during navigation.
12. Render stage labels from authoritative automation status: waiting for inputs,
    processing, human review required, resuming, technical failure, or completed.

After any accepted human resolution, re-read current canonical case, all relevant
documents, current ownership/provider binding, CLM state, automation record, and active
exceptions before computing the next safe stage.

## Permanent regression coverage

Add explicit reproductions for all `P06-QG-001`–`P06-QG-012`, including four canonical
field mutations, invalid PDF state preservation, registry-review attachment,
unexpected-failure injection, mismatch plus low-confidence partial resolution, older
unresolved plus newer clean document, four Phase 05 retained-outcome recovery classes
and malformed response where applicable, all demo APIs disabled/enabled, provider
binding across resume, alternate adapters, polling retry/in-flight skip, navigation/late
response/resolution safety, transition-table invariants, stage labels, metrics, target
call stopping, and zero-replay behavior.

## Sponsor and security boundary

No sponsor question is resolved by this remediation. D-025 remains provisional.
Q-003/Q-005/Q-013/Q-014 still govern document/source/reviewer/privacy policy; Q-004 UBO;
Q-012 live ACRA; Q-002 hierarchy; Q-006/Q-007 related-party mapping/write;
Q-008/D-018 real GoldTier/PingFed; and Q-001 Ready-for-Approval.

No secret, raw sponsor artefact, KYC/PII, provider payload, document bytes, private
exception text, or provider configuration secret may enter tracked files, routine
events/logs, or browser responses.

## Explicit non-goals

Do not add real GoldTier/PingFed, live ACRA, live hierarchy, related-party writes,
sponsor-final UBO/document authority, Ready-for-Approval, durable persistence/queues,
distributed orchestration, RBAC, a production approval workflow, or any next phase.

## Required verification and stop condition

Run full and Phase 01–06 focused backend suites; every new adversarial/state/document/
recovery/adapter/demo/concurrency/stale regression; contract and repository tests; Ruff;
strict mypy; `pip check`; frontend typecheck/tests/build; `npm ls --all`; secret tests and
scan; GoldTier validator tests/classification/expected quarantine exit; and tracked,
cached, and explicit untracked whitespace checks. Then rerun the
`integration-security-review` and `poc-regression-check` workflows and regenerate both
Phase 06 supporting reports with explicit `P06-QG-001`–`P06-QG-012` closure evidence.

Do not overwrite the historical independent FAIL. Do not stage, commit, push, merge,
change branch, start Phase 07, or issue the final independent gate.
