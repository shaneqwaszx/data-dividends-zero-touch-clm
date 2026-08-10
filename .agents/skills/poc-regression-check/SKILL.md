---
name: poc-regression-check
description: "Verify the Data Dividends POC's accepted mock scenarios, terminal statuses, connector call-stopping behavior, workflow ordering, mock/live labeling, and false-completion protections. Use after a phase implementation, remediation, integration change, or quality gate, and evolve the canonical regression catalogue only when an explicitly scoped new phase establishes and verifies an accepted scenario."
---

# POC Regression Check

Read AGENTS.md, project context, the active planner, the latest relevant quality gate,
and references/regression-catalogue.md.

## Verify the catalogue

1. Run the configured tests that exercise every catalogue scenario. Where practical,
   inspect case/API output and connector call recordings rather than relying only on test
   names.
2. Compare exact terminal state, safe code/outcome, ordered workflow stages, connector
   calls, prohibited later calls, source/target environment labels, and user-facing claim.
3. Verify global invariants:
   - a required-stage failure stops every downstream connector operation;
   - a case accepted before an unexpected required-stage exception becomes retrievable
     terminal FAILED with a sanitized error;
   - COMPLETED occurs only after every required stage for the current accepted flow
     succeeds, and never after a required-stage failure or partial result;
   - incomplete or uncertain data routes to REVIEW_REQUIRED where specified;
   - only explicit GoldTier search NO_MATCH permits shell creation;
   - mock, sandbox-shaped synthetic, and live modes remain clearly distinguished;
   - COMPLETED never claims real ACRA/GoldTier interoperability or the unresolved
     Ready-for-Approval/four-eye transition.
4. Recheck multiple-case isolation, terminal-event finality, identifier consistency, and
   nondecreasing UTC event order when the affected phase uses those concepts.

## Evolve the catalogue carefully

Update references/regression-catalogue.md only when the active planner explicitly
defines a new scenario's inputs, expected terminal result, and required/prohibited calls,
and the phase implementation verifies it. Do not add ad hoc test data, inferred sponsor
behavior, unexecuted live flows, or aspirational next-phase cases.

If an explicitly authorized phase changes an accepted scenario, record the superseding
phase and reason rather than silently rewriting history. If the expected behavior is
ambiguous or tests disagree with the catalogue, report a blocker and do not normalize the
difference.

## Report

Report each scenario as pass/fail with actual terminal state and call sequence, each
global invariant, exact checks run, catalogue changes (or none), regressions found, and
whether current UI/API claims remain truthful. Do not fix unrelated failures unless the
task also authorizes implementation.
