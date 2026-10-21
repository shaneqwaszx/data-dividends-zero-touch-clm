# Data Dividends — Codex Project Guidance

## Scope and authority

Build the Zero-Touch Onboarding CLM proof of concept:

`ACRA Singapore -> orchestration -> GoldTier -> unresolved human approval gate`

Work only on the explicitly assigned task or phase. Singapore ACRA is the sole
implemented registry route. Do not invent a business rule, sponsor decision, contract,
mapping, source precedence, security assumption, or Live-integration claim. Record a
material ambiguity or contradiction and stop only the dependent work.

When facts disagree, use this order:

1. current synchronized source and tests;
2. current contracts and decisions;
3. current configuration and composition;
4. sponsor-question and decision records;
5. supplied audits or planner context;
6. architecture and project-context documents;
7. current phase reports;
8. historical reports and prompts.

For GoldTier contract conflicts, apply the precedence recorded in the current contract
and decision documents. Contradictory examples are `INVALID / QUARANTINED`; never turn
them into fixtures, enums, DTOs, mappings, or assertions. Project-defined or provisional
behavior is not sponsor-confirmed.

## Task-scoped context and workflow

For non-trivial work, establish repository/worktree, branch, `BASE_SHA`, `HEAD`,
`origin/main`, status, assigned scope, and applicable change classes from
`docs/DEVELOPMENT_WORKFLOW.md`. Run:

```powershell
python scripts/dev_context.py --change-class <CLASS>
```

Use one argument per affected class and read the emitted Tier 1 sections plus only the
triggered contracts, decisions, questions, skills, owning source/tests, planner, and
nearest relevant accepted gate. Use `--full` when classification or authority remains
uncertain. Load historical/Tier 2 material only for a named unanswered question.

Use `.agents/skills/README.md` to route recurring workflows. The canonical workflows
are `fyp-phase-execution` for ordinary bounded implementation,
`fyp-quality-gate` for independent review, `integration-safe-development` for
integration/pre-PR readiness, and `worktree-task` when concurrent checkout isolation is
actually needed. Skills cannot broaden scope or authorize commit, push, PR, or merge.

Keep active context and handoffs delta-only. Distinguish the current source revision,
the revision/content actually tested, and the exact content independently reviewed.
Record current-session capabilities and relevant shared resources only in proportion to
the task; availability elsewhere is not evidence here.

## Architecture and integration invariants

Use `docs/ARCHITECTURE.md` for the canonical owner/dependency map and
`docs/PROJECT_STATE.md` for the dated capability/provider matrix. Preserve:

- untrusted source DTO -> canonical model/evidence -> target mapping;
- controlled provider, service, and repository interfaces with fail-closed unsupported
  behavior;
- one deterministic Decimal ownership/UBO engine;
- ledger-owned target ordering, call stopping, and no-replay recovery;
- backend-authoritative capability, RBAC, team scope, and safe inaccessible-case `404`;
- reauthorization inside the owning lock/CAS boundary for sensitive mutations;
- explicit memory/Mongo modes with no silent fallback, strict identity/revision CAS,
  insert-only create, update-only mutation, and no stale resurrection after deletion;
- user/session/team-scoped frontend server state, cancellation, and incompatible-cache
  clearing on logout, identity/session change, and `401`.

Do not add direct route-to-Mongo access, frontend authorization, direct ACRA-to-GoldTier
mapping, a second ownership/authorization/persistence owner, a target-ledger bypass, or
runtime composition of dormant providers without the applicable reviewed workflow.

Mock, Local, Sandbox, Partial, Dormant, and Live are distinct evidence classifications.
Never present a non-Live mode as Live. Credentials, tools, placeholders, passing mock
tests, or sandbox access do not prove sponsor approval or interoperability. Consult
current decisions and questions before implementing sponsor-controlled endpoints,
schemas, mappings, authentication/TLS, policy, Ready-for-Approval, related parties, or
hierarchy behavior.

Unless explicitly assigned and supported by current authority, do not implement other
jurisdiction registries, `createRelationship` or multi-level hierarchy creation,
autonomous/final approval, ML-based UBO decisions, a production compliance/risk engine,
full MIS, or a full Exception Workbench.

## Secrets and protected data

Do not access `.env` for ordinary development/governance work. Never track or disclose
passwords or hashes, tokens, authorization headers, client secrets, private keys or
certificates, sponsor credentials, raw confidential sponsor artefacts, KYC/PII,
document bodies, raw provider payloads, or private exception details. Logs and handoffs
use safe identifiers, states, correlation IDs, and sanitized summaries only.

Repository checks must stay on tracked or explicit task-owned paths; do not broadly scan
unrelated, parent, sibling, or protected locations. Physical Mongo work requires an
explicitly relevant, newly generated allowlisted disposable database. Never connect a
test to, mutate, clean, or drop `clm_poc`, and never print or persist a Mongo URI.

## Git and coordination safety

`origin/main` is the integration baseline. Never develop on `main`. Preserve unrelated
changes and other worktrees. Do not reset, clean, stash, force-push, rebase shared
history, broadly stage with `git add -A`, delete/reuse another branch, overwrite a
worktree, or merge a PR. Before any branch/worktree mutation, inspect status, branch,
`HEAD`, `origin/main`, and the worktree list; use `worktree-task` for isolation decisions.
Preserve current main behavior unless the assigned requirement supersedes it; avoid
unrelated refactors, renames, formatting, dependency, generated-file, or lockfile churn.

One coordinator owns Git mutations. Multiple writers require explicit non-overlapping
ownership, and workers sharing a checkout are not isolated. Follow the five-stage
lifecycle in `docs/DEVELOPMENT_WORKFLOW.md`: stable implementation -> one integrated
acceptance -> independent QG `PASS` -> publication -> owner merge. Keep implementation,
independent Quality Gate, remediation, integration/acceptance, and publication as
distinct assigned runs. A Quality Gate does not fix reviewed content; changed reviewed
content requires a fresh independent review. Publication requires exact independent `PASS`, unchanged
reviewed content, and explicit owner authorization. Repository-owner humans merge PRs.

## Verification and completion

Use the change-class matrix in `docs/DEVELOPMENT_WORKFLOW.md`. Iterate with focused
checks; run the broader, adverse-path, regression, security, physical, or contract
evidence the class and scope require once on the integrated candidate, reusing valid
evidence and rerunning only what a later change invalidates. Inspect the complete diff,
including task-owned new files. Check whitespace for untracked Markdown explicitly
because `git diff --check` does not cover it. Never report stale, skipped, unavailable, or
unexecuted evidence as passing.

Before PR readiness, use `integration-safe-development`, fetch and assess latest main,
run `python scripts/pre_pr_check.py` on the required clean committed state, and complete
its `references/PRE_PR_CHECKLIST.md`. Do not run that publication gate merely to certify
an intentionally uncommitted implementation handoff.

A task is complete only when the requested scope is implemented, applicable checks pass,
the final diff is reviewed, no secret/confidential artefact is newly tracked, affected
durable documentation is current, and the handoff reports branch/base/current-main,
files, behavior, evidence, decisions, blockers/risks, and next authorized action. State
explicitly whether API/type, schema, connector, configuration, business-rule, mapping,
auth/security, architecture, provider status, and runtime behavior changed.

Do not commit, push, create a PR, merge, or begin another phase unless explicitly
authorized.
