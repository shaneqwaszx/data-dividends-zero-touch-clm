# ACRA API Marketplace Mock Runtime — Evidence

No credential, authorization material, token value, raw provider payload, Postman
secret, or unapproved identity value is retained in this record.

## Baseline and configuration

- Branch/base/HEAD/current-main at start:
  `feat/acra-marketplace-mock-runtime` /
  `f7e6f65dbcd927f8357c2876d5b8cf293ff81f18`.
- Start tree clean; `.env` ignored and untracked.
- Actual `.env` line changes: `ACRA_AUTH_HEADER_NAME` and
  `ACRA_AUTH_HEADER_VALUE`, both cleared. Required official-Mock credentials, mode,
  timeout, Live-smoke disablement, and empty smoke UEN were already present/correct.

## Sanitized provider observations

- Token: HTTP 200, JSON, 202 bytes. Exact fields were `access_token` (string),
  `expires_in` (integer), `scope` (string), and `token_type` (string); observed expiry
  was 1,799 seconds.
- Garden entity basic: HTTP 200, JSON, 1,921 bytes; requested/returned identity equal;
  strict decode pass; expected Mock legal name observed.
- SIM LIM shareholders: HTTP 200, JSON, 1,278 bytes; requested/returned identity equal;
  strict decode pass; identity/category/status/share-count evidence present.
- Garden shareholders: HTTP 200, JSON, 15 bytes; explicit empty entities; no official
  Mock Garden ownership chain.
- Capital sample: HTTP 200, JSON, 589 bytes; requested/returned identity equal;
  schema-only observation of currency, issued/paid-up capital, allotted-share, and
  share-type fields for a different supplied Mock identity.
- Dedicated minimized receipt and schema validate successfully.

## Runtime and application evidence

- Token endpoint and API base are fixed to `api-sandbox.bizfile.gov.sg` over HTTPS.
- OS trust-store certificate verification was used; redirects and environment proxy
  trust were disabled; time and response size were bounded.
- One process-level application check composed the real configured official Mock lane.
  Startup passed; source environment was `MOCK`; Garden stopped at
  `REVIEW_REQUIRED / REGISTRY_EXPECTED_DATA_MISSING`; acquisition was `PARTIAL`.
- No synthetic Mock fallback, generic sandbox request, relationship fabrication,
  ownership analysis, or GoldTier call occurred.

## Verification evidence

- Focused ACRA auth/provider/mode and adverse-path tests: pass.
- Phase 09/10 routing/acquisition plus ownership regression selection: pass.
- The clean accepted-main worktree reproduced the exact Phase 13 loopback timeout in 7
  of 20 isolated executions. Safe stack evidence showed a connected client waiting for
  a response while the in-thread Uvicorn loop and AnyIO worker were idle.
- Proxy inheritance, unclosed TestClients, manually supplied listener ownership, and
  Uvicorn-owned binding did not close recurrence. Inspecting the active Uvicorn loop
  factory identified the in-thread Windows Proactor selection as the repository-level
  recurrence generator. A Selector-loop counterfactual passed 20 of 20 executions.
- The permanent test-harness repair explicitly selects `asyncio.SelectorEventLoop` for
  the threaded server. The exact test passed 20 consecutive executions; the containing
  module passed 10 consecutive executions; adjacent/Windows lifecycle tests passed all
  25 cases. There is no skip, retry, arbitrary sleep, timeout inflation, assertion
  weakening, or change to the one-backend/two-seeder contract.
- Three consecutive complete backend runs passed: each collected 1,379 cases and ended
  with 1,344 passed, 35 skipped, and 4 known warnings. Run 1 took approximately 89
  seconds of runner wall time; runs 2 and 3 reported 95.68 and 95.15 seconds.
- The focused final backend/governance selection passed 284 tests. The supported
  non-contract root runner passed 275 tests, and the contract runner passed 44 tests.
- Ruff: pass. Strict mypy: pass for 108 source files. The four initial mypy diagnostics
  reproduced identically on clean accepted main and were repaired with type-only
  enum/Literal annotations.
- Frontend: 23 files / 286 tests pass; TypeScript typecheck and production build pass.
- An initial sandboxed lifecycle selection was invalid because the Windows sandbox
  denied process termination; its host-permission rerun passed. A raw combined root
  pytest invocation was likewise invalid because contract modules require the documented
  contract-runner path setup; each supported runner passed independently.
- Secret scanner coverage is included in the 116-test selection. Direct
  tracked/task-owned secret scan: pass.
- Project-state, architecture, policy, external-provider-readiness, and evidence
  checkers: pass.
- `git diff --check`: pass. Task-owned Markdown whitespace is checked again at freeze.

## Evidence boundary

- Confirmed: bounded official Mock token/entity/shareholder interoperability.
- Project-derived: SG/entity-type normalization and source-to-canonical adaptation.
- Still open: token failure/provider error/not-found schema, rates/retries/service limits,
  complete officer/address/constitution semantics, same-entity compatible capital and
  share-class denominator semantics, relationships/control, and every subscriber
  Sandbox, Production, or Live contract.
- Confidence: B for the bounded official-Mock runtime and provider observations. The
  separately owned baseline lifecycle regression is resolved and repeatably green;
  final status now depends only on the fresh independent Quality Gate.
