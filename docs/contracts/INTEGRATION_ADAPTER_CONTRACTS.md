# Integration Adapter Contracts — Phase 06

Phase 06 orchestrates source-neutral provider interfaces. Mock implementations prove
the shapes and outcomes below without claiming equivalence to an unconfirmed live API.

## Registry adapter

Input is a normalized UEN. A successful result supplies a canonical-mappable company
with source system/environment, query-free HTTPS endpoint, and timezone-aware retrieval
time. A valid not-found result is distinct from transport/decoder/authorization error.
The exact subscribed ACRA transport contract remains Q-012.

Provider-returned typed instances remain untrusted. The onboarding service dumps each
result to primitives without serializer warnings, reconstructs a fresh strict nested
`AcraCompanyPayload`, and only then maps it. Required text is nonblank, bounded, and
control-free; retrieval time is timezone-aware UTC; retained provenance must be HTTPS
with a valid host and no userinfo, query, or fragment. The normalized returned UEN must
equal the normalized requested UEN. Wrong identity is a fixed technical
`ACRA_RESPONSE_IDENTITY_MISMATCH`; malformed/bypass-constructed data is
`ACRA_RESPONSE_INVALID`. Neither condition becomes human review or reaches downstream
stages. This query-free rule is a safe retained-reference policy, not an invented live
ACRA endpoint or resolution of Q-012.

The shared ACRA text validator examines every character in the original provider value
for a prohibited Unicode category whose name starts with `C` **before** applying any
trim or normalization. Only control-free input may have ordinary surrounding whitespace
removed. This applies to UEN, entity name/status/type, source environment, country and
endpoint fields, plus block, street, unit, building, postal code, and country in the
nested address. A leading, trailing, or embedded control is malformed provider data;
it cannot be normalized into a trusted value.

## IDP adapter

Input is a validated transient PDF and the provisional corporate profile. Output must
validate as four typed field candidates with independent confidence and safe provider
metadata. Missing values are explicit. Processing errors are typed and sanitized.
Provider output is revalidated before domain use; raw payloads and PDF bytes are not
retained. Real OCR/document types, accuracy, privacy, and reviewer policy remain
Q-003/Q-013/Q-014.

## Ownership adapter

Input contains safe case/registration/display identifiers. Output is a source-neutral,
bounded party/relationship graph with explicit environment provenance. The ownership service reconstructs
and validates that graph, then deterministically distinguishes definitive analysis,
cycle/incomplete review, and provider/shape failure. It does not authorize GoldTier
hierarchy writes. Live hierarchy and UBO semantics remain Q-002/Q-004/Q-006/Q-007.

## GoldTier adapter

Phase 06 calls only the existing Phase 05 connector sequence and contract models:
search, conditional shell create, policy create, and amend. Search must distinguish
`NO_MATCH`, `MATCH_FOUND`, and `FAILURE`; an existing match prevents shell/policy/amend.
Operation results distinguish success, validation failure, and partial success and are
strictly revalidated before acceptance. Request metadata carries correlation, source
case, and UUIDv4 idempotency values. The canonical amend route remains
`POST /v1/eds/parties/{partyId}/amend`.

The Mock connector is credential-free and synthetic. Real PingFed/GoldTier remains
blocked by D-018/Q-008 and cannot be enabled by changing an orchestration scenario.

## Common conformance rules

- Provider selection is dependency injection; generic services contain no scenario
  branching.
- External DTOs never become business-domain authority without validation/mapping.
- Errors crossing API/browser boundaries use fixed safe codes and messages.
- KYC/PII, raw response bodies, credentials, tokens, URLs with queries, and private
  exception text must not enter routine logs, events, or browser responses.
- Conformance tests cover success, absence/incomplete evidence, review outcomes, and
  controlled provider failure for the current Mock adapters. A second local adapter set,
  which does not inherit the Mock implementations, also traverses registry, IDP,
  ownership, readiness, and all four target calls through the full zero-touch service.
- Ownership adapter continuity across a review pause is represented by an opaque,
  process-local binding ID and resolver factory. The generic automation model contains
  neither provider instances nor demo scenario values.
- Replacing a Mock adapter must preserve these semantic outcomes; live verification
  requires the authoritative sponsor contract and authorized environment.
