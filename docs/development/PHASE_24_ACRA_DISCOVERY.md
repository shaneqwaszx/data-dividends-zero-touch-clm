# Phase 24 official ACRA Marketplace Mock discovery

Session dates: 2026-10-01 and 2026-10-02 (Asia/Singapore). Explicit owner authorization: bounded
read-only official Mock OAuth/entity/shareholder discovery. This is observed Mock
network evidence, never Live or production. Exact per-call timestamps were not retained.
Only sanitized counts, identifiers, statuses and field names are recorded here.

| Run | OAuth attempts | GET attempts | HTTP responses | Result |
|---|---:|---:|---:|---|
| Initial TLS attempt | 1 | 1 | 1 | OAuth 200; Garden read failed before HTTP response |
| Repeated TLS attempt | 1 | 1 | 1 | OAuth 200; Garden read failed before HTTP response |
| Composition-aligned discovery | 1 | 5 | 6 | All HTTP 200; verified Garden identity/people; fallback basic entities empty |
| Unbound supported shareholder inspection | 1 | 3 | 4 | All HTTP 200; strict normalization limits retained |
| Documented additional basic candidates | 1 | 6 | 7 | All HTTP 200; five basic identities, capital sample basic empty |
| Fresh Garden canonical normalization/tagging | 1 | 2 | 3 | All HTTP 200; four role scalars, review required, zero candidates |
| Total | 6 | 18 | 22 | 24 attempts, two initial read transport failures before HTTP response |

The first two harness attempts used a different certificate trust configuration from
composition. The successful run reused the composition's verified platform SSL context
and disabled environment proxy inheritance. Certificate verification stayed enabled;
no TLS bypass, Production, arbitrary URL, mutation, GoldTier or PingFed call occurred.
Tokens stayed in process memory. The retained GoldTier recovery state was never accessed.

A read-only specialist also inspected the public
[ACRA resource centre](https://www.bizfile.gov.sg/apimarketplace/getting-started/resource-centre).
The listing included Business Profile specifications and vocabulary PDFs. That search
did not locate the sample catalogue and made zero provider API requests. Subsequently
the user's October 2 clarification supplied the private local source. A bounded lookup
in the named artifact directory found the matching seven-page sample catalogue
(without the duplicate-download suffix). It was inspected in memory only. No PDF,
private path, body or confidential artifact was copied into repository documentation.

The catalogue supplies candidate discovery only: basic examples include Garden and
the additional UENs below; shareholder examples are `111111111M`, `333333333C` and
`222222222C`; capital example is `111111111K`; owner/partner examples also exist.
It establishes no endpoint/schema, denominator semantics or legal-control policy.
Current responses, strictly bound to the same UEN, remain necessary for conclusions.

| UEN / supported operation | Observation | Interpretation |
|---|---|---|
| Garden `11111999A`, entityBasicInformation (company and officer reads) | Same UEN; BUSINESS_PARTNERSHIP; four people, all OWNER/PARTNER/MEMBER roles | Useful role evidence; neither percentage nor legal/control UBO authority |
| `111111111M`, entityBasicInformation | Explicit entities empty | No canonical entity binding |
| `333333333C`, entityBasicInformation | Explicit entities empty | No canonical entity binding |
| `222222222C`, entityBasicInformation | Explicit entities empty | No canonical entity binding |
| `111111111M`, coShareholdersDetails | One entity; four decoded parties; shareAllotted present | Numerator evidence only, unbound to canonical basic identity; no denominator/percentage |
| `333333333C`, coShareholdersDetails | One entity; member representation lacked the supported shareholder collection | Unsupported shape, not proof of empty membership; candidate now rejects it explicitly |
| `222222222C`, coShareholdersDetails | One entity; shareAllotted/shareholders fields observed; group representation failed strict schema | Unsupported group shape; no invented normalized group or derived percentage |
| `201511222D`, `T13FC1122A`, `T15LL1111W`, `T17LP1111A`, entityBasicInformation | One entity each, same-UEN verified; current classifier yields OTHER | Supported company-shareholder operation not dispatched; no guessed legal-form/mapping upgrade |
| `T19PF1111A`, entityBasicInformation | One same-UEN entity; BUSINESS_PARTNERSHIP | No supported quantitative company ownership method applies |
| `111111111K`, entityBasicInformation | Explicit entities empty | Capital catalogue sample does not bind a canonical basic identity |
| Garden fresh canonical acquisition and analysis | Four ROLE scalars; four OWNER_ROLE tags; ML_RUNTIME_NOT_AVAILABLE; REVIEW_REQUIRED; INCOMPLETE_LEGAL_ENTITY and UBO_REVIEW_REQUIRED; zero candidates | Same-UEN role evidence retained by current owners; no numeric numerator, denominator, percentage or legal UBO |

Garden company shareholders were not queried in this session: its legal form did not
justify that operation. Earlier accepted Garden EMPTY receipts remain historical facts.
No capital operation was called. The supplied example capital UEN `111111111K` could
not be combined with another UEN's shareholder numerator. No fallback met canonical
identity plus compatible class/unit/authoritative denominator requirements.

The private sample source is available and the document-dependent discovery was
performed, not deferred. No documented supported sample yielded sufficient coherent
same-entity quantitative ownership/control evidence. This is the truthful result
per the user's clarification, rather than an invented percentage or legal UBO.
Q-012 still controls new partner/member/group/capital contracts. Official Garden role
evidence was retained/tagged/analyzed in process memory by the candidate's current
canonical owners; only the sanitized result above is retained. Offline synthetic
compatible denominator tests prove arithmetic without claiming network UBOs.
The discovery script remains an explicit opt-in task tool, outside runtime composition.

## D-077 five-layer probe lane (2026-10-23)

`scripts/phase24_acra_mock_discovery.py --lane five-layer-hybrid` is the bounded
owner-run probe for the eight D-077 sample UENs (at most 16 reads; one diagnostic
`111111111M` shareholder read labelled `UNBOUND_NOT_CANONICAL`). The implementing session
did not run it: credential access was not permitted there (`NOT_RUN_CREDENTIALS`), so no
new network observation is recorded and the table above remains the latest observation.
