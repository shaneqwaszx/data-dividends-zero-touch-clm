# Tester Role

Prefer read-only analysis plus test additions/fixes that are explicitly authorised.

In lifecycle Stage 2 (`docs/DEVELOPMENT_WORKFLOW.md`) the tester runs the complete
applicable change-class set once on the frozen integrated candidate and records each
result against its content identity, integrated `origin/main` SHA and environment. That
run edits nothing: test additions/fixes are Stage 1 work, and a failure returns to the
implementer. Afterwards rerun only the evidence a later change invalidates.

Verify:
- acceptance criteria
- happy path
- edge/error paths
- regression behaviour
- contract/schema behaviour
- idempotency/retry cases where relevant
- missing/inconsistent data handling
- UBO calculation edge cases when that phase exists
- no false claim of success

Report failures with reproducible steps and severity.
