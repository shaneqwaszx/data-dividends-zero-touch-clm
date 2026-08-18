# Integration Handoff

## Current integration posture

The accepted POC is credential-free and Mock-first. Registry may also run through the
local sandbox-shaped HTTP adapter when authorized ACRA configuration is supplied, but
that mode is not evidence of a verified live ACRA contract. The normal sponsor IDP is
the local text-PDF POC provider; ownership and GoldTier remain synthetic/Mock.

External response → strict source DTO → canonical/internal model → target mapper is the
fixed architecture. `ZeroTouchOrchestrator` coordinates interfaces; it contains no
provider scenario branch and should not change when an adapter is replaced.

## Registry

- Interface: `AcraConnector.fetch_company(uen)` in `apps/backend/app/connectors/acra.py`.
- Current adapters: `MockAcraConnector`; `AcraSandboxConnector` with injected transport,
  authorization, and decoder.
- Request: normalized synthetic/project UEN; live operation binding remains Q-012.
- Required response behavior: fresh strict reconstruction, nonblank bounded fields,
  returned/requested UEN equality, UTC retrieval time, and query-free HTTPS provenance.
- Failure mapping: not-found remains distinct; malformed/identity/provenance/transport
  data becomes a sanitized technical result and stops all downstream work.
- Configuration: `ACRA_CONNECTOR_MODE`; sandbox URL/path/timeout/header values are
  backend-only.
- Missing sponsor dependency: Q-012 contract, authorized subscriber access, auth,
  TLS/mTLS/private-CA, error/rate semantics, and approved test UEN.

## IDP

- Interface: `IdpProvider.process(IdpDocumentInput)` in
  `apps/backend/app/connectors/idp.py`.
- Normal sponsor adapter: deterministic network-free `LocalPdfTextIdpProvider`.
  `MockIdpProvider` remains only at the dedicated developer/test fault boundary.
- Input: bounded transient PDF plus `PROVISIONAL_CORPORATE` profile; bytes are not
  stored or returned.
- Output: exactly four typed candidates, independent confidence, explicit missing
  values, and bounded provider/page/source evidence. Output is reconstructed before use.
- Malformed/provider failure: sanitized terminal document/automation failure; no raw
  OCR body or exception text.
- Missing sponsor dependency: Q-003 document types/fields, Q-005 authority/comparison,
  Q-013 privacy/upload/retention, and Q-014 confidence/reviewer policy.

## Ownership

- Interface: `OwnershipProvider.load(OwnershipProviderRequest)` in
  `apps/backend/app/connectors/ownership.py`.
- Current adapter: `MockOwnershipProvider` with source-neutral graphs.
- Contract: bounded parties and owned-legal-entity → owner relationships; Decimal
  percentages; explicit provider/environment/provenance; fresh reconstruction.
- Processing: deterministic unique paths and aggregation; cycles/incomplete chains
  become review without a definitive UBO; malformed graphs fail safely.
- Resume binding: an opaque process-local provider-binding ID preserves adapter choice;
  provider objects/scenario names never enter domain/browser state.
- Missing dependency: Q-002 hierarchy read endpoint/schema/provenance, Q-004 final UBO
  rule, and Q-006/Q-007 related-party/mapping semantics.

## GoldTier / PingFed

- Interface: `GoldTierConnector` in `apps/backend/app/connectors/goldtier.py`.
- Current adapter: credential-free `MockGoldTierConnector`.
- Accepted order: `searchParty`; shell only on explicit `NO_MATCH`; `createPolicy`;
  `amendParty` at `POST /v1/eds/parties/{partyId}/amend`.
- Request metadata: correlation ID, source case ID, and stable per-operation idempotency
  keys. Real authorization is backend-only and must never be logged.
- Response boundary: every return is freshly reconstructed and strictly validated
  before an identifier is used or a later operation starts.
- Failure behavior: existing match stops after search; stage failure stops later calls;
  partial amend becomes review; malformed response fails safely.
- Recovery: Phase 05 records a minimal safe target outcome before rich receipt mapping.
  `RECOVERY_PENDING` re-enters finalization only with the same submission/correlation/
  idempotency identity and never replays target operations.
- Missing dependency: Q-008/D-018 approved environment, sanitized auth reference,
  fresh secret delivery, PingFed details/scopes, network, TLS 1.3/mTLS/private CA, and
  Q-007 Singapore mappings. The quarantined collection is prohibited.

## Live-integration decision gates

### ACRA live-ready — `BLOCKED`

Ready only after authorized subscriber access, confirmed endpoint/schema/errors,
approved authentication, safe TLS requirements, approved test UEN, and adapter
conformance all exist. None may be inferred from the synthetic adapter.

### Ownership hierarchy live-ready — `BLOCKED`

Ready only after Q-002 supplies endpoint, identifiers, graph/schema, pagination,
provenance, and test hierarchy, followed by deterministic conformance.

### GoldTier real-ready — `NOT READY`

Ready only after D-018 containment is cleared, approved sandbox/PingFed material and
fresh credentials are delivered safely, network/TLS 1.3 is verified, minimum Singapore
mappings are confirmed, strict conformance passes, and recovery semantics are tested.

### Ready-for-Approval — `NOT CONFIRMED`

Q-001 must define the four-eye action/state and authorization. Mock submission must not
be relabeled as this transition.

## Correlation and operational handoff

Use the existing correlation/source-case identifiers for safe tracing. Do not log or
export request/response bodies, KYC/PII, authorization headers, credentials, PDF bytes,
or raw provider errors. The current stores, locks, audit events, metrics, target ledger,
and recovery are process-local. A production adapter project must supply durable
transaction/outbox/idempotency, reviewer RBAC, retention, monitoring, and runbooks.
## Phase 08 local document-provider seam

Normal Mock POC composition now uses `IdpProvider -> LocalPdfTextIdpProvider`. It reads
only uploaded text-based synthetic PDFs with `pypdf`, parses the existing provisional
four-field profile deterministically, and exposes minimal extracted/comparison evidence.
It can be replaced by an approved real IDP/OCR adapter without changing
`ZeroTouchOrchestrator`, document semantic evaluation, explicit exception resolution,
or automatic resume. It is not a production IDP integration; Q-003/Q-013/Q-014 remain
open.
