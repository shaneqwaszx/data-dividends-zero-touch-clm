# Test Plan Workspace

Tests should grow with each phase.

Initial categories:
- unit tests
- schema/contract tests
- connector tests using mocks
- integration tests
- end-to-end tests
- secret/security checks

The project must preserve evidence that sponsor scenarios were tested before UAT.

Phase 03 additionally requires transient-upload validation, bounded streaming,
provider/output failure sanitization, all five deterministic comparison statuses,
independent confidence/provenance, field-level accept/reject/correct and original-value
preservation, all-field completion, parent-case ownership/isolation, browser projection
minimization, and the unchanged Phase 01/02 regression catalogue. Remediation coverage
also includes failures after provider validation (overlong canonical data, comparison,
clock, and recoverable update seams), provider replacement without a Mock scenario,
adversarial provenance, pre-append stream limits, typed/closed review requests, and
UEN-specific internal-whitespace removal. Real PDF/OCR accuracy
and production malware controls cannot be tested until sponsor document/security
requirements are confirmed.

Phase 05 adds current-evidence readiness, immutable target snapshots, call stopping,
concurrency/idempotency, and safe post-target finalization recovery. Phase 06 adds the
straight-through zero-intervention path, every typed exception/technical-failure demo
outcome, multiple blockers, stale/cross-case resolution, automatic resume, duplicate
start/resume, loop guard, malformed target output, provider conformance, UI polling,
server-authorized actions, and Demo/Test Controls separation. The canonical matrix is
maintained in `.agents/skills/poc-regression-check/references/regression-catalogue.md`.
