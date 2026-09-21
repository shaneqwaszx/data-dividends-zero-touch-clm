# Phase 21 — External Integration Activation Readiness Plan

## Identity and preflight

- Worktree: `C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm-postmerge-fix`
- Branch: `phase/21-external-integration-readiness`
- `BASE_SHA`: `5039c7e548dfae1eeb8ad600f128ef374e3a6f2a`
- Base tree: the accepted Phase 20 main tree at that SHA.
- Required post-merge push CI: run `35609501578`, `completed / success`, exact head
  `5039c7e548dfae1eeb8ad600f128ef374e3a6f2`.
- Start state: clean tracked and untracked tree; no active Git operation; target
  branch absent locally and on GitHub before creation; one coordinator owns this
  worktree.
- Capability/resource preflight: PowerShell, Git 2.55.0, Python 3.12.10, GitHub CLI
  2.101.0, Ruff, repository write access, read-only authenticated GitHub browser
  access, and the Codex file/terminal tools are available. No app connector, live
  provider, MongoDB, browser test, lifecycle process, disposable database, or reserved
  port is required for this governance-only phase. Managed worktree Git metadata
  required one approved elevated branch-creation operation; no source files were
  changed by that operation.

## Scope and change classes

Primary classes are `DOCS_ONLY` and bounded `CI_TOOLING / GOVERNANCE`, with
`INTEGRATION_SECURITY` documentation/tooling coverage. No runtime external-provider,
API, frontend, persistence, target-ledger, RBAC, or provider-composition change is
authorized.

The phase creates a machine-readable provider readiness registry, a deterministic
network-free checker, a sanitized evidence schema/validator, an activation contract,
security runbook, sponsor activation packet, current-state refresh, and implementation
report. Existing provider ports, adapters, configuration semantics, and Mock behavior
remain owners of runtime truth.

## Authority and current topology

Phase 20 is accepted on the `5039c7e...` main baseline. D-009 confirms only that
human exception review is allowed/expected. Q-001 through Q-018 remain open. Current
provider truth is: Mock ACRA default; generic ACRA sandbox-shaped seam Partial; BizFile
Dormant and uncomposed; local PDF/text IDP with Mock fault/demo support; local Decimal
ownership engine; Mock GoldTier only; PingFed not implemented. No real provider is
activated or proved.

The readiness registry owns provider activation state. The existing policy-authority
registry remains the owner of sponsor business-policy authority. Cross-boundary
questions are referenced, not duplicated.

## Readiness vocabulary and registry invariants

Current classification is limited to `MOCK`, `LOCAL`, `PARTIAL`, `DORMANT`, and
`NOT_IMPLEMENTED`. Activation state distinguishes `INTERNAL_POC_ONLY`, `BLOCKED`,
`PARTIAL_SCAFFOLD_ONLY`, `READY_FOR_AUTHORIZED_SANDBOX_PROOF`, `SANDBOX_VERIFIED`,
and `LIVE_VERIFIED`.

The checker requires the exact provider inventory and exact entry fields, binds known
provider classifications to current source truth, requires canonical unresolved sponsor
questions to remain on dependent future-provider entries, rejects readiness while those
questions are open, rejects disabled gates with runtime activation, rejects Mock/Local
or dormant providers labelled as Live, and checks that current GoldTier configuration
remains Mock-only. It never reads secret values or makes network calls.

## Evidence contract

`docs/contracts/external_provider_evidence.schema.json` is strict and rejects unknown
fields. Evidence profile v2 uses a bounded positive language: finite enums for provider,
mode, classification, operation, outcome, contract/mapping reference, certificate,
authentication, result, order, and redaction fields; canonical UUID syntax for case and
correlation references; and a control-free, calendar-valid UTC instant. The JSON Schema
and Python validator enforce the same timestamp and identifier language. Both direct
and imported JSON loaders reject duplicate keys with constant diagnostics that do not
echo attacker-controlled key text. The validator is network-free, provider-bound, and
does not use delimiter/secret blacklists or generic containers. No synthetic evidence
fixture is created or labelled as sandbox proof.

Whole-record validity is additionally bound to four current credential-free profiles:
ACRA Mock, local PDF/text IDP, local Decimal ownership, and Mock GoldTier. Each profile
fixes mode, classification, operations, non-HTTP outcome, activation-contract
reference, certificate/auth label, canonical mapping, and applicable order result.
Generic ACRA sandbox, BizFile, future vendor IDP/hierarchy, real GoldTier, and PingFed
have no valid evidence profile until a separately authorized schema change supplies
the missing authority. Bounded scalar validity alone never authorizes a cross-provider
combination.

## Explicit non-runtime boundary

Do not add a real ACRA, GoldTier, PingFed, hierarchy, or vendor OCR adapter; consume
future environment placeholders; infer OAuth, scopes, retries, mTLS/private CA,
pagination, mappings, or error semantics; resurrect BizFile; add Mock fallback; alter
the target ledger/no-replay owner; or claim sandbox/Live interoperability.

## Verification and independent gate

Focused checks cover the readiness checker, evidence validator, strict JSON, adversarial
contradictions, and existing governance/pre-PR tests. Required repository checks include
`dev_context`, project state, architecture, tooling, policy authority, secrets, Ruff,
contract/governance tests, file hygiene, and `pre_pr_check.py` on the clean committed
tree. The security job installs the pinned contract-validation requirements before it
collects the evidence-validator tests, while retaining the same installation for the
later GoldTier validation steps. Physical Mongo, Playwright, and lifecycle checks are
not proportionate unless a runtime surface changes. The implementation owner
self-reviews the complete diff.

A fresh independent reviewer must inspect the exact frozen candidate, challenge P21-01
through P21-22, and write `.ai-pipeline/reports/PHASE_21_QUALITY_GATE.md`. Only exact
`PASS` permits publication. Any other verdict requires remediation and fresh re-QG.

## Stop conditions

Stop if the baseline/main CI identity changes, authority unexpectedly enables runtime,
required contract/security/mapping evidence appears and would require scope
reauthorization, a required check fails, a secret/confidential artefact appears, an
unowned change is found, independent QG is not exact PASS, or latest-main intent cannot
be reconciled safely. Do not start Phase 22 or merge the PR.
