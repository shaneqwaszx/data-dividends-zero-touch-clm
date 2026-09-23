# Pre-Phase 22 ACRA Teammate Reconciliation — Evidence

## Baseline Evidence

- Current source at task start: `83a2c2651f4f719778baf70389a8ff460a43dfa9`.
- Accepted main / `BASE_SHA`: `ef338c9b7926a298e8987acb975fd93c96ed2bfb`.
- Teammate head: `6bcea75efd660e6dbaaa5dc2079b62749fc0abf1`.
- Target branch was absent locally/remotely before creation and was created at the
  assigned current source revision.
- Tracked tree was clean; no merge/rebase operation was active.
- Demo stop was idempotent: no launcher-owned session was recorded.

## Teammate Inventory Evidence

- `4ae4ed19`: added the initial 631-line dormant BizFile adapter; current main contains
  its hardened descendant plus the accepted `74a5fd2f` OAuth retirement.
- `897a4c4`: changed six paths, adding safe URL/empty response/UEN behavior together
  with superseded OAuth, raw debug utilities, and runtime mode activation.
- `79e808f`: added Garden fixture/derivation/tests/docs in the dormant adapter; the
  current task must adapt it to the active synthetic Mock fixture boundary.
- Next decision ID is `D-046`; current `D-034` belongs to Phase 13 security behavior.

## Final Implementer Evidence

- Focused BizFile/Garden/Phase 09/Phase 10: 117 passed.
- Focused ownership analysis/API/zero-touch: 133 passed.
- ACRA mode/mapping/sandbox/smoke/provider conformance: 177 passed with three expected
  malformed-payload warnings.
- Phase 16 cache compatibility: 22 passed after the repair below.
- Full backend: 1176 passed, 28 skipped, three expected warnings.
- Contracts: 44 tests OK.
- Ruff and mypy: PASS; mypy checked 95 source files.
- Project-state, architecture, tooling configuration, policy authority, external-provider
  readiness, supported-secret scan, and tracked diff hygiene: PASS.
- Frontend, physical Mongo, and browser lifecycle checks are not applicable to the
  changed surfaces. No composition, persistence, frontend, or lifecycle file changed.
- Read-only security review confirmed OAuth/token/raw-debug retirement, query-free
  provenance, strict response identity binding, fail-closed ambiguous envelopes, and no
  provider activation/status change.

## Verification Attempt Record

- S1 attempt 1: full backend reached `1175 passed, 28 skipped` with one failure in
  `test_exact_key_fields_are_isolated_and_unknown_provider_is_rejected`. Root cause was
  the candidate changing `MOCK_ACRA_DATASET_NAMESPACE` from V1 to V2, making the test's
  adjacent V2 identity equal the active identity. This was a reproducible compatibility
  defect, not stale evidence or missing infrastructure.
- Remediation: retain V1. Garden had no previously eligible registration identifier, so
  there is no stale Garden cache entry to isolate and no reason to invalidate every
  existing synthetic cache key.

## Review Handoff

- Review scope: working tree at HEAD `83a2c2651f4f719778baf70389a8ff460a43dfa9`
  plus every task-owned untracked path.
- Requirements authority: the assigned Pre-Phase 22 teammate reconciliation request,
  current source/tests, project architecture/contracts/decisions, and open Q-004/Q-012.
- Compatibility: retain both stabilization commits, current Mock scenarios, cache
  identity, target-ledger ordering, and dormant/uncomposed BizFile state.
- Retirement: speculative OAuth, raw debug utilities, and runtime `bizfile_mock` remain
  absent; no fallback or duplicate calculation owner is introduced.
- Gate write boundary: only
  `.ai-pipeline/reports/PRE_PHASE22_ACRA_TEAMMATE_INTEGRATION_QUALITY_GATE.md`.

## First Gate Remediation

- Verdict: `PASS WITH MINOR FIXES`; every functional, contract, architecture, security,
  and regression criterion passed.
- Sole finding: the dormant BizFile module note said `fetch_relationships` failed closed,
  contradicting its deliberate typed-empty, no-network behavior.
- Remediation: corrected only that explanatory note; executable and contract behavior is
  unchanged. A fresh frozen identity and independent exact verdict are required.
