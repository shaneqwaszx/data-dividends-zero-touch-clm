# Token-Efficiency Governance

## Outcome and boundary

Reduce routine Codex/context overhead without weakening current truth, safety,
authority, verification, independent review, or publication controls. Change classes:
`DOCS_ONLY` and `CI_TOOLING`. No product/runtime change, provider activation, external
service, RAG/vector database, new agent framework, PR merge, or Phase 22.

Baseline/worktree:

- branch: `chore/token-efficiency-governance`
- `BASE_SHA`/initial HEAD/initial `origin/main`:
  `83f46e20a9ad36ae61aacb0f470c1404c4732d64`
- accepted tree: `3a7fa0a1f99a97bbade13d3c1434896000660125`
- baseline Project CI: push run `35852747212`, attempt 1, all six required jobs green

## Measured causes

The fixed current canonical start set (`AGENTS.md`, `PROJECT_STATE.md`,
`ARCHITECTURE.md`, `DEVELOPMENT_WORKFLOW.md`) is 4 documents, 67 headings, 84,891
characters, 84,999 LF-normalized UTF-8 bytes, and 1,366 lines before task-specific skills, owners,
tests, handoffs, or reports. Current `dev_context.py` adds 1,534 bytes / 22 lines but
does not select task sections. A representative prior governance planner is 17,567
bytes and its implementation report is 13,332 bytes. Across the constitution,
workflow, Codex/pipeline roles, and relevant skills, the sampled concepts appear in:

| Concept | Documents containing it | Regex hits |
|---|---:|---:|
| context/history | 6 | 30 |
| handoff | 8 | 22 |
| model/reasoning routing | 4 | 18 |
| independent QG | 7 | 71 |
| exact-PASS publication | 7 | 45 |
| destructive Git safety | 4 | 19 |

These are deterministic text proxies, not proprietary model-token or billing counts.
They support the hypotheses that whole-document loading, repeated controls, and large
handoffs/reports dominate routine context.

## Proposed owners and design

- `AGENTS.md`: constitutional invariants and deterministic task-start rule.
- `docs/DEVELOPMENT_WORKFLOW.md`: canonical tiered context, compact handoff/report,
  summary-first evidence, debugging-retirement, and existing model-routing policy.
- `scripts/dev_context.py`: extend the existing read-only owner with deterministic
  change-class manifests, heading validation, fail-closed unknown inputs, high-risk
  expansion, bounded reference output, optional full diagnostic output, and a
  reproducible before/after benchmark.
- `tests/test_dev_context.py`: executable adverse-path and benchmark proof.
- `docs/CODEX_WORKFLOW.md`, pipeline role files, indexes: concise references only when
  they currently duplicate the canonical owner and the local safety cue remains clear.

No parallel context owner or ADR is planned. The existing script and lifecycle document
can hold the responsibility without changing an application architecture boundary.

## Context tiers

- Tier 0: constitutional task/Git/security/authority invariants and source identity.
- Tier 1: deterministic change-class-selected current sections, required skills, owning
  source/tests, acceptance/adverse cases, and triggered contracts/questions.
- Tier 2: supporting architecture detail, accepted gate/remediation, historical report,
  or external research only for a named unanswered question.

Unknown/malformed selection fails closed. `AUTH_RBAC_SECURITY`, `PERSISTENCE`, and
`EXTERNAL_PROVIDER` automatically widen to the full canonical set and applicable skill;
an agent may always escalate to full context. Compact QG input never replaces reviewer
inspection of actual content or required checks.

## Acceptance

- TEG-01..05: precedence, sponsor authority, Git safety, protected data, and truthful
  Mock/Local/Sandbox/Partial/Dormant/Live classifications are unchanged.
- TEG-06..09: meaningful-change QG, exact `PASS`, independent actual-content review,
  and required affected tests remain unchanged.
- TEG-10..12: history is on demand; unknown selection fails closed; high-risk classes
  expand safely.
- TEG-13..15: no product/runtime change, Phase 22, or RAG/vector/agent framework.
- TEG-16: mean routine UTF-8 read-set proxy reduction for `DOCS_ONLY`, `FRONTEND_UI`,
  and `CI_TOOLING` is at least 30%, without moving identical auto-loaded content.

## Benchmark method

Count UTF-8 bytes, characters, physical lines, distinct documents, and selected Markdown
sections from repository files. Baseline is the four full mandatory canonical documents.
Post-change is the exact section union emitted by the manifest for each representative
class. Task-variable planners, source/tests, and skills are reported but excluded from
the percentage because their necessary size is not changed. Run the same built-in
benchmark for routine and high-risk controls; high-risk breadth is a safety result, not
an optimization target. Record current `dev_context` and representative handoff/report
sizes separately. Deterministic ordering and valid headings are tested.

## Expected write set

Primary: `AGENTS.md`, `docs/DEVELOPMENT_WORKFLOW.md`, `docs/CODEX_WORKFLOW.md`,
`scripts/dev_context.py`, `tests/test_dev_context.py`, this planner, compact Aegis work
records, implementation report, and independent QG report. Modify role/index/CI files
only when a proved durable invariant requires it. Do not touch frontend/backend product
runtime files.

## Verification

Tests first for context selection. Focused: `tests.test_dev_context`, representative
CLI modes, benchmark, malformed/unknown input, high-risk expansion, bounded output,
no-env/no-secret, ordering, and heading validity. Broad: project-state, architecture,
tooling-config, policy-authority, external-provider-readiness, secrets, relevant
pre-PR/governance unittests, Ruff for affected Python, mypy only if its configured scope
includes the script, task-owned Markdown hygiene, and `git diff --check`. Product suites
remain out of scope unless actual changes prove otherwise.

## Stop conditions and next action

Stop on unsafe under-reading, a duplicate owner, baseline/latest-main ambiguity,
required evidence failure, non-exact independent verdict, or two failed repair cycles for
one design problem. Next action: tests-first implementation and measurement; then freeze
one exact candidate for one fresh independent QG. Phase 22 remains on hold.
