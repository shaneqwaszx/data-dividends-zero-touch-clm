# Phase 21 Provider Activation Packet

This packet is for the Delta Capita sponsor/API and integration owners. Please supply
sanitized authority and arrange secret delivery through the approved out-of-repository
channel. Do not email, commit, paste into an issue/PR, or place secret values in this
packet.

Current amendments below distinguish later observed Mock/Sandbox facts from the historical
Phase21 activation boundary. They do not authorize new access, writes or Production promotion.

## A. ACRA

Already implemented: Mock ACRA is the default; a generic HTTPS sandbox-shaped seam is
Partial and preserves verified certificates, bounded timeout, controlled redirects,
safe provenance, request-UEN binding, strict DTO reconstruction, sanitized errors, and
downstream call stopping.

Current classification/state: `ACRA_MOCK` is `MOCK / INTERNAL_POC_ONLY`.
`ACRA_GENERIC_SANDBOX` is `PARTIAL / PARTIAL_SCAFFOLD_ONLY`; it is not Live.

Missing material: Q-012 authoritative subscriber contract/access, approved environment
and base URL, paths, request/response schemas, auth, not-found/error semantics,
timeout/rate limits, TLS/mTLS/private-CA rules, subscription, approved synthetic test
UEN, and secret-delivery process.

Required sanitized artefacts: contract reference/version, field/enum/error mapping,
TLS/auth policy reference, approved test-case reference, and an authorized sandbox
smoke receipt with no raw response or customer data.

Required secret action: deliver any credential or certificate only through the approved
backend secret mechanism after owner-confirmed authorization and rotation policy.

What we will implement: reconcile authority, strict source DTO/decoder/mapper tests,
bounded connector behavior, redacted errors, and authorized evidence if the parent task
explicitly reauthorizes runtime integration.

The separate official ACRA Marketplace Mock is MOCK / MOCK_INTEROPERABILITY_OBSERVED:
bounded token request/strict response/raw-token header and approved operation observations
are established. Synthetic Mock and official Mock namespaces remain separate.
Cannot claim subscriber/Production OAuth, generic sandbox success, Live ACRA, Dormant BizFile
runtime, pagination/retries or mappings not supplied by authority.

## B. GoldTier

Already implemented: `MockGoldTierConnector`, ordered target operations, one target
ledger, safe outcome projection, no-replay recovery semantics, and an explicit XPI
sandbox adapter with strict request mapping and bounded safe response projection.

Current classification/state: `GOLDTIER_MOCK` is `MOCK / INTERNAL_POC_ONLY`.
`GOLDTIER_XPI` is `PARTIAL / SANDBOX_PARTIAL`; `GOLDTIER_REAL` is
`NOT_IMPLEMENTED / BLOCKED`.

Missing material: Q-008/D-018 containment and rotation/revocation proof, sanitized auth
reference, approved environment/base URL, exact operation contracts, Singapore mappings,
enum/casing/mandatory fields, error/idempotency/recovery rules, network access, and
Q-001/Q-007/Q-009/Q-010/Q-011/Q-018 authority.

Required sanitized artefacts: corrected operation contract references, mapping/version
references, TLS 1.3 and network policy, authorized test-case receipt, and security
review evidence.

Required secret action: supply fresh least-privilege material only through the approved
out-of-repository backend delivery mechanism after quarantine material is revoked or
rotated.

What remains: obtain sponsor-authoritative target-policy values and remaining mapping,
relationship and child-ID lifecycle decisions before any further mutation proof. Mock
remains the default; XPI is selected only by explicit sandbox configuration and
preserves ledger ownership.

Bounded D-056/D-062 POC mappings/workflow clarifications are recorded.
Cannot claim Live/production GoldTier, universal production mappings, approval,
Ready-for-Approval, OAuth flow, token cache, retries, mTLS, or Mock fallback.

## C. PingFed

Already implemented: no adapter or token acquisition; future placeholders are
unconsumed.

Current classification/state: `PINGFED_AUTH` is `NOT_IMPLEMENTED / BLOCKED`.

Missing material: Q-008/D-018 rotation/revocation, approved token URL, scopes, client
authentication method, TLS/network/private-CA requirements, secret delivery and test
authorization.

Required sanitized artefacts: auth contract/reference, scope and certificate policy
references, and sanitized authorized sandbox outcome categories.

Required secret action: approved backend-only fresh credential delivery after
containment is verified.

What we will implement: a narrow provider-auth seam only after explicit reauthorization
and a complete contract; no generic OAuth assumptions.

Cannot claim: token retrieval, scopes, client-credentials flow, token caching, or
authenticated target connectivity.

## D. Hierarchy/ownership provider

Already implemented: local deterministic Decimal graph analysis is the sole current
ownership calculation owner; related-party creation remains bounded and unexecuted.

Current classification/state: `OWNERSHIP_LOCAL_ENGINE` is `LOCAL / INTERNAL_POC_ONLY`;
`OWNERSHIP_HIERARCHY_FUTURE` is `NOT_IMPLEMENTED / BLOCKED`.

Missing material: Q-002/Q-004/Q-006/Q-007 hierarchy retrieval/write contract, mappings,
authority, security and test data.

Required artefacts/action: sanitized contract and mapping references, synthetic test
case, approved access, and no raw ownership/KYC payload.

What we will implement: only an explicitly authorized extension through the existing
ownership/provider boundaries after reconciliation.

Cannot claim: external ownership service, legal UBO result, multi-level hierarchy
creation, or sponsor-approved relationship semantics.

## E. Vendor IDP/OCR

Already implemented: LocalPdfTextIdpProvider is the normal sponsor POC path; Mock is a
fault/demo boundary only.

Current classification/state: `IDP_LOCAL_PDF_TEXT` is `LOCAL / INTERNAL_POC_ONLY`;
`VENDOR_IDP_FUTURE` is `NOT_IMPLEMENTED / BLOCKED`.

Missing material: Q-003/Q-005/Q-013/Q-014 document scope, extraction schema, confidence,
data handling/retention, auth/TLS, approved provider access and test documents.

Required artefacts/action: sanitized contract/data-handling references and synthetic
test-case evidence; deliver credentials only through the approved backend channel.

What we will implement: a provider adapter/decoder only after authoritative contract,
security review and explicit scope authorization.

Cannot claim: vendor OCR, production document processing, or external extraction.

## F. Production deployment and handoff

Already implemented: local/sandbox-shaped POC architecture, explicit modes, safe
provenance and target-ledger ownership.

Current classification/state: production Zero-Touch/GoldTier handoff is blocked by
Q-018 and the dependent provider/policy gates.

Missing material: deployment topology, ownership/support model, observability and
retention, network/secrets/certificates, incident/recovery runbooks, production
authorization, and the exact approval/handoff boundary.

Required artefacts/action: sanitized deployment/security runbook references and an
approved synthetic end-to-end test plan; no production credential or customer data in
repository evidence.

What we will implement: a separately assigned deployment/integration phase after
provider and policy authority is recorded and independently gated.

Cannot claim: production readiness, Live interoperability, autonomous/final approval,
or operational handoff.
