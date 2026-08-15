# Provider Replacement Guide

## The seam

```text
ZeroTouchOrchestrator
  +-- AcraConnector ------ MockAcraConnector / AcraSandboxConnector / future approved ACRA
  +-- IdpProvider -------- MockIdpProvider / future approved OCR-IDP
  +-- OwnershipProvider -- MockOwnershipProvider / future hierarchy adapter
  `-- GoldTierConnector -- MockGoldTierConnector / future PingFed-GoldTier adapter
```

Generic stage order, document assessment, Decimal ownership calculation, readiness,
and target recovery remain unchanged.

## Replacement procedure for every provider

1. Implement the existing protocol in `apps/backend/app/connectors/`.
2. Create dedicated external request/response DTOs; never pass provider payloads into
   business services.
3. Validate transport status, size/content type, shape, semantic minimums, identity,
   environment, provenance, and timestamps; reconstruct typed returns from primitives.
4. Map only validated facts into existing source-neutral/domain models.
5. Add unit and adversarial conformance tests, including malformed/mutable typed output,
   timeout/error mapping, case isolation, and prohibited later calls.
6. Add explicit configuration and fail closed when it is absent. Secrets stay
   backend-only and outside tracked files.
7. Select the adapter in `apps/backend/app/composition.py`; do not branch in
   `ZeroTouchOrchestrator`.
8. Run the full UAT/regression/security matrices and preserve environment labels.

## Exact implementation locations

| Provider | Protocol | Existing composition | Future implementation location |
|---|---|---|---|
| Registry | `connectors/acra.py` | `composition.build_acra_connector` | New approved connector/decoder/authorizer beside `acra_sandbox.py` |
| IDP | `connectors/idp.py` | `composition.build_document_processing_service` | New provider beside `mock_idp.py` |
| Ownership | `connectors/ownership.py` | `composition.build_ownership_analysis_service` | New provider beside `mock_ownership.py` |
| GoldTier | `connectors/goldtier.py` | `composition.build_onboarding_service` | New transport/auth connector beside `mock_goldtier.py` |

Phase 06 alternate-adapter tests in
`apps/backend/tests/test_phase06_provider_conformance.py` prove that independent local
implementations can traverse the full path without inheriting Mock classes.

## Provider-specific gates

- ACRA: Q-012 and authorized access.
- IDP: Q-003/Q-005/Q-013/Q-014.
- Ownership: Q-002/Q-004/Q-006/Q-007.
- GoldTier: Q-008/D-018, Q-007, TLS 1.3, and Q-001 for the later approval transition.

Until each gate is satisfied, keep the corresponding execution label `MOCK` or the
specifically verified `SANDBOX`; never expose it as `LIVE`.
