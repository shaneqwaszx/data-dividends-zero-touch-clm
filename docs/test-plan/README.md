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
