# External Provider Activation Contract

## Status and owner

This is a readiness boundary for future authorized integration work. The provider
readiness registry owns transport/authority/evidence state; the policy-authority
registry owns sponsor business-policy activation. A registry row is not a contract,
credential, sandbox grant, interoperability result, or Live claim.

Current provider classifications and activation state are machine-checked by
`scripts/check_external_provider_readiness.py`. No row may advance because a setting,
credential, tool, placeholder, Mock test, or documentation example exists.

## State meanings

- `INTERNAL_POC_ONLY`: the current Mock or Local POC path is explicitly bounded to
  internal synthetic behavior. It is not sandbox or Live evidence.
- `BLOCKED`: authority, implementation, access, or security prerequisites are missing.
- `BLOCKED_AUTHORITY`: a bounded sanitized observation exists, but it falsified or could
  not establish a required authority assumption. Runtime activation remains disabled
  until the API owner supplies the missing contract or security decision.
- `MOCK_INTEROPERABILITY_OBSERVED`: an official provider Mock has an explicitly
  authorized, bounded, schema-valid runtime path and sanitized success evidence. It is
  selectable only as Mock and supplies no Sandbox, Production, or Live claim.
- `PARTIAL_SCAFFOLD_ONLY`: authority-independent seam or dormant code exists; it cannot
  be used to infer transport, mapping, auth, retry, or provider success.
- `SANDBOX_PARTIAL`: an explicitly selected sandbox adapter and bounded sanitized
  observations exist, but contract, mapping, business-policy, mutation, or production
  authority remains incomplete. Runtime selection is allowed only for the bounded
  sandbox path; this state is neither `SANDBOX_VERIFIED` nor Live evidence.
- `READY_FOR_AUTHORIZED_SANDBOX_PROOF`: all documented prerequisites are approved and
  access is available, but no sandbox execution evidence has yet been accepted.
- `SANDBOX_VERIFIED`: an authorized execution has passed the contract/security/evidence
  chain. This never implies Live interoperability.
- `LIVE_VERIFIED`: separate explicit Live authorization and sanitized Live evidence
  have been reviewed. No current provider is in this state.

## Evidence chain

### ACRA

`BLOCKED/PARTIAL_SCAFFOLD_ONLY` → authoritative subscriber contract and access →
contract reconciliation → approved auth/TLS requirements → out-of-repository secret
delivery → strict DTO and mapper conformance → authorized synthetic sandbox smoke →
sanitized evidence → integration-security review → independent QG →
`SANDBOX_VERIFIED`.

Q-012 must supply the approved environment/base URL, operation paths, request/response
schemas, remaining token response/error and downstream-value semantics, not-found/error
semantics, timeout/rate/retry rules, TLS/mTLS/private-CA requirements,
subscription/access, approved test UEN, and secret-delivery mechanism. BizFile remains
dormant until a separately authorized provider change.

The official API Marketplace Mock is tracked separately as
`ACRA_API_MARKETPLACE_MOCK / api_marketplace_mock / MOCK`. Supplied Postman exports and
the explicitly authorized 2026-09-26 bounded run establish the exact Mock token request,
strict token response, raw `token` downstream header, and successful entity/shareholder
interoperability for approved Mock identities. The lane is therefore
`MOCK_INTEROPERABILITY_OBSERVED` and explicit opt-in runtime composition is allowed.
Tokens are memory-only, redirects are disabled, certificate verification remains on,
and no generic-sandbox or synthetic fallback exists. Garden shareholder data was
explicitly empty and capital/share-class evidence did not establish a compatible
ownership denominator, so relationship acquisition remains partial. This is neither
Sandbox nor Live. `docs/integration/ACRA_API_MARKETPLACE_MOCK_READINESS.md` is the
bounded evidence summary. Local Mock remains default, generic sandbox remains Partial,
and BizFile remains Dormant.

### GoldTier and PingFed

The sponsor-supplied XPI dialect is `SANDBOX_PARTIAL`. The bounded Singapore path uses
`registrationType=ACRA`, unchanged UEN, both country fields `SG`,
`customerExternalSystem=DSD`, `policy=Singapore`, and
`bookingEntity=ANZBGL (Singapore Branch)`. The corrected standalone OpenAPI 1.0.0 is
the current machine-vocabulary authority for the exact 17 KYC Customer Types and 23
Client Segments; older conflicting lists are quarantined rather than unioned. KYC type
and segment are validated write-once case selections with `USER_AUTHORIZED_POC`
authority. Optional unconfirmed `accountEntityType` and `productType` serialize empty.
Sandbox completion requires ledger-owned Search/readback by retained GoldTier ID and exact
ID equality. D-063 permits AMEND_NOT_REQUIRED when no supported reviewed enrichment exists;
Mock D2 continues to require Amend. Historical attempted/failed Amend evidence remains unchanged. Related-party mutation remains blocked by child-ID lifecycle and
relationship-authority gaps. The adapter is not PingFed or production authentication.

Promotion beyond this bounded state remains: unresolved contract and business authority
→ approved secret delivery → complete Singapore mappings and exact operations →
authorized mutation proof where permitted → sanitized evidence → security review →
independent QG → `SANDBOX_VERIFIED`. Production/Live activation separately requires
Q-008/D-018 containment and rotation/revocation proof, the PingFed token contract,
scopes/client authentication, and separate Live evidence.

Q-001, Q-007, Q-009, Q-010, Q-011, and Q-018 remain dependent XPI/production gates;
Q-008/D-018 remain production/PingFed gates. The existing target ledger remains the
sole call-order and no-replay owner. XPI sandbox selection never consumes the future
PingFed placeholders and has no Mock fallback.

### Ownership hierarchy and vendor IDP/OCR

An external ownership/hierarchy provider requires authoritative hierarchy retrieval and
write semantics, mappings, security, and Q-002/Q-004/Q-006/Q-007 evidence. The local
Decimal graph engine remains the only current ownership calculation owner.

A vendor IDP/OCR provider requires authoritative document scope, extraction contract,
data handling, auth/TLS, and Q-003/Q-005/Q-013/Q-014 evidence. Local PDF/text
extraction is not vendor OCR.

## Security and failure boundary

Secrets are delivered by the owner through an approved mechanism outside Git, docs,
issues, PRs, logs, screenshots, fixtures, and browser fields. Consumption is backend
only and least-privilege. Certificate verification is always on; no TLS-disable flag,
wildcard bypass, or uncontrolled redirect is permitted. GoldTier real transport must
verify TLS 1.3. mTLS/private CA is added only when authoritative. Missing or uncertain
auth, contract, mapping, timeout, retry, idempotency, or error authority fails closed.
No Mock fallback may hide a failed external call.

## Promotion evidence

Every future observation uses the strict sanitized profile in
`external_provider_evidence.schema.json`. Evidence profile v2 accepts only finite
provider/operation/category/reference vocabularies, canonical UUID identifiers, and a
control-free, calendar-valid UTC instant. The schema and Python validator apply the
same identifier/timestamp language, including leap-year rules and rejection of line
terminators. Direct and imported JSON loaders reject duplicate keys with a constant
diagnostic that cannot echo an attacker-controlled key. The profile has no free-text,
path, URL, map, request, response, header, query, body, payload, or error field. Tokens,
secrets, headers, raw bodies, provider errors, customer/KYC data, PDF bytes, and
secret-bearing URLs therefore have no legitimate representation in the artifact.
Sandbox evidence cannot promote a row to `LIVE_VERIFIED`; Live requires a separate
approved environment, authorization, execution, and review record.

Profile v2 also binds whole records to current provider truth. `ACRA_MOCK`,
`IDP_LOCAL_PDF_TEXT`, `OWNERSHIP_LOCAL_ENGINE`, and `GOLDTIER_MOCK` have accepted
credential-free profiles. Its existing `ACRA_API_MARKETPLACE_MOCK` auth-failure profile
remains valid only for that historical failure category. Successful official Mock
operation evidence uses the stricter dedicated
`acra_api_marketplace_mock_evidence.schema.json` receipt, which permits only fixed safe
operation metadata and no credential, query value, header, raw payload, or error text.
Each profile fixes
the compatible mode, classification, operation, outcome, contract, certificate/auth
label, mapping, and call-order category. All sandbox, dormant, future, and real providers
have no accepted evidence profile; adding one requires explicit authority plus a reviewed
schema/validator change.
