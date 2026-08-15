# Adapter Conformance Checklist

Apply this checklist to Registry, IDP, Ownership, and GoldTier adapters before changing
composition. Record evidence per item; a protocol implementation alone is insufficient.

## Common trust boundary

- [ ] Exact request identity is bound to the response/case.
- [ ] External objects, including prevalidated/mutable typed instances, are converted to
  primitives and freshly reconstructed.
- [ ] Required text is nonblank, bounded, control-free, and grammar/enum validated.
- [ ] Response size/count/depth and timestamps are bounded and valid.
- [ ] Absence/not-found is distinct from timeout, authorization, malformed, and business
  review outcomes.
- [ ] Timeout/transport/provider errors map to fixed safe codes/messages.
- [ ] Provenance is validated, minimized, and appropriate to `MOCK`, `SANDBOX`, or `LIVE`.
- [ ] Raw bodies, PDF bytes, KYC/PII, credentials, headers, endpoints with secret/query
  data, and exception text do not enter logs/events/API/browser/export.
- [ ] Cases and provider selections remain isolated under concurrency.
- [ ] Deterministic local success, absence, malformed, failure, and mutable-output tests
  pass.
- [ ] Missing configuration fails closed before a call.

## Registry additions

- [ ] Requested/returned UEN equality is enforced.
- [ ] HTTPS query-free retained provenance and UTC sourcing time are enforced.
- [ ] Not-found and malformed identity stop document/ownership/target work.
- [ ] Redirect, content type/body size, timeout, TLS, and authorization behavior match
  the authoritative subscriber contract.

## IDP additions

- [ ] File type/size/name/signature/EOF and approved production PDF controls are applied.
- [ ] Output matches the sponsor-approved document/field profile.
- [ ] Confidence and missing values remain per field and never approve a case.
- [ ] Bytes and raw output follow approved retention/deletion rules.

## Ownership additions

- [ ] Root identity, party/edge uniqueness, legal-entity parent orientation, percentages,
  limits, provenance, cycle, and incompleteness are validated.
- [ ] Decimal path arithmetic and unique-path aggregation remain authoritative.
- [ ] No incomplete/cyclic/limited graph creates a definitive UBO.

## GoldTier/PingFed additions

- [ ] Search is first and only explicit `NO_MATCH` permits shell creation.
- [ ] Correlation/source-case/idempotency headers and required scopes are correct.
- [ ] TLS 1.3/certificate verification and confirmed mTLS/private-CA rules pass; no bypass.
- [ ] Tokens/secrets remain backend-only and are never logged.
- [ ] Each response is strictly validated before a later call.
- [ ] Safe retry rules distinguish read/transient behavior from side-effect replay.
- [ ] Existing party, policy failure, partial amend, malformed response, and retained-
  outcome recovery produce the exact required/prohibited call prefixes.
- [ ] Durable production idempotency/outbox behavior is defined before multi-process use.

## Required evidence

- Unit/contract tests for the adapter DTO/decoder.
- Full-path provider-conformance tests through zero-touch orchestration.
- Phase 07 UAT evidence and Phase 01–06 regression results.
- Secret scan and integration-security review.
- Authorized sandbox smoke result, labeled `VERIFIED`, before any live-ready claim.
