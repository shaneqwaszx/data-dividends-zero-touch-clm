---
name: architecture-change-review
description: "Use when work creates or replaces a service, repository, provider, state owner, framework, dependency direction, persistence owner, module boundary, or major compatibility surface."
---

# Architecture Change Review

## Trigger

Use before implementation when work creates a new service/repository/provider/state
owner, changes module or persistence ownership, reverses dependency direction, adds a
major library/framework, replaces a canonical owner, or retires a major compatibility
surface. Do not use for an internal edit that stays within an existing owner and
invariant.

## Purpose

Prevent duplicate owners and deadline-driven boundary erosion. The smallest textual
diff is not sufficient if it creates a second authority or permanent fallback.

## Inputs

- bounded requirement/planner handoff and change class;
- proposed owner, callers, consumers, interfaces and files;
- current architecture, source/tests, decisions and compatibility obligations;
- expected verification and retirement outcome.

## Mandatory context

Read `AGENTS.md`, `docs/PROJECT_STATE.md`, `docs/ARCHITECTURE.md`,
`docs/DEVELOPMENT_WORKFLOW.md`, the relevant contract/decision/open question, current
canonical owner source/tests, and `integration-safe-development` for branch work.
Select scoped authority by the proposed boundary: provider name -> its contract/open
questions; persistence -> its profile; auth/cache -> their current profile. If the
provider or responsibility is unspecified, stop for scope rather than reading every
historical artefact.

## Preconditions

- The review uses a current `origin/main` baseline. An authorized feature branch is
  required before implementation, not before a planner-level review.
- The requirement and non-goals are explicit.
- Current owner and affected consumers have been inspected.
- No sponsor or contract ambiguity is being treated as architecture authority.

## Analysis steps

1. State the invariant and responsibility being changed.
2. Perform the mandatory **Existence Check**: *Can an existing canonical owner handle
   this responsibility?* Name each reuse candidate and evidence. Default to reuse.
3. Map current and proposed dependency direction, callers, consumers and trust/data
   boundaries. Reject API-to-persistence, UI-to-backend-storage, raw-provider-to-domain,
   or other prohibited direction.
4. Identify responsibility overlap. A new name around duplicated logic is still a
   duplicate owner.
5. Compare alternatives, including no change and extension of the current port/owner.
6. Run entropy analysis: new branches, adapters, compatibility paths, fallbacks,
   configuration modes, dependencies and operational burden.
7. Define retirement: old owner/path removed now, retained for a proven compatibility
   reason with a trigger/date, or blocked pending authority. “Refactor later” is not a
   retirement plan.
8. Decide whether `docs/decisions/ADR_TEMPLATE.md` is required under the workflow.
9. Define focused, broad affected, architecture-check and independent-QG evidence.
10. Return `PROCEED`, `REVISE`, or `STOP`; this is advisory and does not grant merge.

## Allowed changes

- Extend an existing canonical owner/port where responsibilities fit.
- Add a focused owner only after the existence check proves no fit.
- Update architecture, ADR, tests and retirement documentation with the code change.
- Remove superseded internal logic when compatibility and evidence permit.

## Forbidden changes

- Direct persistence imports in API routes or frontend code.
- Business rules in connectors, routes or UI.
- A second ownership engine, authorization owner, persistence model, target replay
  path, provider router, or cache authority.
- Caller-side fallback that hides an unsupported provider/contract/state.
- “Temporary” duplicate logic without an explicit compatibility owner and retirement
  trigger.
- Architecture approval inferred from a deadline, passing old tests, or absent ADR.
- Renaming duplicate routing as “composition”, injecting direct persistence behind a
  helper, relying on a future checker as permission, or writing an ADR after the code to
  retroactively legitimize a violation.

## Stop conditions

Stop when the canonical owner is unclear, sponsor/contract authority is missing,
dependency direction would violate an invariant, persistent compatibility data is
unknown, retirement cannot be defined, or tests cannot distinguish old and new owners.
`STOP` blocks the dependent implementation. This skill defines no emergency waiver;
only the repository owner may explicitly change scope/authority, followed by a fresh
review.

## Required tests

- Focused tests for the responsibility and prohibited bypass.
- Broad tests for every mapped consumer.
- `python scripts/check_architecture.py`.
- Change-class checks from `docs/DEVELOPMENT_WORKFLOW.md`.
- Independent quality gate; physical evidence only when the affected boundary requires it.

## Required evidence

- existence-check candidates and conclusion;
- before/after owner and dependency map;
- invariant impact and ADR decision;
- entropy inventory and retirement disposition;
- exact checks/results and uncovered risk.

## Expected report

```text
ARCHITECTURE REVIEW: PROCEED | REVISE | STOP
Requirement / change class:
Canonical owner:
Existence check:
Dependency direction:
Invariants affected:
Entropy / retirement:
ADR required:
Verification:
Risks / blockers:
```

## Handoff format

Hand the implementer the approved owner/file boundary, allowed dependency direction,
explicit non-edits, compatibility/retirement rule, exact tests, ADR/context updates and
stop conditions. Hand the quality gate the same map plus fresh evidence; never describe
the review itself as acceptance.
