# ACRA API Marketplace Mock Runtime — Task Intent

## Requested outcome

Activate the existing `api_marketplace_mock` lane as a bounded official ACRA API
Marketplace Mock runtime, using only the authorized Mock token endpoint and read-only
EIQ GET operations. Preserve strict source-to-canonical mapping, fail-closed ownership
behavior, secret containment, and truthful Mock classification.

## Scope and non-goals

- In scope: Postman contract reconciliation; one sanitized token observation; Mock-only
  token client/cache; entity-basic and shareholder GETs; strict decoders; composition;
  network-free tests; bounded authorized Mock smoke; sanitized evidence; `.env` ACRA
  keys only; startup/application verification; Q-012/current-state updates.
- Non-goals: Production/Live ACRA; `api.bizfile.gov.sg`; mutations, purchases, account
  operations, GoldTier/PingFed calls; Bearer downstream auth; synthetic fallback;
  speculative ownership percentages; new registry/ownership/business-rule owner.

## Identity and change classes

- Repository: `C:\Users\shane\Desktop\FYP\data-dividends-zero-touch-clm`
- Branch: `feat/acra-marketplace-mock-runtime`
- BASE/HEAD/origin-main at start: `f7e6f65dbcd927f8357c2876d5b8cf293ff81f18`
- Start tree: clean; `.env` ignored and untracked.
- Classes: `EXTERNAL_PROVIDER`, `AUTH_RBAC_SECURITY`, `BACKEND_DOMAIN`.

## Baseline read set and authority

Read: `AGENTS.md`; development/branch/Codex workflows; architecture/project state;
open questions; ACRA mapping/Mock profile/provider activation contracts; decision log
ACRA entries; Phase 21 plan; existing ACRA auth, connector, configuration, composition,
and focused tests; repository phase/provider/security skills and checklist. The explicit
user assignment is the bounded implementation authority and supersedes the prior
no-token-request limitation for the official Mock host only.

## Impact and risk hints

The change crosses an external authentication and untrusted-payload boundary. Primary
risks are secret/token leakage, Production-host drift, unsafe redirects/TLS bypass,
Bearer substitution, cross-mode fallback, ambiguous identity decoding, and invented
share-denominator semantics.

## Execution Readiness View

- Intent lock: official Mock retrieval, never Production/Live.
- Scope fence: fixed host, one token POST, bounded read-only EIQ GETs.
- Owner lock: existing ACRA connector/composition boundary and existing Decimal UBO
  engine remain owners.
- Compatibility boundary: local synthetic `mock` and generic `sandbox` stay separate.
- Retirement boundary: replace only the fail-closed activation behavior, not the
  dormant decoder wholesale or generic-sandbox settings.
- Verification: focused auth/provider/mode tests, affected backend/regression/contract/
  governance/security checks, startup, sanitized smoke, independent QG.
- Stop/rewind: stop dependent mapping on schema contradiction or absent ownership
  denominator; never weaken call stopping to complete a demo.
