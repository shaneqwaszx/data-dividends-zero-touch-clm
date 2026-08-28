# Phase 09 — Jurisdiction Decision Gateway and ACRA Foundation

## Purpose and boundary

Phase 09 places a source-aware jurisdiction decision before registry acquisition. It
does not add a foreign registry, change ACRA connector mode selection, move document
processing ahead of registry acquisition, or change ownership, UBO, GoldTier, or
Ready-for-Approval policy.

## Implemented flow

```text
Onboarding request
  |-- optional country_of_incorporation (SG/AU/MY/HK)
  `-- bounded registration identifier / UEN
          |
          v
Jurisdiction observations
  |-- USER_INPUT (only when supplied)
  `-- IDENTIFIER_FORMAT (SG only for accepted 9-digits-plus-letter UEN)
          |
          v
JurisdictionResolver
  |-- no observations -----------------> JURISDICTION_UNRESOLVED
  |-- all observations agree ----------> resolved jurisdiction
  `-- observations disagree -----------> JURISDICTION_CONFLICT
                                              |
                         resolved jurisdiction only
                                              v
RegistryProviderRouter
  |-- SG ------------------------------> accepted Singapore UEN eligibility
  |                                         |-- invalid -> controlled Registry blocker
  |                                         `-- valid -> AcraRegistryProviderAdapter
  `-- AU / MY / HK --------------------> REGISTRY_PROVIDER_NOT_IMPLEMENTED
                                              |
                                     Singapore only
                                              v
existing strict ACRA DTO -> requested-UEN binding -> canonical entity -> validation
                                              |
                         existing document / ownership / readiness / Mock GoldTier flow
```

Every outcome creates a retrievable process-local case. Unresolved, conflicting, and
provider-not-implemented outcomes, plus an SG identifier that is not eligible for the
current ACRA path, are controlled `REVIEW_REQUIRED` / zero-touch
`WAITING_FOR_REVIEW` states at the Registry stage. They expose no resolution action
because source precedence and reviewer authority are not sponsor-confirmed.

## Jurisdiction evidence model

`JurisdictionObservation` retains the recognised jurisdiction, evidence source, UTC
observation time, bounded safe evidence reference, and optional confidence. Confidence
is unused by the two active deterministic sources.

The enum also names future `EXISTING_CASE`, `DOCUMENT_IDP`, and `UPSTREAM_SYSTEM`
sources so their evidence can be represented later. Phase 09 does not populate those
sources and does not silently order them. Resolution is set-based: agreement resolves;
disagreement is a conflict. No source wins because of its type or insertion order.

The omitted-input compatibility rule is explicit and auditable. A request with no
country and a registration identifier matching the accepted Singapore UEN format
creates `IDENTIFIER_FORMAT -> SG`; it is not a hidden default. A non-matching identifier
with no country remains unresolved.

The generic intake grammar remains intentionally broader for recognised foreign
registration identifiers. After Singapore is resolved and ACRA is selected, the
service applies the same accepted nine-digits-plus-letter UEN predicate used for
identifier-format evidence and canonical validation. The ACRA adapter repeats that
single shared predicate at its own boundary, so direct internal adapter use also stops
before `AcraConnector.fetch_company`.

## Registry provider boundary

`RegistryProvider` returns a source-neutral `CanonicalLegalEntity`. The Singapore
adapter wraps the existing `AcraConnector`, reconstructs `AcraCompanyPayload` with the
strict source DTO, requires the returned UEN to match the request, then invokes the
existing ACRA mapper. Existing mock/sandbox composition remains inside
`build_acra_connector`; the router neither reads user-provided URLs nor dynamically
loads code.

| Resolved jurisdiction | Decision | Provider call |
|---|---|---|
| `SG` | `SELECTED` / `ACRA` | Existing configured ACRA connector |
| `AU` | `PROVIDER_NOT_IMPLEMENTED` | None |
| `MY` | `PROVIDER_NOT_IMPLEMENTED` | None |
| `HK` | `PROVIDER_NOT_IMPLEMENTED` | None |

Recognition does not claim that ASIC, SSM, Companies Registry, or another foreign
provider is integrated or sponsor-approved.

## API and browser contract

Case-creation requests accept optional `country_of_incorporation` and a bounded
registration identifier in the existing `uen` property for compatibility. Browser
case responses include the jurisdiction resolution, retained observations, safe
evidence references, and provider routing decision. Internal ACRA endpoint provenance,
credentials, connector class names, and raw payloads remain excluded.

The browser offers Not specified, Singapore, Australia, Malaysia, and Hong Kong.
Foreign options state that their provider is not implemented. The backend is the only
routing authority. A registry-stage blocker prevents the combined UI journey from
uploading the selected PDF and the backend document endpoint returns the unchanged
blocked case without invoking IDP.

## State, stopping, and recovery

| Outcome | Case state | Zero-touch state | ACRA | IDP | Ownership | GoldTier |
|---|---|---|---:|---:|---:|---:|
| SG resolved and registry valid | `VALIDATED` | `PENDING_INPUTS` at Document | 1 | 0 until upload | 0 | 0 |
| Unknown jurisdiction | `REVIEW_REQUIRED` | `WAITING_FOR_REVIEW` at Registry | 0 | 0 | 0 | 0 |
| Conflicting jurisdiction | `REVIEW_REQUIRED` | `WAITING_FOR_REVIEW` at Registry | 0 | 0 | 0 | 0 |
| Foreign provider unimplemented | `REVIEW_REQUIRED` | `WAITING_FOR_REVIEW` at Registry | 0 | 0 | 0 | 0 |
| SG identifier not eligible for ACRA | `REVIEW_REQUIRED` | `WAITING_FOR_REVIEW` at Registry | 0 | 0 | 0 | 0 |

These registry exceptions have no pause/resume action in Phase 09. A later phase needs
sponsor-confirmed evidence authority, reviewer permissions, and durable persistence
before implementing a resolution workflow. Existing ACRA technical failures retain
their terminal, sanitized infrastructure behavior.

## Persistence and scope limitations

Jurisdiction evidence and routing decisions are stored only with the existing
process-local `OnboardingCase`. Phase 09 does not adopt the connectivity-only MongoDB
module and adds no migration. Restart still clears cases.

See [ACRA_MOCK_API_PROFILE.md](../contracts/ACRA_MOCK_API_PROFILE.md) for the exact
company data available after Singapore routing.
