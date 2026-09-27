# ACRA Teammate Contribution Reconciliation

## Scope and authority

This matrix accounts for every ACRA-relevant path and behavior introduced by teammate
commits `4ae4ed19`, `897a4c4`, and `79e808f`. Current source/tests and the accepted
security/provider-governance boundaries take precedence over the historical branch.
BizFile remains `DORMANT`, uncomposed, and runtime-disabled. Its strict sample decoders
are reused behind the separately owned official Mock connector; Q-004 and Q-012 remain
open.

Classification values are exactly `ALREADY_PRESENT_HARDENED`,
`PORT_TO_CURRENT_ARCHITECTURE`, `SUPERSEDED_SECURITY`, `BLOCKED_AUTHORITY`, and
`NOT_APPLICABLE`.

## Complete contribution matrix

| Original path | Commit | Original behavior | Current-main equivalent | Classification / selected action | Reason | Test or evidence |
|---|---|---|---|---|---|---|
| `apps/backend/app/connectors/acra_bizfile_sandbox.py` | `4ae4ed19` | Added HTTPS-bounded base/path/query construction and timeout validation for entity basic information and shareholder operations. | Same dormant connection owner, later security-remediated. | `ALREADY_PRESENT_HARDENED` — retain current owner; add only the bounded business-profile helper from `897a4c4`. | Current code preserves HTTPS, no userinfo/query/fragment base, bounded paths/timeouts, injected transport, and safe errors. | BizFile connection/security tests; accepted `ACRA_BIZFILE_SECURITY_REMEDIATION_QUALITY_GATE.md`. |
| same | `4ae4ed19` | Added no-header authorizer and speculative OAuth/token lifecycle. | `NoAuthAcraAuthorizer` remains; the historical lifecycle was removed by `74a5fd2f`. | `SUPERSEDED_SECURITY` — preserve no-header seam; do not restore the historical token lifecycle. | Its token URL/cache/secret and Bearer behavior were speculative. D-053 permits a separate minimal official-Mock auth foundation only. | Module exposure test; secret scan; accepted BizFile security gate; D-053 auth tests. |
| same | `4ae4ed19` | Added tolerant sample-shaped DTOs for address, dates, constitution, embedded officers, shareholder entities, and withdrawn-holder filtering. | Current strict source DTO boundary and dormant decoders. | `ALREADY_PRESENT_HARDENED` — retain and require exactly one returned entity. | Useful decoding already survived current main; stricter single-entity/requested-UEN binding prevents ambiguous reconstruction. | Focused company/officer/ownership, wrong-identity, missing/multiple-entity tests. |
| same | `4ae4ed19` | Added company/officer/ownership connector calls, HTTP status/transport error mapping, UTC clock, and response decoding. | Current dormant `BizfileMockAcraConnector`. | `ALREADY_PRESENT_HARDENED` — retain current safe transport/error boundary. | Current main already preserves typed safe errors and removes speculative auth. | Focused connector tests and accepted security report. |
| same | `4ae4ed19` | Passed query-bearing request URLs into source provenance. | Canonical ACRA source DTO rejects query-bearing provenance. | `PORT_TO_CURRENT_ARCHITECTURE` — retain request query for transport but strip it from provenance. | UEN/query data must not become retained endpoint provenance. | Query-free provenance test and source DTO validators. |
| same | `4ae4ed19` | Failed the unconfirmed relationship operation as unavailable. | Registry acquisition distinguishes valid empty ownership evidence from transport failure. | `PORT_TO_CURRENT_ARCHITECTURE` — return a strict empty typed relationship result without network traffic. | Absence yields truthful `PARTIAL` if composed directly; no endpoint or derived relationship is invented. | Empty relationship focused test; Phase 10 acquisition rules. |
| `apps/backend/app/composition.py` | `897a4c4` | Composed a new runtime `bizfile_mock` mode with HTTP transport and header authorizer. | Local `mock` and generic `sandbox` are composed; official `api_marketplace_mock` is recognized but fails closed; BizFile is explicitly Dormant. | `SUPERSEDED_SECURITY` — no historical import, factory branch, or runtime activation restored. | Phase 21 and remaining Q-012 authority prohibit activation. | Configuration/composition searches, provider-readiness checker, mode tests. |
| `apps/backend/app/config.py` | `897a4c4` | Added `bizfile_mock` to `ACRA_CONNECTOR_MODE`. | Modes are `mock | api_marketplace_mock | sandbox`; default is Mock and the official lane cannot compose. | `SUPERSEDED_SECURITY` — do not restore the historical setting. | The canonical official-Mock name is distinct from dormant BizFile and remains fail-closed. | `test_acra_modes.py`; provider-readiness registry/checker. |
| `apps/backend/app/connectors/acra_bizfile_sandbox.py` | `897a4c4` | Renamed the entity-basic path field and added a `businessProfile` endpoint constructor. | Entity-basic helper already exists under the current field name; no business-profile operation is composed. | `PORT_TO_CURRENT_ARCHITECTURE` — keep current name; add URL construction only. | The helper is bounded/dormant and makes no request or contract claim. | Business-profile helper/no-call test. |
| same | `897a4c4` | Added OAuth2 client credentials, token cache, guessed token behavior, and bearer injection. | Deliberately removed by `74a5fd2f`; none of its lifecycle or Bearer behavior is restored. | `SUPERSEDED_SECURITY` — not restored. | D-053 confirms only bounded request-side facts and explicitly leaves response, downstream value, access, and activation unresolved. | Historical-code absence, minimal auth-foundation tests, secret scan, Q-012. |
| same | `897a4c4` | Normalized provenance by dropping the UEN query. | Required by current source DTO; missing in the remediated dormant connector before this reconciliation. | `PORT_TO_CURRENT_ARCHITECTURE` — restore query-free provenance for every returned operation. | Preserves safe evidence without changing the transport URL. | Query-free company and empty-operation tests. |
| same | `897a4c4` | Treated HTTP 200 plus explicit empty `entities` as company absence and typed empty officers/ownership parties. | Current decoder otherwise classified empty envelopes as malformed. | `PORT_TO_CURRENT_ARCHITECTURE` — restore operation-specific empty semantics while keeping missing/multiple/malformed envelopes invalid. | Distinguishes valid absence from malformed shape without weakening validation. | Empty-entities and missing/multiple-envelope tests. |
| same | `897a4c4` | Returned an empty relationship payload because no relationship endpoint was known. | Current registry acquisition already models empty mandatory ownership evidence as Partial. | `PORT_TO_CURRENT_ARCHITECTURE` — restore strict typed absence, with no transport call or derivation. | Avoids a false technical outage while claiming no unsupported endpoint. | Focused relationship test; Phase 10 partial-state tests. |
| `apps/backend/app/domain/jurisdiction.py` | `897a4c4` | Expanded the narrow UEN regex to 8-digit, 9-digit, and bounded T/S/R forms. | Current shared predicate still accepted only nine digits plus a letter. | `PORT_TO_CURRENT_ARCHITECTURE` — expand the one shared predicate only. | The assignment authorizes syntax support, not Live validity. All routing/call guards remain shared and backend-owned. | Phase 09 predicate and zero-call tests. |
| `apps/backend/check_acra_connector.py` | `897a4c4` | Added a direct network smoke utility. | Current repository has sanitized provider-readiness tooling but no authorized BizFile smoke. | `BLOCKED_AUTHORITY` — do not restore. | Q-012 and Phase 21 block an external network proof/account claim. | File absence; provider-readiness registry/checker. |
| `apps/backend/debug_acra_raw.py` | `897a4c4` | Printed request URLs and raw provider response bodies for debugging. | Raw provider bodies/URLs are excluded from logs and ordinary evidence. | `SUPERSEDED_SECURITY` — do not restore. | Violates current redaction, privacy, and safe-evidence boundaries. | File absence; secret/security checks; integration-security checklist. |
| `apps/backend/app/connectors/acra_bizfile_sandbox.py` | `79e808f` | Added generic `shareAllotted` parsing plus Garden-specific network fallback and relationship derivation inside the dormant connector. | Existing Mock ACRA is the active synthetic dataset and the existing Decimal engine is the sole calculator. | `PORT_TO_CURRENT_ARCHITECTURE` — retain share counts only in a strict local Garden fixture; emit registry edges at the Mock boundary; do not add generic BizFile inference. | Makes Garden demo-usable without network or provider activation and keeps business services scenario-free. | Garden fixture failure/order/percentage tests; ordinary acquisition/ownership/E2E tests. |
| `apps/backend/app/connectors/garden_business_shareholders.py` | `79e808f` | Added two direct Garden shareholder records and constants `11111999A` / `111111111M`. | New `connectors/garden_business.py` strict local fixture includes the direct and recursive chain. | `PORT_TO_CURRENT_ARCHITECTURE` — adapt and validate as exact Decimal local source evidence. | The historical file omitted the SIM LIM child fixture and lived beside a dormant network adapter; the current owner is the synthetic provider fixture boundary. | Garden fixture shape, withdrawn exclusion, malformed share, duplicate identity, and percentage tests. |
| `apps/backend/tests/test_acra_bizfile_sandbox_connector.py` | `79e808f` | Tested historical Garden network fallback, party order, and percentages. | Current focused BizFile tests plus `test_garden_business_fixture.py`. | `PORT_TO_CURRENT_ARCHITECTURE` — adapt assertions to current Mock acquisition and sole ownership engine. | Reconciles intent without restoring network-dependent special handling. | Focused Garden/BizFile suites. |
| `docs/contracts/OWNERSHIP_UBO_PROFILE.md` | `79e808f` | Documented a Garden-only equal-unit derivation tied to historical D-034. | Current profile had no Garden exception and current D-034 has different meaning. | `PORT_TO_CURRENT_ARCHITECTURE` — add the bounded rule under D-046 with exact results and prohibitions. | Preserves provenance and avoids decision-number collision or legal UBO claim. | Contract checker and documentation review. |
| `docs/decisions/DECISION_LOG.md` | `79e808f` | Added historical D-034 for the Garden demo. | D-034 is now Phase 13 security policy; next ID is D-046. | `NOT_APPLICABLE` — do not restore/renumber historical D-034; record the current decision as D-046. | Decision identities are append-only current authority. | Decision-log inspection and policy-authority checker. |

## Final provider/security state

- ACRA Mock: active/default `MOCK`; Garden is synthetic project data.
- Official API Marketplace Mock: explicit opt-in `MOCK_INTEROPERABILITY_OBSERVED`;
  fixed token/entity/shareholder transport with no fallback.
- Generic sandbox: `PARTIAL`, runtime-disabled.
- BizFile: `DORMANT`, uncomposed, runtime activation false.
- Token request/lifecycle/cache and downstream injection: implemented only in the
  dedicated official Mock owner under D-054; tokens remain memory-only.
- Raw debug-response tooling: absent.
- Q-004 and Q-012: open.
- A bounded authorized official Mock smoke exists; no generic Sandbox, Production, or
  Live smoke was run or authorized.

## 2026-09-24 official-Mock authority update

The current provider-orchestration assignment introduces `api_marketplace_mock` as the
sole canonical name for a distinct official API Marketplace Mock lane; it does not revive
historical `bizfile_mock` or reclassify `ACRA_BIZFILE`. A bounded read-only no-auth GET
to the official entity-query Mock endpoint returned HTTP `401`. This falsifies the old
no-auth runtime assumption; at that evidence revision the required mechanism was still
unknown. The lane remains `MOCK / BLOCKED_AUTHORITY`, with runtime activation disabled
pending Q-012. Historical speculative OAuth/token behavior, guessed static headers,
raw-response tooling, Garden fallback, and Live claims remain prohibited. See
`ACRA_API_MARKETPLACE_MOCK_READINESS.md`, D-050, and the later D-053 refinement below.

## 2026-09-25 official-Mock authentication reconciliation

D-053 partially resolves Q-012 only for the official Mock request-side token facts. The
historical OAuth lifecycle remains superseded: no request method/body, token response,
cache/refresh, Bearer injection, operation call, or fallback was restored. The new
foundation is separate from dormant BizFile and consists only of optional inert backend
credentials, the exact Mock token endpoint/header/lifetime constants, and a pure HTTP
Basic constructor. `api_marketplace_mock` remains `MOCK / BLOCKED_AUTHORITY` and runtime
activation remains disabled.

## 2026-09-26 official-Mock runtime reconciliation

D-054 supersedes the activation conclusion of the two dated updates above without
reviving historical `bizfile_mock`. The dedicated `api_marketplace_mock` owner now has
the exact observed token schema, memory-only renewal cache, raw `token` downstream
header, fixed read-only entity/shareholder operations, strict identity-bound decoders,
and sanitized success evidence. The activation state is
`MOCK_INTEROPERABILITY_OBSERVED`, explicit opt-in only. Garden shareholders were empty;
no synthetic fallback, percentage, or relationship was introduced. BizFile remains
dormant, generic sandbox remains Partial, and Q-012 remains open for the unevidenced
provider/error/relationship and every non-Mock contract.
