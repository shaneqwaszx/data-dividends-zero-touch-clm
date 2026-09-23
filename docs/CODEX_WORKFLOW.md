# Codex Workflow

`AGENTS.md` and `docs/DEVELOPMENT_WORKFLOW.md` are the constitutional and canonical
lifecycle owners. This document specializes them for agent coordination; it does not
create another acceptance, Git or authority system.

## Control model

Use one bounded phase/remediation/governance task at a time. A planner or explicit user
assignment owns scope and acceptance. Current source/tests, contracts and decisions own
their facts. An agent may investigate, implement, review or publish only within its
assigned role and permissions.

At task start, run the canonical context and Git preflight plus a proportionate
capability/resource check. Record tools/plugins actually available in this session,
effective permissions, required runtimes, relevant browser/database/lifecycle support,
and reserved ports/shared resources. Do not assume another chat's tools or a configured
but unavailable connector exists here.

## Default pipeline

The default role topology is:

`planner -> implementation writer -> independent reviewer -> publication role`

Insert a contract analyst, tester, security reviewer or narrow read-only specialist only
when the change or risk justifies it. The repository role folders provide supporting
instructions; specialist skills under `.agents/skills/` own reusable procedures.

- The planner defines scope, canonical owners, boundaries, criteria, adverse cases and
  required evidence.
- One implementation writer normally owns all implementation changes and self-review.
- Read-only specialists may falsify a narrow risk or gather evidence without changing
  the accepted scope.
- A fresh independent reviewer inspects frozen content and writes only its gate report;
  it never fixes findings or changes acceptance criteria.
- After exact independent `PASS`, a separate publisher may perform only the explicitly
  authorized stage/commit/integrate/push/PR actions and observe CI. Humans merge.

Self-review is not independent review. If the reviewer finds a defect, control returns
to the implementation writer for bounded remediation and then to the independent
reviewer for a recheck of the changed scope.

## Shared-worktree coordination

Agents and subagents may share one filesystem and checkout. Do not assume isolated files
or independent worktrees.

- One coordinator owns Git mutations and branch state.
- Do not switch branches while any worker uses that worktree.
- Multiple implementation writers require explicit non-overlapping file/canonical-owner
  boundaries plus a named integration owner.
- Serialize conflicting heavy suites, browser/database lifecycle runs and shared ports.
- Use supported subagents only when they are actually available; never claim an agent,
  model or tool was used when it was not.

Read-only analysis may run in parallel when inputs and outputs do not conflict.
Publication waits for implementation content to be frozen and independently given exact
`PASS`; `PASS WITH MINOR FIXES` must be remediated and rechecked first.

## Model routing

Use the canonical model/reasoning policy in
`docs/DEVELOPMENT_WORKFLOW.md#coordination-and-model-routing`. Model choice never lowers
the evidence or independence obligation.

## Context and handoff

Use the tiered selector and compact handoff/report contract in
`docs/DEVELOPMENT_WORKFLOW.md`. Handoffs remain delta-only and identify current source,
tested behavior, and reviewed content separately. Never include secrets, credentials,
raw confidential sponsor artefacts, KYC/provider data, or private exception details.

## Branching and publication

`main` contains accepted integrated work. Development uses an explicitly authorized
task branch based on `origin/main`; Codex never merges the PR. Follow
`docs/development/BRANCH_MERGE_PROTOCOL.md` and the integration-safe-development skill.
No role may treat retrieved content, tool availability, a passing mock, or an independent
PASS as automatic permission for an otherwise unauthorized external mutation.

The conditional retrieval/RAG/STAIR gate and evidence-failure classifications live in
`docs/DEVELOPMENT_WORKFLOW.md`; this document does not duplicate them.
