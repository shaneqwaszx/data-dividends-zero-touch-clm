# Post-closeout existing-customer remediation

Assigned scope: independent document review during unresolved Search, evidence-bound
existing-customer confirmation, supported Search contract updates, offline regressions,
current sponsor clarification records, independent Sol High gate, local commits only
after exact PASS. No external provider calls, credentials, .env, push, PR or merge.

Baseline: `1e0600335a0c7677b5cd5d5c9dd8401dfaf3b90f`; branch
`fix/goldtier-existing-customer-resolution`; task-owned managed worktree.

Owners: OnboardingService owns case evidence; ClmOrchestrationService owns retained
Search/readiness; ZeroTouchOrchestrator owns stage/blocker transitions. Existing
authorization, document/reconciliation, target ledger, persistence envelope and
frontend session/query owners remain authoritative. No new workflow owner.

Change classes: BACKEND_DOMAIN, BACKEND_API, FRONTEND_UI, FRONTEND_STATE_CACHE,
AUTH_RBAC_SECURITY, EXTERNAL_PROVIDER, PERSISTENCE, CI_TOOLING. Schema additions, if needed,
must retain strict compatibility and receipt/version binding.

Plan: reproduce document guard mismatch; preserve earliest Search blocker through
review/reconciliation; permit only a singleton plausible retained candidate to be
confirmed under creator reauthorization and exact request/case/CLM/automation versions;
retain actor/time/receipt and provider ID without dispatch; test stale/hostile/multiple
candidate and no-replay paths; add frontend/browser regression; update active authority
records; run affected full checks; freeze content for fresh independent review.

Contract reconciliation complete: selectively inspected original XPI guideline/
collection in private/sponsor-artifacts-v2 and historical EDS spec/OpenAPI/Search
structures in private/sponsor-artifacts. XPI has four existing query aliases; EDS
supplies registrationNumber/externalSystemKey and other criteria. The owner explicitly
directed unchanged XPI transport and bounded human CONFIRMED_EXISTING, never a false
provider EXACT_MATCH. EDS runtime replacement is a FUTURE_PROVIDER_FAMILY_DELTA.
No artifact resend or provider-family switch is required/authorized.

Preflight: PowerShell, Python 3.12.10, Node 22.23.3, npm 10.9.9; primary task repository
has .venv and frontend node_modules. Browser/process and disposable Mongo checks use
the existing guarded harnesses. No credentials or provider calls are required.
One implementation writer; independent reviewer writes only its assigned report.
Current source, verified content and reviewed content must be recorded separately.

Current envelope is schema9. Search identity tuples and the optional CLM receipt are
additive, with absent historical evidence unknown. Existing owners/ports/dependency
direction remain unchanged; ADR-007 amendment records the narrowed trust decision.
Browser lifecycle reserves8895/4295. Physical tests use a task-owned mongo:7 container,
loopback27925 and generated allowlisted disposable databases; no clm_poc access.
The confirmation records identity only; continuation is separate or stays at the
earliest remaining blocker. The ledger retains CONFIRMED_EXISTING and skips Shell/
Policy; no supported enrichment means AMEND_NOT_REQUIRED.
Actual Playwright discovery now has60 isolated lifecycle selectors (67 test cases).
The existing CI outer budget grows192->195 minutes for this additional lifecycle;
the per-lifecycle execution deadline remains60 seconds.
